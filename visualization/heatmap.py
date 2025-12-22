"""Heatmapa macierzy podobieństwa semantycznego."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config.settings import SIMILARITY_THRESHOLDS


def create_heatmap(
    similarity_matrix: pd.DataFrame,
    title: str = "Macierz Podobieństwa Semantycznego",
    content=None,
) -> go.Figure:
    """
    Tworzy interaktywną heatmapę macierzy similarity.

    Args:
        similarity_matrix: DataFrame z macierzą similarity (labels x labels)
        title: Tytuł wykresu
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure
    """
    # Przygotuj dane
    z = similarity_matrix.values
    x_labels = list(similarity_matrix.columns)
    y_labels = list(similarity_matrix.index)

    # Formatuj etykiety dla czytelności
    def format_label(label: str) -> str:
        if label == "title":
            return "Title"
        elif label == "meta":
            return "Meta"
        elif label == "h1":
            return "H1"
        elif label.startswith("h2_"):
            return f"H2-{label.split('_')[1]}"
        elif label.startswith("h3_"):
            return f"H3-{label.split('_')[1]}"
        return label

    # Użyj czytelnych etykiet z content jeśli dostępne
    if content:
        x_labels_fmt = [content.get_display_name(l) for l in x_labels]
        y_labels_fmt = [content.get_display_name(l) for l in y_labels]
    else:
        x_labels_fmt = [format_label(l) for l in x_labels]
        y_labels_fmt = [format_label(l) for l in y_labels]

    # Tekst dla hover
    text = [[f"{z[i][j]*100:.1f}%" for j in range(len(x_labels))] for i in range(len(y_labels))]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_labels_fmt,
            y=y_labels_fmt,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale=[
                [0.0, "#dc3545"],    # czerwony (0-40%)
                [0.4, "#ffc107"],    # żółty (40%)
                [0.6, "#28a745"],    # zielony (60%)
                [0.8, "#28a745"],    # zielony (80%)
                [1.0, "#1f77b4"],    # niebieski (100%)
            ],
            zmin=0,
            zmax=1,
            colorbar=dict(
                title="Similarity",
                tickformat=".0%",
            ),
            hovertemplate="<b>%{y} ↔ %{x}</b><br>Similarity: %{z:.1%}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis=dict(title="", tickangle=-45),
        yaxis=dict(title="", autorange="reversed"),
        template="plotly_white",
        height=500,
        width=600,
    )

    return fig


def create_core_heatmap(
    similarity_matrix: pd.DataFrame,
    title: str = "Semantic Alignment (Title ↔ Meta ↔ H1)",
    content=None,
) -> go.Figure:
    """
    Tworzy heatmapę tylko dla elementów core (Title, Meta, H1).

    Args:
        similarity_matrix: Pełna macierz similarity
        title: Tytuł wykresu
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure
    """
    core_elements = ["title", "meta", "h1"]
    available = [e for e in core_elements if e in similarity_matrix.columns]

    if len(available) < 2:
        # Zwróć pustą figurę z komunikatem
        fig = go.Figure()
        fig.add_annotation(
            text="Brak wystarczających danych do analizy",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    core_matrix = similarity_matrix.loc[available, available]
    return create_heatmap(core_matrix, title=title, content=content)


def create_annotated_heatmap(
    similarity_matrix: pd.DataFrame,
    thresholds: dict | None = None,
    content=None,
) -> go.Figure:
    """
    Tworzy heatmapę z adnotacjami statusów (PASS/WARNING/FAIL).

    Args:
        similarity_matrix: DataFrame z macierzą similarity
        thresholds: Słownik z progami dla różnych par
        content: ExtractedContent dla czytelnych etykiet (opcjonalnie)

    Returns:
        Plotly Figure z kolorowymi ramkami
    """
    thresholds = thresholds or SIMILARITY_THRESHOLDS

    fig = create_heatmap(similarity_matrix, content=content)

    # Dodaj ramki dla kluczowych par
    key_pairs = [
        ("title", "meta", thresholds["title_meta"]),
        ("title", "h1", thresholds["title_h1"]),
        ("meta", "h1", thresholds["meta_h1"]),
    ]

    labels = list(similarity_matrix.columns)

    for elem_a, elem_b, thresh in key_pairs:
        if elem_a in labels and elem_b in labels:
            i = labels.index(elem_a)
            j = labels.index(elem_b)
            score = similarity_matrix.iloc[i, j]

            # Określ kolor ramki
            if thresh["target_min"] <= score <= thresh["target_max"]:
                color = "green"
            elif thresh["min"] <= score <= thresh["max"]:
                color = "orange"
            else:
                color = "red"

            # Dodaj prostokąt
            fig.add_shape(
                type="rect",
                x0=j - 0.5,
                y0=i - 0.5,
                x1=j + 0.5,
                y1=i + 0.5,
                line=dict(color=color, width=3),
            )

    return fig
