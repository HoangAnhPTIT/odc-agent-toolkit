"""Tests for skills/odc-graph/scripts/odc_graph.py on a small synthetic graph (no real app model)."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('odc_graph', os.path.join(ROOT, 'skills', 'odc-graph', 'scripts', 'odc_graph.py'))
odc_graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(odc_graph)


def sha10(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]


class Builder:
    def __init__(self):
        self.nodes, self.src, self.dst, self.attr = [], [], [], []

    def node(self, _type, **kw):
        self.nodes.append(dict(_type=_type, **kw))
        return len(self.nodes) - 1

    def edge(self, s, t, _type, parent=True, **kw):
        a = dict(_type=_type, **kw)
        if parent:
            a['relationType'] = 'Parent'
        self.src.append(s)
        self.dst.append(t)
        self.attr.append(a)

    def link(self, s, t, ctype):
        self.src.append(s)
        self.dst.append(t)
        self.attr.append({'_type': 'Connector', 'connectorType': 'Links.' + ctype})

    def graph(self):
        return {'v': '3.1', 'nodes': self.nodes, 'edgeSrc': self.src, 'edgeDst': self.dst, 'edgeAttr': self.attr}


def sample_graph():
    b = Builder()
    text_t = b.node('IBasicType', Name='Text')
    # Server action Calc(A) with local B: B = A + "x"; If B = "secret" -> End
    act = b.node('IServerAction', Name='Calc', Description='demo action')
    a = b.node('IInputParameter', Name='A', IsMandatory=True)
    b.edge(act, a, 'InputParameters', index=0)
    b.edge(a, text_t, 'DataType', parent=False)
    loc = b.node('ILocalVariable', Name='B')
    b.edge(act, loc, 'LocalVariables', index=0)
    start = b.node('IStartNode', Name='Start')
    assign = b.node('IAssignNode', Label='SetB')
    asg = b.node('IAssignment', DisplayName='B = A + "x"')
    b.edge(assign, asg, 'Assignments', index=0)
    if_ = b.node('IIfNode', DisplayName='B = ...?')
    cond = b.node('ExpressionAST')
    b.edge(if_, cond, 'Condition')
    eq = b.node('BinaryOperation', Operator='Eq')
    b.edge(cond, eq, 'Root')
    left = b.node('Identifier')
    b.edge(eq, left, 'LeftOperand')
    b.edge(left, loc, 'ReferedObject', parent=False)
    right = b.node('Text', TextLength=6, TextHash=sha10('secret'), TextCategory='Others')
    b.edge(eq, right, 'RightOperand')
    end = b.node('IEndNode', Name='End')
    for i, n in enumerate((start, assign, if_, end)):
        b.edge(act, n, 'obj.Nodes', index=i)
    b.link(start, assign, 'Sequence')
    b.link(assign, if_, 'Sequence')
    b.link(if_, end, 'True')
    b.link(if_, end, 'False')
    # Block Card with input Item: Container "Box" (Style Classes "card") > Expression Item.Name, Visible = unresolved ref
    blk = b.node('IMobileBlock', Name='Card')
    item = b.node('IInputParameter', Name='Item')
    b.edge(blk, item, 'InputParameters', index=0)
    box = b.node('OutSystems.Plugin.NRWidgets.Container', Name='Box', Width='(fill parent)')
    b.edge(blk, box, 'Widgets', index=0)
    style = b.node('ExpressionAST')
    b.edge(box, style, 'Style', parent=False)  # Style Classes hang on a plain edge
    b.edge(style, b.node('Text', TextValue='card', TextHash='card'), 'Root')
    ex = b.node('OutSystems.Plugin.NRWidgets.Expression', Name=None)
    b.edge(box, ex, 'Widgets', index=0)
    val = b.node('ExpressionAST')
    b.edge(ex, val, 'Value')
    cid = b.node('CompoundIdentifier')
    b.edge(val, cid, 'Root')
    b.edge(cid, item, 'ReferedObject', parent=False)
    part = b.node('Identifier')
    b.edge(cid, part, 'IdentifierPart')
    attr = b.node('IStructureAttribute', Name='Name')
    b.edge(part, attr, 'ReferedObject', parent=False)
    vis = b.node('ExpressionAST')
    b.edge(ex, vis, 'Visible')
    unresolved = b.node('Identifier')
    b.edge(vis, unresolved, 'Root')
    b.edge(unresolved, b.node('Text', TextValue='ignored', TextHash='ignored'), 'ReferedObject', parent=False)
    ev = b.node('IBlockEvent', Name='OnPick', IsMandatory=True)
    b.edge(blk, ev, 'Events', index=0)
    ev_in = b.node('IInputParameter', Name='Code')
    b.edge(ev, ev_in, 'InputParameters', index=0)
    b.edge(ev_in, text_t, 'DataType', parent=False)
    # Exposed REST API Api with method Ping(Req: Text): Start -> End (namespaced types, as in a Web app graph)
    rest = 'OutSystems.Plugin.RESTService.'
    api = b.node(rest + 'RestService', Name='Api')
    ping = b.node(rest + 'RestServiceAction', Name='Ping')
    b.edge(api, ping, 'Actions', index=0)
    req = b.node(rest + 'RestServiceActionInput', Name='Req', IsMandatory=True)
    b.edge(ping, req, 'InputParameters', index=0)
    b.edge(req, text_t, 'DataType', parent=False)
    p_start, p_end = b.node('IStartNode', Name='Start'), b.node('IEndNode', Name='End')
    b.edge(ping, p_start, 'obj.Nodes', index=0)
    b.edge(ping, p_end, 'obj.Nodes', index=1)
    b.link(p_start, p_end, 'Sequence')
    # Structure Item(Name: Text)
    st = b.node('IStructure', Name='Item')
    b.edge(st, attr, 'Attributes', index=0)
    b.edge(attr, text_t, 'DataType', parent=False)
    return b.graph()


def response(xre_text, header=None, extra=()):
    blocks = []
    if header is not None:
        blocks.append({'type': 'text', 'text': json.dumps(header)})
    blocks.append({'type': 'text', 'text': xre_text})
    blocks += [{'type': 'text', 'text': t} for t in extra]
    return blocks


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = odc_graph.main(argv)
    return code, out.getvalue()


class OdcGraphTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.xre = json.dumps(sample_graph())
        self.header = {'app_key': 'demo', 'revision': 7, 'latest_revision': 7, 'root': 'Calc', 'page': 1,
                       'has_more': False, 'blocks': ['xre']}
        self.path = self.write('resp.json', response(self.xre, self.header))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = os.path.join(self.tmp.name, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return p

    def test_outline_of_action(self):
        code, out = run([self.path, '--text', '--only', 'Calc'])
        self.assertEqual(code, 0)
        self.assertIn('=== ServerAction Calc', out)
        self.assertIn('In     A: Text mandatory', out)
        self.assertIn('B = A + "x"', out)
        self.assertIn(f'Condition: (B = <text len 6 sha1 {sha10("secret")}>)', out)
        self.assertIn('[True] End End', out)
        self.assertIn('<- back to End', out)

    def test_guess_resolves_hashed_literal(self):
        _, out = run([self.path, '--text', '--only', 'Calc', '--guess', 'secret'])
        self.assertIn('Condition: (B = "secret")', out)

    def test_widget_tree(self):
        _, out = run([self.path, '--text', '--only', 'Card'])
        self.assertIn('Container Box', out)
        self.assertIn('. Style Classes: "card"', out)
        self.assertIn('. Value: Item.Name', out)
        self.assertIn('. Visible: ?', out)          # unresolved reference
        self.assertNotIn('(fill parent)', out)      # default noise hidden
        _, out = run([self.path, '--text', '--only', 'Card', '--keep-defaults'])
        self.assertIn('Width: (fill parent)', out)

    def test_block_events_and_structure_outline(self):
        _, out = run([self.path, '--text', '--only', 'Card'])
        self.assertIn('Event  OnPick: (Code: Text) mandatory', out)
        _, out = run([self.path, '--text', '--only', 'Item'])
        self.assertIn('=== Structure Item', out)
        self.assertIn('  Name: Text', out)

    def test_list(self):
        _, out = run([self.path, '--list'])
        self.assertIn('MobileBlock', out)
        self.assertIn('ServerAction           Calc', out)
        self.assertIn('Structure              Item (1 attributes)', out)

    def test_indexed_list_part(self):
        # Agg.List[Pos].Id: the List part carries an 'Index' child (Indexer whose Root is the index expression)
        b = Builder()
        agg = b.node('IAggregateNode', Name='Agg')
        lst = b.node('RuntimeProperty', Name='List')
        pos = b.node('ILocalVariable', Name='Pos')
        attr = b.node('IEntityAttribute', Name='Id')
        root = b.node('CompoundIdentifier')
        b.edge(root, agg, 'ReferedObject', parent=False)
        part = b.node('CompoundIdentifier')
        b.edge(root, part, 'IdentifierPart')
        b.edge(part, lst, 'ReferedRuntimeProp', parent=False)
        idx = b.node('Indexer')
        b.edge(part, idx, 'Index')
        pos_id = b.node('Identifier')
        b.edge(idx, pos_id, 'Root')
        b.edge(pos_id, pos, 'ReferedObject', parent=False)
        last = b.node('Identifier')
        b.edge(part, last, 'IdentifierPart')
        b.edge(last, attr, 'ReferedObject', parent=False)
        self.assertEqual(odc_graph.Graph(b.graph()).expr(root), 'Agg.List[Pos].Id')

    def test_rest_method(self):
        _, out = run([self.path, '--list'])
        self.assertIn('RestServiceAction      Api\\Ping', out)
        _, out = run([self.path, '--text', '--only', 'Api\\Ping'])
        self.assertIn('=== RestServiceAction Api\\Ping', out)
        self.assertIn('In     Req: Text mandatory', out)
        self.assertIn('Start Start', out)

    def test_paged_answer_and_graphviz(self):
        half = len(self.xre) // 2
        h1 = dict(self.header, has_more=True, blocks=['xre', 'graphviz'])
        h2 = dict(self.header, page=2, has_more=False, blocks=['xre', 'graphviz'])
        p1 = self.write('p1.json', response(self.xre[:half], h1, extra=['digraph {']))
        p2 = self.write('p2.json', response(self.xre[half:], h2, extra=['}']))
        out_dir = os.path.join(self.tmp.name, 'saved')
        code, out = run([p1, p2, '--list', '--save-dir', out_dir, '--name', 'Demo_rev7_root-Calc'])
        self.assertEqual(code, 0)
        self.assertIn('Calc', out)
        with open(os.path.join(out_dir, 'Demo_rev7_root-Calc.xre.json'), encoding='utf-8') as f:
            self.assertEqual(f.read(), self.xre)
        with open(os.path.join(out_dir, 'Demo_rev7_root-Calc.dot'), encoding='utf-8') as f:
            self.assertEqual(f.read(), 'digraph {}')
        for k, src in ((1, p1), (2, p2)):
            with open(src, 'rb') as a, open(os.path.join(out_dir, f'Demo_rev7_root-Calc.page{k}.mcp-response.json'), 'rb') as b:
                self.assertEqual(a.read(), b.read())

    def test_joined_xre_and_headerless_answer(self):
        joined = os.path.join(self.tmp.name, 'g.xre.json')
        with open(joined, 'w', encoding='utf-8') as f:
            f.write(self.xre)
        _, out = run([joined, '--list'])
        self.assertIn('Calc', out)
        bare = self.write('bare.json', response(self.xre))
        _, out = run([bare, '--list'])
        self.assertIn('Calc', out)

    def test_html(self):
        page = os.path.join(self.tmp.name, 'g.html')
        code, _ = run([self.path, '--html', page])
        self.assertEqual(code, 0)
        with open(page, encoding='utf-8') as f:
            text = f.read()
        self.assertTrue(text.startswith('<!doctype html>'))
        self.assertIn('B = A + &quot;x&quot;', text)
        self.assertIn('Structures', text)

    def test_bom_file_and_unsafe_root_name(self):
        header = dict(self.header, root='Orders\\OnSave:x')
        p = os.path.join(self.tmp.name, 'bom.json')
        with open(p, 'w', encoding='utf-8-sig') as f:  # Windows tools often write a BOM
            json.dump(response(self.xre, header), f)
        out_dir = os.path.join(self.tmp.name, 'saved')
        code, out = run([p, '--save-dir', out_dir])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(out_dir)), ['demo_rev7_root-Orders_OnSave_x.mcp-response.json',
                                                      'demo_rev7_root-Orders_OnSave_x.xre.json'])

    def test_save_joined_xre_keeps_its_type(self):
        joined = os.path.join(self.tmp.name, 'g.xre.json')
        with open(joined, 'w', encoding='utf-8') as f:
            f.write(self.xre)
        out_dir = os.path.join(self.tmp.name, 'saved')
        run([joined, '--save-dir', out_dir, '--name', 'Demo'])
        self.assertEqual(os.listdir(out_dir), ['Demo.xre.json'])

    def test_unreadable_file_exits_cleanly(self):
        p = os.path.join(self.tmp.name, 'broken.json')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('{not json')
        with self.assertRaises(SystemExit) as cm:
            run([p, '--list'])
        self.assertIn('cannot read', str(cm.exception))

    def test_unresolved_reference_to_minus_one(self):
        # observed: a call to a built-in function (GenerateGuid) whose ReferedObject edge points at -1
        b = Builder()
        last = b.node('INRBuiltinEvent', DisplayName='On Change')
        call = b.node('Call')
        b.edge(call, -1, 'ReferedObject', parent=False)
        g = odc_graph.Graph(b.graph())
        self.assertEqual(g.expr(call), '?()')
        self.assertEqual(g.name(last), 'On Change')

    def test_no_match_message(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            run([self.path, '--text', '--only', 'Nope'])
        self.assertIn('no element matches', err.getvalue())


if __name__ == '__main__':
    unittest.main()
