---
name: odc-workflow
description: Field-tested working rules for OutSystems Developer Cloud (ODC) through the OutSystems MCP server — what MCP can and cannot do per asset type, the edit → confirm → publish → verify loop with Mentor, Mobile apps (read-only over MCP, changed through a Studio guide), Mentor prompt rules, polling, confirmations, and ODC facts that cause small mistakes. Use for any ODC task that reads, edits, publishes, deploys or explains an app, library or workflow, together with the vendor skill outsystems:outsystems.
---

# ODC working rules

These rules complement the vendor skill `outsystems:outsystems` (auth, tool catalog, vendor rules); they do not replace it, and where a tool description is stricter, the tool description wins. Load the vendor skill before the first OutSystems tool call of a session. Tool names below are the server's (`context_graph`, `mentor_prompt` …); your host may prefix them (for example `mcp__plugin_outsystems_outsystems__`). Items marked *observed* come from real use of the current server and may change between releases.

## 1. Before the first call
- Work with **asset keys and environment keys**, never names: names collide and can be renamed. No key yet: `app_list` with `search`.
- Read what the project already records (README, CLAUDE.md / AGENTS.md, notes files): current revision, open work, pending questions.
- Facts about ODC come from the docs, not memory. The docs source is public: https://github.com/OutSystems/docs-odc (`src/eap/...`); clone it once, grep it, and name the file you rely on.

## 2. What MCP can do, per asset type

| Asset type | Read | Edit | Publish | Other stages | Verify |
|---|---|---|---|---|---|
| WebApplication | context lookups, `context_graph` | Mentor | through the Mentor session | `deploy_start` (`from_env` required unless you pin `build_key` + `revision`) | `publish_status` = success, then `env_app` revision = the publication's `applicationRevision`, then the graph |
| LowCodeLibrary | same | Mentor | through the Mentor session | **No deployment.** Libraries only get debug builds; a published revision becomes a version when it is **released** (version + release notes): in the ODC Portal, or in the Mentor session (section 3, step 10). Then each consumer updates the dependency in ODC Studio and publishes. The library reaches other stages inside its consumers | `publish_status`, then the graph (libraries are not in `env_app`); a release: `app_revisions` shows the `tag` on the revision |
| MobileApplication | context lookups, `context_graph` | **No.** `mentor_load_asset` accepts only WebApplication, Agent, Library, Workflow. Write a Studio guide (skill `odc-studio-guide`) | the user, in ODC Studio | `deploy_start`, only when asked, after the user published | the graph of the new revision, `env_app` |
| Workflow | context lookups, `context_graph` | Mentor | through the Mentor session | `deploy_start` with `build_key` + `revision` from `build_list` (auto-resolution cannot see workflow deployments: `asset_not_deployed_in_source_env`) | `env_app` errors by design: `asset_type_not_listable_by_env_app` means deployed |
| External library (.NET) | `extlib_contents` | your code | `extlib_upload` → `extlib_publish` | inside consumers | `extlib_status` |

Not possible over MCP: managing an app's dependencies (Mentor does not support it), publishing without a Mentor edit, deleting an app. Turn these into steps for the user, in the guide or the answer.

Sources: docs-odc `building-apps/publishing/publishing-your-assets.md`, `building-apps/libraries/libraries.md`, `agentic-development/outsystems-mcp/evolve-app.md`, `agentic-development/ai-limitations.md`; the descriptions of `mentor_load_asset`, `deploy_start`, `publish_status`, `env_app`.

## 3. Edit a web app or library through Mentor
1. **Read first.** `context_graph` with `root` = the element to change (skill `odc-graph`). Note the current expressions.
2. **Design the change.** Write the exact expressions you will ask for. Run 2–3 sample inputs by hand (input → expected output), including empty input and special characters.
3. `mentor_start_session` → `mentor_load_asset(assetKey)` → `mentor_prompt` (section 5). Load one asset per session (`mentor_create_asset`: "only one asset can be loaded or created per session"); a session runs one turn at a time.
4. Poll to a terminal status (section 6). Read the turn's result. *Observed:* it carries `attemptedChange`, `changeApplied` and `validation.errorCount`; continue only with `changeApplied: true` and 0 errors, and read Mentor's answer.
5. **Confirm with the user, then publish** (section 7). Publish the way the catalog offers (on the current server, a `mentor_prompt` "Publish. Publish message: …"; the note is 500 characters at most). *Observed:* the run's `publishAccepted` event carries `revision` and `publicationKey`.
6. **Confirm the publish**: poll `publish_status` with the publication key until `success`. For an app, `env_app` revision must equal the publication's `applicationRevision`; anything else means the change did not land. A `failed` with `indeterminate: true` may still be building: poll again, **never** publish again.
7. **Verify what was stored. Always; do not trust the turn summary.** `context_graph` with the same root: the header `revision` (not `latest_revision`) must equal the new revision; compare every expression you asked for and the node order; confirm hashed literals with `--guess`. *Observed:* Mentor dropped a `+ X` term while rewriting an Assign it was asked to change, and stored a regex `\p{L}` as `\\p{L}`, which silently turned a search into "match almost everything".
8. Wrong: fix it in the same session, confirm, publish, verify again. Never publish while the previous publish of the same asset is not terminal.
9. `mentor_close_session` when done, or when the session talks about elements that do not exist (close it, open a new one).
10. Library: release when the user asks for it (confirm first, like a publish): in the same session, `mentor_prompt` "Release the published revision <N> of this library as version <X.Y.Z>. Release notes: …". *Observed:* the release lands while Mentor's answer may still call the outcome uncertain; `app_revisions` shows `tag: X.Y.Z` on revision N, and that is the check. Then tell the user what is left (update the dependency in each consumer → publish the consumer) and that consumers do not have the change until then.
11. Test real behaviour when you can (a request and its response, the running app) and say what you did not test.

## 4. Mobile apps: read-only over MCP
- Read logic and UI with `context_graph` (`root` = screen, block or action) and the `odc-graph` script. A screen root is often 2–3 MB on one line: never read or grep the raw file.
- Changes become an HTML build guide for ODC Studio (skill `odc-studio-guide`); the user builds and publishes. Do not try Mentor.
- After the user publishes, `app_list` / `app_revisions` shows the new revision: read its graph and compare it with the guide, item by item.

## 5. Prompting Mentor
- One change per turn. Name the real elements (action, node, variable) as the graph shows them. Give the exact expression text. Add "Do not change any other node, variable or expression", "Do not publish", and "Report the exact stored expression" for anything that matters.
- Keep raw backslashes out of what you send: OutSystems text literals have no escape sequences, and Mentor may double a backslash (*observed*). When a value needs one, build it with `Chr(92)`, e.g. `"[^" + Chr(92) + "p{L}" + Chr(92) + "p{N}]+"`. A backslash-free regex is simpler but not equivalent: after `ToLower`, `[^a-z0-9]+` treats accented and non-Latin letters as separators. Pick deliberately, and check the stored value with `--guess`.
- Describe only what changes, never the whole app again (Mentor rebuilds or duplicates what you restate).
- Mentor does not manage dependencies (docs `ai-limitations.md`). When the change needs a library the asset does not reference yet, the user adds it in ODC Studio first.

## 6. Waiting and polling
- Poll a Mentor run right after starting it. While it is not terminal, wait at least 30 s between polls: in Claude Code run `sleep 40` with `run_in_background` and poll when it completes; give the user one short line per wait. Publish and deploy: 5–15 s.
- The vendor sub-agent `outsystems:status-watcher` waits with a foreground `sleep`. *Observed* with Claude Code 2.1.x: the harness rejected that sleep, and the watcher came back almost at once with `OUTCOME: running` and a reason saying no wait was completed. Relaunching it would loop the same way: when you see that reason, poll from the main session instead.
- Only the run's `status` says it ended (`succeeded`, `failed`, `cancelled`). `complete` is an event name and can appear while the run continues.

## 7. Confirm before changing tenant state
- **Publish, deploy, rollback: always confirm right before the call**, restating the asset key, the environment key and what will happen, even when the request already implies it ("fix it and deploy"). Do the edit first, then confirm (the `deploy_start` / `deploy_rollback` descriptions require this).
- Creating an app, uploading / publishing / deleting an external library: confirm first, unless the user authorised exactly that operation in the current turn (vendor skill). An approval never carries over to a later operation.
- No confirmation needed: reads, searches, edits inside a Mentor session, a deployment-impact analysis (`delete: false`).

## 8. Context lookups or the graph
- Context lookups (`context_entities`, `context_actions`, `context_screens`, `context_search` …) are fast and good for listing and finding. With `app` set, `owned_only` defaults to `true`; pass `false` to include library-provided rows. `app_refs` is only complete for the kinds listed in `indexedKinds`.
- `context_graph` gives full logic and UI, for published revisions only, and can lag a publish (`graph_pending`, or an older revision with a `revision_note`). One call at a time.

## 9. ODC facts that cause small mistakes
- Text literal: `"..."`; a quote inside is written `""`; there are no backslash escapes; line break = `NewLine()`; any character = `Chr(n)`.
- `Max` and `Min` take and return Decimal. Assigning a Decimal to an Integer converts implicitly and **truncates**; `DecimalToInteger` **rounds half to even** in client and server logic. Choose on purpose (docs-odc `building-apps/data/convert-data-types.md`, `reference/built-in-functions/data-conversion.md`).
- Roles: ODC generates `Check<RoleName>Role()`, for example `CheckManagerRole()`; there is no generated role variable (docs-odc `user-management/secure-app-with-roles.md`).
- *Observed* runtime HTML: Expression and Text render as `<span>`, Container as `div`, Link as `a`, Button as `button`; an If adds no wrapper; a block instance is wrapped in `div.OSBlockWidget`; an Input sits inside `span.input-text`. A class on an Expression or Text that needs vertical margin, width, text-align, ellipsis or its own line must set `display` (unless the parent is flex or grid).
- OutSystems UI already styles `main-content`, `sidebar`, `header`, `content`, `footer`, `main`, `layout`: do not reuse them for your own classes. Its `a { color: inherit !important }` means link colours need `!important`. Do not put interactive widgets (Input, Button, Upload) inside a Link. (Vendor design-to-app gotchas, `theme-collisions.md`, `widget-link-slot.md`.)
- *Observed:* Studio rejects an output parameter that has the same name as an input parameter of the same action.
- Mobile apps have no app Settings: "In mobile apps, extensibility settings replace ODC app settings" (docs-odc `building-apps/mobile/configuring-mobile-apps.md`). Do not plan a Setting as a switch or mock in a Mobile app.
- *Observed:* Layout placeholders (Title, HeaderRight …) wrap their content in their own `div`; in the header's flex row it keeps its content width, so an ellipsis inside it needs `min-width: 0` on that div.
- Client variables are not indexed by the context lookups and show as `?` in graph expressions; read their names from Assign / If `DisplayName` (skill `odc-graph`). Check which flows set them before relying on one: a variable set in only one flow (for example only by a picker) is empty for users who never pass through it.
- *Observed:* Mentor may drop the **Label** you ask for on a new If / Assign; the graph then shows the condition as the name (`True?`). Do not point a guide or a later prompt at a label before the graph shows it.
- *Observed:* when someone else published the asset while your session was open, the publish run carries `publishAutoMerged` (the other revision) before `publishAccepted`. Tell the user, and read the graph of the new revision, not only your own elements.
- Library revision numbers grow with every publish; a version exists only after a Release (the revision's `tag` in `app_revisions`). Consumers see a "library updates available" prompt when opened in ODC Studio (docs-odc `building-apps/libraries/libraries.md`).

## 10. Optional conventions
Apply these only when the user or the project asks for them:
- Deliver guides and reports as complete HTML files in the project folder, so they open in a browser and live in git.
- Do not encode design rounds in model names (classes, blocks, structures, actions: no `--v3`, `OrderLineV3`); restyle in place or use a descriptive modifier (`--pending`). A version may appear in a document's file name.
- In documents you write, when a new section replaces an old one, replace it in place instead of keeping both with a "replaced by" note. This is about your own documents, never about deleting app elements.
- `check_guide.py --conventions` warns about the first two in guides.

## 11. Tools in this plugin
- Skill `odc-graph`: `scripts/odc_graph.py` keeps raw graph files, lists elements, prints outlines, writes an HTML page, matches hashed literals.
- Skill `odc-studio-guide`: `assets/template.html`, `scripts/check_guide.py`, and `scripts/shot.py` (headless screenshot with a timeout that stops a hung browser and tries the next one; works on Windows, macOS, Linux).
- Python printing non-ASCII text on Windows: set `PYTHONIOENCODING=utf-8` (the cp1252 console default fails).
- Keep raw graphs out of version control: save them outside the repository or add `graph/`, `*.xre.json`, `*.mcp-response.json` to the project's `.gitignore`.
- Report honestly: what you verified (revision, graph, request) and what you did not test.
