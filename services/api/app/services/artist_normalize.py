from __future__ import annotations

import re
import unicodedata


def normalize(name: str) -> str:
    """lower → NFKD → strip diacritics → collapse whitespace → strip."""
    lowered = name.lower()
    nfkd = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    return collapsed
