# Contributing

Thanks for helping other ODC developers avoid the same mistakes.

## What makes a good rule

Every rule or "fact" in a skill needs one of:

- a page in the ODC docs (https://github.com/OutSystems/docs-odc, give the `src/...` path),
- an OutSystems MCP tool description (quote the sentence),
- a reproducible observation, marked "observed", with the steps to see it again.

Write rules as instructions an agent can follow ("Verify X with Y"), not as stories. Keep each skill focused: workflow rules in `odc-workflow`, graph reading in `odc-graph`, Studio guides in `odc-studio-guide`.

## Never include

- Graph dumps, screenshots or names from a real client app. Build test fixtures by hand (see `tests/test_odc_graph.py`).
- Tenant hostnames, asset keys, environment keys, emails, tokens.

## Scripts

- Python 3.9+, standard library only.
- Add or update a test for every behaviour change: `python -m unittest discover -s tests -v`.
- Keep the CLI flags backwards compatible; bump `__version__` and the plugin version together.

## Releasing

1. Update `CHANGELOG.md` and the version in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and both scripts.
2. `claude plugin validate .` and the tests must pass.
3. Tag `vX.Y.Z`.
