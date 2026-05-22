"""
Sends raw items to Claude in one batched call, gets back plain-language
summaries plus tags (category, relevance, key terms).
"""

import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
MODEL = 'claude-sonnet-4-5'


def summarize_batch(items: list) -> list:
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

You'll receive a list of recent items from PubMed, ClinicalTrials.gov, and FDA press releases. For each item that is genuinely relevant to stage 4 / metastatic / castration-resistant prostate cancer, return a JSON object:

{{
  "index": <copy from input>,
  "title": "<cleaned plain-English title, 12 words max>",
  "summary": "<3-4 sentence plain-language summary covering: what was studied/announced, the key finding, and what it means for a patient with advanced disease>",
  "category": "treatment" | "trial" | "biomarker" | "lifestyle" | "approval" | "research" | "supportive_care",
  "relevance": "high" | "medium" | "low",
  "keyTerms": ["...", "..."]  // 2-5 keywords: drug names, biomarkers (BRCA, MSI, PSMA, AR-V7), trial phase, technique
}}

Rules:
- SKIP items that are: benign prostate conditions only, animal-only studies with no clear human relevance, unrelated cancers, retracted papers, or duplicates.
- Mark "relevance: high" only for: practice-changing findings, FDA approvals, phase 3 trial results, novel mechanisms with clinical data, biomarker advances that change treatment selection, or recruiting trials accepting metastatic CRPC patients.
- Write summaries a worried family member can understand — no jargon without a 2-word explanation.
- Be honest. If the abstract is thin or the finding is preliminary, say so.

Items:
{json.dumps(compact, indent=2, ensure_ascii=False)}

Return ONLY a JSON array. No markdown fences. No preamble."""

    msg = client.messages.create(
        model=MODEL,
        max_tokens=12000,
        messages=[{'role': 'user', 'content': prompt}],
    )

    text = msg.content[0].text.strip()
    # Strip markdown fences if Claude added them
    if text.startswith('```'):
        text = text.split('```', 2)[1]
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    text = text.strip()

    start, end = text.find('['), text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError(f'Could not find JSON array in response: {text[:300]}')
    parsed = json.loads(text[start:end + 1])

    # Merge Claude's analysis back with original metadata
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
