#!/usr/bin/env python3
"""Acquire a PubMed record and available JATS, flagging withdrawal before translation.

This is evidence acquisition, not automatic rights clearance or publication.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as E


def text(node):
    return ' '.join(' '.join(node.itertext()).split()) if node is not None else ''


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'DezsredstvaResearch/1.0'})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def article_identifiers(record):
    # Cited references have their own ArticleIdList; never use a descendant search.
    return {x.get('IdType'): text(x) for x in record.findall('./PubmedData/ArticleIdList/ArticleId')}


def validate_jats(root, identifiers, pmid):
    ids = {x.get('pub-id-type'): text(x) for x in root.findall('./front/article-meta/article-id')}
    if root.tag != 'article' or root.find('body') is None:
        raise ValueError('Not a complete JATS article')
    if ids.get('pmcid') != identifiers['pmc'] or ids.get('pmid') != pmid:
        raise ValueError('Full-text identifiers do not match the requested article')
    if identifiers.get('doi') and ids.get('doi', '').lower() != identifiers['doi'].lower():
        raise ValueError('Full-text DOI mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pmid', required=True, type=lambda value: value if re.fullmatch(r'\d+', value) else parser.error('PMID must be numeric'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {'pmid': args.pmid, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'status': 'unknown', 'requires_editorial_rights_review': True}
    try:
        url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urllib.parse.urlencode({'db': 'pubmed', 'id': args.pmid, 'retmode': 'xml'})
        raw = get(url)
        (args.out / 'pubmed.xml').write_bytes(raw)
        record = E.fromstring(raw).find('PubmedArticle')
        if record is None or record.findtext('.//MedlineCitation/PMID') != args.pmid:
            raise ValueError('Missing or mismatched PubMed record')
        title = text(record.find('.//ArticleTitle'))
        types = [text(x) for x in record.findall('.//PublicationType')]
        notices = [{'type': x.get('RefType'), 'pmid': x.findtext('PMID'), 'citation': x.findtext('RefSource')}
                   for x in record.findall('.//CommentsCorrections')]
        identifiers = article_identifiers(record)
        hold = bool(re.search(r'^(WITHDRAWN|RETRACTED|RETRACTION)\b', title, re.I)) or any(
            x in types for x in ['Retracted Publication', 'Retraction of Publication']) or any(
            x['type'] in ['RetractionIn', 'RetractionOf', 'ExpressionOfConcernIn', 'ExpressionOfConcernFor'] for x in notices)
        result.update(title=title, publication_types=types, notices=notices, identifiers=identifiers,
                      status='hold_source_notice' if hold else 'metadata_available')
        pmc = identifiers.get('pmc')
        if pmc and not hold:
            xml = get('https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmc + '/fullTextXML')
            root = E.fromstring(xml)
            validate_jats(root, identifiers, args.pmid)
            (args.out / 'source.xml').write_bytes(xml)
            result.update(status='full_text_available', source_sha256=hashlib.sha256(xml).hexdigest(),
                          permissions=[text(x) for x in root.findall('.//permissions')],
                          figures=len(root.findall('.//fig')), tables=len(root.findall('.//table-wrap')))
    except (OSError, ValueError, E.ParseError) as error:
        result['acquisition_error'] = type(error).__name__
    (args.out / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pmid': args.pmid, 'status': result['status'], 'error': result.get('acquisition_error')}))
    return 2 if result['status'] == 'hold_source_notice' else (0 if result['status'] == 'full_text_available' and not result.get('acquisition_error') else 1)


if __name__ == '__main__':
    raise SystemExit(main())
