import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('snapshot', Path(__file__).parents[1] / 'tools/discovery/snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class SnapshotHealth(unittest.TestCase):
    def data(self):
        return {'metrika': {name: {'status': 200, 'data': {'totals': [0]}}
                            for name in ('totals', 'search_engines', 'landing_pages')},
                'yandex_search': {'status': 200, 'documents': [], 'search_error_code': '15'}}

    def test_valid_zero_results_are_successful_reads(self):
        self.assertEqual(snapshot.assess(self.data()), [])

    def test_api_failure_is_not_zero_traffic(self):
        data = self.data()
        data['metrika']['totals'] = {'status': None, 'error': 'TimeoutError'}
        self.assertEqual(snapshot.assess(data), ['metrika:totals'])

    def test_search_quota_error_is_not_empty_index(self):
        data = self.data()
        data['yandex_search']['search_error_code'] = '32'
        self.assertEqual(snapshot.assess(data), ['yandex_search:32'])

    def test_missing_payload_is_failure_even_with_http_success(self):
        data = self.data()
        data['yandex_search'] = {'status': 200, 'data': {}}
        self.assertEqual(snapshot.assess(data), ['yandex_search'])


if __name__ == '__main__':
    unittest.main()
