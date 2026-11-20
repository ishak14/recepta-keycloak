# recepta-keycloak

Inloggning för Receptläkaren (arbetsnamn Recepta): Keycloak 26.8.2 och PostgreSQL 17.

## Starta lokalt

1. Kopiera `.env.example` till `.env`.
2. `docker compose up -d --build`
3. Adminkonsolen: http://localhost:8081/admin (konto enligt `.env`).
