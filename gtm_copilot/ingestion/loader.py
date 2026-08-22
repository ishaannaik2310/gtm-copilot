"""Document loader for ingestion of local playbooks and sample account files."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Union

from gtm_copilot.config import DATA_DIR, PLAYBOOKS_DIR, SAMPLE_ACCOUNTS_DIR
from gtm_copilot.models import Document

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: Set[str] = {".md", ".txt"}


def clean_text(text: str) -> str:
    """Normalize text by normalizing line endings and trimming excess whitespace."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    # Strip leading and trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def load_file(
    file_path: Union[str, Path],
    source_type: Literal["playbook", "account_data", "web"],
    metadata: Optional[Dict[str, Any]] = None,
) -> Document:
    """Load and clean a single markdown or text file into a Document object.

    Args:
        file_path: Path to the target file.
        source_type: Tag identifying document category ('playbook', 'account_data', 'web').
        metadata: Optional dictionary of additional metadata attributes.

    Returns:
        Document instance populated with cleaned content and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is unsupported.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{path.suffix}'. "
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        raw_content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback to utf-8-sig or latin-1 if strict utf-8 fails
        raw_content = path.read_text(encoding="utf-8-sig", errors="replace")

    cleaned_content = clean_text(raw_content)

    doc_metadata: Dict[str, Any] = {
        "file_name": path.name,
        "file_stem": path.stem,
        "file_path": str(path),
        "file_type": path.suffix.lower(),
        "char_count": len(cleaned_content),
    }

    if metadata:
        doc_metadata.update(metadata)

    return Document(
        source_type=source_type,
        content=cleaned_content,
        metadata=doc_metadata,
    )


def load_directory(
    dir_path: Union[str, Path],
    source_type: Literal["playbook", "account_data", "web"],
    recursive: bool = True,
) -> List[Document]:
    """Load all supported documents (.md, .txt) from a directory.

    Args:
        dir_path: Path to the directory.
        source_type: Source category tag.
        recursive: Whether to search subdirectories recursively.

    Returns:
        List of Document objects. Returns an empty list if directory is empty or does not exist.
    """
    path = Path(dir_path).resolve()
    if not path.exists() or not path.is_dir():
        logger.warning("Directory does not exist or is not a directory: %s", path)
        return []

    documents: List[Document] = []
    pattern = "**/*" if recursive else "*"

    for file_path in sorted(path.glob(pattern)):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                doc = load_file(file_path=file_path, source_type=source_type)
                documents.append(doc)
            except Exception as e:
                logger.error("Failed to load file %s: %s", file_path, e)

    return documents


def load_documents(
    data_dir: Optional[Union[str, Path]] = None,
    playbooks_dir: Optional[Union[str, Path]] = None,
    sample_accounts_dir: Optional[Union[str, Path]] = None,
) -> List[Document]:
    """Load all documents across playbooks and sample accounts directories.

    Args:
        data_dir: Base data directory (defaults to config.DATA_DIR).
        playbooks_dir: Playbooks directory (defaults to config.PLAYBOOKS_DIR).
        sample_accounts_dir: Accounts directory (defaults to config.SAMPLE_ACCOUNTS_DIR).

    Returns:
        Consolidated list of Document objects from all source directories.
    """
    target_playbooks_dir = (
        Path(playbooks_dir)
        if playbooks_dir
        else (Path(data_dir) / "playbooks" if data_dir else PLAYBOOKS_DIR)
    )
    target_accounts_dir = (
        Path(sample_accounts_dir)
        if sample_accounts_dir
        else (Path(data_dir) / "sample_accounts" if data_dir else SAMPLE_ACCOUNTS_DIR)
    )

    documents: List[Document] = []

    # Ingest playbooks
    playbook_docs = load_directory(target_playbooks_dir, source_type="playbook")
    documents.extend(playbook_docs)

    # Ingest sample account profiles
    account_docs = load_directory(target_accounts_dir, source_type="account_data")
    documents.extend(account_docs)

    return documents
