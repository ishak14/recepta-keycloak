#!/usr/bin/env python3
"""Bevis för recepta-keycloak mot kontraktet.

Väntar tills Keycloak svarar, hämtar .well-known/openid-configuration, loggar in
en testanvändare genom recepta-web-klientens flöde (authorization code med PKCE
S256) och kontrollerar access-token: signatur, iss, aud och claims.

Bara standardbiblioteket. Kör: python3 prove/prove.py
"""

import base64, hashlib, html, http.cookiejar, json, os, re, secrets, sys, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def dotenv():
    values = {}
    for name in (".env.example", ".env"):
        path = ROOT / name
        if path.exists():
            for line in path.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
    return values


ENV = {**dotenv(), **os.environ}
BASE = ENV.get("KEYCLOAK_URL", "http://localhost:8081").rstrip("/")
ISSUER = f"{BASE}/realms/recepta"
CLIENT_ID = "recepta-web"
CLIENT_SECRET = ENV.get("RECEPTA_WEB_CLIENT_SECRET", "")
WEB_URL = ENV.get("RECEPTA_WEB_URL", "http://localhost:3000").rstrip("/")
REDIRECT_URI = f"{WEB_URL}/api/auth/callback"
TEST_USER = json.loads((ROOT / "dev" / "testanvandare.json").read_text())["users"][0]
USERNAME = TEST_USER["username"]
PASSWORD = TEST_USER["credentials"][0]["value"]
EXPECTED_PNR = TEST_USER["attributes"]["personal_number"][0]

checks = []


def ok(text):
    checks.append(text)
    print(f"  ok  {text}")


def fail(text):
    sys.exit(f"FEL: {text}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class LocalhostCookies(http.cookiejar.DefaultCookiePolicy):
    """Keycloak märker sina kakor Secure. Webbläsare skickar dem ändå till
    http://localhost; Pythons kakburk gör det inte utan den här regeln."""

    def return_ok_secure(self, cookie, request):
        return True


def browser():
    jar = http.cookiejar.CookieJar(LocalhostCookies())
    return urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(jar))


def call(opener, method, url, form=None):
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    try:
        with opener.open(request, timeout=30) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def unb64url(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def wait_ready(opener):
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            status, headers, _ = call(opener, "GET", f"{ISSUER}/.well-known/openid-configuration")
            if status == 200 and "json" in (headers.get("Content-Type") or ""):
                return
        except Exception:
            pass
        time.sleep(3)
    fail(f"Keycloak svarade inte på {ISSUER} inom tre minuter. "
         "Svarar något annat på porten (till exempel Expo på 8081)?")


def authorize(opener, challenge=None, redirect_uri=REDIRECT_URI):
    query = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": redirect_uri,
        "state": secrets.token_urlsafe(16),
        "kc_idp_hint": "bankid",  # sajten skickar alltid detta
    }
    if challenge:
        query["code_challenge"] = challenge
        query["code_challenge_method"] = "S256"
    return query["state"], call(opener, "GET", f"{CONFIG['authorization_endpoint']}?{urllib.parse.urlencode(query)}")


def login_form_action(body):
    match = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', body.decode())
    if not match:
        fail("inloggningsformuläret hittades inte på sidan")
    return html.unescape(match.group(1))


def login(password, verifier):
    """Går igenom flödet som en webbläsare. Ger (status, Location, state)."""
    opener = browser()
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state, (status, _, body) = authorize(opener, challenge)
    if status != 200:
        fail(f"inloggningssidan gav {status}")
    status, headers, body = call(opener, "POST", login_form_action(body),
                                 {"username": USERNAME, "password": password, "credentialId": ""})
    return status, headers.get("Location") or "", state, body


def token_request(code, verifier, secret=CLIENT_SECRET):
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID, "client_secret": secret}
    if verifier:
        form["code_verifier"] = verifier
    status, _, raw = call(browser(), "POST", CONFIG["token_endpoint"], form)
    return status, json.loads(raw or b"{}")


def code_from(location, state):
    if not location.startswith(REDIRECT_URI + "?"):
        fail(f"omdirigeringen gick inte till sajtens återanrop: {location[:80]}")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    if query.get("state") != [state]:
        fail("state kom inte tillbaka oförändrat")
    if "code" not in query:
        fail(f"ingen kod i återanropet: {sorted(query)}")
    return query["code"][0]


def verify_rs256(token):
    header_b64, payload_b64, signature_b64 = token.split(".")
    header = json.loads(unb64url(header_b64))
    if header.get("alg") != "RS256":
        fail(f"oväntad signaturalgoritm {header.get('alg')}")
    _, _, raw = call(browser(), "GET", CONFIG["jwks_uri"])
    keys = [key for key in json.loads(raw)["keys"] if key.get("kid") == header.get("kid")]
    if not keys:
        fail("signeringsnyckeln finns inte i jwks_uri")
    n = int.from_bytes(unb64url(keys[0]["n"]), "big")
    e = int.from_bytes(unb64url(keys[0]["e"]), "big")
    size = (n.bit_length() + 7) // 8
    signed = pow(int.from_bytes(unb64url(signature_b64), "big"), e, n).to_bytes(size, "big")
    digest = hashlib.sha256(f"{header_b64}.{payload_b64}".encode()).digest()
    prefix = bytes.fromhex("3031300d060960864801650304020105000420")
    expected = b"\x00\x01" + b"\xff" * (size - len(prefix) - len(digest) - 3) + b"\x00" + prefix + digest
    if signed != expected:
        fail("access-tokens signatur stämmer inte mot jwks_uri")
    return json.loads(unb64url(payload_b64))


def main():
    global CONFIG
    if not CLIENT_SECRET:
        fail("RECEPTA_WEB_CLIENT_SECRET saknas (.env eller .env.example)")
    print(f"Bevis mot {ISSUER}")
    opener = browser()
    wait_ready(opener)
    _, _, raw = call(opener, "GET", f"{ISSUER}/.well-known/openid-configuration")
    CONFIG = json.loads(raw)
    if CONFIG.get("issuer") != ISSUER:
        fail(f"issuer är {CONFIG.get('issuer')!r}, väntat {ISSUER!r}")
    ok(f"openid-configuration hämtad, issuer {ISSUER}")
    if "S256" not in CONFIG.get("code_challenge_methods_supported", []):
        fail("S256 saknas bland PKCE-metoderna")

    # Fel väg ska vara stängd.
    _, (status, headers, _) = authorize(browser(), challenge=None)
    if status == 200:
        fail("inloggning utan PKCE släpptes fram till inloggningssidan")
    ok("anrop utan PKCE avvisas")
    _, (status, headers, _) = authorize(browser(), "x" * 43, redirect_uri=f"{WEB_URL}/annan-sida")
    if status != 400:
        fail(f"okänd återanropsadress gav {status}, väntat 400")
    ok("okänd återanropsadress avvisas")
    status, location, _, _ = login("fel-losenord-" + secrets.token_hex(4), secrets.token_urlsafe(48))
    if status != 200 or "code=" in location:
        fail("fel lösenord gav inte tillbaka inloggningssidan")
    ok("fel lösenord avvisas")
    status, _, raw = call(browser(), "POST", CONFIG["token_endpoint"],
                          {"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                           "username": USERNAME, "password": PASSWORD})
    if status == 200:
        fail("lösenordsflödet (direct grant) är påslaget för recepta-web")
    ok("lösenordsflödet utan webbläsare är avstängt")

    # Rätt väg: authorization code med PKCE, som sajten gör.
    verifier = secrets.token_urlsafe(48)
    status, location, state, _ = login(PASSWORD, verifier)
    if status != 302:
        fail(f"inloggningen gav {status}, väntat omdirigering till sajten")
    code = code_from(location, state)
    ok(f"{USERNAME} loggade in och skickades till {REDIRECT_URI}")

    status, body = token_request(code, verifier="fel-" + secrets.token_urlsafe(48))
    if status == 200:
        fail("koden gick att lösa in med fel code_verifier")
    ok("kod med fel code_verifier avvisas")

    verifier = secrets.token_urlsafe(48)
    status, location, state, _ = login(PASSWORD, verifier)
    code = code_from(location, state)
    status, body = token_request(code, verifier, secret="fel-hemlighet")
    if status == 200:
        fail("koden gick att lösa in med fel klienthemlighet")
    ok("fel klienthemlighet avvisas")

    verifier = secrets.token_urlsafe(48)
    status, location, state, _ = login(PASSWORD, verifier)
    code = code_from(location, state)
    status, tokens = token_request(code, verifier)
    if status != 200:
        fail(f"kodutbytet gav {status}: {tokens.get('error')} {tokens.get('error_description')}")
    ok("koden löstes in mot token")

    claims = verify_rs256(tokens["access_token"])
    ok("access-token är signerad med nyckel från jwks_uri (RS256)")
    if claims.get("iss") != ISSUER:
        fail(f"iss är {claims.get('iss')!r}")
    ok("iss stämmer")
    audience = claims.get("aud")
    audience = audience if isinstance(audience, list) else [audience]
    if "recepta-api" not in audience:
        fail(f"aud är {audience!r}, recepta-api saknas")
    ok(f"aud innehåller recepta-api ({', '.join(map(str, audience))})")
    if claims.get("azp") != CLIENT_ID:
        fail(f"azp är {claims.get('azp')!r}")
    if not claims.get("sub"):
        fail("sub saknas")
    ok("sub finns")
    if claims.get("personal_number") != EXPECTED_PNR or not re.fullmatch(r"\d{12}", EXPECTED_PNR):
        fail("personal_number saknas eller har fel form (tolv siffror väntas)")
    ok("personal_number finns, tolv siffror")
    for claim, expected in (("given_name", TEST_USER["firstName"]), ("family_name", TEST_USER["lastName"])):
        if claims.get(claim) != expected:
            fail(f"{claim} är {claims.get(claim)!r}, väntat {expected!r}")
    ok("given_name och family_name stämmer")

    # Personnumret får inte läcka någon annanstans.
    id_claims = json.loads(unb64url(tokens["id_token"].split(".")[1]))
    request = urllib.request.Request(CONFIG["userinfo_endpoint"],
                                     headers={"Authorization": f"Bearer {tokens['access_token']}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        userinfo = json.loads(response.read())
    for name, data in (("id-token", id_claims), ("userinfo", userinfo)):
        if EXPECTED_PNR in json.dumps(data):
            fail(f"personnumret finns i {name}")
    others = {key: value for key, value in claims.items() if key != "personal_number"}
    if EXPECTED_PNR in json.dumps(others):
        fail("personnumret finns i fler claims än personal_number")
    ok("personnumret finns bara i claimet personal_number i access-token")

    print(f"KLART: {len(checks)} kontroller gick igenom")


if __name__ == "__main__":
    main()
