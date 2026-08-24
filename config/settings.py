"""Configuration centrale du projet, chargée depuis les variables d'environnement."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_data_dir() -> Path:
    raw = os.getenv("DATA_DIR")
    if not raw:
        return PROJECT_ROOT / "data"
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


DATA_DIR = _resolve_data_dir()
RAW_DATA_DIR = DATA_DIR / "raw"

TELCO_RAW_PATH = RAW_DATA_DIR / "telco_churn.csv"
RETAIL_RAW_CSV_PATH = RAW_DATA_DIR / "online_retail_ii.csv"
RETAIL_RAW_XLSX_PATH = RAW_DATA_DIR / "online_retail_II.xlsx"
TICKETS_RAW_PATH = RAW_DATA_DIR / "customer_support_tickets_200k.csv"
TELCO_ML_PATH = DATA_DIR / "processed" / "telco_clean.csv"
TELCO_ML_TRAINING_PATH = DATA_DIR / "ml_data" / "processed" / "telco_clean.csv"
TELCO_ML_READY_PATH = DATA_DIR / "ml_data" / "processed" / "telco_train_ready.csv"
MODELS_DIR = PROJECT_ROOT / "src" / "models"
SELECTED_CHURN_MODEL = "logreg"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
# Free-first: groq | gemini | anthropic | template (empty = auto-detect)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
_DEFAULT_DB = DATA_DIR / "processed" / "warehouse.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB.as_posix()}")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "vectorstore"))

CHURN_RISK_THRESHOLD = 0.5  # seuil au-delà duquel l'orchestrateur déclenche la simulation
CALL_RISK_THRESHOLD = 0.7  # au-delà : canal "call", sinon "email"
