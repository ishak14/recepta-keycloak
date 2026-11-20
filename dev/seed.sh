#!/bin/bash
# BARA UTVECKLING. Lägger in testanvändarna i dev/testanvandare.json i realmen
# recepta. Körs av tjänsten dev-seed i compose.yaml och får aldrig köras i drift.
set -euo pipefail

KCADM=/opt/keycloak/bin/kcadm.sh
CONFIG=/tmp/kcadm.config

"$KCADM" config credentials --config "$CONFIG" --server "$KEYCLOAK_URL" --realm master \
  --user "$KEYCLOAK_ADMIN" --password "$KEYCLOAK_ADMIN_PASSWORD" >/dev/null

"$KCADM" create partialImport --config "$CONFIG" -r recepta -o -f /dev-seed/testanvandare.json
echo "Testanvändare för utveckling är inlagda (befintliga lämnas orörda)."
