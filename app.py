"""Content Context Vector Analyzer - Streamlit Application."""

import streamlit as st
import pandas as pd
from pathlib import Path

from config.settings import OLLAMA_CONFIG, STATUS_CONFIG, PRIORITY_CONFIG
from core.models import ExtractedContent, CheckStatus, AnalysisResult
from core.parsers.html_parser import HTMLParser
from core.embeddings.ollama_client import OllamaClient
from core.analysis.similarity import SimilarityAnalyzer
from core.analysis.checklist_evaluator import ChecklistEvaluator
from core.suggestions.llm_suggester import LLMSuggester
from visualization.scatter_plot import create_scatter_plot, create_scatter_with_similarity
from visualization.scatter_3d import create_3d_scatter, create_3d_scatter_with_similarity
from visualization.heatmap import create_heatmap, create_core_heatmap
from visualization.hierarchy_tree import create_hierarchy_tree, create_simple_hierarchy_view

# Page config
st.set_page_config(
    page_title="Content Context Vector Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False
if "embedding_model" not in st.session_state:
    st.session_state.embedding_model = "snowflake-arctic-embed2:latest"
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "gemma3:12b"


def parse_content(content: str) -> ExtractedContent:
    """Parsuje HTML content i zwraca ExtractedContent."""
    parser = HTMLParser()
    return parser.parse(content)


@st.cache_resource
def get_ollama_client() -> OllamaClient:
    """Zwraca singleton klienta Ollama."""
    client = OllamaClient()
    print(f"[DEBUG] OllamaClient created: base_url={client.base_url}, embedding_model={client.embedding_model}")
    return client


@st.cache_data(ttl=3600)
def generate_embeddings(texts: dict[str, str], model: str = "snowflake-arctic-embed2:latest") -> dict[str, list[float]]:
    """Generuje embeddingi z cache."""
    print(f"[DEBUG] generate_embeddings called with model={model}, texts={list(texts.keys())}")
    client = get_ollama_client()
    try:
        embeddings = client.get_batch_embeddings(texts, model=model)
        print(f"[DEBUG] Generated {len(embeddings)} embeddings successfully")
        # Konwertuj numpy arrays na listy dla serializacji cache
        return {k: v.tolist() for k, v in embeddings.items()}
    except Exception as e:
        print(f"[DEBUG ERROR] generate_embeddings failed: {e}")
        raise


def run_analysis(content: ExtractedContent, embedding_model: str = "snowflake-arctic-embed2:latest") -> AnalysisResult:
    """Wykonuje pełną analizę dokumentu."""
    import numpy as np

    # Generuj embeddingi
    texts = content.get_all_text_elements()
    embeddings_dict = generate_embeddings(texts, model=embedding_model)
    embeddings = {k: np.array(v) for k, v in embeddings_dict.items()}

    # Analiza similarity
    analyzer = SimilarityAnalyzer()
    similarity_scores = analyzer.analyze_core_alignment(embeddings)
    h2_scores = analyzer.analyze_h2_alignment(embeddings)
    all_scores = similarity_scores + h2_scores
    topic_drifts = analyzer.detect_topic_drift(embeddings)

    # Ewaluacja checklisty
    evaluator = ChecklistEvaluator()
    checklist_results = evaluator.evaluate_all(content, similarity_scores)
    overall_score = evaluator.calculate_overall_score(checklist_results)

    # Aktualizuj CV-012 jeśli wykryto topic drift
    if topic_drifts:
        for item in checklist_results:
            if item.code == "CV-012":
                item.status = CheckStatus.WARNING if len(topic_drifts) < 3 else CheckStatus.FAIL
                item.value = f"{len(topic_drifts)} drift(s)"
                break

    return AnalysisResult(
        content=content,
        embeddings=embeddings,
        similarity_scores=all_scores,
        checklist_results=checklist_results,
        topic_drifts=topic_drifts,
        overall_score=overall_score,
    )


def render_sidebar():
    """Renderuje sidebar z ustawieniami."""
    with st.sidebar:
        st.header("⚙️ Ustawienia")

        # Status Ollama
        client = get_ollama_client()
        ollama_ok = client.check_connection()

        if ollama_ok:
            st.success("✅ Ollama połączona")
            models = client.list_models()

            if models:
                st.divider()
                st.subheader("🤖 Modele")

                # Filtruj modele embedding (zazwyczaj mają "embed" w nazwie)
                embedding_models = [m for m in models if "embed" in m.lower() or "nomic" in m.lower() or "bge" in m.lower() or "e5" in m.lower()]
                # Jeśli nie ma dedykowanych, pokaż wszystkie
                if not embedding_models:
                    embedding_models = models

                # Model do embeddingów
                default_emb_idx = 0
                if st.session_state.embedding_model in embedding_models:
                    default_emb_idx = embedding_models.index(st.session_state.embedding_model)

                st.session_state.embedding_model = st.selectbox(
                    "📊 Model Embedding:",
                    embedding_models,
                    index=default_emb_idx,
                    help="Model do generowania wektorów semantycznych"
                )

                # Model LLM (wszystkie modele)
                llm_models = [m for m in models if "embed" not in m.lower()]
                if not llm_models:
                    llm_models = models

                default_llm_idx = 0
                if st.session_state.llm_model in llm_models:
                    default_llm_idx = llm_models.index(st.session_state.llm_model)
                elif any("llama" in m.lower() for m in llm_models):
                    default_llm_idx = next(i for i, m in enumerate(llm_models) if "llama" in m.lower())

                st.session_state.llm_model = st.selectbox(
                    "💬 Model LLM (sugestie):",
                    llm_models,
                    index=default_llm_idx,
                    help="Model do generowania sugestii naprawy"
                )

                st.caption(f"Dostępne: {len(models)} modeli")
        else:
            st.error("❌ Ollama niedostępna")
            st.caption("Uruchom: `ollama serve`")

        st.divider()

        # Debug mode
        st.session_state.debug_mode = st.checkbox(
            "🐛 Tryb Debug",
            value=st.session_state.debug_mode,
        )

        # Clear cache
        if st.button("🗑️ Wyczyść cache"):
            st.cache_data.clear()
            st.success("Cache wyczyszczony!")

        st.divider()

        # Info
        st.caption("**Progi Similarity:**")
        st.caption("- Title↔Meta: 60-80%")
        st.caption("- Title↔H1: 80-90%")
        st.caption("- H2↔Title: 50-70%")


def fetch_url_content(url: str) -> str | None:
    """Pobiera HTML z podanego URL."""
    import httpx
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ContentVectorAnalyzer/1.0)"
            }
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        st.error(f"❌ Błąd pobierania URL: {e}")
        return None


def render_input_section() -> str | None:
    """Renderuje sekcję input i zwraca content HTML."""
    st.header("📥 Input")

    tab_url, tab_upload = st.tabs(["🌐 URL strony", "📁 Upload HTML"])

    content = None

    with tab_url:
        url = st.text_input(
            "Podaj URL strony:",
            placeholder="https://example.com/strona",
            help="Wklej pełny URL strony do analizy"
        )

        if url:
            if st.button("📥 Pobierz stronę", key="fetch_url"):
                with st.spinner("Pobieram stronę..."):
                    fetched = fetch_url_content(url)
                    if fetched:
                        st.session_state.fetched_content = fetched
                        st.session_state.fetched_url = url
                        st.success(f"✅ Pobrano: {url}")

            # Użyj pobranej zawartości jeśli istnieje
            if hasattr(st.session_state, 'fetched_content') and st.session_state.get('fetched_url') == url:
                content = st.session_state.fetched_content
                with st.expander("Podgląd HTML (pierwsze 500 zn.)"):
                    st.code(content[:500] + "..." if len(content) > 500 else content, language="html")

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload plik HTML:",
            type=["html", "htm"],
        )

        if uploaded_file:
            content = uploaded_file.read().decode("utf-8")
            st.success(f"✅ Załadowano: {uploaded_file.name}")
            with st.expander("Podgląd HTML (pierwsze 500 zn.)"):
                st.code(content[:500] + "..." if len(content) > 500 else content, language="html")

    return content


def render_overview(result: AnalysisResult):
    """Renderuje tab Overview."""
    content = result.content

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 Wyekstrahowana struktura")

        if content.title:
            st.markdown(f"**Title:** {content.title} *({len(content.title)} zn.)*")
        else:
            st.warning("Brak Title Tag")

        if content.meta_description:
            st.markdown(f"**Meta:** {content.meta_description[:100]}... *({len(content.meta_description)} zn.)*")
        else:
            st.warning("Brak Meta Description")

        if content.h1:
            st.markdown(f"**H1:** {content.h1}")
        else:
            st.warning("Brak H1")

        st.markdown(f"**H2:** {content.h2_count} nagłówków")
        st.markdown(f"**H3:** {content.h3_count} nagłówków")

    with col2:
        st.subheader("📊 Semantic Alignment")

        # Core similarity scores
        display_names = content.get_all_display_names()
        for score in result.similarity_scores[:3]:  # Title-Meta, Title-H1, Meta-H1
            icon = STATUS_CONFIG[score.status.value]["icon"]
            color = STATUS_CONFIG[score.status.value]["color"]
            # Użyj czytelnych nazw jeśli dostępne
            label_a = display_names.get(score.element_a, score.element_a).split(":")[0]  # Tylko "Title", "Meta", "H1"
            label_b = display_names.get(score.element_b, score.element_b).split(":")[0]
            label = f"{label_a} ↔ {label_b}"

            st.markdown(
                f"{icon} **{label}:** "
                f"<span style='color:{color}'>{score.score*100:.0f}%</span> "
                f"*(target: {score.target_min*100:.0f}-{score.target_max*100:.0f}%)*",
                unsafe_allow_html=True,
            )

        st.divider()

        # Overall score
        score_color = "#28a745" if result.overall_score >= 80 else "#ffc107" if result.overall_score >= 60 else "#dc3545"
        st.metric(
            "Overall Score",
            f"{result.overall_score:.0f}/100",
            delta=None,
        )

    # Topic drift warning
    if result.topic_drifts:
        st.warning(f"⚠️ Wykryto topic drift w {len(result.topic_drifts)} elementach")
        for drift in result.topic_drifts:
            elem_name = content.get_display_name(drift[0])
            parent_name = content.get_display_name(drift[1])
            st.caption(f"- {elem_name}: {drift[2]*100:.0f}% similarity z {parent_name}")

    # Quick issues summary
    st.subheader("🚨 Podsumowanie problemów")
    critical = len([i for i in result.checklist_results if i.status == CheckStatus.FAIL and i.priority.value == "CRITICAL"])
    high = len([i for i in result.checklist_results if i.status == CheckStatus.FAIL and i.priority.value == "HIGH"])
    warnings = len([i for i in result.checklist_results if i.status == CheckStatus.WARNING])

    cols = st.columns(3)
    cols[0].metric("🔴 Critical", critical)
    cols[1].metric("🟠 High", high)
    cols[2].metric("🟡 Warnings", warnings)


def render_visualizations(result: AnalysisResult):
    """Renderuje tab Visualizations."""
    viz_type = st.radio(
        "Wybierz wizualizację:",
        ["📊 2D Scatter Plot", "📦 3D Scatter Plot", "🗺️ Heatmapa Similarity", "🌳 Drzewo Hierarchii"],
        horizontal=True,
    )

    if viz_type == "📊 2D Scatter Plot":
        method = st.selectbox("Metoda redukcji:", ["PCA", "UMAP"])
        fig = create_scatter_with_similarity(
            result.embeddings,
            result.similarity_scores,
            method=method.lower(),
            content=result.content,
        )
        st.plotly_chart(fig, width="stretch")

    elif viz_type == "📦 3D Scatter Plot":
        st.caption("Czerwony diament = Centroid, linie do Core (Title/Meta/H1)")
        fig = create_3d_scatter_with_similarity(
            result.embeddings,
            result.similarity_scores,
            content=result.content,
        )
        st.plotly_chart(fig, width="stretch")

    elif viz_type == "🗺️ Heatmapa Similarity":
        analyzer = SimilarityAnalyzer()
        matrix = analyzer.compute_similarity_matrix(result.embeddings)

        show_core_only = st.checkbox("Tylko Core (Title/Meta/H1)", value=True)

        if show_core_only:
            fig = create_core_heatmap(matrix, content=result.content)
        else:
            fig = create_heatmap(matrix, content=result.content)

        st.plotly_chart(fig, width="stretch")

    else:  # Hierarchy Tree
        checklist_statuses = {
            item.code: item.status for item in result.checklist_results
        }
        fig = create_hierarchy_tree(result.content, checklist_statuses)
        st.plotly_chart(fig, width="stretch")

        # Text version
        with st.expander("📝 Tekstowa reprezentacja"):
            st.code(create_simple_hierarchy_view(result.content))


def render_checklist(result: AnalysisResult):
    """Renderuje tab Checklist."""
    # Filtry
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Status:",
            ["PASS", "WARNING", "FAIL"],
            default=["WARNING", "FAIL"],
        )
    with col2:
        priority_filter = st.multiselect(
            "Priorytet:",
            ["CRITICAL", "HIGH", "MEDIUM"],
            default=["CRITICAL", "HIGH", "MEDIUM"],
        )

    # Filtruj wyniki
    filtered = [
        item for item in result.checklist_results
        if item.status.value in status_filter and item.priority.value in priority_filter
    ]

    if not filtered:
        st.info("Brak elementów spełniających kryteria filtru")
        return

    # Grupuj po sekcjach
    sections = {
        "Title Tag": ["CV-001", "CV-002", "CV-003", "CV-004"],
        "Meta Description": ["CV-005", "CV-006", "CV-007"],
        "H1 Tag": ["CV-008", "CV-009", "CV-010"],
        "Semantic Alignment": ["CV-011", "CV-012"],
        "Hierarchia H2": ["CV-013", "CV-014", "CV-015", "CV-016"],
        "Hierarchia H3": ["CV-017", "CV-018", "CV-019"],
    }

    for section_name, codes in sections.items():
        section_items = [i for i in filtered if i.code in codes]
        if not section_items:
            continue

        with st.expander(f"📌 {section_name}", expanded=True):
            for item in section_items:
                status_cfg = STATUS_CONFIG[item.status.value]
                priority_cfg = PRIORITY_CONFIG[item.priority.value]

                st.markdown(
                    f"{status_cfg['icon']} **{item.code}** {priority_cfg['icon']} "
                    f"*{item.name}*  \n"
                    f"Wartość: `{item.value}` | Target: `{item.target}`",
                )
                if item.message:
                    st.caption(f"ℹ️ {item.message}")


def render_suggestions(result: AnalysisResult):
    """Renderuje tab Suggestions."""
    # Inicjalizuj storage dla sugestii
    if "generated_suggestions" not in st.session_state:
        st.session_state.generated_suggestions = {}

    # Użyj wybranego modelu LLM
    client = get_ollama_client()
    client.llm_model = st.session_state.llm_model

    suggester = LLMSuggester(ollama_client=client)
    ollama_ok, message = suggester.check_ollama_available()

    if not ollama_ok:
        st.error(f"❌ {message}")
        return

    st.success("✅ LLM gotowy do generowania sugestii")

    # Pobierz problemy
    problems = [
        item for item in result.checklist_results
        if item.status in (CheckStatus.FAIL, CheckStatus.WARNING)
    ]

    if not problems:
        st.info("🎉 Brak problemów do naprawy!")
        return

    st.subheader(f"🔧 {len(problems)} problemów do naprawy")

    # Generuj sugestie na żądanie
    for item in problems:
        with st.expander(f"{STATUS_CONFIG[item.status.value]['icon']} {item.code} - {item.name}"):
            st.markdown(f"**Problem:** {item.description}")
            st.markdown(f"**Aktualna wartość:** `{item.value}`")
            st.markdown(f"**Target:** `{item.target}`")

            # Sprawdź czy już wygenerowano sugestię
            if item.code in st.session_state.generated_suggestions:
                st.markdown("**Sugestie:**")
                st.markdown(st.session_state.generated_suggestions[item.code])

                # Przycisk do regeneracji
                if st.button(f"🔄 Regeneruj", key=f"regen_{item.code}"):
                    del st.session_state.generated_suggestions[item.code]
                    st.rerun()
            else:
                # Przycisk do generowania
                if st.button(f"💡 Generuj sugestie", key=f"suggest_{item.code}"):
                    with st.spinner("Generuję sugestie..."):
                        suggestion = suggester.generate_suggestion(
                            item,
                            result.content,
                            similarity_score=next(
                                (s.score for s in result.similarity_scores
                                 if item.code == "CV-009" and s.element_a == "title" and s.element_b == "h1"),
                                None,
                            ),
                        )
                        st.session_state.generated_suggestions[item.code] = suggestion
                    st.rerun()  # Odśwież aby pokazać zapisaną sugestię


def render_debug(result: AnalysisResult):
    """Renderuje debug info."""
    st.subheader("🐛 Debug Info")

    with st.expander("Raw Embeddings Shape"):
        for name, emb in result.embeddings.items():
            st.text(f"{name}: {emb.shape}")

    with st.expander("Similarity Scores"):
        for score in result.similarity_scores:
            st.json({
                "a": score.element_a,
                "b": score.element_b,
                "score": score.score,
                "status": score.status.value,
            })

    with st.expander("Topic Drifts"):
        if result.topic_drifts:
            for drift in result.topic_drifts:
                elem_key, parent_key, score = drift
                elem_name = result.content.get_display_name(elem_key)
                parent_name = result.content.get_display_name(parent_key)
                st.markdown(
                    f"**{elem_name}** vs **{parent_name}**: "
                    f"`{score*100:.1f}%` similarity (< 40% = drift)"
                )
        else:
            st.info("Brak wykrytych topic drifts")

    with st.expander("Checklist Results"):
        df = pd.DataFrame([
            {
                "code": i.code,
                "name": i.name,
                "status": i.status.value,
                "priority": i.priority.value,
                "value": i.value,
            }
            for i in result.checklist_results
        ])
        st.dataframe(df)


def main():
    """Main application."""
    st.title("🔬 Content Context Vector Analyzer")
    st.caption("Analiza hierarchicznej struktury semantycznej treści z embeddingami Ollama")

    render_sidebar()

    # Input section
    content = render_input_section()

    if content:
        # Pokaż wybrany model
        st.caption(f"Model embedding: **{st.session_state.embedding_model}**")

        # Analyze button
        if st.button("▶️ Analizuj", type="primary"):
            # Sprawdź dostępność modelu przed analizą
            client = get_ollama_client()

            if not client.check_connection():
                st.error(
                    "❌ **Ollama niedostępna**\n\n"
                    "Uruchom Ollama w terminalu:\n"
                    "```\n"
                    "ollama serve\n"
                    "```"
                )
            elif not client.has_model(st.session_state.embedding_model):
                st.error(
                    f"❌ **Model '{st.session_state.embedding_model}' niedostępny**\n\n"
                    f"Zainstaluj model ręcznie:\n"
                    f"```\n"
                    f"ollama pull {st.session_state.embedding_model}\n"
                    f"```\n\n"
                    f"Dostępne modele: {', '.join(client.list_models()) or 'brak'}"
                )
            else:
                with st.spinner(f"Analizuję dokument (model: {st.session_state.embedding_model})..."):
                    try:
                        parsed = parse_content(content)
                        result = run_analysis(parsed, embedding_model=st.session_state.embedding_model)
                        st.session_state.analysis_result = result
                        st.success("✅ Analiza zakończona!")
                    except Exception as e:
                        st.error(f"❌ Błąd analizy: {str(e)}")
                        if st.session_state.debug_mode:
                            st.exception(e)

    # Results - użyj radio zamiast tabs dla zachowania stanu
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result

        # Inicjalizuj stan aktywnego taba
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "📊 Overview"

        # Radio do wyboru sekcji (zachowuje stan przy rerun)
        tab_options = ["📊 Overview", "🗺️ Wizualizacje", "✅ Checklist", "💡 Sugestie LLM"]
        selected_tab = st.radio(
            "Sekcja:",
            tab_options,
            index=tab_options.index(st.session_state.active_tab),
            horizontal=True,
            key="tab_radio",
        )
        st.session_state.active_tab = selected_tab

        st.divider()

        # Renderuj wybraną sekcję
        if selected_tab == "📊 Overview":
            render_overview(result)
        elif selected_tab == "🗺️ Wizualizacje":
            render_visualizations(result)
        elif selected_tab == "✅ Checklist":
            render_checklist(result)
        elif selected_tab == "💡 Sugestie LLM":
            render_suggestions(result)

        # Debug (if enabled)
        if st.session_state.debug_mode:
            with st.expander("🐛 Debug"):
                render_debug(result)


if __name__ == "__main__":
    main()
