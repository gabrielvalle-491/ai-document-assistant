"""Edge cases for the CLI and the offline (extractive) path. No network or API keys needed."""

import subprocess
import sys

import pytest

from docassist.answer import NOT_FOUND, ask
from docassist.cli import main
from docassist.documents import load_documents, load_folder
from docassist.retrieval import BM25Index


@pytest.fixture(autouse=True)
def no_api_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_help_exits_zero_and_shows_module_name():
    result = subprocess.run([sys.executable, "-m", "docassist", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.startswith("usage: python -m docassist")


def test_folder_without_supported_files_returns_exit_code_1(tmp_path, capsys):
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    assert load_folder(tmp_path) == []
    assert main([str(tmp_path), "anything?", "--no-llm"]) == 1
    assert "No PDF/TXT/MD documents found" in capsys.readouterr().err


def test_missing_folder_returns_exit_code_1_without_traceback(tmp_path, capsys):
    assert main([str(tmp_path / "does_not_exist"), "anything?", "--no-llm"]) == 1
    assert "Folder not found" in capsys.readouterr().err


def test_unsupported_files_are_ignored_next_to_supported_ones(tmp_path):
    (tmp_path / "policy.md").write_text("Remote work is allowed two days per week.")
    (tmp_path / "budget.xlsx").write_bytes(b"not a real spreadsheet")
    assert {c.source for c in load_folder(tmp_path)} == {"policy.md"}


@pytest.mark.parametrize("question", ["", "   ", "the and of?"])
def test_blank_or_stopword_only_question_is_not_found(question, tmp_path, capsys):
    index = BM25Index(load_documents([("notes.txt", b"The office closes at 18:00 on Fridays.")]))
    result = ask(index, question, use_llm=False)
    assert result.text == NOT_FOUND and result.sources == []

    (tmp_path / "notes.txt").write_text("The office closes at 18:00 on Fridays.")
    assert main([str(tmp_path), question, "--no-llm"]) == 0  # answers once, no interactive prompt
    assert NOT_FOUND in capsys.readouterr().out
