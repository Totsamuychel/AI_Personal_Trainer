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
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from matplotlib import patches
import numpy as np

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile
from ai_trainer.db import crud, database
from ai_trainer.bot.utils import send_long_message
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

async def get_lang(state: FSMContext, telegram_id: str) -> str:
    data = await state.get_data()
    lang = data.get("language")
    if not lang:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            lang = user.language if user else "ru"
            await state.update_data(language=lang)
    return lang

def _apply_sleek_style(ax, fig):
    """Applies a sleek dark theme to a specific axes/figure without touching global rcParams."""
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(CARD_COLOR)
    
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['top'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['right'].set_color(GRID_COLOR)
    
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.tick_params(axis='x', colors=SUBTEXT_COLOR)
    ax.tick_params(axis='y', colors=SUBTEXT_COLOR)
    
    ax.grid(True, color=GRID_COLOR, alpha=0.5)
    
    for text in ax.get_xticklabels() + ax.get_yticklabels():
        text.set_color(SUBTEXT_COLOR)
        
    if ax.get_legend():
        legend = ax.get_legend()
        legend.get_frame().set_facecolor(CARD_COLOR)
        legend.get_frame().set_edgecolor(GRID_COLOR)
        for text in legend.get_texts():
            text.set_color(TEXT_COLOR)

async def _generate_1rm_chart(user_id: int, exercise_name: str, lang: str = "ru") -> Optional[bytes]:
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

        # Use crud.calculate_1rm for consistency
        best_1rm = 0
        for r, w in zip(reps_list, weights_list):
            best_1rm = max(best_1rm, crud.calculate_1rm(w, r))
        
        if best_1rm > 0:
            dates.append(date)
            one_rms.append(best_1rm)
            max_weights.append(max(weights_list) if weights_list else 0)

    if len(dates) < 2:
        return None

    fig = Figure(figsize=(10, 5.5), dpi=120)
    ax = fig.add_subplot(111)

    label_1rm = "Расч. 1RM" if lang == "ru" else "Est. 1RM"
    label_max = "Макс. вес" if lang == "ru" else "Max weight"
    label_trend = "Тренд" if lang == "ru" else "Trend"

    # Main 1RM line with gradient fill
    ax.plot(dates, one_rms, color=ACCENT_1, linewidth=2.5, marker="o",
            markersize=6, markerfacecolor=ACCENT_1, markeredgecolor=BG_COLOR,
            markeredgewidth=1.5, label=label_1rm, zorder=5)
    ax.fill_between(dates, one_rms, alpha=0.08, color=ACCENT_1)

    # Max weight line
    ax.plot(dates, max_weights, color=ACCENT_3, linewidth=1.5, marker="s",
            markersize=4, markerfacecolor=ACCENT_3, markeredgecolor=BG_COLOR,
            alpha=0.7, label=label_max, zorder=4)

    # Trend line (linear regression)
    if len(dates) >= 3:
        x_numeric = np.array([(d - dates[0]).total_seconds() for d in dates])
        coeffs = np.polyfit(x_numeric, one_rms, 1)
        trend_y = np.polyval(coeffs, x_numeric)
        ax.plot(dates, trend_y, color=ACCENT_2, linewidth=1.5,
                linestyle="--", alpha=0.6, label=label_trend)

        # Calculate weekly progress
        if x_numeric[-1] > 0:
            weekly_gain = coeffs[0] * 7 * 86400  # slope * seconds_in_week
            progress_text = f"+{weekly_gain:.1f}" if weekly_gain >= 0 else f"{weekly_gain:.1f}"
        else:
            progress_text = "N/A"
    else:
        progress_text = "N/A"

    # Annotations
    weight_unit = "кг" if lang == "ru" else "kg"
    ax.annotate(f"{one_rms[-1]} {weight_unit}",
                xy=(dates[-1], one_rms[-1]),
                xytext=(10, 15), textcoords="offset points",
                fontsize=13, fontweight="bold", color=ACCENT_1,
                arrowprops=dict(arrowstyle="->", color=ACCENT_1, lw=1.2))

    # Title & Labels
    title = f"📈 Динамика 1RM — {exercise_name}" if lang == "ru" else f"📈 1RM Trend — {exercise_name}"
    ax.set_title(title, fontsize=16, fontweight="bold", pad=15, color=TEXT_COLOR)
    ax.set_xlabel("Дата" if lang == "ru" else "Date", fontsize=11)
    ax.set_ylabel("Вес (" + weight_unit + ")", fontsize=11)

    # Stats box
    if lang == "ru":
        stats_text = (
            f"Текущий 1RM: {one_rms[-1]} кг\n"
            f"Макс 1RM: {max(one_rms)} кг\n"
            f"Прогресс/нед: {progress_text} кг"
        )
    else:
        stats_text = (
            f"Current 1RM: {one_rms[-1]} kg\n"
            f"Max 1RM: {max(one_rms)} kg\n"
            f"Weekly gain: {progress_text} kg"
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

    _apply_sleek_style(ax, fig)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG_COLOR)
    buf.seek(0)
    return buf.read()


async def _generate_volume_chart(user_id: int, lang: str = "ru") -> Optional[bytes]:
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

    fig = Figure(figsize=(10, 5.5), dpi=120)
    ax = fig.add_subplot(111)

    # Bar chart
    bar_width = max(0.5, min(2.0, 30 / len(dates)))
    bars = ax.bar(dates, volumes, width=bar_width, color=colors, alpha=0.85,
                  edgecolor=BG_COLOR, linewidth=0.5, zorder=4)

    # Moving average line
    if len(volumes) >= 3:
        window = min(5, len(volumes))
        moving_avg = np.convolve(volumes, np.ones(window) / window, mode="valid")
        ma_dates = dates[window - 1:]
        label_ma = f"Скольз. сред. ({window})" if lang == "ru" else f"Moving avg ({window})"
        ax.plot(ma_dates, moving_avg, color="#f0f6fc", linewidth=2,
                linestyle="-", alpha=0.7, label=label_ma, zorder=5)

    # Title & Labels
    title = "📊 Объём тренировок (тоннаж)" if lang == "ru" else "📊 Training Volume (Tonnage)"
    ax.set_title(title, fontsize=16, fontweight="bold", pad=15, color=TEXT_COLOR)
    ax.set_xlabel("Дата" if lang == "ru" else "Date", fontsize=11)
    ax.set_ylabel("Объём (кг × повторы)" if lang == "ru" else "Volume (kg × reps)", fontsize=11)

    # Legend for workout types
    unique_types = list(set(types_))
    legend_handles = [patches.Rectangle((0, 0), 1, 1, fc=type_colors.get(t, ACCENT_1), alpha=0.85)
                      for t in unique_types]
    ax.legend(legend_handles, unique_types, loc="upper left", framealpha=0.9)

    # Stats
    avg_vol = sum(volumes) / len(volumes)
    max_vol = max(volumes)
    if lang == "ru":
        stats_text = (
            f"Ср. объём: {avg_vol:,.0f} кг\n"
            f"Макс объём: {max_vol:,.0f} кг\n"
            f"Тренировок: {len(volumes)}"
        )
    else:
        stats_text = (
            f"Avg Volume: {avg_vol:,.0f} kg\n"
            f"Max Volume: {max_vol:,.0f} kg\n"
            f"Workouts: {len(volumes)}"
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
    
    _apply_sleek_style(ax, fig)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG_COLOR)
    buf.seek(0)
    return buf.read()


# ─── Telegram Handlers ───

@router.message(F.text.in_(["/progress", "📈 Прогресс", "📈 Progress"]))
async def cmd_progress(message: types.Message, state: FSMContext):
    """Entry point for /progress — shows menu with chart options."""
    telegram_id = str(message.from_user.id)
    lang = await get_lang(state, telegram_id)

    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            msg = "Сначала зарегистрируйся с помощью /start" if lang == "ru" else "Please register first using /start"
            await message.answer(msg)
            return

        exercises = await crud.get_user_exercises(db, user.id)
        records = await crud.get_all_personal_records(db, user.id)

    if not exercises and not records:
        msg = ("📊 У тебя пока нет записанных тренировок.\n"
               "Используй /workout чтобы записать первую тренировку!") if lang == "ru" else \
              ("📊 You don't have any logged workouts yet.\n"
               "Use /workout to log your first training!")
        await message.answer(msg)
        return

    builder = InlineKeyboardBuilder()
    if lang == "ru":
        builder.button(text="📊 Объём тренировок", callback_data="progress_volume")
        for ex in exercises[:8]:
            builder.button(text=f"📈 {ex}", callback_data=f"progress_1rm_{ex}")
        builder.button(text="🏆 Личные рекорды", callback_data="progress_records")
    else:
        builder.button(text="📊 Training Volume", callback_data="progress_volume")
        for ex in exercises[:8]:
            builder.button(text=f"📈 {ex}", callback_data=f"progress_1rm_{ex}")
        builder.button(text="🏆 Personal Records", callback_data="progress_records")
        
    builder.adjust(1)

    # Build summary text
    if lang == "ru":
        summary = "📊 **Прогресс и аналитика**\n\n"
        if records:
            summary += "🏆 **Текущие рекорды (1RM):**\n"
            for pr in records[:6]:
                summary += f"  • {pr.exercise}: **{pr.one_rm_est} кг** ({pr.weight_kg}×{pr.reps})\n"
            summary += "\n"
        summary += "Выбери, что хочешь увидеть:"
    else:
        summary = "📊 **Progress and Analytics**\n\n"
        if records:
            summary += "🏆 **Current Records (1RM):**\n"
            for pr in records[:6]:
                summary += f"  • {pr.exercise}: **{pr.one_rm_est} kg** ({pr.weight_kg}×{pr.reps})\n"
            summary += "\n"
        summary += "Choose what you want to see:"

    await message.answer(summary, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "progress_volume")
async def show_volume_chart(callback: types.CallbackQuery, state: FSMContext):
    """Generates and sends the volume chart."""
    telegram_id = str(callback.from_user.id)
    lang = await get_lang(state, telegram_id)
    
    wait_msg = "⏳ Генерирую график..." if lang == "ru" else "⏳ Generating chart..."
    await callback.answer(wait_msg)

    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            return

    chart_bytes = await _generate_volume_chart(user.id, lang)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="volume_chart.png")
        if lang == "ru":
            caption = ("📊 **Объём тренировок** — суммарный тоннаж (вес × повторы) за каждую тренировку.\n"
                       "Цвета показывают тип тренировки (Push/Pull/Legs).")
        else:
            caption = ("📊 **Training Volume** — total tonnage (weight × reps) per workout.\n"
                       "Colors indicate workout type (Push/Pull/Legs).")
                       
        await callback.message.answer_photo(photo, caption=caption, parse_mode="Markdown")
    else:
        msg = ("📊 Недостаточно данных для графика объёма.\nНужно минимум 2 тренировки.") if lang == "ru" else \
              ("📊 Not enough data for volume chart.\nNeed at least 2 workouts.")
        await callback.message.answer(msg)


@router.callback_query(F.data.startswith("progress_1rm_"))
async def show_1rm_chart(callback: types.CallbackQuery, state: FSMContext):
    """Generates and sends the 1RM chart for a specific exercise."""
    exercise_name = callback.data.replace("progress_1rm_", "")
    telegram_id = str(callback.from_user.id)
    lang = await get_lang(state, telegram_id)
    
    wait_msg = f"⏳ Генерирую 1RM для {exercise_name}..." if lang == "ru" else f"⏳ Generating 1RM for {exercise_name}..."
    await callback.answer(wait_msg)

    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            return

    chart_bytes = await _generate_1rm_chart(user.id, exercise_name, lang)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="1rm_chart.png")
        if lang == "ru":
            caption = (f"📈 **{exercise_name}** — динамика расчётного 1RM (формула Epley).\n"
                       f"Синяя линия — 1RM, оранжевая — макс. рабочий вес, пунктир — тренд.")
        else:
            caption = (f"📈 **{exercise_name}** — estimated 1RM trend (Epley formula).\n"
                       f"Blue line — 1RM, orange — max working weight, dashed — trend.")
                       
        await callback.message.answer_photo(photo, caption=caption, parse_mode="Markdown")
    else:
        msg = (f"📈 Недостаточно данных по '{exercise_name}'.\nНужно минимум 2 записи.") if lang == "ru" else \
              (f"📈 Not enough data for '{exercise_name}'.\nNeed at least 2 logs.")
        await callback.message.answer(msg)


@router.callback_query(F.data == "progress_records")
async def show_records(callback: types.CallbackQuery, state: FSMContext):
    """Shows all personal records in text format."""
    telegram_id = str(callback.from_user.id)
    lang = await get_lang(state, telegram_id)
    await callback.answer()

    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            return
        records = await crud.get_all_personal_records(db, user.id)

    if not records:
        msg = "🏆 Личные рекорды пока не установлены." if lang == "ru" else "🏆 Personal records not established yet."
        await callback.message.answer(msg)
        return

    if lang == "ru":
        text = "🏆 **Личные рекорды (1RM)**\n\n"
        for pr in records:
            date_str = pr.date.strftime("%d.%m.%Y") if pr.date else "—"
            text += (
                f"**{pr.exercise}**\n"
                f"  💪 1RM: **{pr.one_rm_est} кг**\n"
                f"  🏋️ Лучший: {pr.weight_kg} кг × {pr.reps} повт.\n"
                f"  📅 Дата: {date_str}\n\n"
            )
    else:
        text = "🏆 **Personal Records (1RM)**\n\n"
        for pr in records:
            date_str = pr.date.strftime("%d.%m.%Y") if pr.date else "—"
            text += (
                f"**{pr.exercise}**\n"
                f"  💪 1RM: **{pr.one_rm_est} kg**\n"
                f"  🏋️ Best: {pr.weight_kg} kg × {pr.reps} reps\n"
                f"  📅 Date: {date_str}\n\n"
            )

    await send_long_message(callback.message, text, parse_mode="Markdown")
