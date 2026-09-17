# Start VeriTrace on your laptop

Already set up the old version? Read `UPDATE-V2.md` first. For hosting, read `DEPLOY-VERCEL.md`.

## 1. Extract the ZIP

Right-click `VeriTrace.zip` → **Extract All**. Open the extracted `VeriTrace` folder. It must contain `run.py`, `start-windows.bat`, `backend`, `frontend` and `web`.

Do not copy your old project, virtual environment or `.env` over this folder.

## 2. Start without any API keys first

You need Python 3.11 or newer. Check in a terminal:

```powershell
py --version
```

If Python is missing, install it from [python.org](https://www.python.org/downloads/). Enable **Add Python to PATH** during installation.

Double-click **start-windows.bat**. Leave the terminal open. Open:

**http://127.0.0.1:8000**

Click any **Demo** card. Open **Spread tree**, click a node, switch to Network, and try the date slider. All three demos work without an internet connection or keys. They are fictional training cases.

Alternatively, open a terminal in the project folder and run:

```powershell
py -3 run.py
```

Linux/macOS:

```bash
python3 run.py
```

No `pip install` is needed. No SQL password is needed. Do not open `index.html` directly, run a second server on port 5500, or start your old FastAPI app.

## 3. Create your private settings file

Copy `.env.example` and rename the copy to **.env** in the same folder as `run.py`. In Windows Explorer, enable **View → Show → File name extensions** so you do not accidentally create `.env.txt`.

Or run in PowerShell from the project folder:

```powershell
Copy-Item .env.example .env
notepad .env
```

Leave all key values blank until you create your own keys. Never share those values.

## 4. Get a free Tavily key for real web search

1. Visit [Tavily](https://app.tavily.com/).
2. Sign up or sign in. Choose the free plan; do not add a payment card or enable pay-as-you-go.
3. Find **API Keys** in the dashboard and create/copy your key.
4. Paste it after `TAVILY_API_KEY=` in `.env`.

Tavily currently documents **1,000 free credits per month with no credit card required**. VeriTrace requests basic search, disables automatic parameter upgrades, and does not use Tavily Research or paid extraction. Provider quotas can change. See [official documentation](https://docs.tavily.com/) and [Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search).

With only this key, the app retrieves real source links and attempts article extraction. It conservatively leaves evidence as context without an AI classification key.

## 5. Get a free Groq key for evidence classification

1. Visit [Groq API Keys](https://console.groq.com/keys).
2. Sign in and click **Create API Key**.
3. Name it `VeriTrace`, copy the key and paste it after `GROQ_API_KEY=` in `.env`.
4. Stay on the free plan. Do not upgrade or enable paid billing.
5. Keep `GROQ_MODEL=llama-3.3-70b-versatile` unless Groq's dashboard says that model is unavailable to your account.

[Groq's official quickstart](https://console.groq.com/docs/quickstart) shows key creation and this model. [Free-plan rate limits](https://console.groq.com/docs/rate-limits) apply; there is no unlimited free API. If a model is retired or unavailable, choose an available text model in your Groq console and change only `GROQ_MODEL`.

Groq receives the claim and short windows of retrieved article text. It returns classifications and exact quotes; it is not used as a factual source.

Your settings now look like this, with your own private values:

```dotenv
TAVILY_API_KEY=your_tavily_key_here
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GOOGLE_FACTCHECK_API_KEY=
APP_ENV=development
PORT=8000
```

## 6. Restart and investigate

Press **Ctrl+C** in the server terminal. Start it again with `py -3 run.py`. Refresh the page.

Enter one specific factual statement. If you already have the original post/article and articles repeating it, open **Add source URLs you already have** and paste their public URLs, one per line. This gives the citation graph better starting material.

Try a factual claim you can independently verify. Avoid a huge paragraph containing many unrelated claims. For an article URL, the app uses the extracted headline as the claim; edit and resubmit as text if the headline is a question or does not state the claim accurately.

Open **Coverage & service notes** on the report to see what succeeded. The developer panel reports configuration; it does not pretend a key has been tested merely because it exists.

## 7. Optional professional fact-check database

You can leave `GOOGLE_FACTCHECK_API_KEY` blank permanently. VeriTrace still looks for ClaimReview data in pages it can read; the core graph and evidence features do not depend on Google.

If you want Google's database lookup, follow the [official Fact Check Tools setup](https://developers.google.com/fact-check/tools/api): create a Google Cloud project, enable **Fact Check Tools API**, create an API key under APIs & Services → Credentials, and restrict that key to Fact Check Tools API. Paste it in `.env` and restart. Keep this optional service disabled if your account requires paid billing or you cannot obtain no-cost quota; no billing upgrade is necessary for the rest of the project.

A candidate fact-check result is not automatically an exact match. The reviewed wording, publisher's rating and original link are shown for you to inspect.

## Troubleshooting

| What you see | What to do |
|---|---|
| Browser cannot connect | Keep the terminal open and use the printed localhost URL. |
| Port is busy | Close your old server; alternatively set `PORT=8001` in `.env`, restart and open `http://127.0.0.1:8001`. |
| API key not configured | Make sure the filename is `.env`, it is next to `run.py`, and restart the server. |
| API key rejected | Copy a fresh key from that provider's dashboard. Check that you did not paste a Groq key into Tavily's field. |
| Free quota/rate limit reached | Wait for the provider's limit to reset. Use a demo while waiting. No paid fallback is invoked. |
| Provider rejected request | Check the model name in Groq's dashboard and update `GROQ_MODEL`. |
| Search unavailable | Network or provider issue. Try supplied source URLs; demo mode still works. |
| Article text unavailable | The site may block extraction or require JavaScript. That source stays context-only. Try another accessible source. |
| Graph has few/no edges | The retrieved pages do not establish a citation chain. Add articles that actually link to one another; the app deliberately does not fabricate branches. |
| Unable to verify | Read the explanation: it identifies conflicting evidence, an API problem, unreadable text or inconclusive material. |
| Old results look different from current services | History reopens the saved snapshot; submit a new investigation for current evidence. |
| History cannot be saved | Move the extracted folder to a writable location, such as Documents. Export the current report as JSON before closing. |

`data/veritrace.db` is created automatically and contains your history. Keep that file if you move the project. Back it up with the server stopped. The original ZIP contains no personal history or API credentials.
