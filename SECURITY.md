# SECURITY.md — Data Sovereignty

Person C owns this document and this section of the pitch.

**Claim: this system processes data entirely on the machine it runs on, and
never transmits anything to any external host.**

Below is how to verify that rather than take our word for it.

---

## The architecture claim

```
Your data  ->  Your computer  ->  Local model  ->  Your screen
                     |
              (no path outward)
```

Compare with a cloud AI integration:

```
Your data  ->  Internet  ->  Vendor servers (foreign jurisdiction)  ->  back
```

For a project whose subject is sovereign semiconductor capability, sending
every query to a foreign API would contradict the thesis. So we don't.

---

## What the code actually does

**During the demo, exactly one file opens a socket:** `ai/ai_local_claude.py`.

It uses `urllib` against a single hard-coded address:

```python
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
```

`127.0.0.1` is the loopback interface. Traffic to it never reaches a network
adapter — the operating system routes it back to the same machine. A packet
sent to loopback cannot leave the computer even if a network cable is
attached.

**There is no other network code.** No `requests`, no `httpx`, no SDK, no API
key, no environment variable holding a token. Verify with:

```bash
grep -rniE "urllib|socket|requests|httpx|api[_-]?key|token" --include=*.py .
```

Hits fall into exactly three files: `ai_local_claude.py` (loopback only),
`demo_proof.py` (which *blocks* sockets, see below), and
`phase1_cloud_extract.py` — described next.

---

## The one file that does use the internet

`ai/phase1_cloud_extract.py` contacts `api.anthropic.com`. Do not hide this;
it is Phase 1 of the stated architecture, and the pitch is stronger for
explaining it.

| | |
|---|---|
| **When it runs** | Once, during preparation. Never during the demo. |
| **What it sends** | 12 fixed textbook questions, hard-coded in the file |
| **What it does NOT send** | Component data, costs, suppliers, experiment CSVs, optimizer output, judge input — anything at all about this project |
| **What it produces** | `claude_cloud_knowledge.json`, which then stays local forever |

**The "only generic questions leave" claim is enforced in code, not asserted.**
Before any socket opens, every outgoing question is screened against a
blocklist built live from the project's own data — every supplier name,
component name, component ID and cost figure in `components.csv`, plus a list
of project identifiers. A single hit aborts the run before the network is
touched.

Demonstrate it without a network connection:

```bash
python ai/phase1_cloud_extract.py --check
```

```bash
python ai/phase1_cloud_extract.py --dry-run
```

`--check` runs the screen. `--dry-run` prints the exact outbound payload — a
judge can read every byte that would leave the machine, and confirm none of it
concerns the project.

The screen has been verified against deliberate leaks. A question phrased
*"Why is our collector cheaper than the ZEISS Ru-capped collector 5 sr?"* is
blocked on three separate terms and never sent.

**Why this doesn't contradict the sovereignty argument.** The claim is not
"this project never touches a foreign server". It is *"your data never leaves
your machine"* — and that holds. What crosses the border in Phase 1 is
textbook physics flowing **inward**. Nothing about the design, the costs, the
suppliers, or anything a judge types goes outward, at any stage. That is
precisely the pattern the pitch advocates: use global knowledge, bring the
capability inside your borders, keep your data local.

If a judge asks whether the project could run with no internet access ever:
yes. `phase1_generate_knowledge.py` builds a grounded fact base from Person
A's data with zero network calls, and the demo runs on that alone. The cloud
step adds general physics background; it is not load-bearing.

---

## How we prove it, live

`demo_proof.py` claim 9 does not describe the offline property. It enforces it.

Before running the full pipeline, it replaces `socket.socket` with a function
that raises:

```python
def _refuse(*args, **kwargs):
    raise OSError("network access blocked by offline proof")

socket.socket = _refuse
```

Then it runs the entire optimisation, simulation, particle model, data
learning and AI analysis. If any line of code anywhere in the project tried to
open any socket — to any host, loopback included — the pipeline would raise
and the claim would fail.

It passes.

```bash
python demo_proof.py
```

That is a stronger guarantee than a firewall rule, because it tests the code
rather than the environment.

---

## The physical demonstration

For judges, do it in the room:

1. Turn off WiFi. Show the taskbar indicator.
2. Unplug ethernet if connected.
3. Run the demo.
4. Move a slider. Results recalculate.
5. Open the AI screens. Analysis appears.

Nothing degrades, because there was never a call to degrade.

**Rehearse this before Day 3.** Person D's second-laptop clean-clone test and
this offline test should be run together — a clean clone with no network is
the exact condition a judge could impose.

---

## Where the AI runs

| | Cloud API | This project |
|---|---|---|
| Model location | Vendor datacentre | This machine's disk |
| Data leaves device | Yes, every call | No |
| Jurisdiction | Vendor's country | Yours |
| Works offline | No | Yes |
| Cost per call | Metered | Zero |
| Available in demo | Needs connectivity | Always |

The local model is served by [Ollama](https://ollama.com), which binds to
loopback by default. The model weights sit on local disk. Inference is local
CPU/GPU.

---

## Honest limitations — state these before a judge finds them

**1. The local model is small.**
A 7B parameter model is not comparable to a frontier model. It is adequate for
constrained explanatory text over facts we supply, and it is *not* doing the
optimisation. The optimizer is deterministic Python. The AI explains results;
it does not produce them. If the model were removed entirely, every number in
the demo would be unchanged.

**2. We did not fine-tune, and the pitch document currently says we did.**

The project document states, for Phase 2:

> "Claude's reasoning ability is **baked into the local model weights**
> during Phase 2"

**That sentence is not true of what this code does, and it must be corrected
before the pitch.** `ollama create` applies a system prompt, decoding
parameters and an injected fact base to a *frozen* Mistral. No weights are
updated. No gradients are computed. There is no training set, no loss curve,
no adapter.

The accurate version of the same slide:

> "Claude's *knowledge* is extracted once in Phase 1 and baked into the local
> model's **context** in Phase 2 — a constrained system prompt plus a
> generated fact base on a frozen open-weights model, with a validator in
> front of its output. The weights are Mistral's; the grounding is ours."

That is both true and stronger, because it survives the follow-up question.
An ML-literate judge who hears "baked into the weights" will ask what you
fine-tuned on and what your loss curve looked like, and there is no answer.
The honest version invites a better question — why a validator beats a light
fine-tune for factual correctness — which you can answer well.

Real weight-level training would need a LoRA adapter via llama.cpp or unsloth
on a GPU, then `FROM ./adapter` in the Modelfile. That is a multi-day job and
was never in scope for a three-day build. Saying so out loud demonstrates you
understood the tradeoff rather than missed it.

See the header of `phase2_finetune_local.py` for the same explanation next to
the code.

**3. There is a rule-based fallback, and it is not AI.**
If Ollama is not installed or not running, `ai_local_claude.py` returns
deterministic template output so the demo never dies mid-pitch. That output is
labelled `"backend": "rule_based"` and the frontend must display the label.
Presenting rule-based text as model output would be dishonest, and it is the
one failure mode in this layer that would genuinely deserve criticism.

**4. Offline is a property of our code, not of your machine.**
We guarantee this project makes no external calls. We do not control what else
is installed on the computer it runs on.

**5. Ollama binds to loopback by default, but that is configurable.**
If someone sets `OLLAMA_HOST=0.0.0.0`, the daemon becomes reachable from the
local network. That is a deployment choice outside our code. Leave it at the
default.

---

## Questions to rehearse

**"How do I know it's not calling home?"**
One file opens sockets, hard-coded to 127.0.0.1. `demo_proof.py` blocks all
sockets and runs the whole pipeline anyway. Run it yourself. Or unplug the
network and watch the demo work.

**"Is this actually AI or just if-statements?"**
Both are present and they are labelled differently. With Ollama running you
get a local 7B model. Without it you get deterministic rules, marked
`rule_based` on screen. We won't blur the two — and either way, the numbers
come from deterministic physics, not from the model.

**"What did you fine-tune on?"**
Nothing. We ran a frozen model with a constrained system prompt and a
generated fact base, and put a validator in front of its output that rejects
any claim outside the published physical envelope. Weight-level training on a
laptop in three days wasn't realistic, and the validator does more for
correctness than a light fine-tune would have.

**"What stops the model making up numbers?"**
`check_envelope()` in `ai_local_claude.py`. Bounds come from Person A's
`VALIDATION_REPORT.md`. A claim of 95% mirror reflectivity is rejected before
display, because the published ceiling is 75%.
