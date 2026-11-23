# Tasks

## 1. Backend: a code for each address, Tailscale first

- [x] 1.1 Add a pure helper in `api/app/infra/banner.py` that labels an IPv4 address `tailscale` (inside 100.64.0.0/10) or `lan`, and one that orders addresses Tailscale first while keeping the rest in order; verify new cases in `api/tests/infra/test_banner.py` cover 100.64.0.0, 100.127.255.255, 100.63.255.255 and 100.128.0.0 (the range edges), a LAN address, and ordering with and without a Tailscale address (network-access: Tailscale address is the default, Only a LAN address).
- [x] 1.2 Change `sign_in_code()` in `api/app/services/remote_service.py` to render one code per usable address and return `addresses` (`kind`, `address`, `display_url`, `svg`), default first, while keeping top-level `svg`, `display_url`, `expires_at` for the default; keep the "No network address" conflict and the missing-qrcode `Unavailable` error. Update the existing assertions in `api/tests/test_api_data.py` (the code is now rendered per address) and add tests: Tailscale default when present, LAN default when not, no token in any `display_url`, and a remote request with a valid token is still refused; verify `cd api; pytest` passes (network-access: Local request while ready, Other device asks).
- [x] 1.3 Update the `/api/remote-mode/qr` entry in `wiki/Backend/API-Routes.md` for the new `addresses` field and run `python scripts/check_docs.py`; verify it passes.

## 2. Frontend: choose between the addresses

- [x] 2.1 Add the `addresses` entries to `RemoteQr` in `web/src/api/types.ts` (with a kind union `"tailscale" | "lan"`), mirroring the server JSON; verify `cd web; npm run build` type-checks.
- [x] 2.2 In `web/src/components/sessions/RemoteQrDialog.tsx`, show a `ButtonSelector` (Tailscale / LAN) above the code only when `addresses` has more than one entry, select Tailscale first, and render the chosen entry's `svg` and `display_url`; add `web/src/components/sessions/RemoteQrDialog.test.tsx` covering Tailscale selected first, switching to LAN changes the image and address, a single kind shows no control, and no token text appears in the DOM; verify `cd web; npm test` passes (web-dashboard: Tailscale selected first, Switch to the LAN address, One kind of address).
- [x] 2.3 Update `RemoteModeControl.test.tsx` fixtures if the new field breaks them, and document the toggle in `wiki/Frontend/Sessions-Page.md`; verify `cd web; npm test` and `python scripts/check_docs.py` pass.

## 3. Guide and integration check

- [x] 3.1 Update `wiki/User-Guide/Remote-Access.md`: say that the code defaults to the Tailscale address, that a device must be on the same tailnet to use it, and how to pick the LAN address; verify `python scripts/check_docs.py` passes.
- [x] 3.2 Run the whole suite and build: `cd api; pytest`, `cd web; npm test`, `cd web; npm run build`, and `cd widget; npm test` (the widget reads the same response); verify every command exits 0.

## Workflow follow-up

- Archive the change after review, updating the affected wiki pages first as the project's archive guidance asks.
