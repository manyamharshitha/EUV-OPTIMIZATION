> **Nobody has run this yet.** Everything below is written to be rehearsed
> out loud, five times, with one person playing a hostile judge. A team that
> has rehearsed five times beats a team with better code that has rehearsed
> zero times, and that is not a close call.

---

## Before anything else

```bash
python preflight.py
```

Five seconds. If it exits non-zero, you know what to say about it before you
walk on. Run it again after any reboot.

---

## Running order — 10 minutes

Times are targets. The demo is interactive, so the middle will drift; protect
the opening and the closing, they are what gets remembered.

### 0:00–0:45 — The problem, in one breath

**D speaks.**

> "An EUV lithography machine costs about $183 million and only one company
> on earth can build one. We built a tool that asks: if you had to build one
> somewhere else, what would you actually need, what would it cost, and what
> would you have to invent first."

Do not explain EUV physics yet. Do not open with the architecture. Say what
the tool answers.

### 0:45–2:00 — The optimizer running

**D drives, B narrates.**

Set budget $180M, efficiency 50%, timeline 8 years. Run it.

> "That evaluated all 19,440 possible machines — not a sample, every one —
> and ranked the top five. 1.7 seconds."

**B, immediately, unprompted:**

> "The $183M system total is a published figure. The split across the eight
> subsystems is our engineering estimate. Nobody publishes a bill of
> materials for an EUV scanner, so we anchored to the real price and
> apportioned it. The total is defensible, any individual line is an
> estimate."

That sentence is not optional and it does not go later. Say it the first
time a cost appears on screen.

### 2:00–3:30 — Move a slider, then break it

**D drives.**

Drag the budget down. Results recompute — 0.04s, feels instant.

Now drag it to $90M so it returns nothing, and let the failure show:

> "Nothing satisfies that. And rather than a blank screen, it tells you
> which constraint is responsible — each limit is reachable alone, it's the
> combination that fails, and the cheapest machine buildable in five years
> is $124.7 million."

A tool that explains its own failure reads as engineering. A blank panel
reads as a bug.

### 3:30–5:00 — The moment that decides your credibility

**D switches to the cost-focused weighting, and drops the efficiency floor to
30%.** Savings jump to **46%**.

> ⚠️ **Drop the efficiency floor, or this moment doesn't happen.** At the
> default 50% floor the same weighting gives 27% savings with only 2 of 8
> parts hypothetical — `high`, not `critical`. It's the 30% floor that lets
> the optimizer reach for the cheap non-existent parts and produces the 7-of-8
> configuration. Verify with `python disclosure.py` before you present:
> you want `severity: critical` and `7 of 8`.

**B speaks before the judge finishes reading the number:**

> "Stop me there, because that number is not what it looks like. Seven of the
> eight parts in that configuration do not exist. They're specified targets
> we defined, not products anyone can buy. The tool flags it — that red band
> is generated from the configuration, not typed in."

Then:

> "That's the actual output of this project. Not 'India can build an EUV
> machine for $130 million.' It's: here are the four components where
> domestic capability would move the cost most, ranked, with what each one
> would have to achieve."

**If a judge discovers the hypothetical parts before you say this, you have
lost the room.** This is the single highest-stakes 40 seconds in the demo.

### 5:00–6:30 — Physics, and a number you don't reach

**B drives.**

Show the simulation: 30 kW laser → tin plasma → 249 W at intermediate focus
→ 1.5% through ten mirrors → 14.7 nm printed → 165 wafers/hour.

> "Resolution is 14.7 nanometres. We do not reach 7, and we don't claim to —
> Rayleigh gives k1 lambda over NA, and at NA 0.33 that's 14.3. Getting to 7
> needs High-NA optics or multi-patterning. The tool prints what the physics
> gives, not the marketing node name."

Volunteering a number you fail to hit buys more credibility than any number
you hit.

### 6:30–8:00 — Kill the WiFi

**C drives. This is your best moment — do not rush it.**

1. Turn off WiFi in front of them. Show the taskbar icon.
2. Move a slider. Everything recomputes.
3. Open the AI panel. Analysis appears.
4. Show the line: `OLLAMA_HOST = "127.0.0.1"`
5. `grep -r "api_key" --include=*.py .` → nothing.

> "There's no API key in this codebase. The only socket this demo opens is
> to 127.0.0.1, which is this laptop. And we don't just claim that —"

```bash
python demo_proof.py
```

> "That replaces the socket constructor with a function that raises, then
> runs the entire pipeline. If any line anywhere tried to open any
> connection, it fails. 45 out of 45."

> ⚠️ **Start `serve.py` at least ten minutes before you present.**
>
> The local model runs on CPU — no dedicated GPU on this laptop — and a full
> analysis pass is roughly six minutes. The server warms that cache in the
> background at startup, so screen 7 opens instantly *if the server has been
> up a while*. Launch it, watch for `AI cache ready` in the terminal, then
> present.
>
> If you change a slider to a configuration nobody has visited and then open
> screen 7, you will hit an uncached generation and wait. During the demo,
> either stay on the default configuration for screen 7, or open screen 7
> early to warm it.

**If Ollama is not installed, say this instead, before they read the label:**

> "Full disclosure — that panel is rule-based right now, not the model. The
> local model isn't loaded on this machine. Every number on screen is
> deterministic Python either way; the AI explains results, it doesn't
> produce them."

**If the model IS loaded, this is a much stronger moment:**

> "That analysis was generated by a 7-billion-parameter model running on this
> laptop's CPU. No GPU, no API key, no network. Ask it whether we hit 7 nm."

Then run it in front of them:

```bash
ollama run my-claude-local "Can this machine reach 7 nm resolution?"
```

> "No, the half-pitch of this machine is 14.3 nm, which is larger than 7 nm.
> To achieve 7 nm resolution, High-NA optics or multi-patterning would be
> required."

A local model refusing to overclaim, on demand, with the WiFi off, is the
single most convincing thing in this demo.

### 8:00–9:00 — The honesty slide

**A drives.**

> "46.4% of our components carry a real citation. The rest are marked
> MODELED in the data itself. That number is computed live from the files —
> we can't drift from it, because the proof suite prints it."

> "We also found a bug in our own physics doing this. Our first throughput
> figure was 421 wafers per hour. The fastest EUV scanner ever shipped does
> about 150. We'd calibrated at the wrong dose. It's in the validation
> report, and it's fixed."

Admitting a caught bug is the strongest credibility move available to you.
It proves the checking is real.

### 9:00–10:00 — Close

**D speaks.**

> "Three things. It's exhaustive — every combination, not a heuristic. It's
> honest — every number is either cited or labelled as ours. And it runs
> with the network physically disconnected, which for a project about
> sovereign technology isn't a feature, it's the argument."

---

## Hostile judge Q&A

One person plays this role every rehearsal. Their job is to be unpleasant.

### For A — the numbers

**"Where did the component costs come from?"**
> The system total is published, around $183 million. The split across
> subsystems is ours. No public bill of materials exists. We can defend the
> total; the split is an engineering estimate and we'd revise it the moment
> better data existed.

**"So you made them up."**
> We apportioned a real published total by relative complexity. That's an
> estimate, and it's labelled as one in the data. What we did not do is
> invent a citation for it.

**"Your components add up to more than your own benchmark."**
> They did — $294 million against a $200 million benchmark. We traced it to
> double counting: the same hardware described at three levels of
> abstraction. Reconciled it's $182 million, within 9% of the benchmark, and
> the reconciliation lists every excluded line with the reason.

**"Is 5% conversion efficiency real?"**
> Published range is 2% to 6% depending on target geometry; production runs
> 5–6%. Gigaphoton published 5.2% peak, 4.7% average. We use 5%.

**"Which of these numbers would you bet on?"**
> Wavelength, numerical aperture, mirror count, the ISO limits — those are
> settled and cited. Conversion efficiency I'd give you as a range. Any
> per-component cost is our estimate and I'd expect to be wrong.

### For B — the algorithm

**"How does it actually work?"**
> Eight component categories, each with alternatives. Cartesian product is
> 19,440 machines. For each we compute total cost, multiply the efficiencies
> down the chain, take the longest lead time, drop anything violating your
> constraints, then score the rest on normalised cost, efficiency and
> timeline. No heuristics, no sampling, no randomness.

**"Is it really exhaustive, or do you prune?"**
> Really exhaustive. It prints the count. Same input gives bit-identical
> output every time — that's a verified claim, not a description.

**"19,440 is nothing. What happens at real scale?"**
> It's a Cartesian product, so it grows exponentially — that's the honest
> answer. At this size exhaustive search is correct and provable. Past a few
> million you'd need branch-and-bound or an ILP formulation. We chose
> provably optimal at demo scale over approximately optimal at a scale we
> don't have data for.

**"Your savings come from parts that don't exist."**
> Yes — and the tool says so before you ask. Seven of eight in that
> configuration. Tick "real suppliers only" and the saving drops to about
> 13%, all from parts you can order today. Both numbers are one checkbox
> apart, and we show you both.

**"Why should I trust your physics?"**
> Don't — check it. Rayleigh, multiplicative mirror losses, ISO 14644-1.
> Our first throughput number was 3× too high and our own validation caught
> it. The report is in the repo with the derivation.

### For C — the security

**"How do I know it isn't calling home?"**
> One file opens sockets, hard-coded to 127.0.0.1. The proof suite blocks
> all sockets and runs the whole pipeline anyway. Or unplug the network and
> watch it work — that's faster than reading the code.

**"Is this actually AI or just if-statements?"**
> Both exist and they're labelled differently. With the model loaded you get
> a local 7B. Without it you get deterministic rules, marked `rule_based` on
> screen. We won't blur them. Either way the numbers come from physics, not
> the model.

**"What did you fine-tune on?"**
> Nothing, and the word fine-tune is wrong. We ran a frozen Mistral with a
> constrained system prompt, a generated fact base, and a validator that
> rejects any claim outside the published envelope. Weight-level training on
> a laptop in three days wasn't realistic, and the validator does more for
> correctness than a light fine-tune would.

**"So the AI isn't doing anything."**
> It explains; it doesn't decide. Delete the model entirely and every number
> in the demo is identical. That's deliberate — we didn't want an LLM in the
> path of a number a judge might check.

### For D — the product

**"Could I run this myself?"**
> The optimizer runs anywhere — standard library, no installs. The local
> model needs a one-time 4 GB download, so on your laptop you'd see the
> rule-based fallback. That's the same reason this is a sovereignty pitch and
> not a portability pitch.

**"What's actually novel here?"**
> Not the optimization — it's a Cartesian product. What's unusual is that
> every number is either cited or labelled as ours, live from the data, and
> the tool volunteers its own weak points on screen before you find them.

**"Why should anyone care?"**
> The question "what would it take to build this somewhere else" currently
> gets answered with opinion. This answers it with an enumerated search over
> real published specifications, and tells you which parts of the answer are
> guesses.

---

## When something breaks

| Failure | Do this |
|---|---|
| App won't start | Terminal: `python inspect_backend.py`. All nine screens dump as text. Say "let me show you the raw output" and keep going. |
| AI panel is slow | Expected on CPU — 15–40 s. Keep talking. Don't stare at it. |
| AI panel is empty | "The local model isn't responding. The fallback should have caught that — that's a bug and I'd want to know why." Then move on. Do not debug live. |
| Constraints return nothing | Not a failure — it's a feature. Read the diagnostic aloud. |
| Laptop dies | Second laptop, already tested from a clean clone. **This only works if Ollama is installed there too.** |
| A number looks wrong to a judge | "Possible — where would you check it?" Then look it up together. Never defend a number you haven't verified. |

---

## Rehearsal protocol

**Five run-throughs minimum.** Rotate the hostile judge each time.

1. **Timing pass.** Nobody interrupts. Are you under 10 minutes?
2. **Interruption pass.** Judge interrupts twice mid-sentence.
3. **Hostile pass.** Judge uses only the questions above, in the worst order.
4. **Failure pass.** Someone kills WiFi at a random moment, or force-quits
   the app. Practise recovering without panic.
5. **Clean pass.** Full run, second laptop, from a fresh clone.

After each: one sentence each on what to change. Not a discussion — a
sentence.

**Two things to check every single time:**

- Did the hypothetical-parts disclosure get said **before** the judge read
  the savings number?
- Did the cost-basis disclosure get said the **first** time a dollar figure
  appeared?

Those two sentences are the difference between "rigorous" and "overclaiming",
and they are the first things to get dropped when you're nervous.
