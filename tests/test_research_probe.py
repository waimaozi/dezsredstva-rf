import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as E

spec = importlib.util.spec_from_file_location('probe', Path(__file__).parents[1] / 'tools/research/probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class SourceIdentity(unittest.TestCase):
    def test_cited_paper_cannot_replace_article_identifiers(self):
        record = E.fromstring('''<PubmedArticle><PubmedData>
        <ArticleIdList><ArticleId IdType="pmc">PMC13533754</ArticleId>
        <ArticleId IdType="doi">10.3389/fnut.2026.1812387</ArticleId></ArticleIdList>
        <ReferenceList><Reference><ArticleIdList><ArticleId IdType="pmc">PMC5456506</ArticleId>
        <ArticleId IdType="doi">10.3390/ma9020100</ArticleId></ArticleIdList></Reference></ReferenceList>
        </PubmedData></PubmedArticle>''')
        self.assertEqual(probe.article_identifiers(record)['pmc'], 'PMC13533754')

    def test_wrong_full_text_is_rejected(self):
        root = E.fromstring('''<article><front><article-meta>
        <article-id pub-id-type="pmcid">PMC5456506</article-id>
        <article-id pub-id-type="pmid">28787897</article-id>
        </article-meta></front><body><p>Unrelated paper</p></body></article>''')
        with self.assertRaises(ValueError):
            probe.validate_jats(root, {'pmc': 'PMC13533754'}, '42688105')


if __name__ == '__main__':
    unittest.main()
