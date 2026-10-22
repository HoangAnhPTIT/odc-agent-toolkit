# OutSystems ODC (always-on rule, optional)

Copy this file to `~/.claude/rules/` (every project) or `<project>/.claude/rules/` (one project) if you want these points in every session. The full rules live in the plugin skill `odc-agent-toolkit:odc-workflow`, which loads on demand.

- For any OutSystems Developer Cloud task, load the vendor skill `outsystems:outsystems` and the skill `odc-agent-toolkit:odc-workflow` before the first OutSystems tool call.
- Use asset keys and environment keys, never names.
- Mobile apps cannot be edited over MCP (`mentor_load_asset` accepts WebApplication, Agent, Library, Workflow). Read them with `context_graph` (skill `odc-graph`) and write a Studio build guide (skill `odc-studio-guide`).
- After every publish: `publish_status` must reach `success`; for an app, `env_app` must show the new revision; then read the published element with `context_graph` and check every expression you asked for. Do not trust the turn summary.
- Libraries are not deployed: they are released in the ODC Portal, then each consumer updates the dependency in ODC Studio and publishes.
- Always confirm right before publish, deploy and rollback, even when the request implies it. Confirm app creation and external-library changes unless the user authorised exactly that operation in the current turn.
- Do not send raw backslashes to Mentor (OutSystems literals have no escapes and Mentor may double them): build them with `Chr(92)`, and check the stored value.
