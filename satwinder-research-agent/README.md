# Satwinder Research Agent

Daily automated scanner for stage 4 metastatic prostate cancer research.

Runs every morning at 6 AM Eastern. Scans **PubMed**, **ClinicalTrials.gov**, and **FDA press releases** for the past 7 days. Has Claude summarize each finding in plain English and write the results to `data/latest.json`, which your dashboard reads.

---

## What you'll need

1. A **free GitHub account** — https://github.com/signup
2. An **Anthropic API key** — about $1–3/month in usage at this volume, paid as you go. (This is separate from a Claude.ai subscription.)

That's it. No servers to manage, no Python to install on your computer.

---

## One-time setup (about 15 minutes)

### Step 1 — Get your Anthropic API key

1. Go to https://console.anthropic.com
2. Sign in (you can use your Claude.ai account)
3. Click **Settings** (left sidebar) → **API Keys** → **Create Key**
4. Name it "research-agent", click Create
5. **Copy the key** (it starts with `sk-ant-…`). You'll only see it once — keep it somewhere safe for the next steps.
6. On the **Billing** page, add $10 in credits. That will last you many months at one scan per day.

### Step 2 — Create the GitHub repository

1. Go to https://github.com/new
2. Repository name: `satwinder-research-agent` (or anything you like)
3. **Public** is fine — the data flowing through is published medical research, not personal info. Choose Private if you prefer; the setup is identical.
4. Do **not** check "Initialize with README" (we have one).
5. Click **Create repository**.

### Step 3 — Upload the files

The easiest way:

1. On the new empty repository page, click **"uploading an existing file"** (it's in the quick-setup section in the middle of the page).
2. Drag this entire `satwinder-research-agent` folder into the upload area. GitHub will preserve the folder structure.
3. Scroll down, write a commit message like "Initial setup", and click **Commit changes**.

> Alternative if you know git: `git clone` the empty repo, copy these files in, `git add . && git commit -m "init" && git push`.

### Step 4 — Add your API key as a repo secret

1. In your new repo, go to **Settings** (top tab) → **Secrets and variables** → **Actions**.
2. Click **New repository secret**.
3. Name: `ANTHROPIC_API_KEY` (exactly this, all caps with underscores)
4. Secret: paste your `sk-ant-…` key
5. Click **Add secret**.

### Step 5 — Enable Actions and trigger the first run

1. Go to the **Actions** tab of your repo.
2. If GitHub asks "Workflows aren't being run on this repository," click **I understand my workflows, go ahead and enable them**.
3. On the left, click **Daily Research Scan**.
4. Click the **Run workflow** dropdown → **Run workflow** (green button). This kicks off the scan immediately so you don't have to wait until tomorrow morning.
5. After ~2 minutes, refresh — you'll see a green check ✅ if it worked. Click into the run to see logs if it failed.

### Step 6 — Connect to your dashboard

Once the first run succeeds:

1. In your repo, navigate to **`data/latest.json`**.
2. Click the **Raw** button (top-right of the file view).
3. **Copy that URL.** It will look like:  
   `https://raw.githubusercontent.com/yourusername/satwinder-research-agent/main/data/latest.json`
4. Open your dashboard, go to **Profile** (Settings) tab, scroll down to **Daily Agent**, and paste the URL there. Save.
5. Click **Sync now** in the Research tab. The items will flow in.

You're done. The agent will run every morning. The dashboard will auto-pull on each open, and you can also click **Sync now** any time.

---

## How to change what it tracks

Open `agent/agent.py`. At the top you'll see:

```python
PUBMED_QUERIES = [
    'metastatic prostate cancer',
    'castration-resistant prostate cancer',
    ...
]
```

Add or remove queries to match Satwinder's situation as it evolves. For example, if he starts a PARP inhibitor, you might add `'olaparib prostate cancer'`. Commit the change to the repo — the next morning's run picks it up automatically.

Same for `LOOKBACK_DAYS` (default 7) if you want a longer or shorter window.

---

## Cost expectations

At one scan per day with up to 50 items summarized:
- Roughly **5,000–15,000 input tokens** + **2,000–5,000 output tokens** per day
- That's about **$0.05–0.15 per day** = **$1.50–$4.50 per month**

GitHub Actions is free for public repos (2,000 minutes/month for private — way more than you'll use).

---

## If something breaks

- **Workflow fails immediately**: Check the secret name is exactly `ANTHROPIC_API_KEY`.
- **API errors**: Check your Anthropic billing balance.
- **No items returned**: Open the run logs (Actions → click the failed run → click the "Run agent" step). The script prints what it found from each source.
- **Dashboard says "fetch failed"**: Make sure the URL is the **raw** URL (contains `raw.githubusercontent.com`), not the regular GitHub page URL.

If you get stuck, paste the error into a chat with Claude — I can debug it.

---

## What's NOT in here (deliberately)

- **Personal info.** The agent does broad scans on stage 4 prostate cancer. Personalization — matching findings to Satwinder's specific profile — happens locally in the dashboard, which keeps his medical details out of any public repo.
- **Journal RSS feeds.** Many top journals (NEJM, Lancet, JCO) require subscriptions for RSS. PubMed indexes them all anyway, usually within a few days, so we get them via PubMed for free.
- **Email digests.** Could be added later as a GitHub Action that emails you the summary. Ask if you want it.
