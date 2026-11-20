# recepta-keycloak

Inloggning för Receptläkaren (arbetsnamn Recepta): Keycloak 26.8.2 och PostgreSQL 17, uppbyggt efter `safeaid-keycloak`. Det som sajten och API:t räknar med står i kunskapsbasen, `02-Teknik/Kontrakt mellan web, keycloak och api.md`.

**Läge 2026-11-20:** realm, klienter, claims, tema och testanvändare fungerar och bevisas av `prove/prove.py`. BankID är **inte** inkopplat; identitetsleverantören `bankid` ligger avstängd med platshållare. Se [BankID](#bankid).

## Starta lokalt

```bash
cp .env.example .env
docker compose up -d --build
python3 prove/prove.py
```

| Vad | Adress |
|---|---|
| Utfärdare | `http://localhost:8081/realms/recepta` |
| Inställningar för OIDC | `http://localhost:8081/realms/recepta/.well-known/openid-configuration` |
| Adminkonsol | `http://localhost:8081/admin` (konto enligt `.env`) |

Stoppa med `docker compose down`. Databasen ligger kvar i volymen `recepta-keycloak_keycloak-db`.

### Port 8081 och Expo

`safeaid-mobile` kör Expo på `*:8081`. Compose binder därför både `127.0.0.1:8081` och `[::1]:8081`, så att `localhost:8081` är Keycloak så länge behållarna är igång.

- **Keycloak igång:** Expo nås inte på `localhost:8081` (bara på datorns nätverksadress).
- **Keycloak stoppad:** `localhost:8081` svarar från Expo med 404. Får sajten eller API:t 404 från Keycloak-adressen är detta orsaken.

Frågan om en annan port står i `05-Plan/Öppna frågor.md`.

## Testanvändare (bara utveckling)

Läggs in av tjänsten `dev-seed` från `dev/testanvandare.json` varje gång compose startar. De finns inte i realmfilen och inte i avbilden. Personnumren kommer från Skatteverkets öppna lista över testpersonnummer och tillhör ingen människa.

| Användarnamn | Lösenord | Namn | `personal_number` |
|---|---|---|---|
| `test-anna` | `Test-1234!` | Anna Testsson | `189007209803` |
| `test-erik` | `Test-1234!` | Erik Provberg | `189007219810` |
| `test-sara` | `Test-1234!` | Sara Exempelsson | `189007229801` |

Sajten skickar `kc_idp_hint=bankid`. Så länge `bankid` är avstängd bortser Keycloak från det och visar formuläret med användarnamn och lösenord.

## Det sajten och API:t får

- **Klient `recepta-web`:** konfidentiell, authorization code, PKCE S256 är tvingande. Återanrop exakt `http://localhost:3000/api/auth/callback`, efter utloggning exakt `http://localhost:3000/`. Hemligheten i utvecklingsläge är `RECEPTA_WEB_CLIENT_SECRET` i `.env.example`; sajten läser samma värde från `KEYCLOAK_CLIENT_SECRET`.
- **Klient `recepta-api`:** tar bara emot token (`bearerOnly`).
- **Access-token till `recepta-web`:** `iss`, `sub`, `aud` med `recepta-api`, `personal_number` (tolv siffror), `given_name`, `family_name`.
- **Personnumret** finns bara i access-token. Det finns inte i id-token, inte i userinfo och aldrig som användarnamn. Användaren kan varken se eller ändra attributet själv.

## Filer

| Fil | Innehåll |
|---|---|
| `Dockerfile` | Keycloak 26.8.2 med realmfilen och temat inbyggda |
| `compose.yaml` | Postgres 17, Keycloak och `dev-seed`. Bara för lokal utveckling |
| `realm/recepta-realm.json` | Realmen. Värden med `${...}` hämtas från miljön vid inläsning |
| `dev/` | Testanvändare och skriptet som lägger in dem. Bara utveckling |
| `themes/recepta/login` | Inloggningssidan i designens färger, med Geist (OFL) som egen fil |
| `prove/prove.py` | Bevis mot kontraktet |
| `bankid/` | Utvärderingen av `bankid4keycloak` |

## Ändra realmen

Realmfilen läses bara in när realmen inte redan finns. Efter en ändring i `realm/recepta-realm.json`:

```bash
docker compose down -v
```

```bash
docker compose up -d --build
```

`down -v` tömmer den lokala databasen. Ändringar som bara görs i adminkonsolen försvinner då, så skriv dem i filen.

Temat läses direkt från `themes/recepta`, och ändringar där syns vid nästa sidladdning.

## BankID

**Utfall av utvärderingen:** `bankid4keycloak` går inte att bygga mot Keycloak 26.8.2 och används inte. Hela underlaget står i [bankid/UTVARDERING.md](bankid/UTVARDERING.md).

**Det som finns:** identitetsleverantören `bankid` som vanlig OIDC-koppling, avstängd, förberedd för en återförsäljare (till exempel Signicat, GrandID eller Idura). Mappningar finns för personnummer till attributet `personal_number`, för- och efternamn, och ett användarnamn som byggs av leverantörens `sub` så att personnumret aldrig blir användarnamn.

**Det som återstår:**

1. **Välj väg:** återförsäljare (det som är förberett) eller BankID direkt. Underlag i nattrapporten i kunskapsbasen.
2. **Avtal och testkonto** hos återförsäljaren. Lägg deras värden i `.env`: `BANKID_OIDC_ISSUER`, `BANKID_OIDC_AUTHORIZATION_URL`, `BANKID_OIDC_TOKEN_URL`, `BANKID_OIDC_JWKS_URL`, `BANKID_OIDC_CLIENT_ID`, `BANKID_OIDC_CLIENT_SECRET`.
3. **Claim för personnummer:** sätt `BANKID_OIDC_CLAIM_PERSONAL_NUMBER` till det namn återförsäljaren använder. Kontrollera att värdet är tolv siffror utan bindestreck; annars behövs en omformning innan det når API:t.
4. **Slå på:** `"enabled": true` för `bankid` i realmfilen, och läs in realmen på nytt.
5. **Pröva hela vägen** med test-BankID: första inloggningen ska inte fråga efter e-post eller andra uppgifter, och `prove/prove.py` behöver ett motsvarande steg för BankID-vägen.

Inget av detta är prövat mot en riktig återförsäljare.

## Inte för drift

Compose-filen kör `start-dev` över HTTP med hemligheter som står i `.env.example`. För drift krävs minst: `start --optimized` bakom HTTPS, `KC_HOSTNAME` med den riktiga adressen, egna hemligheter, riktiga adresser i `RECEPTA_WEB_URL`, ingen `dev-seed`, och att adminkonsolen och hanteringsporten 9000 inte nås utifrån.
