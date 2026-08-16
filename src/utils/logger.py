"""Logger simple pour tracer les décisions des agents (journalisation)."""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("digital_twin_churn")
