#!/usr/bin/env python3
"""Log in through Cognito with the authorization code flow + PKCE.

Walks the same steps as the whiteboard (and week-09/oauth2-oidc/README.md),
printing each one as it happens. Standard library only.

    python3 login.py \\
        --api-url  https://abc123.execute-api.us-east-1.amazonaws.com/demo \\
        --domain   https://cs1660-w9-xxxxxx.auth.us-east-1.amazoncognito.com \\
        --client-id 4abc123exampleclientid

    source .tokens              # then: curl -H "Authorization: $ID_TOKEN" "$API_URL/me"

Every flag can also come from an environment variable (API_URL, COGNITO_DOMAIN,
CLIENT_ID, CALLBACK_URL). The values are in `terraform -chdir=terraform output`.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer


def parse_args():
    p = argparse.ArgumentParser(description="Cognito login: authorization code flow + PKCE")
    p.add_argument("--api-url", default=os.environ.get("API_URL"),
                   help="API Gateway stage URL, e.g. https://<id>.execute-api.<region>.amazonaws.com/demo")
    p.add_argument("--domain", default=os.environ.get("COGNITO_DOMAIN"),
                   help="Cognito login domain, e.g. https://<prefix>.auth.<region>.amazoncognito.com")
    p.add_argument("--client-id", default=os.environ.get("CLIENT_ID"),
                   help="Cognito app client ID")
    p.add_argument("--callback-url", default=os.environ.get("CALLBACK_URL", "http://localhost:8080/callback"),
                   help="Must match the app client's callback URL exactly (default: %(default)s)")
    args = p.parse_args()

    missing = [f"--{k.replace('_', '-')}" for k in ("api_url", "domain", "client_id") if not getattr(args, k)]
    if missing:
        p.error("missing " + ", ".join(missing))

    args.api_url = args.api_url.rstrip("/")
    args.domain = args.domain.rstrip("/")
    if not args.domain.startswith("http"):
        args.domain = "https://" + args.domain
    return args


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def decode_jwt_payload(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def wait_for_callback(callback_url: str) -> dict:
    """Run a one-shot web server on the callback URL and return its query params."""
    parsed = urllib.parse.urlparse(callback_url)
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path != parsed.path:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Logged in. Go back to the terminal.</h2>")

        def log_message(self, *args):
            pass

    server = HTTPServer((parsed.hostname, parsed.port or 80), Handler)
    while not result:
        server.handle_request()
    server.server_close()
    return result


def main():
    args = parse_args()
    domain, client_id, redirect_uri = args.domain, args.client_id, args.callback_url

    # Secrets for this one login. Only the HASH of the verifier leaves this machine now.
    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())

    authorize_url = f"{domain}/oauth2/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })

    print("[1-2] Sending the browser to Cognito's login page:")
    print(f"      {authorize_url}\n")
    webbrowser.open(authorize_url)

    print("[3]   Log in in the browser (the password goes to Cognito, not to us)...")
    params = wait_for_callback(redirect_uri)

    if "error" in params:
        sys.exit(f"Cognito returned an error: {params}")
    if params.get("state") != state:
        sys.exit("state does not match: this callback is not from our login. Stopping.")
    code = params["code"]
    print(f"[4]   Browser came back with an authorization code: {code[:12]}...\n")

    print("[5]   Exchanging the code (+ code_verifier) for tokens, server to server...")
    req = urllib.request.Request(
        f"{domain}/oauth2/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.load(resp)

    print("[6]   Got tokens: " + ", ".join(k for k in tokens if k.endswith("_token")) + "\n")
    print("      ID token payload (anyone can read this; only Cognito can sign it):")
    print("      " + json.dumps(decode_jwt_payload(tokens["id_token"]), indent=2).replace("\n", "\n      "))

    with open(".tokens", "w") as f:
        f.write(f"export API_URL='{args.api_url}'\n")
        f.write(f"export ID_TOKEN='{tokens['id_token']}'\n")
        f.write(f"export ACCESS_TOKEN='{tokens['access_token']}'\n")

    print("\n[7-8] Now call the API:")
    print("      source .tokens")
    print('      curl "$API_URL/me"                                 # 401: no token')
    print('      curl -H "Authorization: $ID_TOKEN" "$API_URL/me"   # 200: claims echoed back')


if __name__ == "__main__":
    main()