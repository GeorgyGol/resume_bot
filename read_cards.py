"""
Основной файл бота просмотра профилей
"""

import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardRemove)
from aiogram.types.message import ParseMode
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.utils.markdown import text, bold

import dbfuncs
import keys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class selStates(Helper):
    mode = HelperMode.snake_case
    SCOPE = ListItem()
    SKILS = ListItem()


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


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if dbfuncs.check_user(user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE):
        _mess = "Просмотр профилей зарегестрированных пользователй"
        await bot.send_message(message.from_user.id, _mess, reply_markup=main_menu())
        dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                            values={'first_name': message.from_user.first_name}, table=dbfuncs.SHOW_TABLE_NAME)
    else:
        msg = text(bold('Сначала надо завести свою карточку'),
                   'Просматривать профили могут только зарегестрированные пользователи',
                   'Регистрация тут @Users4Lbot', sep='\n')

        await bot.send_message(message.from_user.id, msg, parse_mode=ParseMode.MARKDOWN,
                               reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state='*', commands=['scope'])
async def select_scope(message: types.Message):
    _mess = "Выберете сферу деятельности"
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(selStates.SCOPE)
    await bot.send_message(message.from_user.id, _mess, reply_markup=scope_menu())


@dp.message_handler(state='*', commands=['skils'])
async def select_skils(message: types.Message):
    _mess = "Выберете навыки"
    state = dp.current_state(user=message.from_user.id)
    await state.set_state(selStates.SKILS)
    await bot.send_message(message.from_user.id, _mess, reply_markup=skils_menu())


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    # print(message.from_user.id)
    _mess = "Will be help"
    await bot.send_message(message.from_user.id, _mess)


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)


@dp.callback_query_handler(state='*')
async def process_callback_bt(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    # await bot.send_message(callback_query.from_user.id, 'Нажата первая кнопка!')

    state = dp.current_state(user=callback_query.from_user.id)
    current_state = await state.get_state()
    print(callback_query.data, current_state, current_state[0] == selStates.SCOPE)
    # if current_state[0] == selStates.SCOPE:
    await state.set_state(selStates.SKILS)

    _mess = "Выберете навыки"
    await bot.send_message(callback_query.from_user.id, _mess, reply_markup=skils_menu(scope=callback_query.data))

    # elif current_state == selStates.SKILS:
    print(callback_query.data, current_state)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
