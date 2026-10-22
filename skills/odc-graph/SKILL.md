---
name: odc-graph
description: Read an OutSystems Developer Cloud (ODC) app or library model through the MCP context_graph tool — fetch it, keep the raw files, turn the XRE into a readable outline or HTML page (flows, expressions, widget tree, Style Classes, JavaScript nodes), match hashed literals, and verify what a publish stored. Use whenever you need the logic or UI of an ODC asset, always for Mobile apps (Mentor cannot load them), and after every publish to confirm the change landed.
---

# Read an ODC model with context_graph

`context_graph` returns the stored model graph (XRE JSON) of an asset's latest published revision. It is the only way to read a Mobile app's logic and UI over MCP, and the most precise way to check what a Mentor edit or a publish really stored.

The script lives next to this file: `<skill-dir>/scripts/odc_graph.py`, where `<skill-dir>` is the base directory shown when this skill loads. Python 3.9+, no dependencies.

## 1. Fetch

- `key` = the asset key (not the name). `root` = the element you need: a server or client action, block or screen name. Without `root` you get the whole app, usually too large.
- One call at a time. Parallel calls hit the per-replica budget (`server_busy`, a CapacityError): retry with backoff.
- Usual errors: `graph_pending` (the newest revision is not processed yet, normal right after a publish: retry in about a minute), `graph_store_warming` (about 30 s), `graph_root_not_found` (wrong root name), `graph_source_too_large` (use a narrower root).
- Paged answers: while the header says `has_more: true`, call again with `cursor = next_cursor` and the same `key`, `root` and `graphviz`, and pass every page file to the script, in order.
- The answer is normally too large for the context, so the host saves it to a file. Do not read or grep that file directly (one line of 0.5–3 MB); use the script.

## 2. Use the script

```bash
G="<file the host saved>"            # several files for a paged answer, in order
P="<skill-dir>/scripts/odc_graph.py"
python "$P" "$G" --list                              # screens, blocks, actions, data actions, structures
python "$P" "$G" --text --only "Orders\OnSave"       # outline: parameters, flow, every expression
python "$P" "$G" --text --only OrderCard             # block: inputs, widget tree with Style Classes, events
python "$P" "$G" --html graph/orders.html            # browsable page with a filter box
python "$P" "$G" --save-dir graph --name MyApp_rev57_root-Orders   # keep the raw files
python "$P" "$G" --guess "[^a-z0-9]+" --text --only BuildQuery    # confirm a literal stored as a hash
```

- `--only` matches a substring of the qualified name (`Screen\Action`), case-insensitive.
- `--save-dir` copies the response file(s) unchanged and writes the joined `.xre.json` (and `.dot` when you asked for `graphviz`). Name files `<App>_rev<revision>_root-<Root>`; the `header:` line gives the revision. Raw graphs are your client's model: keep them out of public repositories.
- `--keep-defaults` also prints `Visible: True`, `Enabled: True`, `Width: (fill parent)`.

## 3. What the graph holds

- `nodes[i]` with a `_type`; edges are three parallel arrays, `edgeSrc[k]` → `edgeDst[k]` with meaning `edgeAttr[k]`.
- `relationType: Parent` + `_type` = containment: action → `obj.Nodes` (flow nodes), `InputParameters`, `OutputParameters`, `LocalVariables`; Assign → `Assignments`; If → `Condition`; widget → `Widgets`, `TrueBranch` / `FalseBranch`, `PlaceholdersContent`; expressions → `Root`, `LeftOperand`, `RightOperand`, `Argument`, `IdentifierPart`.
- `Connector` + `connectorType` = flow arrows: `Links.Sequence`, `Links.True` / `Links.False`, `Links.Cycle` (For Each body), `Otherwise`.
- `ReferedObject`, `Action`, `Destination`, `DataSource`, `SourceBlock`, `DataType` = references to other nodes.
- Plain text you can read directly: `IAssignment.DisplayName` (the whole `X = expression`), `IIfNode.DisplayName` (the condition plus `?`, unless the If has a Label), `IJavaScriptNode.JsSourceText`, `INRTextWidget.Text`, `IComment.Text`, every element's `Description`.
- Text literals are either `TextValue` (plain; most short literals in current graphs) or only `TextLength` + `TextHash`, where the hash is the first 10 hex digits of the SHA-1 of the UTF-8 text. A hash can be confirmed, not reversed: `sha1("[^a-z0-9]+")[:10] = cad7a76527`, `sha1("")[:10] = da39a3ee5e`.
- A widget's Style Classes hang on a plain `Style` edge (no `relationType`). Extended properties (attributes) are `IExtendedProperty{Property}` → `Value`.
- Reactive Web and Mobile apps both use `IMobileScreen` / `IMobileBlock`; client screen actions are `IClientScreenAction`.
- References the graph could not resolve (client variables, static entity records, some list `Current`s, elements from other modules) point at a Text node; the script prints `?`. Take the real name from Studio or an earlier guide; never guess it.

## 4. Limits

- Published revisions only. Unpublished Mentor edits are not in the graph: publish, then read.
- The index can lag a publish: trust the graph only when the header `revision` / `latest_revision` equals the revision the publish reported.
- A rooted graph holds the root and what it references, not the whole app. Say which root you read.
- It is the model, not the runtime: it cannot tell you what a regex, a query or an API returns. Test that with real requests.

## 5. Verify a publish (always)

1. Take the `revision` from the `publishAccepted` / `publishSucceeded` event.
2. `context_graph` with the edited element as `root`; the header `revision` must equal it (on `graph_pending`, wait about a minute and call again).
3. `--text --only <element>`: check every expression you asked for, node by node, and the flow order. Mentor can silently drop or rewrite part of an expression it touched.
4. For literals stored as hashes, run `--guess "<expected text>"`: the value must print as text, not as `<text len … sha1 …>`.
5. Report what you checked and what you could not check (runtime behaviour).
