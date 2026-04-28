from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from ai_trainer.db import crud, database
from loguru import logger

router = Router()

class WorkoutStates(StatesGroup):
    choosing_type = State()
    logging_exercise = State()
    entering_sets = State()
    entering_weight = State()
    entering_reps = State()
    adding_more = State()
    entering_duration = State()

@router.message(F.text == "/workout")
async def cmd_workout(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.button(text="Push")
    builder.button(text="Pull")
    builder.button(text="Legs")
    builder.button(text="Full Body")
    builder.adjust(2)
    
    await message.answer("Выбери тип тренировки:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(WorkoutStates.choosing_type)

@router.message(WorkoutStates.choosing_type)
async def process_workout_type(message: types.Message, state: FSMContext):
    await state.update_data(workout_type=message.text, exercises=[])
    await message.answer("Введи название первого упражнения:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.logging_exercise)

@router.message(WorkoutStates.logging_exercise)
async def process_exercise_name(message: types.Message, state: FSMContext):
    await state.update_data(current_exercise=message.text)
    await message.answer(f"Сколько подходов выполнил в '{message.text}'?")
    await state.set_state(WorkoutStates.entering_sets)

@router.message(WorkoutStates.entering_sets)
async def process_sets(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введи число.")
        return
    await state.update_data(current_sets=int(message.text))
    await message.answer("Какой вес использовал (в кг)? Если были разные веса, введи средний или основной.")
    await state.set_state(WorkoutStates.entering_weight)

@router.message(WorkoutStates.entering_weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(current_weight=weight)
        await message.answer("Сколько повторений сделал в каждом подходе? (Введи одно число, если везде одинаково)")
        await state.set_state(WorkoutStates.entering_reps)
    except ValueError:
        await message.answer("Введи число.")

@router.message(WorkoutStates.entering_reps)
async def process_reps(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sets = data['current_sets']
    reps_text = message.text
    
    # Simple parsing: if one number, repeat it for all sets
    if reps_text.isdigit():
        reps = [int(reps_text)] * sets
    else:
        # Try to parse comma or space separated
        reps = [int(x.strip()) for x in reps_text.replace(',', ' ').split() if x.strip().isdigit()]
        if len(reps) < sets:
            reps.extend([reps[-1]] * (sets - len(reps)))
    
    exercise = {
        "name": data['current_exercise'],
        "sets": sets,
        "reps": reps,
        "weight_kg": [data['current_weight']] * sets
    }
    
    data['exercises'].append(exercise)
    await state.update_data(exercises=data['exercises'])
    
    builder = ReplyKeyboardBuilder()
    builder.button(text="Добавить еще")
    builder.button(text="Завершить")
    
    await message.answer("Упражнение записано. Что дальше?", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(WorkoutStates.adding_more)

@router.message(WorkoutStates.adding_more, F.text == "Добавить еще")
async def add_more(message: types.Message, state: FSMContext):
    await message.answer("Введи название упражнения:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.logging_exercise)

@router.message(WorkoutStates.adding_more, F.text == "Завершить")
async def ask_duration(message: types.Message, state: FSMContext):
    await message.answer("Сколько минут длилась тренировка?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.entering_duration)

@router.message(WorkoutStates.entering_duration)
async def finish_workout(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи количество минут числом.")
        return
        
    duration = int(message.text)
    data = await state.get_data()
    telegram_id = str(message.from_user.id)
    
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            
            if not user:
                await message.answer("Ошибка: пользователь не найден.")
                await state.clear()
                return
            
            workout_data = {
                "workout_type": data['workout_type'],
                "duration_min": duration,
                "notes": ""
            }
            await crud.create_workout_session(db, user.id, workout_data, data['exercises'])
            
            # Update PRs
            for ex in data['exercises']:
                await crud.update_personal_record(db, user.id, ex['name'], max(ex['weight_kg']), min(ex['reps']))
                
        await message.answer(f"✅ Тренировка ({duration} мин) сохранена! Отличная работа.")
    except Exception as e:
        logger.error(f"Error saving workout: {e}")
        await message.answer("Произошла ошибка при сохранении тренировки.")
    finally:
        await state.clear()
