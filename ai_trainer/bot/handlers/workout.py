from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from ai_trainer.db import crud, database
from ai_trainer.sheets.client import SheetsClient
from loguru import logger

router = Router()
sheets = SheetsClient()

class WorkoutStates(StatesGroup):
    waiting_for_feeling = State() # Как самочувствие?
    waiting_for_pain = State()    # Есть ли боли?
    choosing_type = State()
    logging_exercise = State()
    entering_sets = State()
    entering_weight = State()
    entering_reps = State()
    adding_more = State()
    entering_duration = State()

async def get_lang(state: FSMContext, telegram_id: str) -> str:
    data = await state.get_data()
    lang = data.get("language")
    if not lang:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            lang = user.language if user else "ru"
            await state.update_data(language=lang)
    return lang

@router.message(F.text.in_(["/workout", "🏋️ Тренировка", "🏋️ Workout"]))
async def cmd_workout(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    
    msg = "Прежде чем начнем, как твое самочувствие сегодня? (устал/бодр/нормально)"
    if lang == "en":
        msg = "Before we start, how are you feeling today? (tired/fresh/normal)"
        
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.waiting_for_feeling)

@router.message(WorkoutStates.waiting_for_feeling)
async def process_feeling(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    await state.update_data(feeling=message.text)
    
    msg = "Есть ли какие-то боли или дискомфорт в суставах/мышцах?"
    if lang == "en":
        msg = "Do you have any pain or discomfort in your joints/muscles?"
        
    await message.answer(msg)
    await state.set_state(WorkoutStates.waiting_for_pain)

@router.message(WorkoutStates.waiting_for_pain)
async def process_pain(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    await state.update_data(pain=message.text)
    
    builder = ReplyKeyboardBuilder()
    builder.button(text="Push")
    builder.button(text="Pull")
    builder.button(text="Legs")
    builder.button(text="Full Body")
    builder.adjust(2)
    
    msg = "Понял. Теперь выбери тип тренировки:"
    if lang == "en":
        msg = "Got it. Now choose workout type:"
        
    await message.answer(msg, reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(WorkoutStates.choosing_type)

@router.message(WorkoutStates.choosing_type)
async def process_workout_type(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    await state.update_data(workout_type=message.text, exercises=[])
    
    msg = "Введи название первого упражнения:"
    if lang == "en":
        msg = "Enter the name of the first exercise:"
        
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.logging_exercise)

@router.message(WorkoutStates.logging_exercise)
async def process_exercise_name(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    await state.update_data(current_exercise=message.text)
    
    msg = f"Сколько подходов выполнил в '{message.text}'?"
    if lang == "en":
        msg = f"How many sets did you do for '{message.text}'?"
        
    await message.answer(msg)
    await state.set_state(WorkoutStates.entering_sets)

@router.message(WorkoutStates.entering_sets)
async def process_sets(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    if not message.text.isdigit():
        msg = "Введи число."
        if lang == "en":
            msg = "Please enter a number."
        await message.answer(msg)
        return
        
    await state.update_data(current_sets=int(message.text))
    
    msg = "Какой вес использовал (в кг)? Если были разные веса, введи средний или основной."
    if lang == "en":
        msg = "What weight did you use (in kg)? If weights varied, enter the average or main weight."
        
    await message.answer(msg)
    await state.set_state(WorkoutStates.entering_weight)

@router.message(WorkoutStates.entering_weight)
async def process_weight(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(current_weight=weight)
        
        msg = "Сколько повторений сделал в каждом подходе? (Введи одно число, если везде одинаково)"
        if lang == "en":
            msg = "How many reps did you do in each set? (Enter one number if consistent)"
            
        await message.answer(msg)
        await state.set_state(WorkoutStates.entering_reps)
    except ValueError:
        msg = "Введи число."
        if lang == "en":
            msg = "Please enter a number."
        await message.answer(msg)

@router.message(WorkoutStates.entering_reps)
async def process_reps(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    data = await state.get_data()
    sets = data['current_sets']
    reps_text = message.text
    
    try:
        # Simple parsing: if one number, repeat it for all sets
        if reps_text.isdigit():
            reps = [int(reps_text)] * sets
        else:
            # Try to parse comma or space separated
            reps = [int(x.strip()) for x in reps_text.replace(',', ' ').split() if x.strip().isdigit()]
            if not reps:
                raise ValueError("No reps found")
            if len(reps) < sets:
                reps.extend([reps[-1]] * (sets - len(reps)))
            elif len(reps) > sets:
                reps = reps[:sets]
    except Exception:
        msg = "Я не смог распознать числа. Пожалуйста, введи количество повторений (например, '10, 10, 8')"
        if lang == "en":
            msg = "I couldn't recognize the numbers. Please enter the number of reps (e.g., '10, 10, 8')"
        await message.answer(msg)
        return
    
    exercise = {
        "name": data['current_exercise'],
        "sets": sets,
        "reps": reps,
        "weight_kg": [data['current_weight']] * sets
    }
    
    data['exercises'].append(exercise)
    await state.update_data(exercises=data['exercises'])
    
    builder = ReplyKeyboardBuilder()
    if lang == "ru":
        builder.button(text="Добавить еще")
        builder.button(text="Завершить")
        msg = "Упражнение записано. Что дальше?"
    else:
        builder.button(text="Add more")
        builder.button(text="Finish")
        msg = "Exercise logged. What's next?"
    
    await message.answer(msg, reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(WorkoutStates.adding_more)

@router.message(WorkoutStates.adding_more, F.text.in_(["Добавить еще", "Add more"]))
async def add_more(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    
    msg = "Введи название упражнения:"
    if lang == "en":
        msg = "Enter exercise name:"
        
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.logging_exercise)

@router.message(WorkoutStates.adding_more, F.text.in_(["Завершить", "Finish"]))
async def ask_duration(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    
    msg = "Сколько минут длилась тренировка?"
    if lang == "en":
        msg = "How many minutes did the workout last?"
        
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WorkoutStates.entering_duration)

@router.message(WorkoutStates.entering_duration)
async def finish_workout(message: types.Message, state: FSMContext):
    lang = await get_lang(state, str(message.from_user.id))
    if not message.text.isdigit():
        msg = "Пожалуйста, введи количество минут числом."
        if lang == "en":
            msg = "Please enter the number of minutes."
        await message.answer(msg)
        return
        
    duration = int(message.text)
    data = await state.get_data()
    telegram_id = str(message.from_user.id)
    
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            
            if not user:
                msg = "Ошибка: пользователь не найден."
                if lang == "en":
                    msg = "Error: user not found."
                await message.answer(msg)
                await state.clear()
                return
            
            workout_data = {
                "workout_type": data['workout_type'],
                "duration_min": duration,
                "notes": f"Feeling: {data.get('feeling', 'N/A')}. Pain: {data.get('pain', 'N/A')}"
            }
            await crud.create_workout_session(db, user.id, workout_data, data['exercises'])
            
            # Correct PR logic: find the best 1RM from all sets of all exercises in this session
            for ex in data['exercises']:
                best_1rm = 0
                best_weight = 0
                best_reps = 0
                
                for w, r in zip(ex['weight_kg'], ex['reps']):
                    current_1rm = crud.calculate_1rm(w, r)
                    if current_1rm > best_1rm:
                        best_1rm = current_1rm
                        best_weight = w
                        best_reps = r
                
                if best_1rm > 0:
                    await crud.update_personal_record(db, user.id, ex['name'], best_weight, best_reps)
            
            # Sync to Google Sheets
            await sheets.log_workout(user.name, {
                "workout_type": data['workout_type'],
                "exercises": data['exercises']
            })
        
        success_msg = f"✅ Тренировка ({duration} мин) сохранена и синхронизирована с Google Таблицей! Отличная работа."
        if lang == "en":
            success_msg = f"✅ Workout ({duration} min) saved and synced with Google Sheet! Great job."
            
        from ai_trainer.bot.keyboards.main_menu import get_main_menu
        await message.answer(success_msg, reply_markup=get_main_menu(lang))
        
    except Exception as e:
        logger.error(f"Error saving workout: {e}")
        error_msg = "Произошла ошибка при сохранении тренировки."
        if lang == "en":
            error_msg = "An error occurred while saving the workout."
        await message.answer(error_msg)
    finally:
        await state.clear()
