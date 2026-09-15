# Validation record

## Passed

- 11 Python standard-library unit and local HTTP integration tests.
- SQLite report save and exact graph replay, evidence counts and foreign-key consistency.
- Demo endpoint, recent history, saved report endpoint, and static asset HTTP responses.
- Missing/rejected provider responses produce structured partial results.
- Background investigation job finishes and saves even when all mocked providers are unavailable.
- Invalid model quotations are rejected; unrelated sources do not receive fabricated graph edges.
- Identical short article copies are grouped and cannot independently satisfy a two-source verdict threshold.
- Private/loopback URLs, private DNS results, credentials in URLs and nonstandard ports are refused.
- Cross-origin mutations are refused; secrets, source files and database files are not served as static assets.
- Priority-queue ordering, cyclic BFS traversal, nonexistent paths and cache eviction.
- HTML navigation/script filtering and invalid/future publication dates.
- TypeScript-to-JavaScript syntax stripping and syntax checks for all browser modules.

Command:

```bash
python -m unittest discover -s tests -v
```

## Not verified here

- Real Tavily, Groq or Google calls using account credentials. No private keys from the old archive were copied or used. Adapter request shapes and setup guidance were checked against official documentation.
- Visual browser rendering, mouse/touch interactions and mobile layout. Chromium was not installed in the execution environment and its download timed out. The implementation is included, but visual QA is not claimed.
- Full static TypeScript checking: the dependency-free build strips types; it does not type-check them.
- A representative factual-accuracy benchmark. This is a conservative research MVP, not a validated automated fact-check authority.

## Quick acceptance test on your laptop

1. Start the app and open all three demo cases.
2. In the first case, click Local blog (S1) and inspect its relationship to Community post (S0).
3. Open Trace a citation path and choose S3 → S0. The shortest observed chain is S3 → S1 → S0.
4. Switch to Network. Toggle Possible links and Claim connections.
5. Filter to Refutes. The correction/review sources should remain; reset to All.
6. Move the date slider. Later dated nodes should disappear. Return to All dates.
7. Zoom, pan, drag a node, Fit, and Reset. Click a node, then close its details with Escape.
8. Reopen the report from Recent investigations. Export its JSON.
9. Add your two free-tier keys, restart, and submit a real claim. Inspect service notes and open the source links.
10. Remove a key and restart. The app must show partial evidence or an explicit unavailable state, never substitute a fictional demo into the live report.
