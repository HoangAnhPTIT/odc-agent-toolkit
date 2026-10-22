---
name: odc-studio-guide
description: Write an HTML build guide that a developer follows in ODC Studio to make a change by hand — required for OutSystems Mobile apps (Mentor cannot load them) and for work MCP and Mentor cannot do (updating dependencies, releasing a library, pasting Theme CSS, adding a Script to a layout). Ships a template (click any value to copy it, copy progress kept per browser, automatic index) and a checker that catches broken expressions and pages before hand-over.
---

# ODC Studio build guide

Files next to this one (`<skill-dir>` = the base directory shown when this skill loads):
- `<skill-dir>/assets/template.html`: start every guide from it.
- `<skill-dir>/scripts/check_guide.py`: run it before you hand the guide over.
- A filled example: `examples/sample-guide.html` in the plugin repository.

## When to use
- Any change to a **MobileApplication**: `mentor_load_asset` accepts only WebApplication, Agent, Library, Workflow.
- Work only ODC Studio or the Portal can do: update an app's dependencies, release a library, paste CSS into a Theme, add a Script to a layout (Required Scripts), end-user groups, settings.
- Web apps and libraries: edit through Mentor by default (skill `odc-workflow`); write a guide only when the user wants to build it themselves or Mentor cannot do it.

## Steps
1. **Read the current model** with skill `odc-graph` (`context_graph`, `root` = the screen, block or action you will change). Take real names from it: widget names, actions, variables, events, Style Classes, placeholders. Never invent names. Where the graph prints `?` (client variables, static entities, other modules), use an earlier guide or ask the user.
2. **Read the spec** (and any earlier guide for the same area). Map every requirement to a build step.
3. **Copy the template** to the project: `<topic>-guide.html`.
4. **Write in build order**: spec and current app (app name, **revision**, date you read the graph) → remove the old version → structures, entities, server actions → client functions → blocks → screens (data actions, handlers, widget tree) → CSS → test scenarios and open questions. Drop sections you do not need; keep h2 numbers consecutive and h3 numbers as `<h2>.<n>`.
5. Every Studio step answers three questions: **where** (flow, screen or block, then placeholder, then parent widget), **what** (add, delete, rename, change a property), **value** (a copy cell).
6. **Check**: `python <skill-dir>/scripts/check_guide.py <topic>-guide.html` must report 0 ERROR. Read every warning.
7. New UI: build a preview page with the app's real CSS and look at it (section "Preview").
8. **Hand over**: the file path, a short list of what the user must do, and the open questions with the assumption you built on.
9. **After the user builds and publishes**: read the new revision's graph and compare it with the guide, item by item (names, expressions, Style Classes, node order). Report differences.

## Components (all in the template)

| Component | Use |
|---|---|
| `div.legend` | The flow in one paragraph, or a general note |
| `ol.order` | Build order; each item links to an h2 (the id must exist) |
| Requirement table | Spec requirement → section |
| "Where / What it does now / Change" table | Current app, from the graph (revision + date) |
| "Where / Remove" table | Delete the old version before building |
| Attribute table + `codebar` JSON | Structure. "Copy JSON" and "Copy as text literal" (a one-line OutSystems literal for a Default Value) |
| Parameter table (Input / Output / Local / Event) | Action, block, screen |
| Flow table `# / Node / Value` | Every node of an action, in flow order; values are `code.cc` |
| `pre.code.cc` | Multi-line expression |
| Widget grid (`table.grid`, tree in `td.gl` with `├─ │ └─`, `div.prop` rows) | Widget tree with one copy cell per property; `prop is-note` rows for where-in-Studio hints |
| `span.tag` ("new") | New input, local or event |
| `div.card.ask` | Open questions with a "Building as" column |

A copy cell is any element with class `cc`. The template's first script gives ids (`cc-1`, `cc-2` …) to copy cells that have none; set an id by hand only on an element a `.copy` button targets (`data-target`). Click copies, the value turns green, Shift+click unmarks it; progress is kept in the browser's localStorage per page.

The template marks every value to fill as `{{...}}`; the checker reports any that are left.

## Writing values (small mistakes this prevents)
- A copy cell must paste into Studio as-is: valid OutSystems syntax, ASCII outside literals (no `−` `–` `“ ”`), literals as `"..."` with `""` for a quote inside.
- OutSystems literals have no escapes: `\` is a plain backslash. Use `Chr(92)`, `Chr(34)`, `NewLine()` for special characters.
- Escape HTML inside values: `&lt;` `&gt;` `&amp;`. The copy script reads `textContent`, so the clipboard gets the real characters.
- One cell, one property. Use the property names Studio shows: Style Classes, Visible, Enabled, Value, Condition, Variable, Source, Prompt, On Click, On Change, Events (Properties → Events → + → pick `onblur`), Attributes (`aria-label`, `role`, `inputmode`), screen destinations (`MainFlow\Orders`).
- Use the right widget: an **Expression** holds an expression; a **Text** holds plain typed text (no quotes). Mark plain-text cells `data-kind="text"` and JavaScript cells `data-kind="js"` when the checker guesses wrong.
- Block instances: name the block, then each input and event handler. If widgets: the Condition, then the True and False branches.
- Client actions: inputs / outputs / locals, Function = Yes when it is a function, then every node. When a client action calls the server, add an Exception Handler so a lost connection does not leave the UI locked.
- Server actions: say which version is a **mock** (now) and which is the **real** one (when the API exists).
- `Max` / `Min` return Decimal: wrap them in `DecimalToInteger(...)` when the target is an Integer.
- Roles: use the generated `Check<RoleName>Role()` functions, never invented variables.
- CSS: Expression and Text render as `<span>`, so a class that needs vertical margin, width, text-align, ellipsis or its own line must set `display`. Do not reuse OutSystems UI class names (`main-content`, `sidebar`, `header`, `content`, `footer`, `main`, `layout`); link colours need `!important`.
- Write in the reader's language; keep widget, action and property names exactly as Studio shows them.

## Preview (when the change adds UI)
- A `<topic>-preview.html` that loads the app's real CSS and uses the tags ODC renders: Expression / Text = `span`, Container = `div`, Link = `a`, Button = `button`, If = no wrapper, block instance = `div.OSBlockWidget`, Input inside `span.input-text`.
- Take a screenshot with a headless browser and always a timeout (headless browsers can hang and block the shell), then look at the image:
  `timeout 60 <chrome-or-edge> --headless --disable-gpu --virtual-time-budget=3000 --screenshot=out.png --window-size=500,1200 file:///<path>/x.html`
  (about 500 px wide for phone, 1400 px for desktop).
