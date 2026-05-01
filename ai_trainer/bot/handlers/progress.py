"""
Progress visualization handler — generates 1RM trend and volume charts,
sends them as PNG images to the Telegram user.
"""
import io
import os
from datetime import datetime
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import numpy as np

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile
from ai_trainer.db import crud, database
from loguru import logger


router = Router()

# ─── Color palette (dark theme, premium look) ───
BG_COLOR = "#0d1117"
CARD_COLOR = "#161b22"
ACCENT_1 = "#58a6ff"      # Blue
ACCENT_2 = "#3fb950"      # Green
ACCENT_3 = "#f78166"      # Orange
ACCENT_4 = "#d2a8ff"      # Purple
GRID_COLOR = "#21262d"
TEXT_COLOR = "#c9d1d9"
SUBTEXT_COLOR = "#8b949e"


def _setup_dark_style():
    """Applies a sleek dark theme to matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": CARD_COLOR,
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.alpha": 0.5,
        "xtick.color": SUBTEXT_COLOR,
        "ytick.color": SUBTEXT_COLOR,
        "text.color": TEXT_COLOR,
        "font.family": "sans-serif",
        "font.size": 11,
        "legend.facecolor": CARD_COLOR,
        "legend.edgecolor": GRID_COLOR,
        "legend.fontsize": 10,
    })


def _calculate_1rm_from_log(reps_list: list, weights_list: list) -> float:
    """Calculates estimated 1RM from exercise log data (Epley formula)."""
    best_1rm = 0
    for r, w in zip(reps_list, weights_list):
        if r > 0 and w > 0:
            if r == 1:
                est = w
            else:
                est = w * (1 + r / 30.0)
            best_1rm = max(best_1rm, est)
    return round(best_1rm, 1)


async def _generate_1rm_chart(user_id: int, exercise_name: str) -> Optional[bytes]:
    """Generates a 1RM trend chart for a specific exercise. Returns PNG bytes."""
    async with database.db_session() as db:
        rows = await crud.get_exercise_progress_with_dates(db, user_id, exercise_name, limit=50)

    if not rows or len(rows) < 2:
        return None

    dates = []
    one_rms = []
    max_weights = []

    for row in rows:
        date, name, sets, reps, weight_kg = row
        reps_list = reps if isinstance(reps, list) else [0]
        weights_list = weight_kg if isinstance(weight_kg, list) else [0]

        est_1rm = _calculate_1rm_from_log(reps_list, weights_list)
        if est_1rm > 0:
            dates.append(date)
            one_rms.append(est_1rm)
            max_weights.append(max(weights_list) if weights_list else 0)

    if len(dates) < 2:
        return None

    _setup_dark_style()
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=120)

    # Main 1RM line with gradient fill
    ax.plot(dates, one_rms, color=ACCENT_1, linewidth=2.5, marker="o",
            markersize=6, markerfacecolor=ACCENT_1, markeredgecolor=BG_COLOR,
            markeredgewidth=1.5, label="Расч. 1RM", zorder=5)
    ax.fill_between(dates, one_rms, alpha=0.08, color=ACCENT_1)

    # Max weight line
    ax.plot(dates, max_weights, color=ACCENT_3, linewidth=1.5, marker="s",
            markersize=4, markerfacecolor=ACCENT_3, markeredgecolor=BG_COLOR,
            alpha=0.7, label="Макс. вес", zorder=4)

    # Trend line (linear regression)
    if len(dates) >= 3:
        x_numeric = np.array([(d - dates[0]).total_seconds() for d in dates])
        coeffs = np.polyfit(x_numeric, one_rms, 1)
        trend_y = np.polyval(coeffs, x_numeric)
        ax.plot(dates, trend_y, color=ACCENT_2, linewidth=1.5,
                linestyle="--", alpha=0.6, label="Тренд")

        # Calculate weekly progress
        if x_numeric[-1] > 0:
            weekly_gain = coeffs[0] * 7 * 86400  # slope * seconds_in_week
            progress_text = f"+{weekly_gain:.1f}" if weekly_gain >= 0 else f"{weekly_gain:.1f}"
        else:
            progress_text = "N/A"
    else:
        progress_text = "N/A"

    # Annotations
    ax.annotate(f"{one_rms[-1]} кг",
                xy=(dates[-1], one_rms[-1]),
                xytext=(10, 15), textcoords="offset points",
                fontsize=13, fontweight="bold", color=ACCENT_1,
                arrowprops=dict(arrowstyle="->", color=ACCENT_1, lw=1.2))

    # Title & Labels
    ax.set_title(f"📈 Динамика 1RM — {exercise_name}",
                 fontsize=16, fontweight="bold", pad=15, color=TEXT_COLOR)
    ax.set_xlabel("Дата", fontsize=11)
    ax.set_ylabel("Вес (кг)", fontsize=11)

    # Stats box
    stats_text = (
        f"Текущий 1RM: {one_rms[-1]} кг\n"
        f"Макс 1RM: {max(one_rms)} кг\n"
        f"Прогресс/нед: {progress_text} кг"
    )
    props = dict(boxstyle="round,pad=0.5", facecolor=BG_COLOR, edgecolor=GRID_COLOR, alpha=0.9)
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment="top", bbox=props, color=TEXT_COLOR)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))
    fig.autofmt_xdate(rotation=30)

    ax.legend(loc="lower right", framealpha=0.9)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


async def _generate_volume_chart(user_id: int) -> Optional[bytes]:
    """Generates a training volume chart (total tonnage per session). Returns PNG bytes."""
    async with database.db_session() as db:
        volume_data = await crud.get_volume_history(db, user_id, limit=30)

    if not volume_data or len(volume_data) < 2:
        return None

    dates = [v["date"] for v in volume_data]
    volumes = [v["total_volume"] for v in volume_data]
    types_ = [v["workout_type"] for v in volume_data]

    # Color by workout type
    type_colors = {
        "Push": ACCENT_1,
        "Pull": ACCENT_2,
        "Legs": ACCENT_3,
        "Full Body": ACCENT_4,
    }
    colors = [type_colors.get(t, ACCENT_1) for t in types_]

    _setup_dark_style()
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=120)

    # Bar chart
    bar_width = max(0.5, min(2.0, 30 / len(dates)))
    bars = ax.bar(dates, volumes, width=bar_width, color=colors, alpha=0.85,
                  edgecolor=BG_COLOR, linewidth=0.5, zorder=4)

    # Moving average line
    if len(volumes) >= 3:
        window = min(5, len(volumes))
        moving_avg = np.convolve(volumes, np.ones(window) / window, mode="valid")
        ma_dates = dates[window - 1:]
        ax.plot(ma_dates, moving_avg, color="#f0f6fc", linewidth=2,
                linestyle="-", alpha=0.7, label=f"Скольз. сред. ({window})", zorder=5)

    # Title & Labels
    ax.set_title("📊 Объём тренировок (тоннаж)",
                 fontsize=16, fontweight="bold", pad=15, color=TEXT_COLOR)
    ax.set_xlabel("Дата", fontsize=11)
    ax.set_ylabel("Объём (кг × повторы)", fontsize=11)

    # Legend for workout types
    unique_types = list(set(types_))
    legend_handles = [plt.Rectangle((0, 0), 1, 1, fc=type_colors.get(t, ACCENT_1), alpha=0.85)
                      for t in unique_types]
    ax.legend(legend_handles, unique_types, loc="upper left", framealpha=0.9)

    # Stats
    avg_vol = sum(volumes) / len(volumes)
    max_vol = max(volumes)
    stats_text = (
        f"Ср. объём: {avg_vol:,.0f} кг\n"
        f"Макс объём: {max_vol:,.0f} кг\n"
        f"Тренировок: {len(volumes)}"
    )
    props = dict(boxstyle="round,pad=0.5", facecolor=BG_COLOR, edgecolor=GRID_COLOR, alpha=0.9)
    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment="top", horizontalalignment="right",
            bbox=props, color=TEXT_COLOR)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))
    fig.autofmt_xdate(rotation=30)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─── Telegram Handlers ───

@router.message(F.text == "/progress")
async def cmd_progress(message: types.Message):
    """Entry point for /progress — shows menu with chart options."""
    telegram_id = str(message.from_user.id)

    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await message.answer("Сначала зарегистрируйся с помощью /start")
            return

        exercises = await crud.get_user_exercises(db, user.id)
        records = await crud.get_all_personal_records(db, user.id)

    if not exercises and not records:
        await message.answer(
            "📊 У тебя пока нет записанных тренировок.\n"
            "Используй /workout чтобы записать первую тренировку!"
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Объём тренировок", callback_data="progress_volume")

    # Show exercises for 1RM charts
    for ex in exercises[:8]:  # Limit to 8 to keep keyboard reasonable
        builder.button(text=f"📈 {ex}", callback_data=f"progress_1rm_{ex}")

    builder.button(text="🏆 Личные рекорды", callback_data="progress_records")
    builder.adjust(1)

    # Build summary text
    summary = "📊 **Прогресс и аналитика**\n\n"
    if records:
        summary += "🏆 **Текущие рекорды (1RM):**\n"
        for pr in records[:6]:
            summary += f"  • {pr.exercise}: **{pr.one_rm_est} кг** ({pr.weight_kg}×{pr.reps})\n"
        summary += "\n"

    summary += "Выбери, что хочешь увидеть:"

    await message.answer(summary, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "progress_volume")
async def show_volume_chart(callback: types.CallbackQuery):
    """Generates and sends the volume chart."""
    await callback.answer("⏳ Генерирую график...")

    telegram_id = str(callback.from_user.id)
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await callback.message.answer("Пользователь не найден.")
            return

    chart_bytes = await _generate_volume_chart(user.id)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="volume_chart.png")
        await callback.message.answer_photo(
            photo,
            caption="📊 **Объём тренировок** — суммарный тоннаж (вес × повторы) за каждую тренировку.\n"
                    "Цвета показывают тип тренировки (Push/Pull/Legs).",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            "📊 Недостаточно данных для графика объёма.\n"
            "Нужно минимум 2 тренировки."
        )


@router.callback_query(F.data.startswith("progress_1rm_"))
async def show_1rm_chart(callback: types.CallbackQuery):
    """Generates and sends the 1RM chart for a specific exercise."""
    exercise_name = callback.data.replace("progress_1rm_", "")
    await callback.answer(f"⏳ Генерирую 1RM для {exercise_name}...")

    telegram_id = str(callback.from_user.id)
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await callback.message.answer("Пользователь не найден.")
            return

    chart_bytes = await _generate_1rm_chart(user.id, exercise_name)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="1rm_chart.png")
        await callback.message.answer_photo(
            photo,
            caption=f"📈 **{exercise_name}** — динамика расчётного 1RM (формула Epley).\n"
                    f"Синяя линия — 1RM, оранжевая — макс. рабочий вес, пунктир — тренд.",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            f"📈 Недостаточно данных по '{exercise_name}'.\n"
            f"Нужно минимум 2 записи с этим упражнением."
        )


@router.callback_query(F.data == "progress_records")
async def show_records(callback: types.CallbackQuery):
    """Shows all personal records in text format."""
    await callback.answer()

    telegram_id = str(callback.from_user.id)
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await callback.message.answer("Пользователь не найден.")
            return

        records = await crud.get_all_personal_records(db, user.id)

    if not records:
        await callback.message.answer("🏆 Личные рекорды пока не установлены.")
        return

    text = "🏆 **Личные рекорды (1RM)**\n\n"
    for pr in records:
        date_str = pr.date.strftime("%d.%m.%Y") if pr.date else "—"
        text += (
            f"**{pr.exercise}**\n"
            f"  💪 1RM: **{pr.one_rm_est} кг**\n"
            f"  🏋️ Лучший: {pr.weight_kg} кг × {pr.reps} повт.\n"
            f"  📅 Дата: {date_str}\n\n"
        )

    await callback.message.answer(text, parse_mode="Markdown")
