"""Pre-download ML models at build time so runtime cold-boots entirely from local disk."""

import logging
import os
import shutil
import sys
from pathlib import Path

# Configure paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CACHE_DIR = PROJECT_ROOT / ".cache"
HF_CACHE_DIR = CACHE_DIR / "huggingface"
CHROMA_CACHE_DIR = CACHE_DIR / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"

os.environ["HF_HOME"] = str(HF_CACHE_DIR)
os.environ["ANONYMIZED_TELEMETRY"] = "False"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_models")


def download_chroma_onnx() -> None:
    """Pre-download and warm-up Chroma's ONNXMiniLM_L6_V2 model."""
    logger.info("Setting up ChromaDB ONNXMiniLM_L6_V2 embedding model in %s...", CHROMA_CACHE_DIR)
    CHROMA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_home_onnx = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx"
    target_onnx = CHROMA_CACHE_DIR / "onnx"

    if local_home_onnx.exists() and not target_onnx.exists():
        logger.info("Found existing local model at %s, copying to %s...", local_home_onnx, target_onnx)
        shutil.copytree(local_home_onnx, target_onnx)

    try:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = str(CHROMA_CACHE_DIR)
        ef = ONNXMiniLM_L6_V2()
        ef._download_model_if_not_exists()
        sample_embed = ef(["warmup query for GTM Copilot RAG"])
        logger.info(
            "ChromaDB ONNX model verified and loaded into cache (embedding dim=%d).",
            len(sample_embed[0]) if sample_embed else 0,
        )
    except Exception as e:
        logger.warning("Could not pre-download Chroma ONNX model: %s", e)


def download_cross_encoder() -> None:
    """Pre-download the sentence-transformers CrossEncoder model if available."""
    logger.info("Setting up CrossEncoder reranker model in %s...", HF_CACHE_DIR)
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_home_hf = Path.home() / ".cache" / "huggingface" / "hub"
    target_hf_hub = HF_CACHE_DIR / "hub"

    if local_home_hf.exists() and not target_hf_hub.exists():
        for item in local_home_hf.glob("models--cross-encoder--ms-marco*"):
            dest = target_hf_hub / item.name
            if not dest.exists():
                logger.info("Found local CrossEncoder at %s, copying to %s...", item, dest)
                target_hf_hub.mkdir(parents=True, exist_ok=True)
                shutil.copytree(item, dest)

    try:
        from sentence_transformers import CrossEncoder

        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ce = CrossEncoder(model_name)
        ce.predict([["sales inquiry", "gtm playbook"]])
        logger.info("CrossEncoder model '%s' verified and loaded into cache.", model_name)
    except Exception as e:
        logger.warning("CrossEncoder pre-download skipped or failed: %s (non-fatal)", e)


if __name__ == "__main__":
    logger.info("=== Starting build-time model download ===")
    download_chroma_onnx()
    download_cross_encoder()
    logger.info("=== Build-time model download complete ===")
