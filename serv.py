"""
сервисные функции телеграм-бота
"""

import re

# словарик с сообщениям - фактически ресурс для хелпа и общения с пользователем
edit_info = {'name': ['id', 'id'],
             'first_name': ['Имя', 'Имя'],
             'scope': ['/scope', 'Сфера деятельности', 'сферу деятельности'],
             'prof': ['/prof', 'Профессия', 'профессию'],
             'skils': ['/skils', 'Навыки', 'навыки'],
             'lndin': ['lndin', 'Профиль linkedin', 'linkedin'],
             'portf': ['portf', 'Портфолио', 'портфолио'],
             'experience': ['experience', 'Стаж', 'стаж']}


def combine_multi_choise(str_saved: str, str_new: str, allcaps: bool = False) -> str:
    """
    Формирует строку из старой (сохраненной в базе) и новой. Проверяет на дубликат, добавляет новые записи через разделитель, если надо - переводит регистр в ALL CAPS
    :param str_saved: "старая" строка
    :param str_new: добавляемая запись
    :param allcaps: True - переводит в ALL CAPC все сообщение
    :return: строка из старой + новой через разделитель (разделитель фиксированный ';')
    """
    if allcaps:
        _lst = list(map(str.upper, re.split('[;,]', str_new)))
    else:
        _lst = re.split('[;,]', str_new)

    if str_saved:
        _lst_o = str_saved.split(';')
        lret = _lst_o + [l.strip() for l in _lst if l not in _lst_o]
        return '; '.join(lret)
    else:
        return ';'.join(set(_lst))


def tail_message(selector: str, user_data: str) -> str:
    """
    формирует сообщениепользователю о текущем редактировании;
    по текущей рабочей команде выбирает соотв. сообщение, добавляет к нему уже имеющийся ввод пользователя
    :param selector: команда бота
    :param user_data: "старый" + новый ввод пользователя
    :return: строка-сообщение
    """
    if selector:
        _s1 = edit_info[selector][2]
        _s2 = user_data
        return f'Редактируем {_s1}:{_s2}'
    else:
        return 'un-known command'


def get_temp_fields(dct):
    lst_inc = ['user_id', 'first_name']
    return {k: v for k, v in dct.items() if k.startswith('tmp_') or k in lst_inc}
