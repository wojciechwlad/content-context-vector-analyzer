# Content Context Vector Analyzer

## Opis projektu
Lokalna aplikacja Streamlit do analizy Content Context Vector (hierarchiczna struktura semantyczna treści HTML/Markdown) z wykorzystaniem embeddingów Ollama.

## Stack technologiczny
- **Python**: 3.11+
- **Frontend**: Streamlit
- **Embeddings**: Ollama `snowflake-arctic-embed2:latest`
- **LLM sugestie**: Ollama `gemma3:12b`
- **Wizualizacje**: Plotly
- **Parser HTML**: BeautifulSoup4
- **Parser MD**: markdown-it-py
- **Baza danych**: duckdb (duckdb.org)
  - https://duckdb.org/docs/stable/connect/overview
  - https://duckdb.org/docs/stable/guides/python/install
  - https://duckdb.org/docs/stable/guides/python/import_pandas
  - https://duckdb.org/docs/stable/guides/python/export_pandas
  - https://duckdb.org/docs/stable/guides/python/import_numpy
  - https://duckdb.org/docs/stable/guides/python/export_numpy
  - https://duckdb.org/docs/stable/core_extensions/vss

## Wymagane modele Ollama
```bash
ollama pull snowflake-arctic-embed2:latest
ollama pull gemma3:12b
```

## Uruchomienie
```bash
# Aktywuj venv
source venv/bin/activate

# Uruchom Streamlit
streamlit run app.py
```

## Struktura projektu
```
context-vector-embeddings/
├── app.py                      # Entry point Streamlit
├── requirements.txt
├── config/
│   ├── settings.py             # Progi, konfiguracja Ollama
│   └── checklist.py            # Definicje CV-001 do CV-036
├── core/
│   ├── parsers/                # Parsery HTML/Markdown
│   ├── embeddings/             # Klient Ollama
│   ├── analysis/               # Similarity, checklist evaluator
│   ├── suggestions/            # Sugestie LLM
│   └── storage/                # DuckDB vector store, cache
├── visualization/              # Plotly wizualizacje
└── docs/                       # Dokumentacja
```

## Konwencje kodu
- Type hints wszędzie
- Dataclasses dla modeli danych
- Docstrings w formacie Google
- Async gdzie możliwe (httpx)

## Progi Semantic Similarity
| Relacja | Target | Opis |
|---------|--------|------|
| Title ↔ Meta | 60-80% | Meta rozszerza Title |
| Title ↔ H1 | 80-90% | H1 potwierdza temat |
| H2 ↔ Title | 50-70% | H2 w kontekście |
| H3 ↔ Parent H2 | 60-80% | H3 jako sub-concept |

## Storage & Cache

### DuckDB Vector Store
- Przechowuje embeddingi w `vectors.duckdb`
- Historia analiz z timestampami
- Indeksy na content_hash dla szybkiego wyszukiwania

```python
from core.storage import DuckDBVectorStore

store = DuckDBVectorStore("vectors.duckdb")
store.store_batch(content_hash, embeddings, texts)
store.get_stats()  # {"embeddings_count": 42, ...}
store.clear_embeddings()  # Czyści wszystkie
```

### Cache Manager
- Plikowy cache z TTL (default: 24h)
- Automatyczne czyszczenie przy przekroczeniu limitu
- Obsługa batch operacji

```python
from core.storage import CacheManager

cache = CacheManager(ttl_hours=24, max_size_mb=100)
cache.get_stats()
cache.clear()  # Czyści wszystko
cache.clear(older_than_hours=48)  # Czyści starsze
```

## Debug Mode
- Włącz w sidebar: "Tryb Debug"
- Pokazuje: raw embeddings shape, similarity scores, topic drifts
- Loguje błędy do console

## Kluczowe komendy
```bash
# Sprawdź modele Ollama
ollama list

# Test embeddings
curl http://localhost:11434/api/embeddings -d '{"model": "nomic-embed-text", "prompt": "test"}'

# Uruchom testy
pytest tests/

# Wyczyść bazę wektorów
python -c "from core.storage import DuckDBVectorStore; DuckDBVectorStore().clear_embeddings()"
```
