# AI Document Assistant

Español: [README.es.md](README.es.md)

![CI](https://github.com/gabrielvalle-491/ai-document-assistant/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Upload documents → ask questions → retrieve information.

Ask questions in plain language about PDFs, text or Markdown files (policies,
contracts, manuals, FAQs) and get a short answer **with the exact document and page
it came from**. Works with Claude or Gemini, and still works offline without any API key.

## The business problem

Employees and support agents waste time searching long PDFs ("how many vacation days
do I have?", "what is the refund policy?", "what credit do we owe if uptime drops?").
Generic chatbots answer confidently but make things up. The team needs answers that are
grounded in *their* documents and easy to verify.

## How it works

```
PDF / TXT / MD ─► extract text per page ─► rebuild sentences ─► chunks (with page numbers)
                                                                     │
 question ─► (optional) AI query expansion EN/ES ─► BM25 search ─────┤ top passages
                                                                     ▼
                       Claude / Gemini answer ONLY from those passages, citing [1], [2]
                       or, without an API key: extractive answer (exact sentences)
```

| Feature | Detail |
|---------|--------|
| **Grounded answers** | The model only sees the retrieved passages and must cite them; if the answer isn't there it says *"I couldn't find this in the uploaded documents."* |
| **Sources** | Every answer lists document + page + relevance score, and you can expand each passage |
| **Cross-language** | Ask in Spanish about English documents (or vice versa) — the AI expands the query into EN/ES keywords |
| **Offline mode** | No key? Extractive answers built from the exact sentences in the documents (zero hallucination) |
| **Graceful failure** | If the AI provider is down or out of quota, it falls back to extractive answers instead of crashing |
| **No heavy infrastructure** | BM25 retrieval in pure Python — no vector DB, no GPU, runs on any laptop |
| **Clean PDF text** | Re-joins sentences broken by PDF line wraps and keeps headings apart |

## Quick start

```bash
pip install -r requirements.txt
python -m docassist.generate_samples samples        # 3 demo company PDFs

# terminal
python -m docassist samples "How many vacation days do employees get?"

# web app (upload your own files)
streamlit run app.py
```

Optional AI provider (pick one):

```bash
export ANTHROPIC_API_KEY=...    # Claude
export GEMINI_API_KEY=...       # Google Gemini (free tier)
```

## Example session (real output)

**With Gemini** — question in Spanish, documents in English:

```
$ python -m docassist samples "¿Cuántos días de vacaciones tienen los empleados y con cuánta anticipación se piden?"

Los empleados a tiempo completo reciben 15 días hábiles de vacaciones pagadas al año, y las
solicitudes deben enviarse en el portal de recursos humanos con al menos 10 días hábiles de
anticipación [1].

  [1] employee_handbook.pdf, p. 2  (relevance 8.60)
  [2] employee_handbook.pdf, p. 1  (relevance 3.56)
  mode: gemini
```

```
$ python -m docassist samples "What happens if uptime is below the target?"

If uptime falls below the target, the client receives a service credit of 10% of the monthly
fee for each 0.5% below the target, up to a maximum of 50% [1].

  [1] service_agreement.pdf, p. 1  (relevance 11.65)
  mode: gemini
```

**Offline (no API key):**

```
$ python -m docassist samples "Can I return custom printed products?" --no-llm

Custom-printed products cannot be returned. [1] Customers can return unused products within
30 days of delivery. [1]

  [1] product_faq.pdf, p. 1
  mode: extractive
```

**Not in the documents:**

```
$ python -m docassist samples "Who is the CEO?"

I couldn't find this in the uploaded documents.
```

## Project structure

```
app.py                     # Streamlit web app (upload + ask + sources)
docassist/
├── documents.py           # PDF/TXT/MD loading, sentence rebuilding, chunking with page numbers
├── retrieval.py           # BM25 index (accent-insensitive, EN/ES stopwords, light stemming)
├── answer.py              # prompt with numbered passages, Claude/Gemini calls, extractive fallback
├── generate_samples.py    # demo PDFs: employee handbook, customer FAQ, SLA
└── cli.py                 # terminal interface
tests/                     # 19 pytest tests (retrieval accuracy, citations, fallbacks)
```

## Tests

```bash
pytest -q
```

## Notes

- Demo documents are fictional (`generate_samples.py`).
- Documents are processed locally; only the top passages are sent to the AI provider when a key is configured.
- Built with Python and [Claude Code](https://claude.com/claude-code) as an AI pair programmer.

## How I would deliver this to a client

If you hire me for this, I would:

- **Ask for the input files** in one shared folder: text-based PDFs, `.txt` or `.md` files (policies, contracts, manuals, FAQs). Other file types are ignored, and scanned PDFs would need OCR first, so I would check a sample of your files before starting.
- **Keep it up to date weekly** by having you drop new or replaced documents into that folder. The index is rebuilt from the folder on every run, so there is nothing to retrain.
- **Make every answer verifiable**: each one lists the document, page and relevance score it came from.
- **Report "not found" honestly**: when the documents don't contain the answer, the tool replies *"I couldn't find this in the uploaded documents."* instead of guessing.
- **Surface errors clearly**: the command exits with code 1 and a message when the folder is missing or contains no supported documents, and if the AI provider fails it shows the extractive answer with an "LLM unavailable" note (the `mode:` line tells you which was used).
- **Agree on what leaves your machine**: documents are processed locally, only the top passages go to the AI provider, and `--no-llm` keeps everything offline.
- **Add a skip-and-report step for unreadable files** before handing it over, since today a corrupted PDF stops the run.

## Author

**Gabriel Valle** — Data & AI automation (Excel, PDF, workflows) · Villa Mercedes, Argentina · Remote
