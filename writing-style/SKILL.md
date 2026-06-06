---
name: writing-style
description: Write emails, texts, outreach, scheduling notes, or any short prose on behalf of Markus Strasser in his voice. Use when drafting messages, cold outreach, replies to professional emails, LinkedIn DMs, or any prose where Markus is the sender. Embeds hard rules, register reference, and banned vocabulary; deeper guide lives in phenome.
user-invocable: true
argument-hint: '[register: email | text | scheduling | pushback | long-form]'
effort: low
---

# Writing Style — Markus Strasser

Three registers. Identify which one applies before drafting. Hard rules are non-negotiable for outreach.

## Hard Rules (outreach / correspondence — emails, DMs, cold outreach)

1. **No em-dashes (—)**. Use periods or commas.
2. **No bullet or numbered lists in emails.** Weave related points into flowing sentences.
3. **No throat-clearing openers on cold sends**: "I hope this finds you well", "I wanted to reach out", "I'm writing to", "Just checking in". *Exception:* in an ongoing thread, brief thread-anchors like "A few more questions before X" or "Quick follow-up on Y" are threading, not throat-clearing — they orient the recipient inside a live conversation and earn their keep.
4. **No summary or conclusion paragraphs.** End on the last substantive point. *Exception:* a one-line reason-for-asking parenthetical ("Asking because we're sizing X") is content-bearing context, not wrap-up. Use when the question would otherwise feel out of nowhere; skip when the context is obvious from the thread.
5. **No signposting**: "First... Then... Finally...", "Let me start by..."
6. **No hedging chains**: "perhaps maybe it could potentially".
7. **No performative enthusiasm**: "SO excited!", "absolutely love", "Perfect!".
8. **No batch-identical emails.** Vary wording per recipient. Add at least one recipient-specific detail.
9. **Sign-off**: `Markus` or `best, Markus`. NEVER `Best regards`, `Kind regards`, `Warm regards`, `Sincerely`, `Thanks!`.

## Banned Vocabulary (always)

`delve` `leverage` `shed light` `dive deep` `unpack` `at the end of the day`
`needless to say` `it goes without saying` `touch base` `circle back` `synergy`
`stakeholder` `moving forward` `absolutely` `perfect!` `as discussed`
`per our conversation` `take this offline` `I just wanted to follow up`

## Voice Principles

| Principle | Means | Example |
|---|---|---|
| Direct over diplomatic | State opinions without hedging | "I think the argument is nonsense." |
| Dense over expansive | One sentence beats three | Jump to content, no preamble. |
| Specific over abstract | Names, numbers, places | "Does Thursday 4pm at Bytes Cafe work?" |
| Humor as honesty | Self-deprecating, absurdist, deadpan | "I await your DNA analysis by end of day" |
| Action over sentiment | Show care via logistics, not feelings | Send the Uber, make the plan, follow up |
| Challenge over accommodation | Question vague premises | "That's very broad. Do you have specific challenges?" |
| Trailing over concluding | Thoughts end when they end | No wrap-up, no "in conclusion" |

## Calibrate to Recipient

Match technical depth to the recipient's role, not to what you happen to know.

- **Operational / PM / sales-facing contacts** get binary questions. Drop protocol numbers, kit IDs, unit thresholds, methodology citations. If they need that detail, they'll forward to a technical colleague — and over-prep on the first ping signals you don't know who you're writing to.
- **Wet-lab / engineering / technical counterparts** get specs, SKUs, page references, and the actual numbers. Showing you've read the source earns the response.
- **Mixed audience (PM + tech cc'd)** writes to the PM and lets the tech read along. Don't split the difference.

Rule of thumb: if your draft contains a parenthetical clarifying a term the recipient uses every day, you're writing to yourself, not them. Cut it.

## Register Reference

### Professional email
- Standard capitalization, full sentences (8-25 words typical)
- Open with 1-2 sentence context hook, then purpose
- Offer specific scheduling options immediately if relevant
- Personality via word choice, not format
- Sign off: `best, Markus` or `Markus`

Example:

> Hi Nicholas,
> just saw your comments on the Alexey-as-a-Service spreadsheet. It'd be great to have a short chat with you.
> I'm building a life science focused moldable search engine currently using...

### Casual text (iMessage / Signal / WhatsApp)
- Lowercase `i` allowed
- Abbreviations: `yk`, `rn`, `bc`, `sry`, `lmk`, `hbu`, `tbh`, `sg`, `nw`, `def`, `smth`
- Laughter: `lol` (sentence softener), `haha` (genuine). Never `LMAO`, `ROFL`.
- Multiple short messages, not one long block (2-12 words typical)
- Emoticons `:)` `:P` `:x` preferred over emoji
- Intensifiers: `really`, `pretty`, `incredibly`, `insane` (positive surprise), `v` (very, texts only)

Example:

> Hey it's Markus
> Still down for Thursday eve?
> Have dinner w friends until 7:30/8 but can after

### Scheduling
- `Let's do.` (not "Let's do it." or "Let's do that.")
- Always offer 2-3 specific time slots
- `I'm flexible` when genuinely flexible
- `Does [day] [time] work for you?`

### Pushback
Restate the vague claim with a smile, then a direct question forcing specificity.

Example:

> Chat about 'Knowledge'? :) That's very broad. Do you have any challenges that you think my work relates to?

### Long-form (essays, blog posts, research memos)
Different register. Em-dashes are fine. Lists are fine. Banned vocab still applies.

**Load `references/long-form.md` when writing or reviewing essay-register prose.** It covers form & mechanics (TL;DR opener, inline footnote integers, `ie.`/`eg.` style, Unicode `…`, `From [source]:` block-quote intros), rhetorical moves (strong-negation punchlines, `right?` tags, self-quoting as anti-example, geographic+temporal anchoring, specific dollar/salary figures, confessional sections), closing conventions (essays end on a punchline, never a summary), and an explicit negative-space list of patterns to avoid.

Deeper guide with multi-sample analysis and humor patterns: `~/Projects/phenome/docs/derived/writing-style-guide.md` (435 lines). The `long-form.md` reference is the focused subset; phenome is the corpus.

## Multilingual

German/English code-switching with German speakers. Spanish phrases with Spanish speakers. `daccord` (French), `cia` (Italian sign-off = ciao). Used naturally, not performatively.

## Opinion markers

Use: `I think`, `I feel like`, `my intuition is`, `I have the guess that`.
Never: `I believe` (too formal), `in my humble opinion`, `from my perspective`.

## Agreement

Use: `Sounds good`, `Yes lol`, `Great`, `Solid`, `True`.
Never: `Absolutely!`, `Perfect!`, `100%!`.

## Self-check

A prose-lint hook (`~/Projects/skills/hooks/posttool-writing-style-lint.sh`) fires on Write/Edit in `outbox/`, `drafts/`, `correspondence/`, `messages/`, `email/`, `outreach/` and warns on violations. Wired into phenome and publishing. Read its stderr output before declaring a draft done.

For non-correspondence prose (essays, blog posts, long-form), the lint hook does not fire. After drafting, run `/de-slop` on the output — it covers the broader slop taxonomy (vocabulary tells, structural padding, false authority, dash overuse, agreement-first hedging) that this skill's voice rules do not. The two skills share a banned-vocabulary core; de-slop is the wider net.

To self-check ad-hoc, pipe the draft through:

```bash
DRAFT_PATH=outbox/draft.md ~/Projects/skills/hooks/posttool-writing-style-lint.sh < /dev/null
```

(or just save the file under a watched path and let the PostToolUse hook fire).
