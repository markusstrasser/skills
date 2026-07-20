# Retrodiction calibration

Append new dated sections; do not rewrite prior results.

## 2026-07-20 — initial v0.31.2 calibration

Scope: the original skill at commit `14a5129`, tested against work that was not used to write it.

### Held-out friction

| Case | What the original skill predicted | Result |
|---|---|---|
| A selected Personal Search lane exposed `aria-pressed="true"` | The compact snapshot should provide enough state for interaction | **FN:** text and JSON snapshots exposed only role, name, and ref; `get attr @eN aria-pressed` returned `true` |
| A named session was closed after the browser check | The daemon-persistence gotcha should prevent treating the remaining session label as an open browser | **Partial catch:** the warning existed, but it did not distinguish daemon `active` from `runtime.browserLaunched=false` and `pageCount=0` |

Both gaps are now explicit in `SKILL.md`. State that gates a decision must come from the relevant attribute, not from snapshot absence.

### Shipped-good controls

| Case | Result | Dead-weight rework demanded by the skill |
|---|---|---|
| Example Domain open → snapshot → attribute read → close | Passed on the system-Chrome fallback | None |
| Personal Search UI open → select Media + Instagram → query `mountain lake` | Passed; 48 visual results, no page errors, CLS 0, FCP/LCP 72 ms | None |

False-positive burden: **0/2** shipped-good controls. The mandatory `skills get core` load was useful version-matched instruction, not rework.

### Reproduction receipt

```bash
agent-browser --session agent-browser-skill-calibration open https://example.com
agent-browser --session agent-browser-skill-calibration eval 'document.body.innerHTML = `<button aria-pressed="true">Media selected</button>`'
agent-browser --session agent-browser-skill-calibration snapshot -i
agent-browser --session agent-browser-skill-calibration snapshot -i --json
agent-browser --session agent-browser-skill-calibration get attr @e1 aria-pressed
agent-browser --session agent-browser-skill-calibration close
agent-browser --session agent-browser-skill-calibration session info --json
```

Observed snapshot ref: `{role: "button", name: "Media selected"}` with no pressed state. The direct attribute read returned `true`; after close, the daemon remained active while `browserLaunched=false` and `pageCount=0`.

Verdict: **adopt** for scripted/headless browser work. Trust navigation and element refs; verify decision-bearing state through its principal attribute and distinguish browser lifecycle from daemon lifecycle.
