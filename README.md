# ODC Agent Toolkit

Field-tested skills and scripts for working on **OutSystems Developer Cloud (ODC)** apps with [Claude Code](https://claude.com/claude-code) and the [OutSystems MCP server](https://github.com/OutSystems/outsystems-mcp).

The vendor plugin gives your agent the tools. This toolkit adds the working habits that keep those tools from producing quiet mistakes: verify every publish against the stored model, read Mobile apps that Mentor cannot open, and turn changes into build guides a developer can follow in ODC Studio without retyping a single expression.

> Community project. Not affiliated with, endorsed by or supported by OutSystems. "OutSystems" is a trademark of OutSystems.

## What is inside

| Skill | What it does |
|---|---|
| `odc-workflow` | Working rules: what MCP can and cannot do per asset type, the edit → confirm → publish → **verify** loop with Mentor, Mobile apps, Mentor prompt rules, polling, confirmations, library release, ODC facts that cause small mistakes. |
| `odc-graph` | `odc_graph.py` turns a `context_graph` result (one 0.5–3 MB JSON line) into an outline or a browsable HTML page: flows, expressions, widget tree with Style Classes, events, JavaScript nodes. It keeps raw files and confirms literals stored as hashes. |
| `odc-studio-guide` | An HTML template for ODC Studio build guides (every value click-to-copy, copy progress remembered, automatic index), `check_guide.py`, which catches broken expressions, curly quotes, Unicode minus signs, unescaped `<`, bad JSON, broken links and leftover placeholders before hand-over, and `shot.py`, a headless screenshot helper that cannot hang the shell. |

Also: `rules/odc-workflow.md` (an optional always-on summary to copy into `~/.claude/rules/`) and `examples/sample-guide.html` (a filled guide for a fictional app).

## Why

Lessons from real ODC projects that the vendor skill does not cover:

- **Mobile apps cannot be edited over MCP.** `mentor_load_asset` accepts WebApplication, Agent, Library and Workflow only. Context lookups list a Mobile app's elements, but `context_graph` is the only way to read its logic and UI, and changes have to be built by hand in ODC Studio.
- **A successful Mentor turn is not proof.** We have seen Mentor drop a `+ X` term from an expression it rewrote, and store a regex `\p{L}` as `\\p{L}`, which turned a search into "match almost everything". Both turns reported success: a tester caught the regex, and reading the published graph caught the dropped term.
- **Libraries are not deployed.** They are released (ODC Portal, or the Mentor session) and travel inside each consumer, which must update the dependency and publish.
- **Raw graphs are unreadable**, and literals may be stored only as SHA-1 prefixes.
- **Hand-typed Studio values break in small ways**: a curly quote, a `−` instead of `-`, an unescaped `<` in HTML.

## Requirements

- Claude Code with plugin support.
- The OutSystems MCP plugin, connected to your tenant:
  ```bash
  claude plugin marketplace add OutSystems/outsystems-mcp
  claude plugin install outsystems@outsystems --config tenant_hostname=<your-tenant>.outsystems.dev
  ```
- Python 3.9 or later on `PATH` (no packages needed).
- Optional: headless Chrome or Edge, to screenshot guides and previews.

## Install

In Claude Code:

```text
/plugin marketplace add HoangAnhPTIT/odc-agent-toolkit
/plugin install odc-agent-toolkit@odc-agent-toolkit
```

Restart Claude Code. The skills load when a task touches ODC. To keep the main rules in every session, copy `rules/odc-workflow.md` to `~/.claude/rules/`.

From a local clone (development): `/plugin marketplace add /path/to/odc-agent-toolkit`, then install as above.

## Use

Ask in plain language; the skills apply themselves:

- "Read the Orders screen of `<app>` and explain how the search works." Reads the graph and summarises it.
- "Fix the search in library `<lib>`, publish it and check the published version." Runs the Mentor loop, asks you right before publishing, checks `publish_status` and the published graph, releases a version when you ask, and lists the consumer steps left for you.
- "Write a Studio guide to add order notes to the mobile app." Reads the current revision and writes `<topic>-guide.html` from the template, then checks it.

The scripts also work on their own, from a clone of this repository (an installed plugin keeps its copy under `~/.claude/plugins/cache/`):

```bash
python skills/odc-graph/scripts/odc_graph.py saved-graph.json --list
python skills/odc-graph/scripts/odc_graph.py saved-graph.json --text --only "Orders\OnSave"
python skills/odc-graph/scripts/odc_graph.py saved-graph.json --html /tmp/graph.html
python skills/odc-studio-guide/scripts/check_guide.py my-guide.html
python skills/odc-studio-guide/scripts/shot.py my-guide.html /tmp/guide.png --width 1400
```

`saved-graph.json` is the file Claude Code writes when a `context_graph` answer is too large for the conversation (under `~/.claude/projects/<project>/<session>/tool-results/`), or a `.xre.json` produced by `--save-dir`.

## The verify loop

```text
read (context_graph)  ->  design + hand-test the expression  ->  Mentor edit (no publish)
      ^                                                                   |
      |                                                          check result fields
  report what was verified                                                |
      ^                                                       ask the user, publish
      |                                                                   |
  compare every expression  <-  context_graph of the new revision  <-  publish_status
                                                                        + env_app revision
```

## Limitations

- `context_graph` reads published revisions only, can lag a publish, and leaves some references unresolved (client variables, static entity records, elements of other modules). The script prints those as `?`.
- The graph is the model, not the runtime: test behaviour with real requests.
- Tool names and behaviour come from the OutSystems MCP server and can change between releases; the skills follow the live tool list.
- Raw graphs contain your client's model. Save them outside your repositories, or add `graph/`, `*.xre.json` and `*.mcp-response.json` to your project's `.gitignore` (the skills tell the agent to do this).

## Develop

```bash
python -m unittest discover -s tests -v
claude plugin validate .
```

See [CONTRIBUTING.md](CONTRIBUTING.md). New rules need evidence: a docs-odc page, a tool description, or a reproducible observation.

## License

[MIT](LICENSE).
