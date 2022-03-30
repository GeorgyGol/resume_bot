"""
Основной файл бота просмотра профилей
"""

import logging
from enum import Enum, auto

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardRemove)
from aiogram.types.message import ParseMode, ContentType
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import text, bold

import dbfuncs
import keys
import serv


class STATE(Enum):
    start = auto()
    scope = auto()
    skils = auto()
    show = auto()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=keys.token)
dp = Dispatcher(bot, storage=MemoryStorage())

def scope_menu():
    scopes = dbfuncs.get_scope(log=logger)
    kb = InlineKeyboardMarkup(row_width=4)
    for s in scopes:
        if len(s) > 10:
            kb.row(InlineKeyboardButton(s, callback_data=str(s)))
        else:
            kb.insert(InlineKeyboardButton(s, callback_data=str(s)))
    kb.insert(InlineKeyboardButton('ВСЕ', callback_data='ВСЕ'))
    return kb


def skils_menu(scope=''):
    _scope = scope if scope != 'ВСЕ' else ''
    skils = dbfuncs.get_skils(log=logger, scope=_scope, table=dbfuncs.USER_TABLE)
    kb = InlineKeyboardMarkup(row_width=4)

    for s in skils:
        if len(s) > 10:
            kb.row(InlineKeyboardButton(s, callback_data=str(s)))
        else:
            kb.insert(InlineKeyboardButton(s, callback_data=str(s)))
    kb.insert(InlineKeyboardButton('ВСЕ', callback_data='ВСЕ'))
    return kb  # InlineKeyboardMarkup(row_width=3).add(*ibtns)


def main_menu():
    btn = [KeyboardButton('/help'), KeyboardButton('/scope'),
           KeyboardButton('/skils'), KeyboardButton('/show')]
    return ReplyKeyboardMarkup(resize_keyboard=True).add(*btn)


def show_menu():
    kbt = ReplyKeyboardMarkup(resize_keyboard=True).row(KeyboardButton('/prev'), KeyboardButton('/next'))
    kbt.row(KeyboardButton('/main'), KeyboardButton('/back'))
    return kbt


@dp.message_handler(commands=['start', 'main'])
async def start(message: types.Message):
    if message.chat.type == 'group':
        return

    if dbfuncs.check_user(user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE):
        _mess = "Просмотр профилей зарегестрированных пользователй"
        await bot.send_message(message.from_user.id, _mess, reply_markup=main_menu())

        dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                            values={'first_name': message.from_user.first_name,
                                    'skils': '',
                                    'scope': '',
                                    'STATE': STATE.start.value, 'PAGE': 0},
                            table=dbfuncs.SHOW_TABLE_NAME)
        # s = dbfuncs.get_user(user_id=str(message.from_user.id), table=dbfuncs.SHOW_TABLE_NAME)['STATE']

    else:
        msg = text(bold('Сначала надо завести свою карточку'),
                   'Просматривать профили могут только зарегестрированные пользователи',
                   'Регистрация тут @Users4Lbot', sep='\n')

        await bot.send_message(message.from_user.id, msg, parse_mode=ParseMode.MARKDOWN,
                               reply_markup=ReplyKeyboardRemove())


@dp.message_handler(commands=['scope'])
async def select_scope(message: types.Message):
    _mess = "Выберете сферу деятельности"
    await bot.send_message(message.from_user.id, _mess, reply_markup=scope_menu())
    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        values={'STATE': STATE.scope.value, 'PAGE': 0},
                        table=dbfuncs.SHOW_TABLE_NAME)


@dp.message_handler(commands=['skils', 'back'])
async def select_skils(message: types.Message):
    uid = message.from_user.id
    user_data = dbfuncs.get_user(user_id=str(uid), table=dbfuncs.SHOW_TABLE_NAME)

    _mess = "Выберете навыки"
    if message.get_command() == '/back':
        await bot.send_message(uid, message.get_command(), reply_markup=main_menu())
    await bot.send_message(uid, _mess, reply_markup=skils_menu(scope=user_data['scope']))
    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        values={'STATE': STATE.skils.value, 'skils': '', 'PAGE': 0},
                        table=dbfuncs.SHOW_TABLE_NAME)


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    _mess = '''<b>Просмотр пользователей</b>\n
Просматривать карточки пользователей могут только зарегестрированные пользователи. Регистрация тут:  @Users4Lbot\n
Карточки с незаполненными либо LinkedIn либо портфолио - игнорируются\n 
Просмотра пользователей - команда /show - выводит карточки по 20 штук за один раз (страницами по 20 записей)\n
Посмотреть предидущую страницу - команда /prev\n
Посмотреть следующую страницу  - команда /next\n
Перед просмотром можно выбрать <b>сферу деятельности</b> - команда /skope\n
Можно выбрать <b>только</b> одну сферу деятельности - или ВСЕ (показывает карточки по всем сферам деятельности)\n
Можно выбрать <b>перечень</b> навыков (либо определив перед этим сфету деятельности, либо не определяя) - команда /skils\n
После вызова этой команды открывается меню с существующими навыками - нажимая на соотв. навык вы добавляете его в набор выбора.\n
Чтобы сбросить выбор надо выбрать ВСЕ (самая последняя кнопка)\n
Команда /main - возврат в главное меню (на первый экран бота)\n
Команда /back - возврат на один шаг назад\n'''

    await bot.send_message(message.from_user.id, _mess, parse_mode=types.ParseMode.HTML, reply_markup=main_menu())


@dp.message_handler(commands=['show', 'prev', 'next'])
async def show(message: types.Message):
    def print_user(num, s):
        ff = lambda x: x if type(x) != float else '-x-'
        x = list()
        x.append(f'{num}. <u>{s.first_name}</u>')
        x.append('<b>сфера:</b> {}'.format(ff(s.scope)))
        x.append('<b>проф:</b> {}'.format(ff(s.prof)))
        x.append('<b>навыки:</b> {}'.format(ff(s.skils)))
        x.append('<b>LinkedIn:</b> {}'.format(ff(s.lndin)))
        x.append('<b>портфолио:</b> {}'.format(ff(s.portf)))
        x.append('______________________\n')
        return x

    PAGE_SIZE = 20

    uid = message.from_user.id
    user_data = dbfuncs.get_user(user_id=str(uid), table=dbfuncs.SHOW_TABLE_NAME)
    scope = user_data['scope'] if user_data['scope'] else 'ВСЕ'
    skils = user_data['skils'] if user_data['skils'] else 'ВСЕ'
    cur_page = user_data['PAGE'] if user_data['PAGE'] else 0
    pdfu = dbfuncs.get_users(table=dbfuncs.USER_TABLE, scope=scope, skils=skils)

    pages = int(pdfu.shape[0] / PAGE_SIZE) + (pdfu.shape[0] % PAGE_SIZE > 0)

    if message.get_command() == '/prev':
        cur_page = 0 if cur_page <= 1 else cur_page - 1

    if message.get_command() == '/next':
        cur_page = pages - 1 if cur_page >= pages - 1 else cur_page + 1

    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        values={'STATE': STATE.show.value, 'PAGE': cur_page},
                        table=dbfuncs.SHOW_TABLE_NAME)

    lstm = list()
    start_pos = int(cur_page * PAGE_SIZE)
    for i, v in pdfu.iloc[start_pos:start_pos + PAGE_SIZE].iterrows():
        lstm += print_user(start_pos + i + 1, v)

    msg = text(*lstm, text(f'Страница {cur_page+1} из {pages} '), sep='\n')
    await bot.send_message(message.from_user.id, msg, parse_mode=types.ParseMode.HTML,
                           reply_markup=show_menu(), disable_web_page_preview=True)


@dp.message_handler(commands=['stop'])
async def send_stop(message: types.Message):
    _mess = f"Пока, {message.from_user.first_name}!\nНадеюсь, еще увидимся?"
    await message.reply(_mess, reply_markup=ReplyKeyboardRemove())


@dp.callback_query_handler()
async def process_callback_bt(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    uid = callback_query.from_user.id
    user_data = dbfuncs.get_user(user_id=str(uid), table=dbfuncs.SHOW_TABLE_NAME)
    current_state = user_data['STATE']
    if current_state == STATE.scope.value:
        _mess = "Выберете навыки"
        dbfuncs.update_user(user_id=str(uid), values={'scope': callback_query.data, 'STATE': STATE.skils.value},
                            table=dbfuncs.SHOW_TABLE_NAME)
        await bot.send_message(uid, _mess, reply_markup=skils_menu(scope=callback_query.data))
    elif current_state == STATE.skils.value:
        if callback_query.data == 'ВСЕ' or user_data['skils'] == 'ВСЕ':
            skls = callback_query.data
        else:
            skls = serv.append_text(user_data['skils'], callback_query.data)

        dbfuncs.update_user(user_id=str(uid), values={'skils': skls}, table=dbfuncs.SHOW_TABLE_NAME)
        _mess = f'<b>Выберете навыки:</b>\n{skls}'
        try:
            await bot.edit_message_text(message_id=callback_query.message.message_id,
                                        chat_id=callback_query.message.chat.id, parse_mode=types.ParseMode.HTML,
                                        text=_mess, reply_markup=skils_menu(scope=user_data['scope']))
        except MessageNotModified:
            pass

    # elif current_state == selStates.SKILS:


@dp.message_handler()
async def echo(message: types.Message):
    await send_help(message)
    # await message.answer(message.text)


@dp.message_handler(content_types=ContentType.ANY)
async def unknown_message(msg: types.Message):
    message_text = text('Ха-ха. Вы пошутили - я тоже посмеялся',
                        '(/help вам в помощь)')
    await bot.send_message(msg.from_user.id, message_text, parse_mode=types.ParseMode.HTML,
                           reply_markup=main_menu())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
