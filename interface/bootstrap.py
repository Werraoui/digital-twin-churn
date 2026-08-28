"""Ensure project root is on sys.path when Streamlit runs from interface/."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Prefer local HF cache; avoid noisy hub probes in the Streamlit terminal.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

for noisy in (
    "httpx",
    "httpcore",
    "huggingface_hub",
    "huggingface_hub.utils",
    "sentence_transformers",
    "urllib3",
):
    logging.getLogger(noisy).setLevel(logging.ERROR)
