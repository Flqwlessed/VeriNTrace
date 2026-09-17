import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / '.env').read_text().splitlines() if (ROOT / '.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('\"\''))
TAVILY_KEY = os.getenv('TAVILY_API_KEY', '')
GROQ_KEY = os.getenv('GROQ_API_KEY', '')
GOOGLE_KEY = os.getenv('GOOGLE_FACTCHECK_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
DEVELOPMENT = os.getenv('APP_ENV', 'development') == 'development'
DB_PATH = Path(os.getenv('VERITRACE_DB', str(ROOT / 'data' / 'veritrace.db')))

HOSTED = os.getenv('VERCEL') == '1'
