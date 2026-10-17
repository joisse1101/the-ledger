"""Prints the gateway's sign-in link and QR; the logic lives in app/infra/gateway_signin.py.

Kept at the api/ root because gateway/Start-Gateway.ps1 and Start-Ledger.ps1 run it by path.
"""

from app.infra.gateway_signin import main

if __name__ == "__main__":
    raise SystemExit(main())
