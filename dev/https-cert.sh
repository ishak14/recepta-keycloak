#!/bin/bash
# BARA UTVECKLING. Exporterar datorns utvecklingscertifikat för localhost till
# certs/, så att Keycloak kan svara på https://localhost:8444 (compose.https.yaml).
#
# Certifikatet är det som .NET skapar med `dotnet dev-certs https`. Samma
# certifikat används av recepta-api och recepta-web, så att webbläsaren, .NET
# och Node litar på alla tre. Filerna checkas aldrig in (.gitignore).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/certs"

if ! dotnet dev-certs https --check --trust >/dev/null 2>&1; then
  echo "Hittar inget betrott utvecklingscertifikat för localhost." >&2
  echo "Skapa och lita på ett själv, det kräver ditt lösenord:" >&2
  echo "  dotnet dev-certs https --trust" >&2
  exit 1
fi

mkdir -p "$DIR"
rm -f "$DIR/localhost.pem" "$DIR/localhost.key"
dotnet dev-certs https --export-path "$DIR/localhost.pem" --format Pem --no-password >/dev/null
# Keycloak körs som en annan användare i behållaren och måste kunna läsa nyckeln.
chmod 644 "$DIR/localhost.pem" "$DIR/localhost.key"
echo "Certifikat och nyckel ligger i $DIR"
