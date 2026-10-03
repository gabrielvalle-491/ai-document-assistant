"""Ask questions from the terminal.

    python -m docassist samples "How many vacation days do employees get?"
    python -m docassist samples            # interactive mode
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docassist.answer import ask
from docassist.documents import load_folder
from docassist.retrieval import BM25Index


def print_answer(index: BM25Index, question: str, use_llm: bool) -> None:
    """Answer one question and print the answer, its sources and the mode used."""
    result = ask(index, question, use_llm=use_llm)
    print(f"\n{result.text}\n")
    for number, chunk, score in result.sources:
        print(f"  [{number}] {chunk.citation}  (relevance {score:.2f})")
    print(f"  mode: {result.mode}\n")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(prog="python -m docassist", description="Ask questions about a folder of documents")
    parser.add_argument("folder", type=Path, help="Folder with PDF, TXT or Markdown files")
    parser.add_argument("question", nargs="?", help="Question to ask (omit for interactive mode)")
    parser.add_argument("--no-llm", action="store_true", help="Extractive answers only (no API calls)")
    args = parser.parse_args(argv)

    chunks = load_folder(args.folder)
    if not chunks:
        print(f"No PDF/TXT/MD documents found in {args.folder}", file=sys.stderr)
        return 1
    index = BM25Index(chunks)
    print(f"Indexed {len(chunks)} passages from {len({c.source for c in chunks})} documents.")

    if args.question:
        print_answer(index, args.question, not args.no_llm)
        return 0
    while True:
        try:
            question = input("Question (empty to quit): ").strip()
        except EOFError:
            break
        if not question:
            break
        print_answer(index, question, not args.no_llm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
