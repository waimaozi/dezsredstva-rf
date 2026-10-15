import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from translation import common, demand, quality, sources
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'tools/publish-translations.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublisherTests(unittest.TestCase):
    def test_http_200_provider_failure_is_an_error(self):
        with patch.object(common, 'secret', return_value='test'), patch.object(
                common, 'json_fetch', return_value={'code': 422, 'msg': 'The channel is not supported'}):
            with self.assertRaisesRegex(RuntimeError, 'no completion'):
                common.chat('test', Path('/unused'))

    def test_numeric_and_coverage_defects_block_publication(self):
        for target in [{'a': 'Выдерживать 5 минут'}, {'b': 'Выдерживать 10 минут'}, {}]:
            with self.assertRaises(RuntimeError):
                quality.validate({'a': 'Keep wet for 10 minutes'}, target)
        quality.validate({'a': 'Keep wet for 10 minutes'}, {'a': 'Оставить влажной на 10 минут'})

    def test_review_cannot_omit_a_segment(self):
        with patch.object(quality, 'chat', return_value={'checked_ids': [], 'issues': []}):
            with self.assertRaisesRegex(RuntimeError, 'every source segment'):
                quality.review({'a': 'No safe threshold'}, {'a': 'Безопасный порог не установлен'}, Path('/unused'))

    def test_table_relationships_inequality_and_escaping_survive(self):
        raw = '<div id="source"><h2>Monitoring</h2><p>' + 'Background context. ' * 55 + '</p>'
        raw += '<table><tr><th>Time</th><td><span class="text-underline">&gt;</span>48 hours</td></tr></table></div>'
        value = sources.extract(raw, {'selector': '#source', 'url': 'https://www.cdc.gov/test'})
        rendered = sources.render(value['tree'], value['segments'])
        self.assertIn('<th>Time</th>', rendered)
        self.assertIn('≥', rendered)
        self.assertIn('48 hours', rendered)
        key = next(iter(value['segments']))
        value['segments'][key] = '<script>alert(1)</script>'
        self.assertNotIn('<script>', sources.render(value['tree'], value['segments']))

    def test_seed_volume_is_not_evidence_for_an_unseen_query(self):
        row = {'seed': 'люминометр', 'response': {'totalCount': '10000'}, 'provider': 'yandex_wordstat'}
        self.assertIsNone(demand.evidence_for({'queries': ['что показывает люминометр']}, {'rows': [row]}))

    def test_reachable_changed_source_cannot_use_snapshot(self):
        item = {'url': 'https://www.cdc.gov/healthcare-associated-infections/hcp/cleaning-global/procedures.html',
                'selector': '#missing', 'approved_sha256': 'old', 'source_checked_at': '2026-10-15'}
        with patch.object(sources, 'fetch', return_value=b'<html>A changed page</html>'):
            with self.assertRaisesRegex(RuntimeError, 'section is missing'):
                sources.read_source(item)

    def test_google_fallback_never_fabricates_counts(self):
        def response(url, *args, **kwargs):
            if 'yandex' in url:
                raise RuntimeError('Upstream HTTP 500')
            return ['люминометр', ['что показывает люминометр']]
        with tempfile.TemporaryDirectory() as tmp, patch.object(demand, 'SEEDS', ['люминометр']), \
             patch.object(demand, 'secret', return_value='test'), patch.object(demand, 'json_fetch', side_effect=response):
            result = demand.collect(Path(tmp) / 'demand.json')
            evidence = demand.evidence_for({'queries': ['что показывает люминометр']}, result)
            self.assertEqual(evidence['provider'], 'google_suggest')
            self.assertIsNone(evidence['count'])
            self.assertEqual(len(result['errors']), 1)

    def test_preview_writes_only_evidence_not_articles_or_publication_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            (repo / 'tools/translation').mkdir(parents=True)
            (repo / 'src/content/articles').mkdir(parents=True)
            (repo / 'tools/translation/catalog.json').write_text(json.dumps([{'id': 'test', 'title': 'Вопрос', 'queries': []}]))
            evidence = {'rows': [{'provider': 'yandex_wordstat', 'response': {}}]}
            source = {'segments': {'a': 'A source sentence'}, 'tree': {}, 'sha256': 'test'}
            args = types.SimpleNamespace(state_dir=str(Path(tmp) / 'state'), publish=False, refresh_demand=False)
            with patch.object(publisher, 'REPO', repo), patch.object(publisher, 'collect', return_value=evidence), \
                 patch.object(publisher, 'evidence_for', return_value={'phrase': 'test'}), \
                 patch.object(publisher, 'read_source', return_value=source), \
                 patch.object(publisher, 'translate', return_value={'a': 'Перевод'}), \
                 patch.object(publisher, 'review'), patch.object(publisher, 'prepare') as prepare, \
                 patch.object(publisher, 'commit') as commit:
                self.assertEqual(publisher.run(args), 0)
                prepare.assert_not_called()
                commit.assert_not_called()
                status = json.loads((Path(tmp) / 'state/last-run.json').read_text())
                self.assertEqual(status['status'], 'validated_preview')
                self.assertIsNone(status['published'])
                self.assertEqual(list((repo / 'src/content/articles').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
