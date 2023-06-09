import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
import sqlite3

# Загрузка JSON-файла
with open('cats.json', 'r') as file:
    rubricator_data = json.load(file)

# Создание объектов бота и диспетчера
bot = Bot(token='6178296096:AAE6Rn_8B7mLb9_8L43OIBWR4l3xROjPcMU')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

db = sqlite3.connect('users.db')
cursor = db.cursor()

# Создание кнопок на основе JSON-данных
def create_inline_buttons(data):
    buttons = []
    for item in data:
        button = types.InlineKeyboardButton(item['title'], callback_data=str(item['id']))
        buttons.append(button)
    return buttons


# Обработчик команды /start
@dp.message_handler(Command('start'))
async def start_command(message: types.Message):
    await message.reply('Бот приветствует тебя! 🙌\n'
                        'Чтобы начать следить за объявлениями, выберите нужную вам категорию при помощи кнопок ниже. ⬇')

    # Check if the user already exists in the database
    cursor.execute("SELECT id FROM viewers WHERE login = ?", (message.from_user.username,))
    if cursor.fetchone() is None:
        data = (message.from_user.username, message.from_user.id, message.chat.id, '')
        cursor.execute("INSERT INTO viewers VALUES (null, ?, ?, ?, ?);", data)
        db.commit()
    # Получение первого уровня категорий
    categories = rubricator_data['result']['children']

    # Создание инлайн клавиатуры с кнопками категорий
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = create_inline_buttons(categories)
    keyboard.add(*buttons)

    # Отправка клавиатуры пользователю
    await message.reply('Выберите категорию:', reply_markup=keyboard)


# Обработчик инлайн-кнопок
@dp.callback_query_handler()
async def inline_button_callback(query: types.CallbackQuery, state: FSMContext):
    category_id = int(query.data)

    # Поиск категории в JSON-данных по идентификатору
    def find_category_by_id(category_id, data):
        for item in data:
            if item['id'] == category_id:
                return item
            if 'children' in item:
                result = find_category_by_id(category_id, item['children'])
                if result:
                    return result
        return None

    category = find_category_by_id(category_id, rubricator_data['result']['children'])

    if category:
        # Проверка, есть ли дочерние категории
        if 'children' in category:
            # Создание инлайн клавиатуры с кнопками дочерних категорий
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            buttons = create_inline_buttons(category['children'])
            keyboard.add(*buttons)

            # Редактирование сообщения с новой клавиатурой
            await query.message.edit_text('Выберите категорию:', reply_markup=keyboard)
        else:
            # Выбрана конечная категория, можно выполнять нужные действия
            navigation_attributes = category['navigation'].get('attributes', [])
            attribute_values = ', '.join(str(attr['value']) for attr in navigation_attributes)

            # Получение цепочки выбранных категорий
            category_chain = []
            current_category = category
            while current_category:
                category_chain.insert(0, current_category['title'])
                parent_id = current_category.get('parentId')
                current_category = find_category_by_id(parent_id, rubricator_data['result']['children'])

            category_chain_text = ' - '.join(category_chain)

            answer_text = f'Выбрана категория: {category_chain_text}, атрибуты навигации: {attribute_values}'
            await query.answer(answer_text)

    # Ответить на CallbackQuery, чтобы убрать "часики" в интерфейсе
    await query.answer()



# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)

