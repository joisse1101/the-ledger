# Alert tiering ideas

> Requirements live in `openspec/specs/`, not here. This page is a **parked idea**, not a description of working code.

The idea: replace the single, always-loud toast with alerts that are sorted by how much each event matters. Each alert gets a channel that costs the user's attention in proportion. Only the first step, sound only, is planned. The rest is kept here for later.

## Status

- **Planned now:** sound only when away. Two chimes ("finished" and "needs you"), played only when you are away from the PC, and merged when several sessions fire at once. Away means Windows sees no keyboard or mouse input for 5 minutes, or the widget's AFK button is on.
- **Parked:** everything else on this page (the "full tiering"), including:
  - A delayed reminder when a session sits unanswered.
  - Away detection from session activity, instead of keyboard and mouse input.
- **Owner of the next step:** the repo owner, who decides when to start tiering. No date is set.

## Why

- The toast in `hooks/scripts/Send-ClaudeToast.ps1` fires on every `Notification` and `Stop` hook event, for every session.
- It does not tell "finished" apart from "needs you".
- It does not know whether you are already at the terminal.
- It does not merge several sessions finishing together.
- The widget already flags a waiting prompt, but it only helps if you glance at it.

## Events worth separating

| Event | Urgency | Why |
|---|---|---|
| Blocked on a permission or question | High | The session is stalled until you act |
| Finished a task | Medium | Nothing is lost if you are slow, but you are idle-waiting |
| Finished after a long run (say 5+ minutes) | Medium-high | You probably walked away |
| Finished a quick run (under 30 seconds) | Low | You are likely still watching |
| Still unanswered after a long wait | Rising | A reminder that grows if ignored |

The thresholds in the table are starting guesses. They are unchecked against real use.

## Reminder types, quiet to loud

```
quiet                                                          loud
  |                                                              |
  v                                                              v
 widget      tray icon    taskbar     soft chime    toast    repeat/
 row flag    badge/color  flash       (per event)   (today)  escalate
```

- **Widget row flag:** exists today. Passive.
- **Tray icon state:** the icon turns amber while anything is waiting and clears when nothing is. A persistent cue with no popup.
- **Taskbar flash:** the VS Code or terminal button blinks orange. Silent, and Windows clears it when you focus the window.
- **Two chimes:** a soft "done" sound and a more distinct "needs you" sound. Sound works when you are not looking at the screen.
- **Escalation:** the first alert is quiet. If a prompt is still unanswered after about 2 minutes, one firmer alert fires. Then nothing more.
- **Toast:** kept, but only for high-urgency events.

## Rules that keep it from being annoying

These matter more than which sounds are chosen.

1. **Focus-aware:** stay silent when the session's VS Code window is already focused.
2. **Debounce and batch:** several sessions finishing within a few seconds make one chime, not several.
3. **Duration threshold:** quick runs stay silent.
4. **One alert per waiting episode:** do not re-fire for the same unanswered prompt, except the deliberate escalation.
5. **Quiet mode:** one click in the widget or tray mutes everything, and it can switch itself back on after an hour.

## Where the logic could live

- **In the hooks:**
  - A hook fires once and keeps no memory.
  - It cannot see other sessions.
  - So it can play a sound, but it cannot debounce or escalate.
- **In the widget or backend:**
  - The widget already polls session state.
  - It knows what is waiting, for how long, and which sessions exist.
  - It could own all five rules, with the hooks reduced to a trigger.
  - The cost is that alerts would depend on the widget running, so they would be silent if it is closed.
- **Leaning:** the widget or backend. This is an assumption, not yet tested against the code.

## Open questions

- Should sound play only on this PC, or also on other devices through the dashboard when you are away from your desk? The second is a larger design.
- How should "the session's window is focused" be detected on Windows? Not yet checked.
- Do the toast and the sound use the same hook event, or does the sound come from the widget's own polling? Depends on the leaning above.

## Suggested order if this is picked up

1. Sound only (planned now).
2. Add the tray icon state and taskbar flash.
3. Add escalation and quiet mode, and limit the toast to high urgency.
