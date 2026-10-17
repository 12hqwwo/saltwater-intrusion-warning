"""Extract PDF text for review; never converts text into accepted observations.

Requires pypdf. Original pages remain authoritative; scans need visual/OCR review.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader


def inspect(folder):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    destination = folder / 'review'
    destination.mkdir(exist_ok=True)
    results = []
    for entry in manifest:
        if entry['status'] != 'DOWNLOADED' or entry['kind'] != 'RIA2_ATTACHMENT':
            continue
        path = folder / entry['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Source checksum mismatch: ' + path.name)
        if path.suffix != '.pdf':
            results.append(dict(file=path.name, status='NEEDS_DOCUMENT_CONVERSION', samples_added=0))
            continue
        try:
            pages = [{'page': i + 1, 'text': p.extract_text() or ''} for i, p in enumerate(PdfReader(path).pages)]
            (destination / (path.stem + '.pages.json')).write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
            results.append(dict(file=path.name, pages=len(pages), text_characters=sum(len(p['text'].strip()) for p in pages),
                                status='NEEDS_VISUAL_TABLE_REVIEW', method='pypdf text extraction', samples_added=0))
        except Exception as exc:
            results.append(dict(file=path.name, status='EXTRACTION_FAILED', error=str(exc), samples_added=0))
    (destination / 'inspection.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    inspect(parser.parse_args().folder)
