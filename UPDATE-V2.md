# Update from your previous VeriTrace ZIP

1. Stop the old server with Ctrl+C.
2. Extract this new ZIP into a **new folder**.
3. Copy your existing private `.env` into the new inner `VeriTrace` folder, next to `run.py`. No new keys are needed. Do not send the key values to anyone.
4. To keep local history, copy the old `data` folder while the old server is stopped.
5. Run the new `start-windows.bat` and hard-refresh the browser with **Ctrl+F5**.
6. Submit the claim as a **new investigation**. Existing history preserves old verdicts; it does not automatically rerun them.

For Vercel, read `DEPLOY-VERCEL.md` and use environment variables instead of uploading `.env`.

## What was fixed

- TRUE and FALSE labels for supported determinations.
- One strong, directly relevant source can settle a claim; a second source is not always required.
- Matching professional fact-check ratings can be used rather than merely displayed. Exact matches do not need Groq; paraphrase matching does. Changed numbers/dates block semantic matches. Ambiguous and partial ratings are not forced into binary labels.
- A citation alone no longer merges two sources into one evidence group. Near-duplicate text and common publisher identity still reduce double counting.
- Short explicit denials can be accepted. Quote validation normalizes whitespace and preserves text provenance.
- Analysis sees the article lead plus a relevant passage rather than one isolated window.
- Tavily-retrieved article text can be used when the website blocks direct extraction. Search snippets alone remain insufficient. This fallback cannot fabricate citation links.
- Groq requests have a longer timeout and clearer errors.
- Public-IP connections can try another checked address if the first address is unreachable, rather than failing immediately on an unusable IPv6/IPv4 route.
- Vercel streaming function, API routing and browser-local history are included.

The app still says **UNABLE TO VERIFY** when sources conflict, analysis is unavailable, or no readable relevant evidence exists. It explains which condition occurred. It never converts an API outage into TRUE or FALSE.
