"""2D Scatter Plot dla wizualizacji embeddingów Content Context Vector."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA


def format_element_label(name: str) -> str:
    """Formatuje klucz techniczny na czytelną etykietę dla wizualizacji."""
    if name == "title":
        return "Title"
    elif name == "meta":
        return "Meta"
    elif name == "h1":
        return "H1"
    elif name.startswith("h2_"):
        idx = name.split("_")[1]
        return f"H2-{idx}"
    elif name.startswith("h3_"):
        idx = name.split("_")[1]
        return f"H3-{idx}"
    return name


def reduce_dimensions(
    embeddings: dict[str, np.ndarray],
    method: str = "pca",
    n_components: int = 2,
) -> pd.DataFrame:
    """
    Redukuje wymiarowość embeddingów do 2D.

    Args:
        embeddings: Słownik {nazwa: embedding}
        method: Metoda redukcji ("pca" lub "umap")
        n_components: Liczba wymiarów wyjściowych

    Returns:
        DataFrame z kolumnami: name, x, y, type, label
    """
    names = list(embeddings.keys())
    vectors = np.array([embeddings[k] for k in names])

    if method == "pca":
        reducer = PCA(n_components=n_components)
        coords = reducer.fit_transform(vectors)
    elif method == "umap":
        try:
            from umap import UMAP
            reducer = UMAP(n_components=n_components, random_state=42)
            coords = reducer.fit_transform(vectors)
        except ImportError:
            # Fallback to PCA if UMAP not installed
            reducer = PCA(n_components=n_components)
            coords = reducer.fit_transform(vectors)
    else:
        raise ValueError(f"Unknown method: {method}")

    # Określ typ elementu
    def get_type(name: str) -> str:
        if name in ("title", "meta", "h1"):
            return "Core"
        elif name.startswith("h2"):
            return "H2"
        elif name.startswith("h3"):
            return "H3"
        return "Other"

    df = pd.DataFrame({
        "name": names,
        "label": [format_element_label(n) for n in names],
        "x": coords[:, 0],
        "y": coords[:, 1],
        "type": [get_type(n) for n in names],
    })

    return df


def create_scatter_plot(
    embeddings: dict[str, np.ndarray],
    method: str = "pca",
    title: str = "Content Context Vector - Przestrzeń Embeddingów",
    content=None,
) -> go.Figure:
    """
    Tworzy interaktywny 2D scatter plot embeddingów.

    Args:
        embeddings: Słownik {nazwa: embedding}
        method: Metoda redukcji wymiarów ("pca" lub "umap")
        title: Tytuł wykresu
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure
    """
    df = reduce_dimensions(embeddings, method=method)

    # Użyj pełnych etykiet z content jeśli dostępne
    if content:
        df["label"] = df["name"].apply(content.get_display_name)

    # Kolory i rozmiary dla typów
    color_map = {
        "Core": "#1f77b4",  # niebieski
        "H2": "#ff7f0e",    # pomarańczowy
        "H3": "#2ca02c",    # zielony
        "Other": "#7f7f7f", # szary
    }

    size_map = {
        "Core": 20,
        "H2": 12,
        "H3": 8,
        "Other": 10,
    }

    df["color"] = df["type"].map(color_map)
    df["size"] = df["type"].map(size_map)

    fig = go.Figure()

    # Dodaj punkty dla każdego typu osobno (dla legendy)
    for elem_type in ["Core", "H2", "H3"]:
        type_df = df[df["type"] == elem_type]
        if len(type_df) > 0:
            fig.add_trace(
                go.Scatter(
                    x=type_df["x"],
                    y=type_df["y"],
                    mode="markers+text",
                    name=elem_type,
                    text=type_df["label"],  # Użyj czytelnych etykiet
                    textposition="top center",
                    marker=dict(
                        size=size_map[elem_type],
                        color=color_map[elem_type],
                        line=dict(width=1, color="white"),
                    ),
                    hovertemplate="<b>%{text}</b><br>x: %{x:.3f}<br>y: %{y:.3f}<extra></extra>",
                )
            )

    # Dodaj linie łączące Core elements (Title → Meta → H1)
    core_df = df[df["type"] == "Core"]
    if len(core_df) >= 2:
        # Sortuj: title, meta, h1
        order = {"title": 0, "meta": 1, "h1": 2}
        core_df = core_df.copy()
        core_df["order"] = core_df["name"].map(order)
        core_df = core_df.sort_values("order")

        fig.add_trace(
            go.Scatter(
                x=core_df["x"],
                y=core_df["y"],
                mode="lines",
                name="Semantic Chain",
                line=dict(color="rgba(31, 119, 180, 0.3)", width=2, dash="dot"),
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title=f"{method.upper()} Dimension 1",
        yaxis_title=f"{method.upper()} Dimension 2",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
        ),
        hovermode="closest",
        template="plotly_white",
        height=500,
    )

    return fig


def create_scatter_with_similarity(
    embeddings: dict[str, np.ndarray],
    similarity_scores: list,
    method: str = "pca",
    content=None,
) -> go.Figure:
    """
    Tworzy scatter plot z liniami pokazującymi similarity.

    Args:
        embeddings: Słownik embeddingów
        similarity_scores: Lista SimilarityScore
        method: Metoda redukcji
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure z liniami similarity
    """
    fig = create_scatter_plot(embeddings, method=method, content=content)
    df = reduce_dimensions(embeddings, method=method)

    # Aktualizuj etykiety jeśli mamy content
    if content:
        df["label"] = df["name"].apply(content.get_display_name)

    # Dodaj linie dla par z similarity scores
    h2_lines_added = False  # Dla legendy H2

    for score in similarity_scores:
        a_row = df[df["name"] == score.element_a]
        b_row = df[df["name"] == score.element_b]

        if len(a_row) > 0 and len(b_row) > 0:
            # Sprawdź czy to połączenie z H2
            is_h2_connection = "h2" in score.element_a or "h2" in score.element_b

            # Kolor i grubość linii zależne od typu połączenia
            if is_h2_connection:
                # H2 - bardziej widoczne
                color = {
                    "PASS": "rgba(40, 167, 69, 0.8)",
                    "WARNING": "rgba(255, 193, 7, 0.8)",
                    "FAIL": "rgba(220, 53, 69, 0.8)",
                }.get(score.status.value, "rgba(128, 128, 128, 0.8)")
                line_width = 3
                show_legend = not h2_lines_added
                legend_name = "H2 Connections" if show_legend else None
                h2_lines_added = True
            else:
                # Core - standardowe
                color = {
                    "PASS": "rgba(40, 167, 69, 0.6)",
                    "WARNING": "rgba(255, 193, 7, 0.6)",
                    "FAIL": "rgba(220, 53, 69, 0.6)",
                }.get(score.status.value, "rgba(128, 128, 128, 0.6)")
                line_width = 2
                show_legend = False
                legend_name = None

            # Użyj czytelnych etykiet w hover
            label_a = format_element_label(score.element_a)
            label_b = format_element_label(score.element_b)

            fig.add_trace(
                go.Scatter(
                    x=[a_row["x"].values[0], b_row["x"].values[0]],
                    y=[a_row["y"].values[0], b_row["y"].values[0]],
                    mode="lines",
                    name=legend_name,
                    line=dict(color=color, width=line_width),
                    hovertemplate=f"{label_a} ↔ {label_b}: {score.score*100:.0f}%<extra></extra>",
                    showlegend=show_legend,
                )
            )

    return fig
