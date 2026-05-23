"""
Uses Claude to summarize and tag the raw items.
"""

import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
MODEL = 'claude-sonnet-4-5'


def summarize_batch(items):
    if not items:
        return []

    compact = []
    for i, it in enumerate(items):
        compact.append({
            'index': i,
            'source': it.get('source', ''),
            'title': it.get('title', ''),
            'date': it.get('date', ''),
            'kind': it.get('kind', ''),
            'phase': it.get('phase', ''),
            'status': it.get('status', ''),
            'abstract': (it.get('abstract') or '')[:900],
        })

    prompt = f"""You are a medical research analyst helping a family track stage 4 metastatic prostate cancer research.

For each input item that is genuinely relevant, return a JSON object:
{{
  "index": <copy from input>,
  "title": "<cleaned plain-English title, 12 words max>",
  "summary": "<3-4 sentence plain-language summary>",
  "category": "treatment" | "trial" | "biomarker" | "lifestyle" | "approval" | "research" | "supportive_care",
  "relevance": "high" | "medium" | "low",
  "keyTerms": ["...", "..."]
}}

Skip items that are: benign prostate only, animal-only studies, unrelated cancers, duplicates.
Mark "relevance: high" only for: FDA approvals, phase 3 results, novel mechanisms with clinical data, biomarker advances, or recruiting trials for metastatic CRPC.
Write summaries a family member can understand.

Items:
{json.dumps(compact, indent=2, ensure_ascii=False)}

Return ONLY a JSON array. No markdown fences. No preamble."""

    msg = client.messages.create(
        model=MODEL,
        max_tokens=12000,
        messages=[{'role': 'user', 'content': prompt}],
    )

    text = msg.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('```', 2)[1]
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    text = text.strip()

    start, end = text.find('['), text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError(f'Could not find JSON array: {text[:300]}')
    parsed = json.loads(text[start:end + 1])

    out = []
    for p in parsed:
        idx = p.get('index')
        if idx is None or idx < 0 or idx >= len(items):
            continue
        orig = items[idx]
        out.append({
            'id': f"agent-{orig.get('source','')[:20]}-{idx}-{orig.get('date','')}".replace(' ', '_'),
            'title': p.get('title') or orig.get('title'),
            'source': orig.get('source'),
            'url': orig.get('url'),
            'date': orig.get('date'),
            'summary': p.get('summary'),
            'category': p.get('category', 'research'),
            'relevance': p.get('relevance', 'medium'),
            'keyTerms': p.get('keyTerms', []),
            'kind': orig.get('kind'),
            'status': orig.get('status', ''),
            'phase': orig.get('phase', ''),
        })
    return out
