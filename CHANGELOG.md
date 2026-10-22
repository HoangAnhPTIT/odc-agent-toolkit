# Changelog

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
