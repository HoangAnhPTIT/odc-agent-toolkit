# Security

The scripts in this repository only read files you pass them and write the files you name. They make no network calls.

Graph files exported from `context_graph` contain your application's model (logic, UI, names). Treat them like source code: keep them out of public repositories and issues. The `.gitignore` excludes `*.mcp-response.json`, `*.xre.json` and `graph/` by default.

To report a vulnerability, open a private security advisory on the GitHub repository instead of a public issue.
