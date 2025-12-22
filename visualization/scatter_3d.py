"""3D Scatter Plot z centroidem dla wizualizacji embeddingów Content Context Vector."""

import numpy as np
import pandas as pd
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


def reduce_dimensions_3d(
    embeddings: dict[str, np.ndarray],
) -> pd.DataFrame:
    """
    Redukuje wymiarowość embeddingów do 3D.

    Args:
        embeddings: Słownik {nazwa: embedding}

    Returns:
        DataFrame z kolumnami: name, x, y, z, type, label
    """
    names = list(embeddings.keys())
    vectors = np.array([embeddings[k] for k in names])

    reducer = PCA(n_components=3)
    coords = reducer.fit_transform(vectors)

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
        "z": coords[:, 2],
        "type": [get_type(n) for n in names],
    })

    return df


def compute_centroid(df: pd.DataFrame) -> tuple[float, float, float]:
    """
    Oblicza centroid wszystkich punktów.

    Args:
        df: DataFrame z kolumnami x, y, z

    Returns:
        Tuple (x, y, z) centroidu
    """
    return df["x"].mean(), df["y"].mean(), df["z"].mean()


def create_3d_scatter(
    embeddings: dict[str, np.ndarray],
    title: str = "Content Context Vector - 3D Przestrzeń Semantyczna",
    content=None,
) -> go.Figure:
    """
    Tworzy interaktywny 3D scatter plot embeddingów z centroidem.

    Args:
        embeddings: Słownik {nazwa: embedding}
        title: Tytuł wykresu
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure
    """
    df = reduce_dimensions_3d(embeddings)

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
        "Core": 12,
        "H2": 8,
        "H3": 5,
        "Other": 6,
    }

    fig = go.Figure()

    # Dodaj punkty dla każdego typu osobno (dla legendy)
    for elem_type in ["Core", "H2", "H3"]:
        type_df = df[df["type"] == elem_type]
        if len(type_df) > 0:
            fig.add_trace(
                go.Scatter3d(
                    x=type_df["x"],
                    y=type_df["y"],
                    z=type_df["z"],
                    mode="markers+text",
                    name=elem_type,
                    text=type_df["label"],
                    textposition="top center",
                    marker=dict(
                        size=size_map[elem_type],
                        color=color_map[elem_type],
                        line=dict(width=1, color="white"),
                    ),
                    hovertemplate="<b>%{text}</b><br>x: %{x:.3f}<br>y: %{y:.3f}<br>z: %{z:.3f}<extra></extra>",
                )
            )

    # Oblicz centroid
    centroid = compute_centroid(df)

    # Dodaj centroid jako większy punkt
    fig.add_trace(
        go.Scatter3d(
            x=[centroid[0]],
            y=[centroid[1]],
            z=[centroid[2]],
            mode="markers",
            name="Centroid",
            marker=dict(
                size=15,
                color="red",
                symbol="diamond",
                line=dict(width=2, color="darkred"),
            ),
            hovertemplate="<b>Centroid</b><br>x: %{x:.3f}<br>y: %{y:.3f}<br>z: %{z:.3f}<extra></extra>",
        )
    )

    # Dodaj linie od centroidu TYLKO do Core elements (Title, Meta, H1)
    core_df = df[df["type"] == "Core"]
    for _, row in core_df.iterrows():
        fig.add_trace(
            go.Scatter3d(
                x=[centroid[0], row["x"]],
                y=[centroid[1], row["y"]],
                z=[centroid[2], row["z"]],
                mode="lines",
                line=dict(color="rgba(255, 0, 0, 0.5)", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=dict(text=title, x=0.5),
        scene=dict(
            xaxis_title="PCA Dimension 1",
            yaxis_title="PCA Dimension 2",
            zaxis_title="PCA Dimension 3",
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
        ),
        template="plotly_white",
        height=600,
    )

    return fig


def create_3d_scatter_with_similarity(
    embeddings: dict[str, np.ndarray],
    similarity_scores: list,
    content=None,
) -> go.Figure:
    """
    Tworzy 3D scatter plot z liniami pokazującymi similarity między elementami.

    Args:
        embeddings: Słownik embeddingów
        similarity_scores: Lista SimilarityScore
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure z liniami similarity
    """
    fig = create_3d_scatter(embeddings, content=content)
    df = reduce_dimensions_3d(embeddings)

    # Aktualizuj etykiety jeśli mamy content
    if content:
        df["label"] = df["name"].apply(content.get_display_name)

    # Dodaj linie dla par z similarity scores
    for score in similarity_scores:
        a_row = df[df["name"] == score.element_a]
        b_row = df[df["name"] == score.element_b]

        if len(a_row) > 0 and len(b_row) > 0:
            # Kolor linii zależny od statusu
            color = {
                "PASS": "rgba(40, 167, 69, 0.6)",
                "WARNING": "rgba(255, 193, 7, 0.6)",
                "FAIL": "rgba(220, 53, 69, 0.6)",
            }.get(score.status.value, "rgba(128, 128, 128, 0.6)")

            # Użyj czytelnych etykiet w hover
            label_a = format_element_label(score.element_a)
            label_b = format_element_label(score.element_b)

            fig.add_trace(
                go.Scatter3d(
                    x=[a_row["x"].values[0], b_row["x"].values[0]],
                    y=[a_row["y"].values[0], b_row["y"].values[0]],
                    z=[a_row["z"].values[0], b_row["z"].values[0]],
                    mode="lines",
                    line=dict(color=color, width=2),
                    hovertemplate=f"{label_a} ↔ {label_b}: {score.score*100:.0f}%<extra></extra>",
                    showlegend=False,
                )
            )

    return fig
