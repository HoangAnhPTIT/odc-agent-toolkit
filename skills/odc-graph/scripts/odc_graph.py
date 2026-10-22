#!/usr/bin/env python3
"""Read an OutSystems Developer Cloud (ODC) model graph and print or render it readably.

Input: the file(s) your MCP host saved for a `context_graph` call (a JSON array of content blocks:
one header block, then the blocks listed in the header's "blocks"), or an already-joined `.xre.json`.
For a paged result pass every page file, in order.

  python odc_graph.py GRAPH --list                         # screens, blocks, actions, structures
  python odc_graph.py GRAPH --text --only "Orders\\OnSave"  # outline of matching elements
  python odc_graph.py GRAPH --html graph.html              # browsable page with a filter box
  python odc_graph.py GRAPH --save-dir graph --name MyApp_rev12_root-Orders   # keep the raw files
  python odc_graph.py GRAPH --guess "[^a-z0-9]+" --text    # confirm a literal that is stored as a hash

Text literals are kept either as plain `TextValue` or only as `TextLength` + `TextHash`, where the hash
is the first 10 hex digits of the SHA-1 of the UTF-8 text. Hashes are matched against quoted strings
found in DisplayName fields, Text widgets, comments and every --guess value; anything else prints as
<text len N sha1 H>. References the graph cannot resolve print as `?`.

No third-party dependencies. Python 3.9+.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
from collections import defaultdict

__version__ = '0.1.0'

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.setrecursionlimit(20000)

OPS = {'Plus': '+', 'Minus': '-', 'Mul': '*', 'Div': '/', 'Eq': '=', 'NEq': '<>', 'GT': '>', 'GE': '>=',
       'LT': '<', 'LE': '<=', 'And': 'and', 'Or': 'or', 'Not': 'not', 'Neg': '-'}
# Element types that own a flow (obj.Nodes) or a widget tree. Reactive Web and Mobile apps both use the
# IMobileScreen / IMobileBlock types in current graphs; the others are kept for older or other app kinds.
CONTAINERS = ('IServerAction', 'IClientAction', 'IClientScreenAction', 'IDataAction', 'IServiceAction',
              'IMobileScreen', 'IMobileBlock', 'IWebScreen', 'IWebBlock', 'IScreen', 'IBlock')
UI = ('IMobileScreen', 'IMobileBlock', 'IWebScreen', 'IWebBlock', 'IScreen', 'IBlock')
WIDGET_RELS = ('Widgets', 'TrueBranch', 'FalseBranch', 'PlaceholdersContent', 'Content')
PROP_LABEL = {'Style': 'Style Classes', 'StyleClasses': 'Style Classes', 'OnClick': 'On Click', 'OnChange': 'On Change'}
DEFAULT_NOISE = {('Visible', 'True'), ('Enabled', 'True'), ('Width', '(fill parent)')}


def short(t):
    """IIfNode -> IfNode, IMobileScreen -> MobileScreen (drop the leading I of a model interface name)."""
    return t[1:] if len(t) > 1 and t[0] == 'I' and t[1].isupper() else t


def _blocks(raw):
    """Split one saved MCP response into (header dict, {kind: [text, ...]})."""
    texts = [b.get('text', '') for b in raw if isinstance(b, dict) and b.get('type', 'text') == 'text']
    header = {}
    if texts:
        try:
            first = json.loads(texts[0])
            if isinstance(first, dict) and 'blocks' in first and 'nodes' not in first:
                header = first
        except ValueError:
            pass
    if not header:  # an answer without a header is the complete graph in one piece
        return {}, {'xre': texts[:1] if texts else [], 'graphviz': texts[1:2]}
    kinds = defaultdict(list)
    for kind, text in zip(header.get('blocks', []), texts[1:]):
        kinds[kind].append(text)
    return header, kinds


def load(paths):
    """Return (graph dict, header of the last page, joined XRE text or None, joined graphviz text)."""
    headers, xre, dot = [], [], []
    for path in paths:
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, dict) and 'nodes' in raw:  # already-joined .xre.json
            if len(paths) > 1:
                sys.exit('error: pass a joined .xre.json on its own')
            return raw, {}, None, ''
        if not isinstance(raw, list):
            sys.exit(f'error: {path} is neither a context_graph response nor an .xre.json')
        header, kinds = _blocks(raw)
        headers.append(header)
        xre += kinds.get('xre', [])
        dot += kinds.get('graphviz', [])
    last = headers[-1] if headers else {}
    if last.get('has_more'):
        print('warning: the last page says has_more=true; fetch the next page with cursor=next_cursor', file=sys.stderr)
    body = ''.join(xre)
    try:
        return json.loads(body), last, body, ''.join(dot)
    except ValueError as e:
        sys.exit(f'error: the XRE blocks do not form valid JSON ({e}). Missing a page?')


class Graph:
    def __init__(self, g, guesses=()):
        self.N = g['nodes']
        self.out = defaultdict(list)
        self.parent = {}
        for s, t, a in zip(g['edgeSrc'], g['edgeDst'], g['edgeAttr']):
            self.out[s].append((t, a))
            if a.get('relationType') == 'Parent' and t not in self.parent:
                self.parent[t] = s
        self.known = {}
        texts = list(guesses) + ['', ' ', ',', '.', '-', ':', '|', '*', '?', '/', '"']
        for n in self.N:
            for s in re.findall(r'"((?:[^"]|"")*)"', n.get('DisplayName') or ''):
                texts.append(s.replace('""', '"'))
            if isinstance(n.get('Text'), str):
                texts.append(n['Text'])
        for t in texts:
            self.known[hashlib.sha1(t.encode('utf-8')).hexdigest()[:10]] = t

    # ---- graph helpers
    def kids(self, i, rel=None):
        r = [(t, a) for t, a in self.out[i] if rel is None or a.get('_type') == rel]
        return sorted(r, key=lambda x: x[1].get('index', 0))

    def child(self, i, rel):
        k = self.kids(i, rel)
        return k[0][0] if k else None

    def name(self, i):
        n = self.N[i]
        if n['_type'] == 'Text':  # reference the graph could not resolve (client variable, static entity
            return '?'            # record, element of another module): the Text node is not its name
        return n.get('Name') or n.get('Label') or n.get('DisplayName') or ''

    def literal(self, n, quote=True):
        if 'TextValue' in n:
            v = n['TextValue']
        elif n.get('TextHash') in self.known:
            v = self.known[n['TextHash']]
        else:
            return f'<text len {n.get("TextLength")} sha1 {n.get("TextHash")}>'
        return '"' + v.replace('"', '""') + '"' if quote else v

    def ref(self, i, rels=('ReferedObject', 'ReferedRuntimeProp', 'Action', 'Destination', 'DataSource', 'Event', 'SourceBlock', 'Exception')):
        for t, a in self.out[i]:
            if a.get('_type') in rels:
                return self.name(t) or '?'
        return ''

    def dtype(self, i):
        for t, a in self.out[i]:
            if a.get('_type') == 'DataType':
                return self.name(t)
        return ''

    def qual(self, i):
        parts, cur, seen = [], i, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            if self.N[cur]['_type'] in CONTAINERS:
                parts.append(self.name(cur))
            cur = self.parent.get(cur)
        return '\\'.join(reversed(parts))

    # ---- expressions
    def expr(self, i):
        if i is None:
            return ''
        n = self.N[i]
        t = n['_type']
        if t in ('ExpressionAST', 'Argument'):
            return self.expr(self.child(i, 'Root'))
        if t == 'Text':
            return self.literal(n)
        if t in ('Integer', 'Decimal', 'Boolean', 'LongInteger', 'Currency', 'Date', 'Time', 'DateTime'):
            return str(n.get('Value'))
        if t == 'Identifier':
            return self.ref(i) or '?'
        if t == 'CompoundIdentifier':
            nxt = self.child(i, 'IdentifierPart')
            return (self.ref(i) or '?') + ('.' + self.expr(nxt) if nxt is not None else '')
        if t == 'Indexer':
            return self.expr(self.child(i, 'Root')) + '[' + self.expr(self.child(i, 'Index')) + ']'
        if t == 'BinaryOperation':
            op = OPS.get(n.get('Operator'), n.get('Operator'))
            return '(' + self.expr(self.child(i, 'LeftOperand')) + ' ' + op + ' ' + self.expr(self.child(i, 'RightOperand')) + ')'
        if t == 'UnaryOperation':
            return OPS.get(n.get('Operator'), n.get('Operator')) + ' ' + self.expr(self.child(i, 'Operand'))
        if t == 'Call':
            return (self.ref(i) or '?') + '(' + ', '.join(self.expr(a) for a, _ in self.kids(i, 'Argument')) + ')'
        if t.startswith('Reference') or self.ref(i):
            return self.ref(i) or self.name(i)
        return f'<{t}>'

    def exprs_of(self, i, skip=()):
        """(relation, expression) for every ExpressionAST child of node i. Not only relationType=Parent
        edges: a widget's Style Classes hang on a plain 'Style' edge."""
        r = []
        for t, a in self.out[i]:
            if self.N[t]['_type'] == 'ExpressionAST' and a.get('_type') not in tuple(skip) + ('DataType',):
                r.append((a.get('_type'), self.expr(t)))
        return r

    def args(self, i):
        return [(self.name(a), self.expr(self.child(a, 'Value'))) for a, _ in self.kids(i, 'Arguments')]

    # ---- flows
    def node_lines(self, i):
        n = self.N[i]
        t = n['_type']
        lines = []
        if t == 'IAssignNode':
            for a, _ in self.kids(i, 'Assignments'):
                dn = self.N[a].get('DisplayName') or ''
                if '=' not in dn:
                    dn = self.expr(self.child(a, 'Variable')) + ' = ' + self.expr(self.child(a, 'Value'))
                lines.append(dn)
        elif t == 'IIfNode':
            lines.append('Condition: ' + self.expr(self.child(i, 'Condition')))
        elif t == 'IForEachNode':
            lines.append('Record List: ' + self.expr(self.child(i, 'RecordList')))
        elif t == 'IJavaScriptNode':
            lines += [f'{k} = {v}' for k, v in self.args(i)]
            lines.append('JS: ' + (n.get('JsSourceText') or ''))
        else:
            target = self.ref(i)
            if target:
                lines.append('-> ' + target)
            lines += [f'{k} = {v}' for k, v in self.args(i)]
            lines += [f'{k}: {v}' for k, v in self.exprs_of(i)]
        return lines

    def flow(self, c):
        nodes = [t for t, a in self.out[c] if a.get('_type') == 'obj.Nodes']
        starts = [x for x in nodes if self.N[x]['_type'] in ('IStartNode', 'IExceptionHandlerNode')]
        starts.sort(key=lambda x: self.N[x]['_type'] != 'IStartNode')
        rows, seen = [], set()

        def walk(i, d, via):
            label = self.name(i)
            if i in seen:
                rows.append((d, via, 'goto', label, []))
                return
            seen.add(i)
            rows.append((d, via, short(self.N[i]['_type']).replace('Node', ''), label, self.node_lines(i)))
            nxt = [(t, a.get('connectorType', '').replace('Links.', '')) for t, a in self.out[i] if a.get('_type') == 'Connector']
            rank = {'Cycle': 0, 'True': 0, 'Sequence': 1, 'False': 1, 'Otherwise': 2}
            nxt.sort(key=lambda x: rank.get(x[1], 1))
            for t, ctype in nxt:
                branch = len(nxt) > 1 or ctype in ('Cycle', 'True', 'False')
                walk(t, d + (1 if branch else 0), '' if ctype == 'Sequence' else ctype)

        for s in starts:
            walk(s, 0, '')
        for x in nodes:
            if x not in seen and self.N[x]['_type'] != 'IComment':
                walk(x, 0, 'not connected')
        for x in nodes:
            if self.N[x]['_type'] == 'IComment':
                rows.append((0, 'comment', 'Comment', self.N[x].get('Text') or '', []))
        return rows

    def params(self, c):
        r = []
        for rel, kind in (('InputParameters', 'In'), ('OutputParameters', 'Out'), ('LocalVariables', 'Local')):
            for t, _ in self.kids(c, rel):
                extra = []
                if self.N[t].get('IsMandatory') in (True, 'True'):
                    extra.append('mandatory')
                dv = self.expr(self.child(t, 'DefaultValue'))
                if dv:
                    extra.append('default ' + dv)
                r.append((kind, self.name(t), self.dtype(t), ', '.join(extra), self.N[t].get('Description') or ''))
        for t, a in self.out[c]:
            if self.N[t]['_type'] in ('IUILifeCycleEvent', 'IOnSyncStartEvent', 'IOnSyncCompleteEvent', 'IOnSyncErrorEvent'):
                h = self.ref(t, ('Destination', 'Action', 'Handler'))
                if h:
                    r.append(('Event', self.name(t), '', '-> ' + h, ''))
        if self.N[c].get('Fetch'):
            r.append(('Fetch', self.N[c]['Fetch'], '', '', ''))
        return r

    # ---- widgets
    def widget_label(self, i):
        n = self.N[i]
        t = n['_type']
        name = n.get('Name') if n.get('Name') not in (None, 'None', '') else ''
        if t in ('IMobileBlockInstanceWidget', 'IWebBlockInstanceWidget'):
            block = self.ref(i, ('SourceBlock',)) or n.get('DisplayName') or '?'
            return f'Block {block}' + (f' ({name})' if name and name != block else '')
        if t == 'INRPlaceholderContentWidget':
            return f'Placeholder {name}'
        if t == 'INRIfBranchWidget':
            return f'{n.get("DisplayName") or ""} branch'
        base = {'INRIfWidget': 'If', 'INRTextWidget': 'Text'}.get(t, t.split('.')[-1])
        return base + (f' {name}' if name else '')

    def widgets(self, c, keep_defaults=False):
        rows = []

        def wid(i, d):
            n = self.N[i]
            props = []
            if isinstance(n.get('Text'), str):
                props.append(('Text', '"' + n['Text'] + '"'))
            for k in ('InputType', 'MaxLength', 'Width'):
                if n.get(k) not in (None, 'None', ''):
                    props.append((k, str(n[k])))
            props += [(PROP_LABEL.get(k, k), v) for k, v in self.exprs_of(i)]
            for t2, a in self.out[i]:
                ty, rel = self.N[t2]['_type'], a.get('_type')
                if ty == 'INRBuiltinEvent':
                    props.append((PROP_LABEL.get(rel, rel), self.ref(t2, ('Destination', 'Action')) or '(none)'))
                elif ty == 'IExtendedProperty':
                    props.append(('attr ' + (self.N[t2].get('Property') or ''), self.expr(self.child(t2, 'Value'))))
                elif ty == 'IEventHandler':
                    handler = next((self.name(t3) for t3, a3 in self.out[t2] if a3.get('_type') in ('Destination', 'Handler', 'Action')), '')
                    props.append(('event ' + self.ref(t2, ('Event',)), handler or '(none)'))
            props += self.args(i)
            if not keep_defaults:
                props = [p for p in props if p not in DEFAULT_NOISE]
            rows.append((d, self.widget_label(i), props))
            for t2, a in sorted([x for x in self.out[i] if x[1].get('_type') in WIDGET_RELS],
                                key=lambda x: (WIDGET_RELS.index(x[1]['_type']), x[1].get('index', 0))):
                wid(t2, d + 1)

        for t, a in self.kids(c, 'Widgets'):
            wid(t, 0)
        return rows

    def structures(self):
        r = []
        for i, n in enumerate(self.N):
            if n['_type'] == 'IStructure':
                r.append((self.name(i), [(self.name(t), self.dtype(t)) for t, a in self.kids(i, 'Attributes')]))
        return r

    def containers(self, only=None):
        cs = [i for i, n in enumerate(self.N) if n['_type'] in CONTAINERS]
        if only:
            cs = [i for i in cs if only.lower() in self.qual(i).lower()]
        return sorted(cs, key=lambda i: (self.N[i]['_type'] not in UI, self.qual(i).lower()))


def text_out(G, cs, keep_defaults=False):
    for c in cs:
        n = G.N[c]
        print(f'\n=== {short(n["_type"])} {G.qual(c)}')
        for kind, nm, ty, extra, desc in G.params(c):
            print(f'  {kind:6} {nm}: {ty} {extra} {desc}'.rstrip())
        if n['_type'] in UI:
            for d, label, props in G.widgets(c, keep_defaults):
                print('  ' + '  ' * d + label)
                for k, v in props:
                    print('  ' + '  ' * d + f'    . {k}: {v}')
        for d, via, typ, label, lines in G.flow(c):
            pre = '  ' + '  ' * d + (f'[{via}] ' if via else '')
            print(pre + (f'<- back to {label}' if typ == 'goto' else f'{typ} {label}'))
            for line in lines:
                print('  ' + '  ' * d + '    | ' + line)


PAGE_CSS = '''
:root{--bg:#f5f6f8;--card:#fff;--text:#1d2433;--muted:#667085;--line:#dde1e7;--code:#f1f3f6;--acc:#0b5cad;--via:#b35c00}
@media (prefers-color-scheme:dark){:root{--bg:#11161c;--card:#1a2129;--text:#e8edf2;--muted:#9aa6b2;--line:#2b3540;--code:#222b35;--acc:#5aa7e6;--via:#f0a04b}}
body{margin:0;font:14px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--text)}
header{padding:14px 20px;border-bottom:1px solid var(--line);background:var(--card)} header p{margin:4px 0 0;color:var(--muted)}
.wrap{display:flex;gap:20px;padding:16px 20px} nav{position:sticky;top:10px;align-self:flex-start;width:300px;max-height:92vh;overflow-y:auto;overflow-x:hidden;flex:none}
nav input{width:100%;box-sizing:border-box;padding:6px 8px;margin-bottom:8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--text)}
nav ul{list-style:none;margin:0;padding:0} nav a{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:3px 6px;color:var(--text);text-decoration:none;border-radius:5px;font-size:13px} nav a:hover{background:var(--code)}
.k{font-size:11px;color:var(--muted)} main{flex:1;min-width:0}
section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 18px;margin-bottom:18px} h2{font-size:17px;margin:4px 0 8px} h3{font-size:14px;margin:14px 0 6px;color:var(--acc)}
table{border-collapse:collapse;margin:4px 0 8px} td,th{border:1px solid var(--line);padding:2px 8px;text-align:left;vertical-align:top;font-size:13px}
code,.ln{font-family:Consolas,ui-monospace,monospace;font-size:12.5px} code{white-space:pre-wrap;word-break:break-word}
.w,.s{margin-left:calc(var(--d)*22px);border-left:2px solid var(--line);padding:2px 8px;margin-top:2px}
.p{display:flex;gap:8px;margin-left:8px} .p span{flex:0 0 120px;color:var(--muted);font-size:12px} .p code{background:var(--code);padding:0 6px;border-radius:4px}
.ln{white-space:pre-wrap;word-break:break-word;margin-left:10px} .via{color:var(--via);font-weight:600;font-size:12px} .ty{font-size:11px;background:var(--code);padding:0 6px;border-radius:4px;color:var(--muted)}
.back{color:var(--muted);border-left-style:dashed} .desc{color:var(--muted)}
@media (max-width:800px){.wrap{display:block} nav{position:static;width:auto;max-height:none}}
'''


def html_out(G, cs, path, title, keep_defaults=False):
    e = html.escape
    nav, body = [], []
    for c in cs:
        n, q, anchor = G.N[c], G.qual(c), f'n{c}'
        nav.append(f'<li><a href="#{anchor}"><span class="k">{e(short(n["_type"]))}</span> {e(q)}</a></li>')
        sec = [f'<section id="{anchor}"><h2><span class="k">{e(short(n["_type"]))}</span> {e(q)}</h2>']
        if n.get('Description') not in (None, 'None', ''):
            sec.append(f'<p class="desc">{e(n["Description"])}</p>')
        ps = G.params(c)
        if ps:
            sec.append('<table><tr><th></th><th>Name</th><th>Type</th><th>Note</th></tr>' + ''.join(
                f'<tr><td>{e(k)}</td><td><code>{e(nm)}</code></td><td>{e(ty)}</td><td>{e(" ".join(x for x in (extra, desc) if x))}</td></tr>'
                for k, nm, ty, extra, desc in ps) + '</table>')
        if n['_type'] in UI:
            ws = G.widgets(c, keep_defaults)
            if ws:
                sec.append('<h3>Widgets</h3>' + ''.join(
                    f'<div class="w" style="--d:{d}"><b>{e(label)}</b>' + ''.join(f'<div class="p"><span>{e(k)}</span><code>{e(v)}</code></div>' for k, v in props) + '</div>'
                    for d, label, props in ws))
        fl = G.flow(c)
        if fl:
            sec.append('<h3>Flow</h3>' + ''.join(
                f'<div class="s{" back" if typ == "goto" else ""}" style="--d:{d}">' + (f'<span class="via">{e(via)}</span> ' if via else '') +
                (f'&larr; back to {e(label)}' if typ == 'goto' else f'<span class="ty">{e(typ)}</span> <b>{e(label)}</b>') +
                ''.join(f'<div class="ln">{e(line)}</div>' for line in lines) + '</div>' for d, via, typ, label, lines in fl))
        sec.append('</section>')
        body.append(''.join(sec))
    st = G.structures()
    if st:
        nav.append('<li><a href="#structures"><span class="k">Structures</span></a></li>')
        body.append('<section id="structures"><h2>Structures</h2>' + ''.join(
            f'<h3>{e(s)}</h3><table>' + ''.join(f'<tr><td><code>{e(a)}</code></td><td>{e(t)}</td></tr>' for a, t in attrs) + '</table>'
            for s, attrs in st) + '</section>')
    page = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{e(title)}</title><style>{PAGE_CSS}</style></head><body>\n'
            f'<header><b>{e(title)}</b><p>Built from an ODC context_graph result by odc_graph.py {__version__}. Literals stored only as a hash show as '
            f'&lt;text len N sha1 H&gt;; references the graph could not resolve show as ?. Indented = branch (True / False / Cycle); '
            f'&larr; back to = goes back to a node already shown.</p></header>\n'
            f'<div class="wrap"><nav><input placeholder="Filter..." aria-label="Filter" oninput="for(const li of this.nextElementSibling.children)'
            f'li.style.display=li.textContent.toLowerCase().includes(this.value.toLowerCase())?\'\':\'none\'"><ul>{"".join(nav)}</ul></nav>'
            f'<main>{"".join(body)}</main></div>\n</body></html>\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)
    print('wrote', path, len(cs), 'elements')


def save(paths, header, body, dot, save_dir, name):
    os.makedirs(save_dir, exist_ok=True)
    base = os.path.join(save_dir, name or f'{header.get("app_key", "graph")}_rev{header.get("revision", "")}_root-{header.get("root") or "all"}')
    for k, p in enumerate(paths, 1):
        suffix = '' if len(paths) == 1 else f'.page{k}'
        shutil.copyfile(p, f'{base}{suffix}.mcp-response.json')
    if body is not None:
        with open(base + '.xre.json', 'w', encoding='utf-8') as f:
            f.write(body)
    if dot:
        with open(base + '.dot', 'w', encoding='utf-8') as f:
            f.write(dot)
    print('saved', base + '.*')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Read an ODC context_graph result.')
    ap.add_argument('graph', nargs='+', help='saved context_graph response file(s), pages in order, or one .xre.json')
    ap.add_argument('--list', action='store_true', help='list screens, blocks, actions and structures')
    ap.add_argument('--text', action='store_true', help='print an outline')
    ap.add_argument('--html', metavar='FILE', help='write a browsable HTML page')
    ap.add_argument('--only', metavar='NAME', help='only elements whose qualified name contains NAME (case-insensitive)')
    ap.add_argument('--guess', action='append', default=[], metavar='TEXT', help='literal to match against hashed Text nodes (repeatable)')
    ap.add_argument('--keep-defaults', action='store_true', help='also print Visible=True, Enabled=True, Width=(fill parent)')
    ap.add_argument('--save-dir', metavar='DIR', help='copy the raw response(s) and write the joined .xre.json (and .dot) here')
    ap.add_argument('--name', help='base file name for --save-dir, e.g. MyApp_rev12_root-Orders')
    ap.add_argument('--version', action='version', version=__version__)
    a = ap.parse_args(argv)
    g, header, body, dot = load(a.graph)
    if header:
        print('header:', json.dumps(header))
    if a.save_dir:
        save(a.graph, header, body, dot, a.save_dir, a.name)
    G = Graph(g, a.guess)
    cs = G.containers(a.only)
    if a.only and not cs:
        print(f'no element matches "{a.only}"; run --list', file=sys.stderr)
    if a.list:
        for c in cs:
            print(f'{short(G.N[c]["_type"]):22} {G.qual(c)}')
        for s, attrs in G.structures():
            print(f'{"Structure":22} {s} ({len(attrs)} attributes)')
    if a.text:
        text_out(G, cs, a.keep_defaults)
    if a.html:
        title = a.name or (f'{header.get("root") or "graph"} rev {header.get("revision", "")}' if header else os.path.basename(a.graph[0]))
        html_out(G, cs, a.html, title, a.keep_defaults)
    if not (a.list or a.text or a.html or a.save_dir):
        ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
