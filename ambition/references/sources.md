# Sources for /ambition

Fetched 2026-10-24 via Exa crawl. Quotes are verbatim.

## Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models" (2026-10-13)

https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
Author works on Claude at Anthropic (engineering lead for Claude.ai, Cowork, Claude Code Desktop).

Four types: Speed, Altitude, Depth, Range.

**Altitude**
- "To be more ambitious in altitude, ask yourself - what do you want to happen next? What's the goal beyond the goal? At the beginning of last year, I still asked Claude to fix individual crashes for me. Eventually I asked Claude to simply keep our apps crash-free."
- "A good tell-tale sign that ambition in altitude is a good idea is if you're going to have meetings to discuss whatever you're working on."
- "The altitude approach works best if you really are after some ultimate outcome; it works less well for creative endeavors."
- "in order to let Claude make sure our app is crash-free, I first had to make sure it can easily fetch crash reports, understand which app version maps to what git commit, and give it access to Windows, macOS, and Linux computers so it can actually independently reproduce and verify fixes."
- QBR example: "Design a better way to do that than a quarterly deck, show from our own history that it would have caught things sooner, and run it beside the current one for a quarter."

**Depth**
- "When prompted to act like a professional, models often switch vocabulary without actually switching methods. ... When Claude reaches for markdown tables, insist on the use of databases and statistical models. You don't necessarily have to know what the experts use, Claude usually does."
- "Pick unreasonable goals and tell the model that they're very reasonable: You need your website to load in 5s instead of 10s? Ask for 200ms."
- "We believe churn is an onboarding problem. Try to reproduce that from the raw data."
- "Build a simulation of our customers that reproduces the last year from our logs. Then find the earliest signal of churn we don't know about yet, and show it predicts on data it has not seen."
- "Use an outside judge: Do not ask the model to judge itself. ... in October 2026, I implore you to insist on outside validation. Ideally that's a tool the model can run to get feedback immediately."
- The prompt: "I want a deeper version of this task, not a bigger one. Before rewriting it: (1) say what a top professional in this field would do here that I'm not asking for; (2) name the rawest material they would start from instead of what has already been digested for me; (3) name the specific methods and tools they would use; (4) say what, other than you or me, would show the result is right. Then rewrite my prompt to ask for exactly that."

**Range**
- "Try to replace the nouns with verbs ... A quarterly review isn't 'a deck'. It's 'getting busy people to believe a story about cause and effect, and to decide under uncertainty, in 30 minutes'."
- "It is easy to accidentally engage in role play, which will make your transcript weirder without improving the actual outcome. Use this method to find fields and techniques. Don't ask the model to write like a short seller, ask it to do what a short seller does to research their position."

**Prerequisite**
- "All the ways in which I describe ambition require the model to have a computer with the ability to install software and access to all kinds of relevant data."

## Eric Porres, "Friday Edition: Tips Need Evals Too" (2026-10-16)

https://promptedbyeric.substack.com/p/viral-ai-tips-need-evals-too

Design: three candidate rule changes from Felix's prompt, 16 Claude Opus 5.5 agent runs over 4
real tasks, half old rules and half new, pairs shuffled and labels stripped, judged by Claude
Fable 5.1 (web access) and GPT-6 Astra (no web).

- "The new rules won 13–3 with Fable and 11–4, with one tie, with Astra." Lengths averaged 685 vs 695 words.
- "On the investor brief, the winners quoted the 10-K. The losers quoted MarketBeat."
- Failure: "My rule had turned 'primary source' into 'the one document.'" New-rules agents read the EU AI Act and missed the Commission's 2026-07-20 Article 50 guidelines. Fix: "Guidance and amendments count as the system of record, and when an agent can't read the primary in full, it uses the summary's substance with a label instead of dropping it."
- "A judge without tools is just an opinion." (The judges disagreed on 6 of 16 pairs; Astra, without web access, misjudged.)
- Shipped: the system-of-record rule; "Every definition of done needs one check that something other than the author or me can run."
- Held: the practitioner-additions interview, because its effect was confounded with change 2.
- Skipped the "rewrite my prompt" step: "In my setup, that costs a turn and hands me homework when I wanted work."
- "A tip is a hypothesis with good distribution. Run it before you adopt it."

## Elicitation research added 2026-10-24

Prior work: `~/Projects/agent-infra/research/2026-06-18-elicitation-best-practices.md`
(RE canon, Spec Kit assume-and-mark, Active Task Disambiguation). Its top recommendation,
choosing questions by how they split the solution set, was missing from v1 of this skill.
Graded HAD-LEVER and fixed in v2.

Post-June LLM papers (abstracts read via arXiv; full text not read):
- Zhang et al., "Ask Less, Ask Better" (arXiv:2610.24411, 2026-10-17): "limiting agents to one to three questions reduces user-attention cost by 36-73% while keeping 86-94% of the task reward"; "reviewing each question against the memory of users' earlier answers cuts attention cost by another 13%."
- Li et al., "Ask, Relax, or Act?" (arXiv:2610.03102, 2026-10-02): "act when an accepted action is shared across all admissible preferences or objectives, clarify when each possibility is feasible but no action is shared, and propose a minimum-cost permitted constraint repair when the request is infeasible." Models "still intervene when a justified action already exists."
- Tack, Laban, Neville, "LLMs Get Lost in Evolving User Intent" (arXiv:2607.20734): "strong static-setting performance does not transfer to the evolving-intent setting, with substantial drops across model families."
- Kim et al., "What Did the AI Take On?" (arXiv:2610.06328): "participants viewed about half of all steps (48.6%) as AI-initiated, meaning the AI took on work they had not requested."
- Holter et al., "Let Me Clarify: Interactive Modeling of Soft Attributes" (arXiv:2610.20227): softness = "the diversity of valid interpretations a description permits"; soft attributes are turned into executable functions.

Psychology classics (cited from memory, not re-fetched; verify before citing them outside this skill):
- Laddering / means-end chains: Reynolds & Gutman 1988, J. Advertising Research.
- Prospective hindsight: Mitchell, Russo & Pennington 1989, J. Behavioral Decision Making (imagining that an outcome has already happened raised the number of reasons people generated, about 30% in their study); premortem: Klein 2007, HBR.
- Critical Decision Method: Klein, Calderwood & MacGregor 1989 (recall tacit expertise through a specific incident and cue probes).
- Miracle question: de Shazer, solution-focused brief therapy.
- Learning vs performance goals on complex novel tasks: Winters & Latham 1996; Seijts & Latham 2001. Stretch-goal boundary conditions: Sitkin et al. 2011, AMR "The paradox of stretch goals" (help with recent success and slack resources, hurt without them).
