"""
Основной файл бота (функция бота):
"""

import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton, ParseMode, error
from telegram.ext import (Updater, CommandHandler, CallbackContext, MessageHandler, Filters,
                          ConversationHandler)

import dbfuncs
import keys
import serv

# уровни редактирования
SELECT, DONE_EDIT, RESTART = range(20, 23)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR)
logger = logging.getLogger(__name__)


def get_user_id(update: Update):
    """
    выделение ID ователя из сообщения (можно попробовать использовать другое, имя, например)
    :param update:
    :return:
    """
    if update.message.chat.type == 'group':
        # если все-таки чат групповой, то бросаем ошибку (сюда не должны попасть никогда)
        logger.info('group chat')
        raise error.BadRequest('Работает только в личке')

    user = update.message.from_user
    #     return user.username
    return str(user.id)


def bhelp(update: Update, context: CallbackContext):
    """
    Реакция на команду /help - вывод справки
    :param update:
    :param context:
    :return:
    """
    html_mess = '''<b>Карточка пользователя:</b>
нужна для показа выборок пользователей по разным критериям\n
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

    context.bot.send_message(chat_id=update.effective_chat.id, text=html_mess, parse_mode=ParseMode.HTML)


def start(update: Update, context: CallbackContext):
    # вызывается сначала и разово, при старте бота
    if update.message.chat.type == 'group':
        # роверка запуска из группового чата
        return

    uid = get_user_id(update)

    user = update.message.from_user
    # dbfuncs.loc_user(user_id=uid, log=logger)
    dbfuncs.init_user_edit(user_id=uid, log=logger)

    dbfuncs.update_user(user_id=uid, values={'first_name': user.first_name, 'AT_WORK': ''}, log=logger)

    logger.info(f'start edit for {uid} - {user.first_name}')

    return show_main_menu(update, context, f'Привет {user.first_name}! Начнем редактировать карточку?')


def as_start(update: Update, context: CallbackContext):
    # вызывается после редактирования раздела - возврат на первый уровень редактирования
    #     user = update.message.from_user
    uid = get_user_id(update)
    dbfuncs.update_user(user_id=uid, values={'AT_WORK': ''}, log=logger)
    logger.debug(f"return back to main menu")
    return show_main_menu(update, context, f'Продолжим?')


def edit_item(user_id=None, message='', command='save'):
    assert user_id

    def _do_edit(combine=True, old_m=''):
        if command == 'cancel':
            return ''
        elif command == 'clear':
            return ''
        else:
            if combine:
                return serv.combine_multi_choise(old_m, message, allcaps=at_work in ['scope', ])
            else:
                return message

    usr_data = dbfuncs.loc_user(user_id=user_id, log=logger)
    at_work = usr_data['AT_WORK']

    if at_work != '':
        old_mess = usr_data.setdefault(f'tmp_{at_work}', '')
        usr_data[f'tmp_{at_work}'] = _do_edit(old_m=old_mess, combine=at_work in ['scope', 'skils', 'prof'])

        upd_data = {k: v for k, v in usr_data.items() if k.startswith('tmp_')}
        dbfuncs.update_user(user_id=user_id, values=upd_data, log=logger)

        return serv.tail_message(at_work, usr_data[f'tmp_{at_work}'])
    else:
        #         str_sub_mess = 'неизвестно'
        return ''


def view(update: Update, context: CallbackContext):
    def make_mess(str_pre, key='', dct=None):
        try:
            return f'{str_pre}: {dct[key]}\n'
        except:
            return f'{str_pre}\n'

    #     user = update.message.from_user
    uid = get_user_id(update)
    dbfuncs.update_user(user_id=uid, values={'AT_WORK': ''}, log=logger)
    temp_data = serv.get_temp_fields(dbfuncs.loc_user(user_id=uid, log=logger))
    logger.info(f"return back to main menu with view")

    str_mess = make_mess("<b>Ваши даные</b>")
    str_mess += make_mess("<b>Имя</b>", key='first_name', dct=temp_data)

    # str_mess += make_mess("<b>id</b>", key='user_id', dct=temp_data)

    str_mess += make_mess("<b>Сфера деятельности /scope</b>", key='tmp_scope', dct=temp_data)
    str_mess += make_mess("<b>Профессия /prof</b>", key='tmp_prof', dct=temp_data)
    str_mess += make_mess('<b>Навыки /skils</b>', key='tmp_skils', dct=temp_data)
    str_mess += make_mess('<b>LinkeIn /lndin</b>', key='tmp_lndin', dct=temp_data)
    str_mess += make_mess('<b>Портфолио /portf</b>', key='tmp_portf', dct=temp_data)
    str_mess += make_mess('<b>Cтаж /experience</b>', key='tmp_experience', dct=temp_data)
    str_mess += make_mess('<b>Сохранение в базе: /save</b>')
    str_mess += make_mess('<b>Выход: /stop</b>')

    context.bot.send_message(chat_id=update.effective_chat.id, text=str_mess, parse_mode=ParseMode.HTML)
    return show_main_menu(update, context, f'Продолжим?')


def save(update: Update, context: CallbackContext):
    #     user = update.message.from_user
    uid = get_user_id(update)
    dbfuncs.save_user_data(user_id=uid, log=logger)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Данные сохранены в БД')
    return show_main_menu(update, context, f'Продолжим?')


def show_main_menu(upd, context, start_mess):
    logger.debug(f"show main menu")
    keyboard = [
        [
            KeyboardButton("/scope"),
            KeyboardButton("/prof"),
            KeyboardButton("/skils"),
            KeyboardButton("/lndin"),
            KeyboardButton("/portf")],
        [KeyboardButton("/experience")],
        [KeyboardButton("/help"),
         KeyboardButton("/view"),
         KeyboardButton("/save"),
         KeyboardButton("/stop"),
         ]
    ]

    # upd.message.reply_text(start_mess,
    #                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False,
    #                            input_field_placeholder='Что редактируем?'),
    #                        )
    context.bot.send_message(chat_id=upd.effective_chat.id, text=start_mess,
                             reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False,
                                                              input_field_placeholder='Что редактируем?'),
                           )
    return SELECT


def show_menu(upd, start_mess):
    logger.info(f"show sub menu")
    keyboard = [
        [
            KeyboardButton('/clear', callback_data='clear'),
            KeyboardButton('/done', callback_data='done'),
        ]
    ]
    upd.message.reply_text(start_mess,
                           reply_markup=ReplyKeyboardMarkup(
                               keyboard, resize_keyboard=True, one_time_keyboard=False,
                               input_field_placeholder='Действие?'),
                           )
    return DONE_EDIT


def select(update: Update, context: CallbackContext) -> int:
    #     user = update.message.from_user
    uid = get_user_id(update)
    logger.info(f'Received selection - {update.message.text}')
    usr_data = dbfuncs.loc_user(user_id=uid, log=logger)
    try:
        sub_mess = serv.edit_info[usr_data['AT_WORK']][2]
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Редактируем {sub_mess}')
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Неверный выбор!')
        as_start(update, context)
    return SELECT


def item_select(update: Update, context: CallbackContext):
    #     user = update.message.from_user
    uid = get_user_id(update)
    command = update.message.text.split()[0][1:]
    dbfuncs.update_user(user_id=uid, values={'AT_WORK': command}, log=logger)
    usr_data = dbfuncs.loc_user(user_id=uid, log=logger)
    try:
        old_data = usr_data[command]
    except:
        old_data = ''
    return show_menu(update, serv.tail_message(command, old_data))


def echo(update: Update, context: CallbackContext):
    #     user = update.message.from_user
    uid = get_user_id(update)
    strReply = edit_item(user_id=uid, message=update.message.text, command='save')
    return show_menu(update, strReply)


def clear(update: Update, context: CallbackContext):
    #     user = update.message.from_user
    uid = get_user_id(update)
    strReply = edit_item(user_id=uid, message=update.message.text, command='clear')
    return show_menu(update, strReply)


def bot_stop(update, _):
    logger.info('bot stoped')
    #     user = update.message.from_user
    uid = get_user_id(update)
    dbfuncs.update_user(user_id=uid, values={'AT_WORK': ''}, log=logger)
    update.message.reply_text('Бот остановлен. Для старта - команда /start', reply_markup=ReplyKeyboardRemove())
    return RESTART


def catch(update: Update, context: CallbackContext):
    return show_main_menu(update, context, f'Только дозволенные команды можно вводить. И текст')

def main() -> None:
    updater = Updater(keys.token)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT: [
                CommandHandler('scope', item_select),
                CommandHandler('skils', item_select),
                CommandHandler('prof', item_select),
                CommandHandler('lndin', item_select),
                CommandHandler('portf', item_select),
                CommandHandler('experience', item_select),
                CommandHandler('help', bhelp),
                CommandHandler('view', view),
                CommandHandler('save', save),
                MessageHandler(Filters.text & ~Filters.command, select),
                MessageHandler(~Filters.text, bhelp)
            ],
            DONE_EDIT: [
                CommandHandler('done', as_start),
                CommandHandler('clear', clear),
                MessageHandler(Filters.text & ~Filters.command, echo),
            ],
            RESTART: [
                CommandHandler('start', start),
            ],
        },
        fallbacks=[CommandHandler('stop', bot_stop)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
