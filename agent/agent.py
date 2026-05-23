"""
Satwinder Research Agent — Daily scanner for stage 4 prostate cancer.
"""

import os
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sources import fetch_pubmed, fetch_clinical_trials, fetch_fda
from summarize import summarize_batch

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
LATEST_FILE = DATA_DIR / 'latest.json'
ARCHIVE_DIR = DATA_DIR / 'archive'

LOOKBACK_DAYS = 7

PUBMED_QUERIES = [
    'metastatic prostate cancer',
    'castration-resistant prostate cancer',
    'advanced prostate cancer treatment',
    'PSMA-targeted therapy prostate',
    'lutetium-177 prostate cancer',
    'PARP inhibitor prostate cancer',
    'androgen receptor inhibitor prostate',
]

MAX_ITEMS_TO_SUMMARIZE = 50


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=LOOKBACK_DAYS)).date()
    print(f"[{now.isoformat()}] Scanning items since {since}")

    raw_items = []

    print("-> PubMed")
    for q in PUBMED_QUERIES:
        try:
            items = fetch_pubmed(q, since, max_results=15)
            print(f"   '{q}': {len(items)}")
            raw_items.extend(items)
        except Exception as e:
            print(f"   '{q}' FAILED: {e}", file=sys.stderr)

    print("-> ClinicalTrials.gov")
    try:
        items = fetch_clinical_trials(since, max_results=30)
        print(f"   {len(items)} trials")
        raw_items.extend(items)
    except Exception as e:
        print(f"   FAILED: {e}", file=sys.stderr)

    print("-> FDA press releases")
    try:
        items = fetch_fda(since, max_results=15)
        print(f"   {len(items)} items")
        raw_items.extend(items)
    except Exception as e:
        print(f"   FAILED: {e}", file=sys.stderr)

    seen, unique = set(), []
    for it in raw_items:
        key = it.get('url') or it.get('title', '')
        if key and key not in seen:
            seen.add(key)
            unique.append(it)

    print(f"Total unique: {len(unique)}")

    unique.sort(key=lambda x: x.get('date', ''), reverse=True)
    to_summarize = unique[:MAX_ITEMS_TO_SUMMARIZE]
    print(f"Summarizing top {len(to_summarize)} with Claude...")

    summarized = summarize_batch(to_summarize)
    print(f"Got {len(summarized)} summarized items")

    output = {
        'generatedAt': now.isoformat(),
        'lookbackDays': LOOKBACK_DAYS,
        'count': len(summarized),
        'sources': {
            'pubmed': sum(1 for x in summarized if 'pubmed' in (x.get('url') or '').lower()),
            'trials': sum(1 for x in summarized if 'clinicaltrials' in (x.get('url') or '').lower()),
            'fda': sum(1 for x in summarized if 'fda' in (x.get('url') or '').lower()),
        },
        'items': summarized,
    }

    DATA_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    LATEST_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    archive = ARCHIVE_DIR / f"{now.date().isoformat()}.json"
    archive.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"Wrote {LATEST_FILE.relative_to(ROOT)}")
    print(f"Wrote {archive.relative_to(ROOT)}")
    print("Done.")


if __name__ == '__main__':
    main()
