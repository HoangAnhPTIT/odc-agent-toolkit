"""Tests for skills/odc-studio-guide/scripts/check_guide.py."""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('check_guide', os.path.join(ROOT, 'skills', 'odc-studio-guide', 'scripts', 'check_guide.py'))
check_guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_guide)

TEMPLATE = os.path.join(ROOT, 'skills', 'odc-studio-guide', 'assets', 'template.html')
SAMPLE = os.path.join(ROOT, 'examples', 'sample-guide.html')

BAD = '''<!doctype html><html><head><meta charset="utf-8"><title>t</title></head><body><main>
<h2 id="a">1. A</h2><h3>2.1 wrong section</h3><a href="#missing">x</a>
<code class="cc">If(Qty &lt; Moq, “a”, "b")</code>
<code class="cc">Max(1, 2</code>
<code class="cc">"abc</code>
<code class="cc">x − 1</code>
<code class="cc">Product.?</code>
<code class="cc">"card--v3"</code>
<code class="cc">Replace(Text, "\\p", "")</code>
<code class="cc">&lt;text len 10 sha1 cad7a76527&gt;</code>
<code class="cc">If(a <b, 1, 2)</code>
<button class="copy" data-target="j-9">Copy JSON</button><pre class="code" id="j-9">{"a": 1,}</pre>
<p>Replaced by section 4</p>
</main></body></html>'''


def run(path, conventions=True):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        ok = check_guide.check(path, conventions)
    return ok, out.getvalue()


class CheckGuideTest(unittest.TestCase):
    def test_sample_guide_is_clean(self):
        ok, out = run(SAMPLE)
        self.assertTrue(ok, out)
        self.assertIn('  OK', out)

    def test_template_reports_only_placeholders(self):
        ok, out = run(TEMPLATE)
        self.assertFalse(ok)
        errors = [l for l in out.splitlines() if l.strip().startswith('ERROR')]
        self.assertTrue(errors)
        for e in errors:
            self.assertTrue('placeholder' in e, e)

    def test_bad_guide(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'bad.html')
            with open(p, 'w', encoding='utf-8') as f:
                f.write(BAD)
            ok, out = run(p)
            self.assertFalse(ok)
            for needle in ('link to #missing', 'JSON in #j-9 does not parse', 'curly quote outside a literal',
                           'parentheses not balanced', 'unclosed "', 'minus sign U+2212', '"?" outside a literal',
                           'hashed literal', 'unescaped "<" inside a copy value', 'version suffix', 'backslash inside a literal',
                           'sits under section 1', 'convention: delete replaced content'):
                self.assertIn(needle, out)
            _, quiet = run(p, conventions=False)
            self.assertNotIn('version suffix', quiet)
            self.assertNotIn('convention: delete replaced content', quiet)

    def test_kind_guess(self):
        g = check_guide.guess_kind
        self.assertEqual(g('Leave without saving?'), 'text')
        self.assertEqual(g('CanOrder and not IsBusy'), 'expr')
        self.assertEqual(g('$actions.Refresh();\nreturn;'), 'js')
        self.assertEqual(g('Order.Total'), 'expr')

    def test_literal_split(self):
        chunks, unclosed = check_guide.split_literals('If(A, "say ""hi""", B)')
        self.assertFalse(unclosed)
        self.assertEqual([c for lit, c in chunks if lit], ['"say ""hi"""'])


if __name__ == '__main__':
    unittest.main()
