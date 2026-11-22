#!/bin/bash
# BARA UTVECKLING. Lägger in testanvändarna i dev/testanvandare.json i realmen
# recepta. Körs av tjänsten dev-seed i compose.yaml och får aldrig köras i drift.
set -euo pipefail

KCADM=/opt/keycloak/bin/kcadm.sh
CONFIG=/tmp/kcadm.config

"$KCADM" config credentials --config "$CONFIG" --server "$KEYCLOAK_URL" --realm master \
  --user "$KEYCLOAK_ADMIN" --password "$KEYCLOAK_ADMIN_PASSWORD" >/dev/null

# Återanrop och adress efter utloggning följer RECEPTA_WEB_URL. Så går det att
# byta mellan http och https (compose.https.yaml) utan att tömma databasen.
CLIENT=$("$KCADM" get clients --config "$CONFIG" -r recepta -q clientId=recepta-web --fields id --format csv --noquotes)
"$KCADM" update "clients/$CLIENT" --config "$CONFIG" -r recepta \
  -s "rootUrl=$RECEPTA_WEB_URL" \
  -s "redirectUris=[\"$RECEPTA_WEB_URL/api/auth/callback\"]" \
  -s "attributes.\"post.logout.redirect.uris\"=$RECEPTA_WEB_URL/"
echo "Sajtens adress i realmen: $RECEPTA_WEB_URL"

# Ingen HSTS lokalt. Webbläsaren sparar HSTS per värdnamn, inte per port: en
# sådan rubrik från https://localhost:8444 skulle tvinga https på allt annat
# som körs på localhost. I drift ska rubriken finnas kvar (realmens förval).
for REALM in recepta master; do
  "$KCADM" update "realms/$REALM" --config "$CONFIG" -s 'browserSecurityHeaders.strictTransportSecurity='
done

# Roller som har tillkommit efter att realmen skapades. Realmfilen läses bara in
# när realmen saknas, så en befintlig utvecklingsdatabas får dem här.
for ROLE in coach; do
  if ! "$KCADM" get "roles/$ROLE" --config "$CONFIG" -r recepta >/dev/null 2>&1; then
    "$KCADM" create roles --config "$CONFIG" -r recepta -s "name=$ROLE" >/dev/null
    echo "Rollen $ROLE är tillagd."
  fi
  # Rollen ska följa med i token till recepta-web. Att lägga till den igen ändrar inget.
  ROLE_JSON=$("$KCADM" get "roles/$ROLE" --config "$CONFIG" -r recepta --fields id,name)
  "$KCADM" create "clients/$CLIENT/scope-mappings/realm" --config "$CONFIG" -r recepta -b "[$ROLE_JSON]" >/dev/null
done

"$KCADM" create partialImport --config "$CONFIG" -r recepta -o -f /dev-seed/testanvandare.json
echo "Testanvändare för utveckling är inlagda (befintliga lämnas orörda)."
