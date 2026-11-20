# recepta-keycloak: regler för agenter

Läs också `../AGENTS.md`. Kontraktet (realm, klienter, claims, portar) står i `../recepta-knowledgebase/02-Teknik/Kontrakt mellan web, keycloak och api.md`.

Förebild: `/Users/ishak/Projects/safeaid/safeaid-keycloak` (`Dockerfile`, `compose.yaml`, `realm/`, `themes/`, `prove/`). Lösenordsleverantören och migreringsverktyget där hör till safeaid och kopieras inte.

## Regler

- Realmen beskrivs i `realm/recepta-realm.json` och läses in vid start. Ändringar görs i filen, inte bara i adminkonsolen.
- Inga hemligheter i realmfilen eller i git. Värden kommer från `.env`; `.env.example` visar vilka som behövs.
- Testanvändare och utvecklingshemligheter får bara finnas i utvecklingsrealmen och ska vara tydligt märkta.
- BankID nås genom identitetsleverantören med alias `bankid`. Bygg ingen egen BankID-koppling vid sidan av.
- Personnummer lämnas ut i claimet `personal_number` och ingen annanstans.
- Adminkonsolen och hanteringsporten 9000 exponeras aldrig publikt.
- Port 8081 lokalt, eftersom safeaid använder 8080.

## Kontroll

Efter en ändring: bygg och starta med `docker compose up -d --build`, och kör bevisskriptet i `prove/`.
