"""The gateway's sign-in addresses: the link a QR code encodes and the address shown beside it.

The link carries the Remote mode session's access token, so it is only ever put in the QR the
dashboard shows to the machine running the app (see `remote_service.sign_in_code`).
"""

from __future__ import annotations


def signin_url(address: str, gateway_port: int, token: str) -> str:
    """The link that signs a device in: the gateway's HTTPS address plus the access token."""
    return f"{display_url(address, gateway_port)}/?token={token}"


def display_url(address: str, gateway_port: int) -> str:
    """The gateway's address as shown on screen: never carries the token."""
    return f"https://{address}:{gateway_port}"
