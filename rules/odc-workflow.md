# OutSystems ODC (always-on rule, optional)

Copy this file to `~/.claude/rules/` (every project) or `<project>/.claude/rules/` (one project) if you want these points in every session. The full rules live in the plugin skill `odc-agent-toolkit:odc-workflow`, which loads on demand.

- For any OutSystems Developer Cloud task, load the vendor skill `outsystems:outsystems` and the skill `odc-agent-toolkit:odc-workflow` before the first OutSystems tool call.
- Use asset keys and environment keys, never names.
- Mobile apps cannot be edited over MCP (`mentor_load_asset` accepts WebApplication, Agent, Library, Workflow). Read them with `context_graph` (skill `odc-graph`) and write a Studio build guide (skill `odc-studio-guide`).
- After every Mentor publish, read the published element with `context_graph` and check every expression you asked for. Do not trust the turn summary.
- Libraries are not deployed: they are released in the ODC Portal, then each consumer updates the dependency in ODC Studio and publishes.
- Ask before publish, deploy, rollback, app creation and external-library changes, unless the user authorised that exact operation in the current turn.
- No backslashes in text literals sent to Mentor (OutSystems has no escapes; use `Chr(92)`); avoid `\p{…}`, `\d`, `\s`, `\w` in regex patterns.
