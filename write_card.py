"""
код бота заполнения персональной карты на библиотеке aiogram
"""

import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup,
                           InlineKeyboardButton)
from aiogram.types.message import ParseMode, ContentType
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import text, bold

import dbfuncs
import keys
import serv

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

bot = Bot(token=keys.token)
dp = Dispatcher(bot)


def main_menu():
    btn = [[KeyboardButton('/scope'), KeyboardButton('/prof'),
            KeyboardButton('/skils'), KeyboardButton('/lndin'),
            KeyboardButton('/portf')],
           [KeyboardButton('/experience'), ],
           [KeyboardButton('/help'), KeyboardButton('/view'),
            KeyboardButton('/save'), KeyboardButton('/stop')]]
    kbt = ReplyKeyboardMarkup(resize_keyboard=True).row(*btn[0]).row(*btn[1]).row(*btn[2])
    return kbt

def edit_menu():
    btn = [KeyboardButton('/clear'), KeyboardButton('/cancel'), KeyboardButton('/done')]
    kbt = ReplyKeyboardMarkup(resize_keyboard=True).row(*btn)
    return kbt


def scope_menu():
    scopes = dbfuncs.get_scope(log=logger)
    kb = InlineKeyboardMarkup(row_width=4)
    for s in scopes:
        if len(s) > 10:
            kb.row(InlineKeyboardButton(s, callback_data=str(s)))
        else:
            kb.insert(InlineKeyboardButton(s, callback_data=str(s)))
    return kb

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if message.chat.type == 'group':
        return

    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        values={'first_name': message.from_user.first_name,
                                'full_name': message.from_user.full_name,
                                'mention': message.from_user.mention,
                                'user_url': message.from_user.url},
                        table=dbfuncs.USER_TABLE)
    dbfuncs.init_user_edit(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)

    _mess = f"Привет {message.from_user.full_name}!\nНачнем редактировать карточку?"
    await message.reply(_mess, reply_markup=main_menu())


@dp.message_handler(commands=['stop'])
async def send_stop(message: types.Message):
    _mess = f"Пока, {message.from_user.full_name}!\nНадеюсь, еще увидимся?"
    await message.reply(_mess, reply_markup=ReplyKeyboardRemove())



@dp.message_handler(commands=['view'])
async def view_card(message: types.Message):
    def _gets(key):
        _s1 = serv.edit_info[key][1]
        _s2 = usr_info.setdefault(f'tmp_{key}', '')
        return f'{_s1}: {_s2}'

    usr_info = dict(dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE))
    msg = text(bold(f'{usr_info["full_name"]}, Ваши данные:'),
               _gets('scope'), _gets('prof'), _gets('skils'), _gets('lndin'), _gets('portf'),
               _gets('experience'),
               sep='\n')

    await bot.send_message(message.from_user.id, msg, parse_mode=ParseMode.MARKDOWN,
                           reply_markup=main_menu())


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    html_mess = '''<b>Карточка пользователя:</b> нужна для показа выборок пользователей по разным критериям\n
<b>Заполняется следующее:</b>
/scope - сфера деятельности (например: IT; КОНСАЛТИНГ)
/prof - профессия (например: программист; сисадмин)
/skils - навыки, рабочий стек (например: Python; pandas; Flusk; docker, kubernetes)
/lndin - ссылка на профиль LinkedIn
/portf - ссылка на портфолио (например на github)
/experience - рабочий стаж\n

<b>Как заполнять:</b>
1. выбрать раздел в меню (или набрать команду)
2. постить в чат данные, либо через разделитель "," или ";" либо отправляя каждую записть отдельно
3. по окончании ввода данных раздела нажать /done, стереть все введенное - /clear
4. после ввода данных раздела данные в базу не записываются, сохраняются во временной карточке
5. в любой момент все введенное можно посмотреть командой /view
6. сохранение в базе - командой /save ТОЛКО ПОСЛЕ ЭТОГО ОНИ СОХРАНЯТСЯ
7. Команда /stop - останов бота, сброс временного введенных данных\n

<b>Пример:</b>
- После старта бота выбираем /scope
- Вводим "IT" - посылаем в чат, вводим КОНСАЛТИНГ - посылаем в чат
- Нажимаем /done - возвращаемся в главное меню
- Выбираем /lndin
- Вводим ссылку на провиль LinkedIn
- Нажимаем /done - возвращаемся в главное меню
- Выбираем /view просматриваем, что ввели
- Если все в порядке выбираем /save'''

    await bot.send_message(message.from_user.id, html_mess, parse_mode=ParseMode.HTML,
                           reply_markup=main_menu())


@dp.message_handler(commands=['save'])
async def save_edit(message: types.Message):
    dbfuncs.save_user_data(user_id=str(message.from_user.id), log=logger)
    _mess = f"{message.from_user.full_name}, Ваши данные сохраненыв БД!"
    await message.reply(_mess, reply_markup=main_menu())


@dp.message_handler(commands=['scope'])
async def edit_scope(message: types.Message):
    _m = select_main(message, 'scope')
    await bot.send_message(message.from_user.id, text=_m, reply_markup=edit_menu())
    # await message.reply(_m, reply_markup=edit_menu())


@dp.message_handler(commands=['skils'])
async def edit_skils(message: types.Message):
    _m = select_main(message, 'skils')
    await message.reply(_m, reply_markup=edit_menu())


@dp.message_handler(commands=['prof'])
async def edit_prof(message: types.Message):
    _m = select_main(message, 'prof')
    await message.reply(_m, reply_markup=edit_menu())


@dp.message_handler(commands=['lndin'])
async def edit_lndin(message: types.Message):
    _m = select_main(message, 'lndin')
    await message.reply(_m, reply_markup=edit_menu())


@dp.message_handler(commands=['portf'])
async def edit_portf(message: types.Message):
    _m = select_main(message, 'portf')
    await message.reply(_m, reply_markup=edit_menu())


@dp.message_handler(commands=['experience'])
async def edit_experience(message: types.Message):
    _m = select_main(message, 'experience')
    await message.reply(_m, reply_markup=edit_menu())


def select_main(message, cmd):
    tmp_f = f'tmp_{cmd}'
    usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        table=dbfuncs.USER_TABLE, values={'AT_WORK': cmd})

    return f"Редактируем {serv.edit_info[cmd][2]}: {usr_info[tmp_f]}"


@dp.message_handler(commands=['clear'])
async def clear_text(message: types.Message):
    usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    cur_state = usr_info['AT_WORK']

    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        table=dbfuncs.USER_TABLE, values={f'tmp_{cur_state}': None})

    _mess = f"Редактируем {serv.edit_info[cur_state][2]}: "
    await bot.send_message(message.from_user.id, _mess, reply_markup=edit_menu())


@dp.message_handler(commands=['cancel'])
async def cancel_text(message: types.Message):
    usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    cur_state = usr_info['AT_WORK']

    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        table=dbfuncs.USER_TABLE, values={f'tmp_{cur_state}': usr_info[cur_state]})

    _mess = f"Редактируем {serv.edit_info[cur_state][2]}: {usr_info[cur_state]}"
    await bot.send_message(message.from_user.id, _mess, reply_markup=edit_menu())

@dp.message_handler(commands=['done'])
async def done_text(message: types.Message):
    # usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        table=dbfuncs.USER_TABLE, values={'AT_WORK': ''})
    _mess = f"Продолжим?"
    await bot.send_message(message.from_user.id, _mess, reply_markup=main_menu())


@dp.message_handler(commands=['show'])
async def show(message: types.Message):
    usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    if usr_info['AT_WORK'] == 'scope':
        kbt = scope_menu()
    else:
        return
    _m = select_main(message, 'scope')
    await bot.send_message(message.from_user.id, _m, reply_markup=kbt)


@dp.callback_query_handler()
async def process_callback_bt(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    uid = callback_query.from_user.id
    user_data = dbfuncs.get_user(user_id=str(uid), table=dbfuncs.USER_TABLE)

    if user_data['AT_WORK'] == 'scope':

        try:
            new_text = serv.append_text(user_data[f'tmp_scope'], callback_query.data, allcaps=True)
        except ValueError:
            await callback_query.reply('Недопустимые символы во вводе', reply_markup=edit_menu())
            return
        dbfuncs.update_user(log=logger, user_id=str(uid),
                            table=dbfuncs.USER_TABLE, values={f'tmp_scope': new_text})
        _mess = f"Редактируем {serv.edit_info['scope'][2]}: {new_text}"
        try:
            await bot.edit_message_text(message_id=callback_query.message.message_id,
                                        chat_id=callback_query.message.chat.id, parse_mode=types.ParseMode.HTML,
                                        text=_mess, reply_markup=scope_menu())
        except MessageNotModified:
            pass

@dp.message_handler()
async def edit_text(message: types.Message):
    usr_info = dbfuncs.get_user(log=logger, user_id=str(message.from_user.id), table=dbfuncs.USER_TABLE)
    cur_state = usr_info['AT_WORK']

    if usr_info['AT_WORK'] in ['scope', 'skils', 'prof']:
        try:
            new_text = serv.append_text(usr_info[f'tmp_{cur_state}'], message.text, allcaps=(cur_state == 'scope'))
        except ValueError:
            await message.reply('Недопустимые символы во вводе', reply_markup=edit_menu())
            return
    elif usr_info['AT_WORK']:
        new_text = message.text
    else:
        await bot.send_message(message.from_user.id, 'Надо выбрать, что редкатировать\n(/help вам в помощь)',
                               reply_markup=main_menu())
        return

    dbfuncs.update_user(log=logger, user_id=str(message.from_user.id),
                        table=dbfuncs.USER_TABLE, values={f'tmp_{cur_state}': new_text})
    _mess = f"Редактируем {serv.edit_info[cur_state][2]}: {new_text}"
    await bot.send_message(message.from_user.id, _mess, reply_markup=edit_menu())

@dp.message_handler(content_types=ContentType.ANY)
async def unknown_message(msg: types.Message):
    message_text = text('Ха-ха. Вы пошутили - я тоже посмеялся',
                        '(/help вам в помощь)')
    await msg.reply(message_text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
