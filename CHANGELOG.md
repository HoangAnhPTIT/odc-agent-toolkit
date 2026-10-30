# Changelog

## 0.1.12 (2026-10-30)

- `odc-workflow` section 5: readable flows. Ask Mentor for named empty Assign nodes as join points (one per phase, plus one before a loop's return), the main path in one column and branches to the right; a far `<- back to X` in the outline is the sign of a flow that needs it.

## 0.1.11 (2026-10-29)

- `odc-workflow` section 9, transactions: `Get<Entity>` / `Get<Entity>ForUpdate` raise an exception for a missing Id (observed message `... with key 'inParamId' was not found.`), so they cannot check existence; lock and check in one SQL node `SELECT ... FOR UPDATE` instead of an aggregate plus `Get<Entity>ForUpdate` or a catch-all handler.

## 0.1.10 (2026-10-29)

- `odc-graph` script: an indexed list in an expression (`Agg.List[Pos].X`) keeps its `[Pos]`; before, expressions rendered from the tree (arguments, conditions) dropped it and read like `Agg.List.X`.

## 0.1.9 (2026-10-29)

- `odc-graph` script: exposed REST methods and their OnAuthentication flow (namespaced `OutSystems.Plugin.RESTService.*` types) are listed and outlined like server actions, named `<API>\<Method>`. Before, `--list` / `--text` skipped them.

## 0.1.8 (2026-10-28)

- `odc-workflow` section 9, transactions: commit only after the whole unit of work (an early commit after creating a parent record leaves it behind on a later error); a unique-index race needs no early commit on PostgreSQL; a service action commits when it ends; unit tests roll back with `AbortTransaction` in the test endpoint instead of a commit switch on the production action.

## 0.1.7 (2026-10-28)

- `odc-workflow` section 9, new "Transactions" fact: one transaction per request, `CommitTransaction` / `AbortTransaction` system actions (AbortTransaction has no docs-odc page), return a business error with assign + `AbortTransaction` + End instead of raising and catching a user exception in the same action, keep handlers for errors you cannot test for first (`DatabaseException`).

## 0.1.6 (2026-10-28)

- `odc-workflow` section 10, new optional convention: a change to a guide already handed over also produces `fix_<guide-name>.html` with only the delta (baseline revisions, what changed, steps to do or undo, tests for the changed parts).
- `odc-studio-guide` step 10: how to change a handed-over guide (in place, plus the fix file under that convention).

## 0.1.5 (2026-10-26)

- `odc-workflow` section 9, new "SQL nodes: write Aurora PostgreSQL": queries on the app's own entities run PostgreSQL syntax (ANSI-92 only with external entities); names, `LIMIT`, `||`, INSERT / UPDATE without entity prefix, case- and accent-insensitive collation (`LIKE` needs `caseaccent_normalize`), list parameters as JSON expanded with `json_array_elements_text` and cast to the column type, empty list as `[]`, bounded results, indexes, no query in a loop, Test Query differs from runtime. Section 5: give Mentor the whole PostgreSQL text and read the stored SQL back.

## 0.1.4 (2026-10-23)

From a field mistake that cost a Studio round trip (a "leave without saving?" guard on a Mobile app screen).

- `odc-workflow` section 9, new "Client actions and JavaScript": screen and block client actions have no output parameters; pass every input when JavaScript calls `$actions.X()` (missing mandatory Booleans ran as False, no error); a JavaScript node's `$parameters` are a copy, so a callback that needs live screen state calls a synchronous screen action that answers through the script; how ODC routes every navigation (history POP from the Android back button included) through `registerNavigationHandler`, then the back-handler queue.
- `odc-studio-guide`: say where each client action lives and never give a screen action an output; JavaScript calling `$actions` passes every input; write and verify both If branches.
- `odc-graph`: read the deployed JavaScript (bundle → screen chunk) to check Required Scripts and compiled JavaScript nodes when a JavaScript feature does not work.

## 0.1.3 (2026-10-22)

- `odc-workflow`: a library can be released from the Mentor session (prompt "Release the published revision N as version X.Y.Z…"), checked with the revision's `tag` in `app_revisions`; Mentor's answer may call a successful release uncertain (observed). Mentor may drop requested node Labels; a publish can auto-merge another user's revision (`publishAutoMerged`).
- `odc-studio-guide`, README, rule: releasing a library is no longer listed as Portal-only.

## 0.1.2 (2026-10-22)

From a blind field test: an agent rebuilt a real Mobile-app feature guide using only this plugin.

- `odc_graph.py --text`: prints a block's own events with their inputs, prints structures (`--only <Structure>`), and adds `Node text:` (the If's DisplayName) when a condition holds unresolved names.
- `shot.py`: keeps a `?query` on file paths (preview states), refuses a missing file, warns that `#fragment` shots come out blank in headless browsers.
- `odc-graph`: what to do with small inline answers; where real client-variable names survive; nested `.gitignore` option.
- `odc-workflow` / `odc-studio-guide`: Mobile apps have no app Settings; Layout placeholders wrap content in their own `div` (ellipsis needs `min-width: 0`); check which flows set a client variable; preview states from the URL query and a self-test state; the checker's limits stated; template UI strings may be translated.

## 0.1.1 (2026-10-22)

Fixes from an independent review against the ODC docs and the OutSystems MCP tool descriptions.

- `odc-workflow`: always confirm right before publish, deploy and rollback, as the tool descriptions require; publish verification now goes `publish_status` → `env_app` revision → graph; Workflow deployments need `build_key` + `revision`; Mentor cannot manage dependencies; regex advice explains the `[a-z0-9]` trade-off and the `Chr(92)` way; Decimal → Integer truncates while `DecimalToInteger` rounds half to even; server-specific details marked *observed*; conventions are opt-in.
- `odc-graph`: correct remedy for `graph_source_too_large`; check the header `revision` (not `latest_revision`) and `revision_note`; literal storage varies by asset; advice to keep raw graphs out of repositories.
- `odc_graph.py`: reads files with a UTF-8 BOM, exits cleanly on unreadable input, safe file names for roots such as `Screen\Action`, `--save-dir` on a joined `.xre.json` keeps its type.
- `check_guide.py`: convention warnings are opt-in (`--conventions`), BOM pages no longer report a missing doctype, `{{}}` placeholders are caught, URLs in literals are not mistaken for JavaScript, one-word prose such as `Continue?` is not checked as an expression.
- New `shot.py`: headless screenshot with a per-browser timeout that stops hung browsers and tries the next one (Windows, macOS, Linux).
- Plugin icon.

## 0.1.0 (2026-10-22)

First release.

- Skill `odc-workflow`: MCP capability matrix per asset type, Mentor edit → confirm → publish → verify loop, Mobile app handling, Mentor prompt rules, polling, confirmations, library release, ODC facts.
- Skill `odc-graph` with `odc_graph.py`: `--list`, `--text`, `--html`, `--save-dir`, `--guess`, paged answers, graphviz blocks, Reactive Web and Mobile widget trees.
- Skill `odc-studio-guide` with `assets/template.html` and `check_guide.py`.
- Optional always-on rule `rules/odc-workflow.md`, example guide, tests.
