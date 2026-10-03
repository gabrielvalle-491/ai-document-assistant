# AI Document Assistant

English: [README.md](README.md)

![CI](https://github.com/gabrielvalle-491/ai-document-assistant/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Subir documentos → hacer preguntas → obtener información.

Haga preguntas en lenguaje natural sobre archivos PDF, de texto o Markdown (políticas,
contratos, manuales, preguntas frecuentes) y obtenga una respuesta breve **con el documento y la página
exactos de los que proviene**. Funciona con Claude o Gemini, y también funciona sin conexión, sin ninguna clave de API.

## El problema de negocio

Los empleados y agentes de soporte pierden tiempo buscando en PDF extensos ("¿cuántos días de vacaciones
tengo?", "¿cuál es la política de reembolsos?", "¿qué crédito debemos si baja la disponibilidad?").
Los chatbots genéricos responden con seguridad, pero inventan información. El equipo necesita respuestas
basadas en *sus propios* documentos y fáciles de verificar.

## Cómo funciona

```
PDF / TXT / MD ─► extract text per page ─► rebuild sentences ─► chunks (with page numbers)
                                                                     │
 question ─► (optional) AI query expansion EN/ES ─► BM25 search ─────┤ top passages
                                                                     ▼
                       Claude / Gemini answer ONLY from those passages, citing [1], [2]
                       or, without an API key: extractive answer (exact sentences)
```

| Característica | Detalle |
|----------------|---------|
| **Respuestas fundamentadas** | El modelo solo ve los fragmentos recuperados y debe citarlos; si la respuesta no está allí, indica *"I couldn't find this in the uploaded documents."* |
| **Fuentes** | Cada respuesta indica documento + página + puntaje de relevancia, y es posible expandir cada fragmento |
| **Entre idiomas** | Pregunte en español sobre documentos en inglés (o viceversa): la IA amplía la consulta con palabras clave en EN/ES |
| **Modo sin conexión** | ¿No tiene clave? Respuestas extractivas construidas con las oraciones exactas de los documentos (cero alucinaciones) |
| **Fallas controladas** | Si el proveedor de IA no está disponible o se agotó la cuota, recurre a respuestas extractivas en lugar de fallar |
| **Sin infraestructura pesada** | Recuperación BM25 en Python puro: sin base de datos vectorial, sin GPU, funciona en cualquier computadora portátil |
| **Texto de PDF limpio** | Vuelve a unir las oraciones cortadas por los saltos de línea del PDF y mantiene los títulos separados |

## Inicio rápido

```bash
pip install -r requirements.txt
python -m docassist.generate_samples samples        # 3 demo company PDFs

# terminal
python -m docassist samples "How many vacation days do employees get?"

# web app (upload your own files)
streamlit run app.py
```

Proveedor de IA opcional (elija uno):

```bash
export ANTHROPIC_API_KEY=...    # Claude
export GEMINI_API_KEY=...       # Google Gemini (free tier)
```

## Sesión de ejemplo (salida real)

**Con Gemini**: pregunta en español, documentos en inglés:

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

**Sin conexión (sin clave de API):**

```
$ python -m docassist samples "Can I return custom printed products?" --no-llm

Custom-printed products cannot be returned. [1] Customers can return unused products within
30 days of delivery. [1]

  [1] product_faq.pdf, p. 1
  mode: extractive
```

**Información que no está en los documentos:**

```
$ python -m docassist samples "Who is the CEO?"

I couldn't find this in the uploaded documents.
```

## Estructura del proyecto

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

## Pruebas

```bash
pytest -q
```

## Notas

- Los documentos de demostración son ficticios (`generate_samples.py`).
- Los documentos se procesan localmente; cuando hay una clave configurada, solo los fragmentos más relevantes se envían al proveedor de IA.
- Desarrollado con Python y [Claude Code](https://claude.com/claude-code) como programador asistente de IA.

## Cómo se lo entregaría a un cliente

Si me contrata para esto, yo:

- **Solicitaría los archivos de entrada** en una sola carpeta compartida: PDF con texto, archivos `.txt` o `.md` (políticas, contratos, manuales, preguntas frecuentes). Los demás tipos de archivo se ignoran y los PDF escaneados requieren OCR previo, por lo que revisaría una muestra de sus archivos antes de comenzar.
- **Lo mantendría actualizado semanalmente**: basta con agregar a esa carpeta los documentos nuevos o reemplazados. El índice se reconstruye a partir de la carpeta en cada ejecución, así que no hay nada que reentrenar.
- **Haría que cada respuesta sea verificable**: cada una indica el documento, la página y el puntaje de relevancia de los que proviene.
- **Informaría con honestidad cuando algo no se encuentra**: si los documentos no contienen la respuesta, la herramienta responde *"I couldn't find this in the uploaded documents."* en lugar de adivinar.
- **Mostraría los errores con claridad**: el comando finaliza con código 1 y un mensaje cuando la carpeta no existe o no contiene documentos compatibles; si el proveedor de IA falla, muestra la respuesta extractiva con la nota "LLM unavailable" (la línea `mode:` indica cuál se utilizó).
- **Acordaría qué información sale de su equipo**: los documentos se procesan localmente, solo los fragmentos más relevantes se envían al proveedor de IA y `--no-llm` mantiene todo sin conexión.
- **Agregaría un paso que omita e informe los archivos ilegibles** antes de la entrega, ya que actualmente un PDF dañado detiene la ejecución.

## Autor

**Gabriel Valle** — Automatización de datos e IA (Excel, PDF, flujos de trabajo) · Villa Mercedes, Argentina · Remoto
