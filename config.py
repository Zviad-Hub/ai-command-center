
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "AI Command Center"
APP_VERSION = "0.1.0"

# AI provider configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Organization
DEPARTMENTS = [
    "media",
    "tenders",
    "finance",
    "business",
    "pentester",
    "technical",
    "audit"
]

# Safety settings
PENTEST_REQUIRE_DOCUMENT = True
PENTEST_REQUIRE_CEO_APPROVAL = True
PENTEST_ALLOW_UNAUTHORIZED_TARGETS = False

# Execution settings
MAX_AGENT_RETRIES = 2
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
