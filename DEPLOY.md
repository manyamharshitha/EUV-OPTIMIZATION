# Deploying to AWS EC2

The app is pure Python standard library — no `pip install`, no `requirements.txt`
— and the React bundle is committed in `web/dist`. So a deployment is: get the
repo onto a box with Python 3.10+, run it as a service, put nginx in front.

**Architecture on the instance**

```
internet ──▶ nginx :80 ──▶ 127.0.0.1:8000 (serve.py, systemd unit "euv-optimizer")
```

nginx is not decoration. `serve.py` uses the standard library's `http.server`,
which Python's own documentation says is **not intended for production** — it
has no rate limiting, no request-size caps, and no defence against slow-client
attacks. nginx handles the hostile side of the internet; the Python process
binds loopback only and is never directly reachable from outside the instance.

---

## Before you start

- An AWS account, and the ability to launch an instance in it.
- An SSH key pair (create one in the EC2 console at *Network & Security → Key
  Pairs* if you don't have one).
- **Set a billing alarm first.** *Billing → Budgets → Create budget → Zero
  spend budget.* This is the single most useful five minutes you can spend; it
  emails you the moment anything starts costing money.

## Cost

A `t3.micro` is free-tier eligible for 750 hours/month for the first 12 months
on a new account — enough to run one instance continuously. Outside that it is
roughly **$7–9/month** on-demand, plus about **$3.60/month** for an Elastic IP
*if you allocate one and leave the instance stopped*. Free-tier terms have
changed for accounts created recently, so confirm yours at
<https://aws.amazon.com/free/> rather than trusting this paragraph.

---

## 1. Launch the instance

EC2 console → **Launch instance**.

| Setting | Value |
|---|---|
| Name | `euv-optimizer` |
| AMI | **Ubuntu Server 24.04 LTS** |
| Instance type | `t3.micro` |
| Key pair | your key pair |
| Storage | 8 GiB gp3 (the default) is plenty — the repo is ~2 MB |

**AMI choice matters.** Ubuntu 24.04 ships Python 3.12. This codebase needs
3.10+ (it uses PEP 604 `X | None` annotations). Amazon Linux 2023 defaults to
Python 3.9 and would fail without an extra install step.

Under **Network settings → Edit**, create a security group with exactly two
inbound rules:

| Type | Port | Source | Why |
|---|---|---|---|
| SSH | 22 | **My IP** | Never `0.0.0.0/0`. Open SSH is scanned within minutes. |
| HTTP | 80 | `0.0.0.0/0` | So judges can reach the demo. |

Under **Advanced details → User data**, paste the contents of
[`deploy/user-data.sh`](deploy/user-data.sh). It installs git, nginx and
Python, clones this repo to `/opt/euv-optimizer`, installs the systemd unit and
the nginx site, starts both, and then polls `/api/health` so that a failure
shows up in the boot log rather than as a blank page later.

Launch it.

## 2. Verify

First boot takes about 60–90 seconds. Then, from your machine:

```bash
curl -s http://<PUBLIC-IP>/api/health
```

You should get JSON back. Open `http://<PUBLIC-IP>/` in a browser for the app.

If it doesn't come up, SSH in and look:

```bash
ssh -i <your-key.pem> ubuntu@<PUBLIC-IP> "sudo journalctl -u euv-optimizer -n 50 --no-pager; sudo tail -40 /var/log/cloud-init-output.log"
```

## 3. Updating after a push

```bash
ssh -i <your-key.pem> ubuntu@<PUBLIC-IP> "cd /opt/euv-optimizer && sudo git fetch --depth 1 origin main && sudo git reset --hard origin/main && sudo chown -R euv:euv . && sudo systemctl restart euv-optimizer"
```

`web/dist` is committed, so there is no build step on the server.

## 4. Tearing it down

**Do this when the hackathon is over.** A running instance bills whether or not
anyone visits it.

EC2 console → select the instance → *Instance state → Terminate*. Then check
*Elastic IPs* and release any you allocated — an unattached Elastic IP is
charged by the hour.

---

## Known limitations of this deployment

Read these before you put the URL in front of anyone.

**There is no authentication.** Every route is open to whoever has the address.
The app holds no user data and no secrets, so the exposure is compute, not
information — but anyone can run the optimizer as often as nginx's rate limit
allows.

**It is HTTP, not HTTPS.** Traffic is in the clear and browsers will mark it
"Not secure". For a demo that is usually tolerable. To fix it you need a domain
name pointed at the instance, then:

```bash
sudo apt-get install -y certbot python3-certbot-nginx && sudo certbot --nginx -d your-domain.example
```

Certbot cannot issue a certificate for a bare IP address, so the domain is a
prerequisite, not an optional extra.

**The AI analysis will label itself `rule_based`, not `local_model`.**
`ai/ai_local_claude.py` probes Ollama on `127.0.0.1:11434`. There is no Ollama
on this instance, and a 7B model would not fit on a `t3.micro` anyway. The app
degrades honestly by design — the analysis still appears, correctly labelled.
If your pitch claims a local model, either say "on the local demo machine" or
deploy Ollama on a much larger instance.

**A single `t3.micro` is one small box.** No autoscaling, no redundancy. If it
falls over mid-demo, the local `python serve.py` remains the reliable path —
and `demo_proof.py` still certifies the whole pipeline runs with the network
pulled, which is the stronger claim anyway.
