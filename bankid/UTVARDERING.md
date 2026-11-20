# Utvärdering av bankid4keycloak (2026-11-20)

**Utfall: används inte.** Leverantören går inte att bygga mot Keycloak 26.8.2, som är den version vi kör (samma som `safeaid-keycloak`). Identitetsleverantören `bankid` ligger därför i realmen som en vanlig OIDC-koppling med platshållare, avstängd tills en återförsäljare är vald.

## Vad som prövades

| Prov | Resultat |
|---|---|
| Bygga huvudgrenen (commit `34a5932`, 2026-03-23) mot Keycloak 26.8.2 | **Misslyckas.** Kompileringsfel, se nedan |
| Bygga samma commit mot 26.5.6, den version projektet själv anger | Lyckas |
| Lägga den 26.5.6-byggda jar-filen i Keycloak 26.8.2 och köra `kc.sh build` | Går igenom, men klassen saknar en abstrakt metod som 26.8.2 kräver. Binärt oförenlig och utan stöd; inte prövad längre än så |
| Inloggning mot BankID:s testmiljö (`appapi2.test.bankid.com`) | **Inte prövad.** Vi kom aldrig till en körbar leverantör för vår version, och testcertifikatet hämtades därför inte |

Felet vid bygget mot 26.8.2:

```
BankidIdentityProvider.java:[19,8] org.keycloak.broker.bankid.BankidIdentityProvider is not abstract
and does not override abstract method retrieveToken(KeycloakSession, FederatedIdentityModel,
UserSessionModel, UserModel) in org.keycloak.broker.provider.UserAuthenticationIdentityProvider
```

Upprepa: `docker build -f bankid/utvardering.Dockerfile --target build bankid` (lägg till `--build-arg KEYCLOAK_VERSION=26.5.6` för bygget som lyckas).

## Licens och underhåll (verifierat mot GitHub 2026-11-20)

- **Licens:** Apache-2.0. Inget hinder.
- **Källa:** https://github.com/sweid4keycloak/bankid4keycloak (48 stjärnor, inte arkiverad).
- **Senaste ändring på huvudgrenen:** 2026-03-23. Byggfilen pekar på Keycloak 26.5.6.
- **Senaste färdiga utgåva:** `v25.0.0`, 2024-07-11. Nyare versioner måste byggas själv från huvudgrenen.
- **Rättningen finns men är inte sammanfogad:** PR #85 "Upgrading keycloak deps to 26.7.0 and protostream to 6.0.9" (öppnad 2026-07-27) lägger till just den metod som saknas. Även #83 och #84 (26.6.x) ligger öppna.
- **Öppet sedan 2024-08:** ärende #58, "Not able to map SSN during first login".

Bedömning: projektet lever, men ligger två–tre Keycloak-versioner efter och släpper inga färdiga utgåvor. Den som använder det får själv hålla en egen gren i takt med Keycloak.

## Iakttagelser i koden som spelar roll även om den byggs

- **Personnumret blir användarnamn.** `BankidEndpoint.done()` sätter användarnamnet till personnumret (eller, med ett val, en SHA-256-summa av det). Användarnamn syns i `preferred_username`, i adminkonsolen och i händelseloggar. Det går emot vår regel att personnumret bara lämnas ut i claimet `personal_number`.
- **Inget användarattribut.** Personnumret läggs som sessionsanteckning (`bankid.pnr`), inte som attributet `personal_number`. Vår mappning från attribut skulle behöva bytas mot en mappning från sessionsanteckning.
- **Direkt mot BankID.** Leverantören pratar med BankID:s RP-API med eget klientcertifikat (PKCS12) och visar QR-kod. Det kräver ett eget BankID-avtal genom en bank och ett eget FP-certifikat.

## Vad som krävs för att ändå välja den vägen

1. Vänta tills projektet stöder vår Keycloak-version, eller lås Keycloak till en version det stöder (går emot att följa `safeaid-keycloak`).
2. Avtal om BankID genom en bank, och FP-certifikat för drift.
3. Lösa att personnumret inte får bli användarnamn.

Att själva lappa in den saknade metoden är avsiktligt inte gjort: byggplanen säger att inget eget hack ska byggas.
