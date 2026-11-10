import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from translation import common


class DownloadVerificationTests(unittest.TestCase):
    def test_large_download_hash_includes_bytes_beyond_previous_limit(self):
        payload = b'a' * 8_000_000 + b'final PDF pages'
        reads = []

        class Response(io.BytesIO):
            def read(self, size=-1):
                reads.append(size)
                return super().read(size)

        with patch.object(common.urllib.request, 'urlopen', return_value=Response(payload)):
            self.assertEqual(common.download_sha256('https://example.test/translation.pdf'),
                             hashlib.sha256(payload).hexdigest())
        self.assertTrue(all(0 < size <= 1_000_000 for size in reads))

    def test_size_limit_accepts_exact_boundary_and_rejects_extra_byte(self):
        for size in [1024, 1025]:
            with self.subTest(size=size), patch.object(
                    common.urllib.request, 'urlopen', return_value=io.BytesIO(b'x' * size)):
                if size == 1024:
                    self.assertEqual(common.download_sha256('https://example.test/file', max_bytes=1024),
                                     hashlib.sha256(b'x' * size).hexdigest())
                else:
                    with self.assertRaisesRegex(RuntimeError, 'size limit'):
                        common.download_sha256('https://example.test/file', max_bytes=1024)

    def test_interrupted_transfer_cannot_return_a_partial_digest(self):
        class Response(io.BytesIO):
            def read(self, size=-1):
                if self.tell():
                    raise OSError('Connection interrupted')
                return super().read(size)

        with patch.object(common.urllib.request, 'urlopen', return_value=Response(b'partial')):
            with self.assertRaisesRegex(OSError, 'Connection interrupted'):
                common.download_sha256('https://example.test/file')

    def test_http_error_omits_upstream_body(self):
        error = urllib.error.HTTPError('https://example.test/file', 403, 'private details', {},
                                       io.BytesIO(b'private upstream body'))
        with patch.object(common.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, '^Upstream HTTP 403$'):
                common.download_sha256('https://example.test/file')


if __name__ == '__main__':
    unittest.main()
