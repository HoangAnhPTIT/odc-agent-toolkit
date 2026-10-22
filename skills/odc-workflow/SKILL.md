---
name: odc-workflow
description: Field-tested working rules for OutSystems Developer Cloud (ODC) through the OutSystems MCP server — what MCP can and cannot do per asset type, the edit → confirm → publish → verify loop with Mentor, Mobile apps (read-only over MCP, changed through a Studio guide), Mentor prompt rules, polling, confirmations, and ODC facts that cause small mistakes. Use for any ODC task that reads, edits, publishes, deploys or explains an app, library or workflow, together with the vendor skill outsystems:outsystems.
---

# ODC working rules

These rules complement the vendor skill `outsystems:outsystems` (auth, tool catalog, vendor rules); they do not replace it. Load the vendor skill before the first OutSystems tool call of a session. Tool names below are the server's (`context_graph`, `mentor_prompt` …); your host may prefix them (for example `mcp__plugin_outsystems_outsystems__`).

## 1. Before the first call
- Work with **asset keys and environment keys**, never names: names collide and can be renamed. No key yet: `app_list` with `search`.
- Read the project's notes (NOTES / AGENTS / CLAUDE files): current revision, open work, pending questions.
- Facts about ODC come from the docs, not memory. The docs source is public: https://github.com/OutSystems/docs-odc (`src/eap/...`); clone it once and grep it, and name the file you rely on.

## 2. What MCP can do, per asset type

| Asset type | Read | Edit | Publish | Other stages | Verify |
|---|---|---|---|---|---|
| WebApplication | context lookups, `context_graph` | Mentor | Mentor ("Publish") | `deploy_start` (`from_env` required unless you pin `build_key` + `revision`) | `env_app`: revision = the one just published |
| LowCodeLibrary | same | Mentor | Mentor | **No deployment.** Libraries only get debug builds; a user with the Release permission **releases** a revision in the ODC Portal (version + release notes), then each consumer updates the dependency in ODC Studio and publishes. The library reaches other stages inside its consumers | `context_graph` header revision + the edited nodes |
| MobileApplication | context lookups, `context_graph` | **No.** `mentor_load_asset` accepts only WebApplication, Agent, Library, Workflow. Write a Studio guide (skill `odc-studio-guide`) | the user, in ODC Studio | `deploy_start`, only when asked, after the user published | `context_graph` of the new revision, `env_app` |
| Workflow | context lookups, `context_graph` | Mentor | Mentor | `deploy_start` | `env_app` errors by design: `asset_type_not_listable_by_env_app` means deployed |
| External library (.NET) | `extlib_contents` | your code | `extlib_upload` → `extlib_publish` | inside consumers | `extlib_status` |

MCP cannot: release a library, update an app's dependencies, publish without a Mentor edit, delete an app, paste Theme CSS, add a Script to a layout. Turn these into steps for the user (in the guide or the answer).

Sources: docs-odc `building-apps/publishing/publishing-your-assets.md`, `building-apps/libraries/libraries.md`, `agentic-development/outsystems-mcp/evolve-app.md`, `agentic-development/ai-limitations.md`; the `mentor_load_asset` tool description.

## 3. Edit a web app or library through Mentor
1. **Read first.** `context_graph` with `root` = the element to change (skill `odc-graph`). Note the current expressions.
2. **Design the change.** Write the exact expressions you will ask for. Run 2–3 sample inputs by hand (input → expected output), including empty input and special characters.
3. `mentor_start_session` → `mentor_load_asset(assetKey)` → `mentor_prompt` (section 5). One session holds one asset and runs one turn at a time.
4. Poll to a terminal status (section 6). Read `result`: `changeApplied: true`, `validation.errorCount: 0`, and Mentor's answer.
5. **Ask the user before publishing** (section 7). Publish with `mentor_prompt` "Publish. Publish message: …" (500 characters at most). The `publishAccepted` / `publishSucceeded` events carry the new `revision`.
6. **Verify what was published. Always; do not trust the turn summary.** `context_graph` with the same root: the header `revision` must equal the new revision; compare every expression you asked for and the node order; confirm hashed literals with `--guess`. Observed in practice: Mentor dropped a `+ X` term while rewriting an Assign it was asked to change, and stored a regex `\p{L}` as `\\p{L}`, which silently broke a search.
7. Wrong: fix it in the same session, publish again, verify again. Never publish while the previous publish of the same asset is not terminal. A publish result with `indeterminate: true` may still be building: poll again, do **not** publish again.
8. `mentor_close_session` when done, or when the session answers about elements that do not exist (close, open a new one).
9. Library: tell the user the remaining steps (Release → update the dependency in each consumer → publish the consumer) and that consumers do not have the change until then.
10. Test real behaviour when you can (a request and its response, the running app) and say what you did not test.

## 4. Mobile apps: read-only over MCP
- Read with `context_graph` (`root` = screen, block or action) and the `odc-graph` script. A screen root is often 2–3 MB on one line: never read or grep the raw file.
- Changes become an HTML build guide for ODC Studio (skill `odc-studio-guide`); the user builds and publishes. Do not try Mentor.
- After the user publishes, `app_list` / `app_revisions` shows the new revision: read its graph and compare it with the guide, item by item.

## 5. Prompting Mentor
- One change per turn. Name the real elements (action, node, variable) as the graph shows them. Give the exact expression text. Add "Do not change any other node, variable or expression", "Do not publish", and "Report the exact stored expression" for anything that matters.
- Keep backslashes out of literals you send: OutSystems text literals have no escape sequences, and Mentor may double a backslash. Use `Chr(92)` when you need one. In regex patterns avoid `\p{…}`, `\d`, `\s`, `\w`; write `[a-z0-9]`, `[0-9]`, `[ ]`.
- Describe only what changes, never the whole app again (Mentor rebuilds or duplicates what you restate).
- Mentor may fail to add a new dependency. When the change needs a library the asset does not reference yet, ask the user to add it in ODC Studio.

## 6. Waiting and polling
- Poll a Mentor run right after starting it. While it is not terminal, wait at least 30 s between polls: in Claude Code run `sleep 40` with `run_in_background` and poll when it completes; give the user one short line per wait. Publish and deploy: 5–15 s.
- The vendor sub-agent `outsystems:status-watcher` waits with a foreground `sleep`. Claude Code builds that block foreground sleep make it return `running` without having waited; then poll from the main session.
- Only the run's `status` says it ended (`succeeded`, `failed`, `cancelled`). `complete` is an event name and can appear while the run continues.

## 7. Confirm before changing tenant state
- Publishing, deploying, rolling back, creating an app, uploading / publishing / deleting an external library: restate the operation with the asset key and environment key, then wait for the user. Exception: the user authorised exactly this operation in the current turn ("fix it and publish"). An earlier approval does not carry over to a new operation.
- No confirmation needed: reads, searches, edits inside a Mentor session, a deployment-impact analysis (`delete: false`).

## 8. Context lookups or the graph
- Context lookups (`context_entities`, `context_actions`, `context_screens`, `context_search` …) are fast and good for listing and finding. With `app` set, `owned_only` defaults to `true`; pass `false` to include library-provided rows. `app_refs` is only complete for the kinds listed in `indexedKinds`.
- `context_graph` gives full logic and UI, for published revisions only, and can lag a publish (`graph_pending`). One call at a time.

## 9. ODC facts that cause small mistakes
- Text literal: `"..."`; a quote inside is written `""`; there are no backslash escapes; line break = `NewLine()`; any character = `Chr(n)`.
- `Max` and `Min` take and return Decimal: wrap them in `DecimalToInteger(...)` when assigning to an Integer (docs-odc `reference/built-in-functions/numeric.md`).
- Roles: ODC generates `Check<RoleName>Role()` (for a role Store: `CheckStoreRole()`); there is no `IsStore` variable (docs-odc `user-management/secure-app-with-roles.md`).
- Observed runtime HTML: Expression and Text render as `<span>`, Container as `div`, Link as `a`, Button as `button`; an If adds no wrapper; a block instance is wrapped in `div.OSBlockWidget`; an Input sits inside `span.input-text`. A class on an Expression or Text that needs vertical margin, width, text-align, ellipsis or its own line must set `display` (unless the parent is flex or grid).
- OutSystems UI already styles `main-content`, `sidebar`, `header`, `content`, `footer`, `main`, `layout`: do not reuse them for your own classes. Its `a { color: inherit !important }` means link colours need `!important`. Do not put interactive widgets (Input, Button, Upload) inside a Link. (From the vendor design-to-app gotchas.)
- Observed: Studio rejects an output parameter that has the same name as an input parameter of the same action.
- Library revision numbers grow with every publish; a version exists only after a Release. Consumers get a "library updates available" prompt when opened in ODC Studio.

## 10. Conventions (opinionated; override them in your own CLAUDE.md)
- Deliver guides and reports as complete HTML files in the project folder, so they open in a browser and live in git.
- Do not encode design rounds in model names (classes, blocks, structures, actions: no `--v3`, `OrderLineV3`). Restyle in place or use a descriptive modifier (`--pending`). A version may appear in a document's file name.
- When something replaces an older version, delete the old one and put the new one in its place; do not keep it with a "replaced by" note. Git keeps history.
- Report honestly: what you verified (revision, graph, request) and what you did not test.

## 11. Tools in this plugin
- Skill `odc-graph`: `scripts/odc_graph.py` saves raw graph files, lists elements, prints outlines, writes an HTML page, matches hashed literals.
- Skill `odc-studio-guide`: `assets/template.html` and `scripts/check_guide.py` for Studio build guides.
- Python printing non-ASCII text on Windows: set `PYTHONIOENCODING=utf-8` (the console default cp1252 fails).
- Headless browser screenshots (checking a guide or preview): always wrap them in `timeout 60`; headless Chrome / Edge can hang and block the shell.
