"""Wizualizacja hierarchicznego drzewa Content Context Vector."""

import plotly.graph_objects as go
from core.models import ExtractedContent, ChecklistItem, CheckStatus


def get_status_color(status: CheckStatus | str) -> str:
    """Zwraca kolor na podstawie statusu."""
    if isinstance(status, str):
        status = CheckStatus(status) if status in [s.value for s in CheckStatus] else CheckStatus.PASS

    colors = {
        CheckStatus.PASS: "#28a745",
        CheckStatus.WARNING: "#ffc107",
        CheckStatus.FAIL: "#dc3545",
    }
    return colors.get(status, "#6c757d")


def create_hierarchy_tree(
    content: ExtractedContent,
    checklist_results: dict[str, CheckStatus] | None = None,
) -> go.Figure:
    """
    Tworzy wizualizację hierarchicznego drzewa Content Context Vector.

    Args:
        content: Wyekstrahowana zawartość dokumentu
        checklist_results: Słownik {element_id: status} dla kolorowania

    Returns:
        Plotly Figure z drzewem hierarchii
    """
    checklist_results = checklist_results or {}

    # Buduj dane dla drzewa
    nodes = []
    edges = []

    # Poziomy Y dla elementów
    y_levels = {
        "title": 0,
        "meta": 1,
        "h1": 2,
        "h2": 3,
        "h3": 4,
    }

    # Title (root)
    if content.title:
        title_short = content.title[:40] + "..." if len(content.title) > 40 else content.title
        nodes.append({
            "id": "title",
            "label": f"Title: {title_short}",
            "x": 0,
            "y": y_levels["title"],
            "color": get_status_color(checklist_results.get("title", CheckStatus.PASS)),
        })

    # Meta
    if content.meta_description:
        meta_short = content.meta_description[:40] + "..." if len(content.meta_description) > 40 else content.meta_description
        nodes.append({
            "id": "meta",
            "label": f"Meta: {meta_short}",
            "x": 0,
            "y": y_levels["meta"],
            "color": get_status_color(checklist_results.get("meta", CheckStatus.PASS)),
        })
        if content.title:
            edges.append(("title", "meta"))

    # H1
    if content.h1:
        h1_short = content.h1[:40] + "..." if len(content.h1) > 40 else content.h1
        nodes.append({
            "id": "h1",
            "label": f"H1: {h1_short}",
            "x": 0,
            "y": y_levels["h1"],
            "color": get_status_color(checklist_results.get("h1", CheckStatus.PASS)),
        })
        if content.meta_description:
            edges.append(("meta", "h1"))
        elif content.title:
            edges.append(("title", "h1"))

    # H2
    h2_width = max(len(content.h2_list), 1)
    for i, h2 in enumerate(content.h2_list):
        h2_id = f"h2_{i}"
        h2_short = h2.text[:30] + "..." if len(h2.text) > 30 else h2.text
        x_pos = (i - (len(content.h2_list) - 1) / 2) * 2

        nodes.append({
            "id": h2_id,
            "label": f"H2: {h2_short}",
            "x": x_pos,
            "y": y_levels["h2"],
            "color": get_status_color(checklist_results.get(h2_id, CheckStatus.PASS)),
        })
        if content.h1:
            edges.append(("h1", h2_id))

    # H3
    for i, h3 in enumerate(content.h3_list):
        h3_id = f"h3_{i}"
        h3_short = h3.text[:25] + "..." if len(h3.text) > 25 else h3.text

        # Pozycja X zależna od rodzica H2
        if h3.parent_index is not None and h3.parent_index < len(content.h2_list):
            parent_node = next((n for n in nodes if n["id"] == f"h2_{h3.parent_index}"), None)
            x_pos = parent_node["x"] if parent_node else 0
            # Offsetuj H3 pod H2
            h3_siblings = [h for h in content.h3_list if h.parent_index == h3.parent_index]
            sibling_idx = h3_siblings.index(h3) if h3 in h3_siblings else 0
            x_pos += (sibling_idx - (len(h3_siblings) - 1) / 2) * 0.5
        else:
            x_pos = i * 0.5

        nodes.append({
            "id": h3_id,
            "label": f"H3: {h3_short}",
            "x": x_pos,
            "y": y_levels["h3"],
            "color": get_status_color(checklist_results.get(h3_id, CheckStatus.PASS)),
        })

        # Krawędź do rodzica
        if h3.parent_index is not None:
            edges.append((f"h2_{h3.parent_index}", h3_id))

    # Stwórz figurę
    fig = go.Figure()

    # Dodaj krawędzie
    for start_id, end_id in edges:
        start_node = next((n for n in nodes if n["id"] == start_id), None)
        end_node = next((n for n in nodes if n["id"] == end_id), None)

        if start_node and end_node:
            fig.add_trace(
                go.Scatter(
                    x=[start_node["x"], end_node["x"]],
                    y=[start_node["y"], end_node["y"]],
                    mode="lines",
                    line=dict(color="#cccccc", width=1),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    # Dodaj węzły
    for node in nodes:
        fig.add_trace(
            go.Scatter(
                x=[node["x"]],
                y=[node["y"]],
                mode="markers+text",
                marker=dict(
                    size=15,
                    color=node["color"],
                    line=dict(width=2, color="white"),
                ),
                text=[node["label"]],
                textposition="middle right",
                textfont=dict(size=10),
                hovertemplate=f"<b>{node['label']}</b><extra></extra>",
                showlegend=False,
            )
        )

    # Konfiguracja layoutu
    fig.update_layout(
        title=dict(text="Hierarchia Content Context Vector", x=0.5),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-h2_width - 1, h2_width + 1],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            autorange="reversed",
            range=[-0.5, 5],
        ),
        showlegend=False,
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    # Dodaj etykiety poziomów po lewej
    level_labels = ["Title", "Meta", "H1", "H2", "H3"]
    for i, label in enumerate(level_labels):
        fig.add_annotation(
            x=-h2_width - 0.5,
            y=i,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=12, color="#666"),
            xanchor="right",
        )

    return fig


def create_simple_hierarchy_view(content: ExtractedContent) -> str:
    """
    Tworzy tekstową reprezentację hierarchii (dla debugowania).

    Args:
        content: Wyekstrahowana zawartość

    Returns:
        String z hierarchią w formie drzewa
    """
    lines = []

    if content.title:
        lines.append(f"📌 Title: {content.title}")

    if content.meta_description:
        lines.append(f"  └─ 📝 Meta: {content.meta_description[:60]}...")

    for i, h1 in enumerate(content.h1_list):
        lines.append(f"     └─ 🔤 H1: {h1}")

    for i, h2 in enumerate(content.h2_list):
        prefix = "        ├─" if i < len(content.h2_list) - 1 else "        └─"
        lines.append(f"{prefix} 📑 H2: {h2.text}")

        # Znajdź H3 dla tego H2
        h3_children = [h for h in content.h3_list if h.parent_index == i]
        for j, h3 in enumerate(h3_children):
            h3_prefix = "           ├─" if j < len(h3_children) - 1 else "           └─"
            lines.append(f"{h3_prefix} 📄 H3: {h3.text}")

    return "\n".join(lines)
