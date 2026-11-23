# Design

## Context

`sign_in_code()` in `api/app/services/remote_service.py` takes `banner.discover_ipv4()[0]` and renders one code. `discover_ipv4()` already returns every usable IPv4 address (outbound-interface one first), so a Tailscale address is in the list today and is simply never chosen. The dialog (`RemoteQrDialog.tsx`) shows `svg` and `display_url` from `GET /api/remote-mode/qr`. The desktop widget also reads that response (`widget/src/main/api.ts`). See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Tailscale address preselected when present; LAN one-click away.
- Additive API change, so the widget and any older reader keep working.

**Non-Goals:**
- Fixing the certificate warning, or any gateway or firewall change.
- A toggle in the desktop widget.
- MagicDNS names (`*.ts.net`) in the code.

## Decisions

**Recognise Tailscale by address range, not adapter name.** An address in `100.64.0.0/10` (the carrier-grade NAT range Tailscale uses) is Tailscale. Windows labels the adapter "Unknown", and names can change, whereas the range is fixed. Alternative: read the adapter name through the OS; rejected as fragile and platform-specific. A new helper in `banner.py` classifies an address; it is pure, so it is tested without a network.

**One response carries every code.** The response keeps `svg`, `display_url` and `expires_at` for the default address and adds `addresses`, a list of `{kind, address, display_url, svg}` with the default first. Each code embeds the token, so each needs its own image; the dialog then switches locally with no second request and no stale state. Alternative: an `?address=` query parameter and a refetch per toggle; rejected because it adds a loading state and a second token-bearing request for no gain. The response stays local-only, as today, so no extra exposure.

**Default order.** Tailscale first, then the remaining addresses in `discover_ipv4()` order. If several Tailscale addresses exist, the first is the default and each still gets its own entry.

**Dialog.** `QrBody` keeps the chosen kind in component state and falls back to the first entry. It uses the shared `ButtonSelector` for the choice and renders it only when the list holds more than one entry. The body unmounts on close, so the choice resets to Tailscale each time the dialog opens.

## Risks / Trade-offs

- [A phone on the same Wi-Fi but without Tailscale scans the default code and fails] → the LAN choice is one click away, and the guide says which devices each address suits.
- [Several addresses of one kind give a long list] → the control labels by kind, and the address is shown under the code, so entries are distinguishable.
- [The response grows by one SVG per address] → a few KB each, local only, fetched only while the dialog is open.
