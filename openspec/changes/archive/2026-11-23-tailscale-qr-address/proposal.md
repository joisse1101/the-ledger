# Proposal

## Why

The Remote-mode QR code always encodes the machine's first network address, which is the Wi-Fi or LAN address. A device that is not on the same network, such as a phone on mobile data, cannot reach it. The machine is on Tailscale, and its Tailscale address (stable, and already confirmed to reach the dashboard) works from any device on the same tailnet, but the code never uses it.

## What Changes

- The sign-in code response lists every usable address, each labelled "Tailscale" or "LAN", with its own code and display address.
- An address in `100.64.0.0/10` is labelled Tailscale. All others are labelled LAN.
- The Tailscale address is selected by default when one exists. Otherwise the LAN address is.
- The "Open on another device" dialog shows a toggle (only when both kinds exist) that switches the code and the address shown under it.
- The existing response fields (`svg`, `display_url`, `expires_at`) stay and describe the default address, so existing readers such as the desktop widget keep working.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-access`: the sign-in code requirement changes from "the machine's first network address" to "a choice of the machine's addresses, Tailscale first".
- `web-dashboard`: the Remote mode modal gains an address toggle.

## Impact

- Backend: `api/app/infra/banner.py` (classify addresses), `api/app/services/remote_service.py` (build one code per address), their tests in `api/tests/`.
- Frontend: `web/src/api/types.ts`, `web/src/components/sessions/RemoteQrDialog.tsx` and its test.
- Docs: `wiki/User-Guide/Remote-Access.md`, `wiki/Backend/API-Routes.md`.
- No new dependency. The certificate warning is unchanged, and the gateway is untouched.
- Not covered: the desktop widget keeps showing the default address only, with no toggle.
