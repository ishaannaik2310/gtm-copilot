"""Unit tests for document ingestion loader."""

from pathlib import Path
import pytest
from gtm_copilot.ingestion.loader import (
    clean_text,
    load_directory,
    load_documents,
    load_file,
)
from gtm_copilot.models import Document


def test_clean_text():
    raw = "\r\n\n  Line 1   \r\nLine 2\t\n\n\n"
    cleaned = clean_text(raw)
    assert cleaned == "  Line 1\nLine 2"


def test_load_file_markdown(tmp_path: Path):
    md_file = tmp_path / "playbook.md"
    md_file.write_text("# Sales Playbook\n\nICP criteria and messaging.", encoding="utf-8")

    doc = load_file(file_path=md_file, source_type="playbook")

    assert isinstance(doc, Document)
    assert doc.source_type == "playbook"
    assert "# Sales Playbook" in doc.content
    assert doc.metadata["file_name"] == "playbook.md"
    assert doc.metadata["file_type"] == ".md"
    assert doc.metadata["char_count"] > 0
    assert doc.id is not None
    assert doc.created_at is not None


def test_load_file_text(tmp_path: Path):
    txt_file = tmp_path / "account.txt"
    txt_file.write_text("Account: Acme Corp\nARR: $10M", encoding="utf-8")

    doc = load_file(file_path=txt_file, source_type="account_data", metadata={"custom_tag": "vip"})

    assert doc.source_type == "account_data"
    assert "Acme Corp" in doc.content
    assert doc.metadata["custom_tag"] == "vip"
    assert doc.metadata["file_type"] == ".txt"


def test_load_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_file("non_existent_file.md", source_type="playbook")


def test_load_file_unsupported_extension(tmp_path: Path):
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_text("dummy", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        load_file(pdf_file, source_type="playbook")


def test_load_directory(tmp_path: Path):
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()

    (playbooks_dir / "pb1.md").write_text("# Playbook 1", encoding="utf-8")
    (playbooks_dir / "pb2.txt").write_text("Playbook 2 text", encoding="utf-8")
    (playbooks_dir / "ignored.json").write_text("{}", encoding="utf-8")

    docs = load_directory(playbooks_dir, source_type="playbook")
    assert len(docs) == 2
    assert all(d.source_type == "playbook" for d in docs)
    file_names = {d.metadata["file_name"] for d in docs}
    assert file_names == {"pb1.md", "pb2.txt"}


def test_load_directory_non_existent(tmp_path: Path):
    non_existent = tmp_path / "missing_dir"
    docs = load_directory(non_existent, source_type="playbook")
    assert docs == []


def test_load_all_documents_with_sample_data(tmp_path: Path):
    # Test loading structured directory
    data_dir = tmp_path / "data"
    pb_dir = data_dir / "playbooks"
    acc_dir = data_dir / "sample_accounts"
    pb_dir.mkdir(parents=True)
    acc_dir.mkdir(parents=True)

    (pb_dir / "sales_strategy.md").write_text("# Strategy Guide", encoding="utf-8")
    (acc_dir / "acme.md").write_text("# Acme Profile", encoding="utf-8")

    docs = load_documents(data_dir=data_dir)
    assert len(docs) == 2

    source_types = {d.source_type for d in docs}
    assert "playbook" in source_types
    assert "account_data" in source_types
