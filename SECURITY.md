# Security

The scripts in this repository only read the files you pass them and write the files you name. They make no network calls. `shot.py` starts a local headless browser on the page you give it.

Graph files exported from `context_graph` contain your application's model (logic, UI, names). Treat them like source code:
- save them outside your repositories, or add `graph/`, `*.xre.json`, `*.mcp-response.json` and `*.dot` to the project's `.gitignore` before saving inside one;
- never attach them to public issues or pull requests here. Build a small synthetic graph instead (see `tests/test_odc_graph.py`).

To report a vulnerability, open a private security advisory on the GitHub repository instead of a public issue.
