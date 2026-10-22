"""Tests for skills/odc-studio-guide/scripts/shot.py (URL handling; no browser needed)."""
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('shot', os.path.join(ROOT, 'skills', 'odc-studio-guide', 'scripts', 'shot.py'))
shot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shot)


class ShotTest(unittest.TestCase):
    def test_to_url(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'preview page.html')
            open(p, 'w').close()
            self.assertTrue(shot.to_url(p).startswith('file:'))
            self.assertIn('preview%20page.html', shot.to_url(p))
            self.assertTrue(shot.to_url(p + '?role=staff&store=0#card').endswith('preview%20page.html?role=staff&store=0#card'))
            self.assertTrue(shot.to_url(p + '#card').endswith('.html#card'))
            self.assertIsNone(shot.to_url(os.path.join(d, 'missing.html?x=1')))
        self.assertEqual(shot.to_url('https://example.com/a?b=1'), 'https://example.com/a?b=1')

    def test_explicit_browser_comes_first(self):
        self.assertEqual(shot.browsers('/custom/browser')[0], '/custom/browser')


if __name__ == '__main__':
    unittest.main()
