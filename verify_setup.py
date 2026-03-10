import os
from dotenv import load_dotenv

load_dotenv()

print("Checking environment...\n")

checks = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
    "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"),
}

all_good = True
for key, value in checks.items():
    if value and not value.endswith("your-key-here"):
        print(f"✅ {key} is set")
    else:
        print(f"❌ {key} is MISSING or not filled in")
        all_good = False

print()

# Check imports
try:
    import langgraph
    import langchain
    import tavily
    import yfinance
    import fastapi
    import reportlab
    print("✅ All packages imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    all_good = False

print()
if all_good:
    print("🟢 Phase 0 complete. You're ready for Phase 1.")
else:
    print("🔴 Fix the issues above before moving on.")