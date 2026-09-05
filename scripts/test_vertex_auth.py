"""Quick Vertex AI auth + connectivity check.

Run: `uv run python scripts/test_vertex_auth.py`

This script:
1. Reads GCP_PROJECT_ID from .env
2. Verifies the service account JSON key is readable
3. Pings Vertex AI with one tiny embedding call
4. Reports success or a precise error

If anything fails, the error message tells you exactly which env var to fix.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env first so this works even if you haven't sourced it
from dotenv import load_dotenv

load_dotenv()

PROJECT = os.getenv("GCP_PROJECT_ID", "").strip()
REGION = os.getenv("GCP_REGION", "us-central1").strip()
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
EMBED_MODEL = os.getenv("VERTEX_EMBEDDING_MODEL", "text-embedding-005")

# Auto-discover a service account JSON in secrets/ if the env var is empty.
# This must happen BEFORE importing google.cloud.* — the SDK reads
# GOOGLE_APPLICATION_CREDENTIALS at import time.
if not KEY_PATH:
    secrets_dir = Path("secrets")
    if secrets_dir.exists():
        candidates = sorted(secrets_dir.glob("*.json"))
        if candidates:
            KEY_PATH = str(candidates[0].resolve())
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH


def _check(label: str, ok: bool, detail: str = "") -> bool:
    icon = "[OK]" if ok else "[FAIL]"
    print(f"{icon} {label}: {detail}")
    return ok


def main() -> int:
    print("=" * 60)
    print("FinRAG — Vertex AI auth check")
    print("=" * 60)

    all_ok = True

    # 1. Project ID
    if not PROJECT:
        all_ok &= _check("GCP_PROJECT_ID", False, "empty — set it in .env")
    else:
        all_ok &= _check("GCP_PROJECT_ID", True, PROJECT)

    # 2. Region
    all_ok &= _check("GCP_REGION", bool(REGION), REGION)

    # 3. Service account key (auto-discovery already done at module load)
    if not KEY_PATH:
        all_ok &= _check(
            "GOOGLE_APPLICATION_CREDENTIALS",
            False,
            "empty — set it to the absolute path of your service account JSON, or drop a *.json in secrets/",
        )
    else:
        p = Path(KEY_PATH)
        if not p.exists():
            all_ok &= _check("GOOGLE_APPLICATION_CREDENTIALS", False, f"file not found: {p}")
        else:
            size = p.stat().st_size
            all_ok &= _check("GOOGLE_APPLICATION_CREDENTIALS", True, f"{p} ({size} bytes)")

    if not all_ok:
        print()
        print("Fix the above in your .env file, then re-run.")
        print("Service account key goes at: F:/projects/FinRAG.../secrets/vertex-key.json")
        print("  (or any *.json in that directory — auto-discovery picks the first one)")
        return 1

    # 3b. Show which project the service account key was issued for, so a
    # mismatch with GCP_PROJECT_ID is obvious (the most common auth bug).
    try:
        import json as _json
        _key = _json.loads(Path(KEY_PATH).read_text())
        _key_project = _key.get("project_id", "?")
        if _key_project != PROJECT:
            print()
            print(f"[WARN] Service account key was issued for project '{_key_project}'")
            print(f"       but GCP_PROJECT_ID='{PROJECT}'.")
            print("       The Vertex AI call will hit the key's project, not the one in .env.")
            print("       Fix: set GCP_PROJECT_ID in .env to the same project as the key,")
            print("       or use a key that belongs to your target project.")
    except Exception:
        pass

    # 4. Try the actual Vertex call
    print()
    print("Pinging Vertex AI with one embedding call...")
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(project=PROJECT, location=REGION)
        model = TextEmbeddingModel.from_pretrained(EMBED_MODEL)
        result = model.get_embeddings(["hello world"])
        vec = result[0].values
        _check("Vertex AI embedding call", True, f"got vector of dim {len(vec)}")
    except Exception as e:
        print(f"[FAIL] Vertex AI call failed: {type(e).__name__}: {e}")
        print()
        print("Common fixes:")
        print("  1. Enable the Vertex AI API on your project:")
        print("     https://console.cloud.google.com/apis/library/aiplatform.googleapis.com")
        print("  2. Make sure the service account has 'Vertex AI User' role:")
        print("     https://console.cloud.google.com/iam-admin/iam")
        print("  3. Wait 1-2 minutes after enabling the API; propagation can lag.")
        print("  4. If the error mentions a 'consumer: projects/...' number,")
        print("     the key and GCP_PROJECT_ID belong to different projects.")
        return 2

    print()
    print("All checks passed. You're ready to set EMBEDDER_BACKEND=vertex and GENERATOR_BACKEND=vertex in .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
