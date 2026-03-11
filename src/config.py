import os
from dotenv import load_dotenv

load_dotenv()

# ── Models ──────────────────────────────────────────
LLM_PRO   = "gemini-2.0-pro"    # used for reasoning-heavy agents
LLM_FLASH = "gemini-2.0-flash"  # used for cheaper/faster tasks

# ── API Keys ─────────────────────────────────────────
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# ── Cache ─────────────────────────────────────────────
CACHE_DIR = ".cache"
CACHE_TTL_HOURS = 24  # how long cached results stay valid

# ── Agent settings ────────────────────────────────────
MAX_RETRIES = 2
MAX_NEWS_RESULTS = 5
SEC_BUSINESS_MAX_CHARS  = 1500
SEC_RISK_MAX_CHARS      = 2500
SEC_MDA_MAX_CHARS       = 2500