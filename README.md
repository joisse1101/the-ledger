# The Ledger

A little dashboard for keeping an eye on your Claude Code usage. If you run Claude Code
across a bunch of projects and terminals, it's easy to lose track of what's actually
running, how a past session went, or how much you've been spending. This app reads the
files Claude Code already keeps on your machine and puts them in one place so you don't
have to go digging.

## What you can do with it

**Get the big picture.** The Overview page has a donut chart breaking down every
session you've ever run by project, plus a panel of headline numbers next to it —
total projects, sessions, and messages, how long your sessions tend to run (average,
longest, shortest), and what they've cost (average, most expensive, cheapest, total).
Tap or hover the longest/shortest/cheapest/most-expensive figures to see which project
and session they came from.

**See what's running right now.** The Sessions page has a "Live" table that shows every
Claude Code process currently running on your machine — which project it's in, what
it's doing, when it last updated. It refreshes itself every couple of seconds, so you
can just leave it open in a tab while you work.

**Look back at every session you've ever run.** Below that is an "All" table pulling
from your session transcripts, going back as far as Claude Code has kept them. It'll
show you how many messages a session had and roughly what it cost, so you can spot the
expensive ones. This table is a manual refresh (there's a ⟳ button) since scanning every
transcript on every tick would be slow.

**Check which projects you've used Claude Code in.** The Projects page lists every
directory you've run or trusted Claude Code in, along with the last session's cost,
CLI version, lines changed, and any MCP servers configured for it.

It also works from your phone or another device on the same network — see "Run from
another device" below — and each device remembers its own light/dark theme preference.

## Quick start

Create the venv and install dependencies (Windows PowerShell), then start everything from the
repo root. You'll also need [Node.js](https://nodejs.org/).

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
.\Start-Ledger.ps1      # API + frontend (+ gateway); .\Stop-Ledger.ps1 stops them
```

Open the URL the frontend prints (http://localhost:4173 by default), not the API's address.

## Documentation

The docs live in [`wiki/`](wiki/Home.md) and are mirrored to the GitHub wiki on every push to
`main`. Edit them in the repo, not on the wiki. Requirements live in `openspec/specs/`.

- [Setup and run](wiki/Setup-And-Run.md): install, dev vs. build mode, ports and `.env`, the
  history backup task
- [Gateway](wiki/Gateway.md): reading the dashboard from a phone or another device, the token,
  HTTPS
- [Testing](wiki/Testing.md): the Python and frontend suites
- [Repository layout](wiki/Repository-Layout.md): the five folders and what each holds
- [Hooks](wiki/Hooks.md): toast notification hooks
- [All pages](wiki/Home.md)

## A couple of things worth knowing

- Cost numbers are estimates, worked out from token counts in the transcripts — Claude
  Code doesn't write a dollar figure to disk anywhere except your most recent session
  per project. If you've used a model this app doesn't recognize yet, its cost won't be
  counted.
- The "Live" table can occasionally show a session that's no longer actually running —
  Claude Code doesn't always clean up its registry file the moment a process exits.
- Each device remembers its own light/dark theme preference locally (it follows your
  system setting until you flip the toggle yourself), so there's nothing to configure
  and nothing that syncs between devices.
