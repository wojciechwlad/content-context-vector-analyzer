# Content Context Vector Analyzer

Analizator semantycznej struktury treści dla SEO. Wykorzystuje embeddingi (Ollama) do oceny spójności tematycznej strony.

**Przeczytaj artykuł:** [Content Context Vector Checklist](https://rozenberger.com/posts/p/content-context-vector-checklist/)

## Czym jest Content Context Vector?

Content Context Vector to metryka semantyczna, która analizuje czy wszystkie elementy strony (Title, H1, H2, H3, meta description) są ze sobą powiązane tematycznie. W przeciwieństwie do tradycyjnej analizy keyword-based, CCV używa embeddingów do mierzenia rzeczywistej bliskości semantycznej.

## Funkcje

- **Analiza semantyczna** - wykorzystuje embeddingi do porównywania elementów strony
- **Wykrywanie topic drift** - identyfikuje nagłówki odbiegające od głównego tematu
- **Checklista SEO** - 16 punktów kontrolnych z priorytetami (Critical/High/Medium)
- **Sugestie LLM** - automatyczne propozycje poprawek generowane przez AI
- **Wizualizacje**:
  - Scatter plot 2D/3D (UMAP) - rozmieszczenie elementów w przestrzeni semantycznej
  - Heatmapa similarity - macierz podobieństwa między elementami
  - Drzewo hierarchii - struktura nagłówków z oznaczeniem spójności

## Wymagania

- Python 3.10+
- Ollama - lokalne modele AI

### Modele Ollama

```bash
# Embeddingi (wymagany)
ollama pull snowflake-arctic-embed2

# LLM do sugestii (opcjonalny)
ollama pull gemma3:12b
```

## Instalacja

```bash
# Klonuj repozytorium
git clone https://github.com/romek-rozen/content-context-vector-analyzer.git
cd content-context-vector-analyzer

# Utwórz wirtualne środowisko
python -m venv venv
source venv/bin/activate  # Linux/macOS
# lub: venv\Scripts\activate  # Windows

# Zainstaluj zależności
pip install -r requirements.txt
```

## Uruchomienie

```bash
# Upewnij się, że Ollama działa
ollama serve

# Uruchom aplikację
streamlit run app.py
```

Aplikacja będzie dostępna pod adresem: http://localhost:8501

## Użycie

1. **Wklej HTML** - skopiuj kod źródłowy strony do pola tekstowego
2. **Analizuj** - kliknij przycisk "Analizuj"
3. **Przejrzyj wyniki**:
   - Tab "Wyniki" - checklista z oceną elementów
   - Tab "Wizualizacje" - scatter plot, heatmapa, drzewo hierarchii
4. **Wygeneruj sugestie** - kliknij na problematyczny element, aby otrzymać propozycje poprawek od LLM

## Struktura checklisty

| Kod | Element | Priorytet |
|-----|---------|-----------|
| CV-001 | Title present | Critical |
| CV-002 | Title length (50-60 chars) | High |
| CV-003 | H1 present | Critical |
| CV-004 | Single H1 | High |
| CV-005 | Meta description present | High |
| CV-006 | Meta description length (150-160 chars) | Medium |
| CV-007 | H2 headers present | High |
| CV-008 | H2 count (3-8 optimal) | Medium |
| CV-009 | Title-H1 similarity (80-95%) | Critical |
| CV-010 | H1-Meta similarity (70-90%) | High |
| CV-011 | H2-Core alignment (>60%) | High |
| CV-012 | Topic drift detection | High |
| CV-013 | H3 under H2 structure | Medium |
| CV-014 | Heading word count (3-10 words) | Medium |
| CV-015 | Question headings (>30%) | Medium |
| CV-016 | Overall semantic coherence | Critical |

## Konfiguracja

### Modele

Domyślne modele można zmienić w sidebar aplikacji:
- **Embedding model**: `snowflake-arctic-embed2:latest`
- **LLM model**: `gemma3:12b`

### Własne prompty

Prompty dla sugestii LLM znajdują się w katalogu `/prompts`. Format nazwy: `CV-XXX-opis.txt`.

Dostępne zmienne w promptach:
- `{title}`, `{h1}`, `{meta}` - elementy strony
- `{current_value}`, `{target}` - aktualna i docelowa wartość
- `{h2_list}`, `{h3_list}` - listy nagłówków
- `{similarity}` - wynik podobieństwa
- `{problem}`, `{element_type}` - opis problemu

## Struktura projektu

```
content-context-vector-analyzer/
├── app.py                      # Główna aplikacja Streamlit
├── config/
│   └── settings.py             # Konfiguracja
├── core/
│   ├── models.py               # Modele danych
│   ├── parsers/
│   │   ├── html_parser.py      # Parser HTML
│   │   └── markdown_parser.py  # Parser Markdown
│   ├── embeddings/
│   │   └── ollama_client.py    # Klient Ollama API
│   ├── analysis/
│   │   ├── similarity.py       # Analiza podobieństwa
│   │   └── checklist_evaluator.py
│   └── suggestions/
│       └── llm_suggester.py    # Generator sugestii LLM
├── visualization/
│   ├── scatter_plot.py         # Scatter 2D
│   ├── scatter_3d.py           # Scatter 3D
│   ├── heatmap.py              # Heatmapa
│   └── hierarchy_tree.py       # Drzewo hierarchii
├── prompts/                    # Szablony promptów LLM
└── tests/                      # Testy
```

## Licencja

MIT License - zobacz [LICENSE](LICENSE)

## Autor

Roman Rozenberger

## Wsparcie

Jeśli projekt jest dla Ciebie przydatny, możesz wesprzeć jego rozwój:

- [GitHub Sponsors](https://github.com/sponsors/romek-rozen)
- [Patreon](https://patreon.com/RomanRozenberger)
- [Patronite](https://patronite.pl/romanrozenberger)
