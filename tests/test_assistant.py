import pytest

from docassist import answer as answer_mod
from docassist.answer import NOT_FOUND, ask, build_prompt, extractive_answer
from docassist.documents import Chunk, load_documents, load_folder, split_text, text_units
from docassist.generate_samples import generate
from docassist.retrieval import BM25Index, tokenize


@pytest.fixture(autouse=True)
def no_api_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    folder = tmp_path_factory.mktemp("docs")
    generate(folder)
    return BM25Index(load_folder(folder))


def test_tokenize_normalizes_accents_stopwords_and_plurals():
    assert tokenize("¿Cuáles son las políticas de reembolsos?") == ["politica", "reembolso"]
    assert tokenize("refund policies") == tokenize("Refund policy")


def test_split_text_respects_max_size_and_overlaps():
    text = " ".join(f"Sentence number {i} talks about topic {i}." for i in range(60))
    chunks = split_text(text, max_chars=200)
    assert len(chunks) > 5
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[1].split("\n")[0] == chunks[0].split("\n")[-1]  # last sentence repeated as overlap


def test_pdf_line_wraps_are_rejoined_and_headings_kept_apart():
    raw = "Returns and refunds\nCustomers can return products within 30\ndays of delivery. Refunds take 7 days.\n"
    assert text_units(raw) == ["Returns and refunds", "Customers can return products within 30 days of delivery.",
                               "Refunds take 7 days."]


def test_pdf_pages_are_tracked(index):
    pages = {(c.source, c.page) for c in index.chunks}
    assert ("employee_handbook.pdf", 2) in pages


@pytest.mark.parametrize("question, source, fact", [
    ("How many vacation days do employees get?", "employee_handbook.pdf", "15 business days"),
    ("What is the refund policy for returns?", "product_faq.pdf", "30 days"),
    ("What service credit applies if uptime is below target?", "service_agreement.pdf", "10%"),
    ("How long is the probation period?", "employee_handbook.pdf", "90 days"),
])
def test_retrieval_and_extractive_answer(index, question, source, fact):
    result = ask(index, question, use_llm=False)
    assert result.sources[0][1].source == source
    assert fact in result.text
    assert "[1]" in result.text or "[2]" in result.text


def test_unknown_question(index):
    assert ask(index, "zebra quantum spaceship", use_llm=False).text == NOT_FOUND


def test_prompt_numbers_passages_with_citations():
    hits = [(Chunk("Refunds take 7 days.", "faq.pdf", 1, 0), 1.0)]
    prompt = build_prompt("refund?", hits)
    assert "[1] (faq.pdf, p. 1)" in prompt and "Question: refund?" in prompt


def test_llm_failure_falls_back_to_extractive(index, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    def boom(*_args, **_kwargs):
        raise ConnectionError("offline")

    monkeypatch.setattr(answer_mod, "call_llm", boom)
    result = ask(index, "How many vacation days do employees get?")
    assert result.mode == "extractive" and "15 business days" in result.text


def test_txt_files_supported():
    chunks = load_documents([("notes.txt", b"The office wifi password policy changes every 90 days.")])
    assert extractive_answer("wifi password", [(chunks[0], 1.0)]).endswith("[1]")
