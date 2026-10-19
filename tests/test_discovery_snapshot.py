import importlib.util
import datetime as dt
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('snapshot', Path(__file__).parents[1] / 'tools/discovery/snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)
measure_spec = importlib.util.spec_from_file_location('measure', Path(__file__).parents[1] / 'tools/discovery/measure.py')
measure = importlib.util.module_from_spec(measure_spec)
measure_spec.loader.exec_module(measure)


class SnapshotHealth(unittest.TestCase):
    def data(self):
        return {'metrika': {name: {'status': 200, 'data': {'totals': [0]}}
                            for name in ('totals', 'search_engines', 'landing_pages', 'returning_visitors', 'reader_goals', 'reader_responses')},
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

    def test_failed_feedback_report_is_unknown(self):
        data = self.data()
        data['metrika']['reader_responses'] = {'status': 400, 'error': 'HTTPError'}
        self.assertEqual(snapshot.assess(data), ['metrika:reader_responses'])

    def test_reader_measurement_never_backfills_unmeasured_days(self):
        config = {'instrumented_since': '2026-10-19', 'goals': {'reader_useful': 123}}
        def coverage(start, end):
            return measure.reader_measurement(dt.date.fromisoformat(start), dt.date.fromisoformat(end), config)
        before = coverage('2026-10-12', '2026-10-18')
        self.assertEqual(before['coverage'], 'not_measured')
        self.assertIsNone(before['observed_period'])
        mixed = coverage('2026-10-14', '2026-10-20')
        self.assertEqual(mixed['coverage'], 'partial_period')
        self.assertEqual(mixed['observed_period'], ['2026-10-19', '2026-10-20'])
        self.assertEqual(coverage('2026-10-19', '2026-10-19')['coverage'], 'partial_period')
        self.assertEqual(coverage('2026-10-20', '2026-10-26')['coverage'], 'measured')


if __name__ == '__main__':
    unittest.main()
