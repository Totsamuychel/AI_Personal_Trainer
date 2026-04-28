from langchain.tools import tool
from datetime import datetime, timedelta

PERIODIZATION_CYCLE = [
    {
        "week_type": "strength",
        "name": "💪 Силовая неделя",
        "intensity": "85-90% от 1RM",
        "sets": 4,
        "reps_range": "4-6",
        "rest_sec": 180,
    },
    {
        "week_type": "hypertrophy",
        "name": "🏗️ Гипертрофия",
        "intensity": "70-75% от 1RM",
        "sets": 4,
        "reps_range": "8-12",
        "rest_sec": 90,
    },
    {
        "week_type": "volume",
        "name": "📦 Объёмная неделя",
        "intensity": "60-65% от 1RM",
        "sets": 3,
        "reps_range": "12-15",
        "rest_sec": 60,
    },
    {
        "week_type": "deload",
        "name": "🔄 Разгрузочная неделя",
        "intensity": "50% от 1RM",
        "sets": 2,
        "reps_range": "10-12",
        "rest_sec": 60,
    },
]

@tool
def get_periodization_info(week_number: int) -> dict:
    """Возвращает параметры периодизации для указанной недели (0-3)."""
    return PERIODIZATION_CYCLE[week_number % 4]

@tool
def calculate_target_weight(one_rm: float, week_type: str) -> float:
    """Считает целевой рабочий вес на основе 1RM и типа недели."""
    intensity_map = {
        "strength": 0.875,
        "hypertrophy": 0.725,
        "volume": 0.625,
        "deload": 0.50,
    }
    intensity = intensity_map.get(week_type, 0.7)
    raw_weight = one_rm * intensity
    # Округление до 2.5 кг
    return round(raw_weight / 2.5) * 2.5
