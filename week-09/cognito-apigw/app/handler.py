"""Dummy backend for the Cognito + API Gateway demo.

There is no token checking in here. On /me, API Gateway's Cognito authorizer
has already verified the token before this function runs, and it hands us the
token's claims in the event.
"""

import json


def handler(event, context):
    route = event.get("resource")

    if route == "/me":
        claims = event["requestContext"]["authorizer"]["claims"]
        body = {
            "message": f"Hello {claims.get('email')}, API Gateway already checked your token.",
            "sub": claims.get("sub"),  # stable user ID: use this as your DynamoDB key
            "email": claims.get("email"),
            "token_use": claims.get("token_use"),
            "iss": claims.get("iss"),
            "aud": claims.get("aud"),
        }
    else:
        body = {"message": "Public route: no token required, so anyone gets this."}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, indent=2),
    }
