# Deploy VeriTrace 2 on Vercel

This ZIP includes a Vercel Python function and the browser-ready frontend. It has been tested through local HTTP tests, but has not been deployed to your Vercel account from this chat.

## What changes when hosted

| Feature | Your laptop | Vercel |
|---|---|---|
| Website and graph | Included frontend | Same frontend |
| Investigation | Local background job and polling | Python function streams stage updates and result in one request |
| History | SQLite in `data/veritrace.db` | IndexedDB in each visitor's browser |
| API keys | Private `.env` beside `run.py` | Vercel environment variables |
| Extra database key | None | None |

Browser history stays on that browser/device and deployment origin. Clearing site data removes it. It does not synchronize across devices or become a shared public database. Export JSON for records you need to keep. The local SQLite schema and DBMS code remain included for your project demonstration.

## 1. Put the extracted project on GitHub

Create a repository and upload the **contents of the inner `VeriTrace` folder**. The repository root should contain `vercel.json`, `package.json`, `build.mjs`, `api/`, `backend/`, `frontend/`, and `web/`.

Never upload `.env`, your API keys, `data/`, or an old virtual environment. `.gitignore` and `.vercelignore` are provided. GitHub's web upload may not show hidden files by default; verify `vercel.json` is at the chosen root. Your private keys belong only in Vercel's environment settings.

## 2. Import on Vercel

1. Sign in to [Vercel](https://vercel.com/).
2. Select **Add New → Project** and import the GitHub repository.
3. Choose the free **Hobby** plan for your personal, non-commercial college project. Free quotas apply; do not upgrade to a paid plan for this setup.
4. Set **Root Directory** to the directory containing `vercel.json`. If you uploaded the outer folder, this is `VeriTrace`; if you uploaded its contents, leave it at the repository root.
5. Framework Preset: **Other**.
6. Build Command: **`node build.mjs`**.
7. Output Directory: **`web`**.
8. Node.js Version: **24.x**. Leave the install command at its default; there are no npm runtime dependencies.

The checked-in `vercel.json` supplies the build/output settings and API rewrites. Do not deploy only `web/`; the Python backend must be present.

## 3. Add environment variables

In the import screen, or Project → Settings → Environment Variables, add:

| Name | Value |
|---|---|
| `TAVILY_API_KEY` | Your existing Tavily key |
| `GROQ_API_KEY` | Your existing Groq key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `APP_ENV` | `production` |
| `GOOGLE_FACTCHECK_API_KEY` | Optional; omit if you don't have it |

Set them for Production and Preview if you want both deployments to work. Do not use `NEXT_PUBLIC_`, `VITE_` or other frontend-exposed prefixes. You do not need `PORT`, a PostgreSQL URL, or a new AI provider.

## 4. Deploy

Click **Deploy**. The project uses `api/dispatch.py` as a Python Vercel Function. `vercel.json` rewrites `/api/health`, `/api/demos` and `/api/investigate` to this function with an explicit route query parameter.

This build requires **Fluid compute** and configures a 180-second maximum function duration. Vercel's documented Hobby maximum with Fluid compute is 300 seconds. If your existing project uses legacy function limits, enable Fluid compute in its settings before deploying.

Open the deployment URL. Try a demo, then a live claim. Open `/api/health` on the deployment: you should see `"storage":"browser"`, `"transport":"stream"`, and `"version":"2.0"`.

After changing environment variables, redeploy for the changes to apply. A local `.env` change does not update Vercel.

## 5. Verify

- Demo: tree and network appear without API calls.
- Live request: stage updates arrive, followed by a report.
- TRUE/FALSE: open citations and check the actual basis for the label.
- History: refresh the same browser and reopen the saved report.
- Mobile: inspect graph controls and source cards on your phone.

## Troubleshooting

| Symptom | Check |
|---|---|
| Website loads, API returns 404 | Make sure `api/`, `backend/` and `vercel.json` are at the selected project root. |
| API says keys are missing | Add server environment variables, then redeploy. |
| Python import error | The whole `backend/` folder must be committed, not only `api/dispatch.py`. |
| Build fails on TypeScript stripping | Select Node.js 24.x. |
| Function duration rejected | Enable Fluid compute; this project asks for 180 seconds. |
| Stream ends without a report | Check Vercel function logs for a timeout; try fewer supplied source URLs. |
| History differs between devices | Hosted history is intentionally stored in each browser, not on Vercel's filesystem. |
| API quota runs out | Wait for the free quota reset and use demos. No paid fallback is configured. |

The included function limits concurrent work and throttles repeat requests within each warm instance. These limits are not a distributed abuse-control system. For a link you only want to demonstrate privately, use the deployment protection available to your account; public traffic can consume your provider quotas. A large public service needs stronger shared rate limits and authenticated cloud storage.

## Official references

- [Python functions in /api](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [Python runtime and filesystem behavior](https://vercel.com/docs/functions/runtimes/python)
- [Function duration limits](https://vercel.com/docs/functions/limitations)
- [Hobby plan](https://vercel.com/docs/plans/hobby)
