"""
Data source fetchers. All use free public APIs.
"""

import requests
import xml.etree.ElementTree as ET
import feedparser
from datetime import date

PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CTGOV = "https://clinicaltrials.gov/api/v2/studies"
FDA_RSS = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"
UA = "satwinder-research-agent/1.0 (family caregiver use)"


def fetch_pubmed(query, since, max_results=15):
    search = {
        'db': 'pubmed',
        'term': f'({query}) AND ("{since:%Y/%m/%d}"[Date - Publication] : "3000"[Date - Publication])',
        'retmax': max_results,
        'retmode': 'json',
        'sort': 'pub_date',
    }
    r = requests.get(f"{PUBMED}/esearch.fcgi", params=search,
                     headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    ids = r.json().get('esearchresult', {}).get('idlist', [])
    if not ids:
        return []

    r = requests.get(f"{PUBMED}/esummary.fcgi",
                     params={'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'json'},
                     headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    metadata = r.json().get('result', {})

    abstracts = {}
    try:
        r = requests.get(f"{PUBMED}/efetch.fcgi",
                         params={'db': 'pubmed', 'id': ','.join(ids),
                                 'rettype': 'abstract', 'retmode': 'xml'},
                         headers={'User-Agent': UA}, timeout=30)
        if r.ok:
            root = ET.fromstring(r.text)
            for article in root.iter('PubmedArticle'):
                pmid = article.findtext('.//PMID')
                parts = [t.text or '' for t in article.findall('.//Abstract/AbstractText')]
                if pmid and parts:
                    abstracts[pmid] = ' '.join(parts).strip()
    except Exception:
        pass

    items = []
    for pid in ids:
        d = metadata.get(pid, {})
        if not d:
            continue
        items.append({
            'source': d.get('fulljournalname') or d.get('source', 'PubMed'),
            'title': d.get('title', '').strip(),
            'url': f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
            'date': (d.get('pubdate') or '')[:10],
            'abstract': abstracts.get(pid, '')[:2000],
            'kind': 'paper',
        })
    return items


def fetch_clinical_trials(since, max_results=30):
    params = {
        'query.cond': 'metastatic prostate cancer',
        'filter.advanced': f'AREA[LastUpdatePostDate]RANGE[{since.isoformat()},MAX]',
        'pageSize': max_results,
        'format': 'json',
        'sort': 'LastUpdatePostDate:desc',
    }
    r = requests.get(CTGOV, params=params, headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    studies = r.json().get('studies', [])

    items = []
    for s in studies:
        ps = s.get('protocolSection', {})
        ident = ps.get('identificationModule', {})
        status_mod = ps.get('statusModule', {})
        design = ps.get('designModule', {})
        desc = ps.get('descriptionModule', {})

        nct = ident.get('nctId', '')
        items.append({
            'source': 'ClinicalTrials.gov',
            'title': ident.get('briefTitle', ''),
            'url': f"https://clinicaltrials.gov/study/{nct}" if nct else '',
            'date': status_mod.get('lastUpdatePostDateStruct', {}).get('date', ''),
            'abstract': (desc.get('briefSummary') or '')[:2000],
            'kind': 'trial',
            'status': status_mod.get('overallStatus', ''),
            'phase': ', '.join(design.get('phases', [])) if design.get('phases') else '',
        })
    return items


def fetch_fda(since, max_results=15):
    feed = feedparser.parse(FDA_RSS)
    items = []
    keywords = ['prostat', 'oncolog', 'cancer', 'tumor', 'metastat', 'urolog',
                'androgen', 'psma', 'lutetium', 'enzalutamide', 'abiraterone']

    for entry in feed.entries[:80]:
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        text = (title + ' ' + summary).lower()
        if not any(k in text for k in keywords):
            continue

        pp = entry.get('published_parsed')
        if pp:
            d = date(pp[0], pp[1], pp[2])
            if d < since:
                continue
            date_str = d.isoformat()
        else:
            date_str = ''

        items.append({
            'source': 'FDA',
            'title': title,
            'url': entry.get('link', ''),
            'date': date_str,
            'abstract': summary[:2000],
            'kind': 'approval',
        })
        if len(items) >= max_results:
            break
    return items
