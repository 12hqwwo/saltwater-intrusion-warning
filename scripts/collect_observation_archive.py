"""Bounded collection of official source documents, never automatic observations.

python scripts/collect_observation_archive.py --pages 4
Keeps raw originals, URL lineage and failures; reruns create a new directory.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urljoin, urlsplit, urldefrag

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.fetch_public_research_data import download, write_json

RIA = 'https://vienthuysan2.org.vn/'
CATEGORY = RIA + 'category/tin-hoat-dong/ban-tin-quan-trac-chat-luong-nuoc/'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and ((tag == 'a' and key == 'href') or
                          (tag in ('iframe', 'embed') and key == 'src') or
                          (tag == 'object' and key == 'data')):
                self.urls.append(value)


def links(html, base):
    parser = Links()
    parser.feed(html)
    result = set()
    for href in parser.urls:
        url = urldefrag(urljoin(base, href))[0]
        parts = urlsplit(url)
        if parts.scheme == 'https' and parts.hostname == 'vienthuysan2.org.vn':
            result.add(url)
    return sorted(result)


def is_bulletin(url):
    path = urlsplit(url).path.lower()
    return 'ca-tra' in path and ('quan-trac' in path or 'chat-luong-nuoc' in path) and '/category/' not in path


def is_document(url):
    return Path(urlsplit(url).path).suffix.lower() in ('.pdf', '.docx', '.xlsx', '.xls', '.doc')


def inventory(out, records):
    """Hash verified documents and exact-file overlap, not claimed new samples."""
    previous = ROOT / 'data/external/ec_recovery_20261011/ec_recovery_manifest.json'
    known = {r['sha256'] for r in json.loads(previous.read_text(encoding='utf-8'))['sources']} if previous.exists() else set()
    documents = []
    for record in records:
        if record['status'] != 'DOWNLOADED' or record['kind'] != 'RIA2_ATTACHMENT':
            continue
        raw = (out / record['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Downloaded original hash mismatch: ' + record['file'])
        signature = ('PDF' if raw.startswith(b'%PDF-') else 'OLE_DOCUMENT' if raw.startswith(bytes.fromhex('D0CF11E0A1B11AE1'))
                     else 'ZIP_CONTAINER' if raw.startswith(b'PK') else 'UNRECOGNIZED')
        documents.append(dict(file=record['file'], url=record['url'], sha256=record['sha256'],
                              signature=signature, already_in_ec_recovery=record['sha256'] in known,
                              extraction_status='PENDING_TABLE_REVIEW', quality='UNVERIFIED',
                              labelled_samples_added=0))
    write_json(out / 'document_inventory.json', documents)
    return documents


def collect(out, pages=4, max_articles=24):
    out.mkdir(parents=True, exist_ok=False)
    records, seen = [], {}

    def fetch(url, kind, parent=None):
        if url in seen:
            return seen[url]
        suffix = Path(urlsplit(url).path).suffix.lower()
        if suffix not in ('.pdf', '.docx', '.xlsx', '.xls', '.doc'):
            suffix = '.html'
        filename = hashlib.sha256(url.encode()).hexdigest()[:20] + suffix
        record = dict(url=url, kind=kind, discovered_from=parent,
                      attempted_at=datetime.now(timezone.utc).isoformat(),
                      classification='SOURCE_DOCUMENT_PENDING_EXTRACTION',
                      observation_imported=False)
        try:
            record.update(download(url, out / filename))
            record['status'] = 'DOWNLOADED'
        except Exception as exc:
            record.update(status='BLOCKED', error_type=type(exc).__name__, error=str(exc))
        records.append(record)
        seen[url] = record
        write_json(out / 'manifest.json', records)
        print(json.dumps({'status': record['status'], 'url': url}), flush=True)
        return record

    articles = {}
    for page in range(1, pages + 1):
        url = CATEGORY if page == 1 else CATEGORY + f'page/{page}/'
        record = fetch(url, 'RIA2_INDEX')
        if record['status'] == 'DOWNLOADED':
            for link in links((out / record['file']).read_text(encoding='utf-8-sig', errors='replace'), url):
                if is_bulletin(link):
                    articles.setdefault(link, url)
    for url, parent in list(articles.items())[:max_articles]:
        record = fetch(url, 'RIA2_CATFISH_BULLETIN', parent)
        if record['status'] == 'DOWNLOADED':
            for link in links((out / record['file']).read_text(encoding='utf-8-sig', errors='replace'), url):
                if is_document(link):
                    fetch(link, 'RIA2_ATTACHMENT', url)
    for bulletin_id in ('455332', '455336', '455412', '455416', '522066'):
        fetch('https://thuyloitiengiang.vn/web/thuyloitiengiang/chi-tiet-tin-tuc?id=' + bulletin_id,
              'TIENGIANG_BULLETIN')
    documents = inventory(out, records)
    summary = dict(source_documents=sum(r['status'] == 'DOWNLOADED' for r in records),
                   documents_not_in_existing_recovery=sum(not d['already_in_ec_recovery'] for d in documents),
                   attachments=sum(r['kind'] == 'RIA2_ATTACHMENT' and r['status'] == 'DOWNLOADED' for r in records),
                   failures=sum(r['status'] == 'BLOCKED' for r in records),
                   discovered_articles=len(articles), article_limit=max_articles,
                   observations_imported=0,
                   next_step='Review original tables, measurement dates, units and site identities before extraction.')
    write_json(out / 'summary.json', summary)
    print(json.dumps({'output': str(out), **summary}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pages', type=int, choices=range(1, 11), default=4)
    parser.add_argument('--max-articles', type=int, choices=range(1, 51), default=24)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    collect(args.out or ROOT / 'data/external' / datetime.now(timezone.utc).strftime('observation_archive_%Y%m%dT%H%M%S%fZ'),
            args.pages, args.max_articles)
