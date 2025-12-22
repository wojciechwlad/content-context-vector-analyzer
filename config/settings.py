"""Konfiguracja aplikacji Content Context Vector Analyzer."""

# Konfiguracja Ollama
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "embedding_model": "snowflake-arctic-embed2:latest",
    "llm_model": "gemma3:12b",
    "timeout": 30,
    "embedding_dimensions": 1024,  # snowflake-arctic-embed2 uses 1024 dimensions
}

# Progi similarity
SIMILARITY_THRESHOLDS = {
    "title_meta": {"min": 0.50, "target_min": 0.60, "target_max": 0.80, "max": 0.85},
    "title_h1": {"min": 0.75, "target_min": 0.80, "target_max": 0.90, "max": 0.95},
    "meta_h1": {"min": 0.65, "target_min": 0.70, "target_max": 0.85, "max": 0.90},
    "h2_title": {"min": 0.40, "target_min": 0.50, "target_max": 0.70, "max": 0.80},
    "h3_parent_h2": {"min": 0.50, "target_min": 0.60, "target_max": 0.80, "max": 0.90},
    "topic_drift": 0.40,  # poniżej = drift detected
}

# Progi strukturalne
THRESHOLDS = {
    # Title
    "title_min_length": 30,
    "title_optimal_min": 50,
    "title_optimal_max": 60,
    "title_max_length": 70,
    "title_keyword_position_max": 60,
    "title_max_keyword_count": 2,

    # Meta Description
    "meta_min_length": 120,
    "meta_optimal_min": 150,
    "meta_optimal_max": 160,
    "meta_max_length": 170,
    "meta_title_unique_content_min": 0.60,

    # H1
    "h1_count_expected": 1,
    "h1_title_similarity_min": 0.80,
    "h1_title_similarity_max": 0.90,

    # H2
    "h2_count_min": 4,
    "h2_count_max": 8,
    "h2_question_ratio_min": 0.50,

    # H3
    "h3_words_per_section_min": 150,
    "h3_words_per_section_max": 300,

    # Keyword density
    "keyword_vector_count_min": 3,
    "keyword_vector_count_max": 5,
}

# Konfiguracja statusów
STATUS_CONFIG = {
    "PASS": {"color": "#28a745", "icon": "✅", "label": "Spełnione"},
    "WARNING": {"color": "#ffc107", "icon": "⚠️", "label": "Do poprawy"},
    "FAIL": {"color": "#dc3545", "icon": "❌", "label": "Błąd"},
}

# Konfiguracja priorytetów
PRIORITY_CONFIG = {
    "CRITICAL": {"color": "#dc3545", "icon": "🔴", "weight": 3.0},
    "HIGH": {"color": "#fd7e14", "icon": "🟠", "weight": 2.0},
    "MEDIUM": {"color": "#ffc107", "icon": "🟡", "weight": 1.0},
}
