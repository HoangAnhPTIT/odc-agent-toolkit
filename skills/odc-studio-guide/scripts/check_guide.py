#!/usr/bin/env python3
"""Check an ODC Studio build guide (HTML) before handing it over.

  python check_guide.py guide.html [more.html ...] [--conventions]

ERROR (exit code 1): breaks the page, or would paste a wrong value into ODC Studio.
warn: worth a look (odd characters inside text literals, section numbering). --conventions adds
opinionated warnings: version suffixes in names, "replaced by" notes.

Expression checks run on click-to-copy values (elements with class "cc") that hold OutSystems
expressions. JavaScript and plain-text values are recognised and skipped; mark an element with
data-kind="expr" | "js" | "text" when the guess is wrong. A string literal is "...", with "" for a
quote inside it, as in OutSystems.

No third-party dependencies. Python 3.9+.
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser

__version__ = '0.1.1'

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
KNOWN = VOID | {'html', 'head', 'title', 'style', 'script', 'body', 'main', 'nav', 'header', 'footer', 'section', 'article',
                'aside', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'b', 'i', 'u', 's', 'em', 'strong', 'small',
                'sup', 'sub', 'a', 'ol', 'ul', 'li', 'dl', 'dt', 'dd', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
                'caption', 'colgroup', 'code', 'pre', 'kbd', 'samp', 'var', 'mark', 'details', 'summary', 'button', 'label',
                'select', 'option', 'textarea', 'form', 'fieldset', 'legend', 'figure', 'figcaption', 'svg', 'path', 'g',
                'circle', 'rect', 'line', 'polyline', 'polygon', 'text', 'defs', 'use', 'symbol', 'blockquote', 'q', 'abbr',
                'time', 'del', 'ins', 'iframe', 'picture', 'video', 'audio', 'canvas', 'noscript', 'template'}
JS_HINTS = ('$parameters', '$actions', '$public', 'function', '=>', '/*', 'document.', 'window.', 'var ', 'let ', 'const ', ';\n')
JS_COMMENT = re.compile(r'(^|\n)\s*//')  # a line comment; '//' inside a URL literal is not JavaScript
PLACEHOLDER = re.compile(r'\{\{[^{}\n]{0,60}\}\}')  # the template marks every value to fill as {{...}}


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # [tag, attrs, line, captured text list or None, is_cc]
        self.ids = {}            # id -> [lines]
        self.hrefs = []          # (target id, line)
        self.copies = []         # (target id, data-mode, line)
        self.cc = []             # (text, line, data-kind)
        self.by_id = {}          # id -> text, for <pre>/<code> with an id
        self.heads = []          # (tag, text, line)
        self.title = False
        self.unknown = []        # (tag, line)
        self.prose = []          # visible text outside <script>/<style>

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if tag not in KNOWN:
            self.unknown.append((tag, line))
        if 'id' in a:
            self.ids.setdefault(a['id'], []).append(line)
        href = a.get('href') or ''
        if tag == 'a' and href.startswith('#') and len(href) > 1:
            self.hrefs.append((href[1:], line))
        classes = (a.get('class') or '').split()
        if tag == 'button' and 'copy' in classes and a.get('data-target'):
            self.copies.append((a['data-target'], a.get('data-mode', ''), line))
        if tag == 'title':
            self.title = True
        if tag in VOID:
            return
        capture = 'cc' in classes or tag in ('pre', 'h1', 'h2', 'h3') or (tag == 'code' and 'id' in a)
        self.stack.append([tag, a, line, [] if capture else None, 'cc' in classes])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] != tag:
                continue
            while len(self.stack) > k:
                t, a, line, cap, is_cc = self.stack.pop()
                if cap is None:
                    continue
                text = ''.join(cap)
                if is_cc:
                    self.cc.append((text, line, a.get('data-kind', '')))
                if a.get('id'):
                    self.by_id[a['id']] = text
                if t in ('h1', 'h2', 'h3'):
                    self.heads.append((t, re.sub(r'\s+', ' ', text).strip(), line))
            return

    def handle_data(self, data):
        if not any(s[0] in ('script', 'style') for s in self.stack):
            self.prose.append(data)
        for s in self.stack:
            if s[3] is not None:
                s[3].append(data)


def split_literals(expr):
    """Return ([(is_literal, chunk), ...], unclosed). OutSystems literal: "..." with "" for a quote."""
    out, buf, in_s, i, n = [], [], False, 0, len(expr)
    while i < n:
        c = expr[i]
        if c == '"':
            if in_s and i + 1 < n and expr[i + 1] == '"':
                buf.append('""')
                i += 2
                continue
            if in_s:
                buf.append('"')
                out.append((True, ''.join(buf)))
                buf, in_s = [], False
            else:
                if buf:
                    out.append((False, ''.join(buf)))
                buf, in_s = ['"'], True
            i += 1
            continue
        buf.append(c)
        i += 1
    if buf:
        out.append((in_s, ''.join(buf)))
    return out, in_s


def guess_kind(text):
    """expr = OutSystems expression; js = JavaScript; text = plain text typed as-is (Text widget, label)."""
    t = text.strip()
    if any(h in t for h in JS_HINTS) or JS_COMMENT.search(t):
        return 'js'
    if re.fullmatch(r"[A-Za-z][\w']*[?!.]", t):  # one word of prose, e.g. Continue?
        return 'text'
    if re.search(r'\b(and|or|not|True|False)\b|\w\.\w|\u2212', t):
        return 'expr'
    if ' ' in t and not re.search(r'["()+=<>\[\]]', t):
        return 'text'
    return 'expr'


def check_expr(text, line, conventions, errs, warns):
    t = text.strip()
    where = f'line {line}: {t[:70]!r}'
    if not t:
        errs.append(f'{where}: empty copy value')
        return
    if '<text len' in t or re.search(r'sha1 [0-9a-f]{10}', t):
        errs.append(f'{where}: hashed literal pasted from a graph dump; write the real text')
    chunks, unclosed = split_literals(t)
    if unclosed:
        errs.append(f'{where}: unclosed " (a quote inside a literal is written "")')
    code = ''.join(c for lit, c in chunks if not lit)
    lits = ''.join(c for lit, c in chunks if lit)
    if code.count('(') != code.count(')'):
        errs.append(f'{where}: parentheses not balanced outside literals ({code.count("(")} open, {code.count(")")} close)')
    if code.count('[') != code.count(']'):
        errs.append(f'{where}: brackets not balanced outside literals')
    if re.search(r'[{}]', code):
        errs.append(f'{where}: {{...}} outside a literal: template placeholder left?')
    if '?' in code:
        errs.append(f'{where}: "?" outside a literal: unresolved name pasted from a graph dump?')
    for ch, name in (('\u2212', 'minus sign U+2212'), ('\u2013', 'en dash'), ('\u2014', 'em dash'),
                     ('\u201c', 'curly quote'), ('\u201d', 'curly quote'), ('\u2018', 'curly apostrophe'), ('\u2019', 'curly apostrophe')):
        if ch in code:
            errs.append(f'{where}: {name} outside a literal; expressions need ASCII')
    for ch, name in (('\u201c', 'curly quote'), ('\u201d', 'curly quote'), ('\u2019', 'curly apostrophe')):
        if ch in lits:
            warns.append(f'{where}: {name} inside a literal (intended?)')
    if '\u00a0' in t:
        warns.append(f'{where}: non-breaking space')
    if '\\' in lits:
        warns.append(f'{where}: backslash inside a literal is a plain backslash (OutSystems has no escapes); use Chr(92) when editing through Mentor')
    if conventions and re.search(r'--v\d|\bV\d\b|[a-z]V\d\b', lits):
        warns.append(f'{where}: version suffix in a name or class (convention: restyle in place, no v2 / v3 names)')


def check(path, conventions=False):
    try:
        with open(path, encoding='utf-8-sig') as f:  # -sig: tolerate a BOM from Windows editors
            src = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f'{path}: cannot read ({e})')
        return False
    p = Parser()
    p.feed(src)
    p.close()
    errs, warns = [], []
    if not src.lstrip().lower().startswith('<!doctype html'):
        errs.append('missing <!doctype html>')
    if not re.search(r'<meta[^>]+charset', src, re.I):
        errs.append('missing <meta charset>')
    if not p.title:
        errs.append('missing <title>')
    for tag, line in p.unknown:
        errs.append(f'line {line}: <{tag}> is not an HTML tag: unescaped "<" in an expression? write &lt;')
    # A raw "<" inside a copy value can also look like a real tag ("a <b , c" opens <b>): scan the source.
    for m in re.finditer(r'<(code|pre|span|div)\b[^>]*\bclass="[^"]*\bcc\b[^"]*"[^>]*>(.*?)</\1>', src, re.S):
        inner = re.sub(r'</?(b|i|em|strong)>|<br\s*/?>|</?span\b[^>]*>', '', m.group(2))
        if '<' in inner:
            line = src.count('\n', 0, m.start()) + 1
            errs.append(f'line {line}: unescaped "<" inside a copy value: write &lt; ({inner.strip()[:50]!r})')
    for i, lines in p.ids.items():
        if len(lines) > 1:
            errs.append(f'duplicate id "{i}" at lines {lines}')
    for h, line in p.hrefs:
        if h not in p.ids:
            errs.append(f'line {line}: link to #{h}, but no element has that id')
    for target, mode, line in p.copies:
        if target not in p.ids:
            errs.append(f'line {line}: copy button targets #{target}, which does not exist')
            continue
        text = p.by_id.get(target, '')
        if mode != 'literal' and text.strip()[:1] not in ('{', '['):
            continue  # a plain code block (script, CSS) copied as-is
        try:
            json.loads(text)
        except ValueError as e:
            errs.append(f'line {line}: JSON in #{target} does not parse ({e})')
    kinds = {'expr': 0, 'js': 0, 'text': 0}
    for text, line, kind in p.cc:
        kind = kind if kind in kinds else guess_kind(text)
        kinds[kind] += 1
        if kind == 'expr':
            check_expr(text, line, conventions, errs, warns)
    section = 0
    for tag, text, line in p.heads:
        m2 = re.match(r'^(\d+)\.\s', text)
        if tag == 'h2' and m2:
            n = int(m2.group(1))
            if n != section + 1:
                warns.append(f'line {line}: h2 "{text[:40]}" is numbered {n}, expected {section + 1}')
            section = n
        m3 = re.match(r'^(\d+)\.(\d+)\s', text)
        if tag == 'h3' and m3 and int(m3.group(1)) != section:
            warns.append(f'line {line}: h3 "{text[:40]}" sits under section {section}')
    prose = ''.join(p.prose)
    left = sorted(set(PLACEHOLDER.findall(prose)))
    if left:
        errs.append('template placeholders still in the text: ' + ', '.join(left[:8]) + (' ...' if len(left) > 8 else ''))
    if conventions:
        for pat in (r'[Rr]eplaced by', r'kept for reference', r'\(old version\)'):
            if re.search(pat, prose):
                warns.append(f'text matches "{pat}" (convention: delete replaced content instead of keeping it with a note)')
    print(f'{path}: {len(p.cc)} copy values ({kinds["expr"]} expressions checked, {kinds["js"]} JS, {kinds["text"]} plain text), '
          f'{len(p.copies)} copy buttons, {len(p.heads)} headings')
    for e in errs:
        print('  ERROR', e)
    for w in warns:
        print('  warn ', w)
    if not errs and not warns:
        print('  OK')
    return not errs


def main(argv=None):
    ap = argparse.ArgumentParser(description='Check an ODC Studio build guide (HTML).')
    ap.add_argument('files', nargs='+')
    ap.add_argument('--conventions', action='store_true',
                    help='also warn about version suffixes in names and "replaced by" notes (opinionated)')
    ap.add_argument('--version', action='version', version=__version__)
    a = ap.parse_args(argv)
    results = [check(f, a.conventions) for f in a.files]
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
