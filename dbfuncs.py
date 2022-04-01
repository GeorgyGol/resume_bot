"""
Функции работы с базой данных
База данных - облачная, яндексовская, не-sql (boto3 - Amazon AWS)
Специфика работы бота телеграмма не позволяет иметь временные переменные для хранения текущего, несохраненного ввода пользователя
Поэтому, для хранениея таких данных, используется запись пользователя в БД. Каждому значимому полю в БД соответствует такое же поле, к имени которого добавлен префикс tmp_
При старте бота в поля tmp_ тся данные из соотв. постоянных полей
при вводе пользователя работа происходит с полями tmp_ (добавление новых записей, удаление, и т.д.)
при команде /save бота записи из полей tmp_ переносятся в соотв. постоянные поля (поля tmp_ теоретически можно удалить)
"""

import itertools
import logging

import boto3
import pandas as pd
from boto3.dynamodb.conditions import Attr

import keys
import serv

USER_TABLE = 'Users'
SHOW_TABLE_NAME = 'TMPVIEW'

dynamodb = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def connect_db(linkdb=dynamodb):
    """
    Проверяет наличие установленной связи с БД, если нет - создает из: при отладке из данных в файле keys
    при работе - из системных переменных яндекс-функции
    :param linkdb: объект-коннекш к БД или None
    :return: объект-коннекш к БД
    """
    if not linkdb:
        return boto3.resource('dynamodb',
                              endpoint_url=keys.USER_STORAGE_URL,
                              region_name=keys.REGION,
                              aws_access_key_id=keys.ID,
                              aws_secret_access_key=keys.SECRET
                              )
    else:
        return linkdb


def create_user_table(t_name: str = USER_TABLE, linkdb=dynamodb):
    """
    Создание таблицы - выполняется разово (однократно)
    :param t_name: имя таблицы в базе данных
    :linkdb: объект-коннект к базе данных
    :return:
    """
    dynamodb = connect_db(linkdb=linkdb)
    table = dynamodb.create_table(
        TableName=t_name,
        KeySchema=[
            {
                'AttributeName': 'user_id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput=
        {
            'ReadCapacityUnits': 123,
            'WriteCapacityUnits': 123
        }
    )

    # Wait until the table exists.
    table.wait_until_exists()

    # Print out some data about the table.
    print(table.item_count)

    return table


def loc_user(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE) -> str:
    """
    "Локализация" пользователя: пользователь идентифицируется по id (данные из телеграма)
    есди он уже есть в базе - обновляется его имя (именем телеграм-пользователя - не ИД), если нет - пользователь создается
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return: данные пользователя из БД
    """
    assert user_id
    log.debug(f'loc user {user_id}')
    tbl = connect_db(linkdb=dblink).Table(table)
    response = tbl.get_item(
        Key={'user_id': user_id}
    )
    try:
        fname = response['Item']['first_name']
        log.debug(f'user first_name = {fname}')
        return response['Item']
    except KeyError:
        log.debug(f'user not found - create new')
        tbl.put_item(
            Item={'user_id': user_id}
        )
        response = tbl.get_item(
            Key={'user_id': user_id}
        )
    return response['Item']


def check_user(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE) -> bool:
    assert user_id
    log.debug(f'check user {user_id} in {table}')
    tbl = connect_db(linkdb=dblink).Table(table)
    response = tbl.get_item(
        Key={'user_id': user_id}
    )
    return 'Item' in response


def get_user(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE):
    assert user_id
    log.debug(f'get info for {user_id} in {table}')
    tbl = connect_db(linkdb=dblink).Table(table)
    response = tbl.get_item(
        Key={'user_id': user_id}
    )
    return response['Item']


def delete_user(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE):
    """
    Удаление пользователя по ID (id пользователя в базе данных совпадает с  зователя в телеграме)
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return:
    """
    assert user_id
    # log.debug(f'delete user {user_id}')
    tbl = connect_db(linkdb=dblink).Table(table)
    tbl.delete_item(Key={'user_id': user_id})


def update_user(dblink=dynamodb, log=logger, user_id: str = None, values=dict(), table: str = USER_TABLE):
    """
    Обновление данных пользователя в базе данных
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :param values: словарь с данными пользователя: ключ словаря = имени поля в базе данных
    :return:
    """
    assert user_id
    log.debug(f'update user {user_id}')
    tbl = connect_db(linkdb=dblink).Table(table)
    expression = [f'{k} = :{k}' for k in values.keys()]
    strExp = 'SET {}'.format(', '.join(expression))
    vals = {f':{k}': v for k, v in values.items()}
    tbl.update_item(
        Key={'user_id': user_id},
        UpdateExpression=strExp,
        ExpressionAttributeValues=vals
    )


def init_user_edit(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE):
    """
    Создаются (еслиих еще нет) поля tmp_ каждого значимого поля записи пользователя в БД;
    создается специальное поле-индикатор (AT_WORK) того, что пользователь в данный момент времени редактирует (фактически в нем - текущая команда редактирования)
    поля tmp_ заполняются данными из соответствующих постоянных полей записи пользователя
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return:
    """
    assert user_id
    log.debug(f'init temp fileds for user {user_id}')
    exist_data = loc_user(user_id=user_id, log=log, table=table)

    for k in serv.edit_info.keys():
        if k not in ['user_id', 'first_name', 'AT_WORK', 'full_name', 'mention', 'user_url']:
            exist_data.setdefault(k, '')
            exist_data.setdefault(f'tmp_{k}', '')
        else:
            exist_data.pop(k)

    exist_data.update({'AT_WORK': ''})

    update_user(dblink=dynamodb, log=log, user_id=user_id, values=exist_data, table=table)


def save_user_data(dblink=dynamodb, log=logger, user_id: str = None, table: str = USER_TABLE):
    """
    Переписывает данные текущего ввода (поля с префиком tmp_ в соотв. постоянные поля записи пользователя в БД)
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return:
    """
    assert user_id
    dct = get_user(dblink=dblink, log=log, user_id=user_id, table=table)

    tmp_fld = [k for k in dct if k.startswith('tmp_')]
    for tk in tmp_fld:
        new_k = tk[4:]
        dct.setdefault(new_k, dct[tk])
        dct[new_k] = dct[tk]

    update_user(dblink=dblink, log=log, user_id=user_id,
                values={k[4:]: v for k, v in dct.items() if k in tmp_fld}, table=table)


def _sorted_from_list2(lst2: list) -> list:
    ret = list(set(map(str.strip, itertools.chain.from_iterable(lst2))))
    return sorted(ret)


def _drop_duplicates(lst: list) -> list:
    ret = list()
    st = set()
    for i in lst:
        if i.lower() not in st:
            ret.append(i)
            st.add(i.lower())
    return ret

def get_scope(dblink=dynamodb, log=logger, table=USER_TABLE) -> list:
    log.debug(f'select all scope')
    tbl = connect_db(linkdb=dblink).Table(table)

    scan_kwargs = {
        'FilterExpression': Attr('scope').size().gt(0),
    }

    response = tbl.scan(**scan_kwargs)
    # pprint(response)

    if 'Items' in response:
        scps = [i['scope'].split(';') for i in response['Items']]
        sc_list = _sorted_from_list2(scps)
        return _drop_duplicates(sc_list)
    else:
        return ''


def get_skils(dblink=dynamodb, log=logger, scope='', skils='', table=USER_TABLE) -> list:
    log.debug(f'select all skils for scope {scope}')

    tbl = connect_db(linkdb=dblink).Table(table)
    if scope:
        scan_kwargs = {
            'FilterExpression': Attr('scope').contains(scope),
        }
    else:
        scan_kwargs = {
            'FilterExpression': Attr('scope').size().gt(0),
        }
    if skils:
        scan_kwargs['FilterExpression'] = scan_kwargs['FilterExpression'] and Attr('skils').contains(skils)

    scan_kwargs['FilterExpression'] = scan_kwargs['FilterExpression'] and (
                Attr('lndin').size().gt(0) or Attr('portf').size().gt(0))

    response = tbl.scan(**scan_kwargs)

    if 'Items' in response:
        # skls = response['Items'][0]['skils']
        _lsts = list()
        for i in response['Items']:
            try:
                _lsts.append(i['skils'].split(';'))
            except KeyError:
                pass

        skls = _sorted_from_list2(_lsts)

        return _drop_duplicates(skls)
    else:
        return ''


def get_users(dblink=dynamodb, table=USER_TABLE, scope='', skils='', log=logger):
    def compare(str1, str2):
        if type(str1) != str:
            return False
        skl1 = set(map(str.lower, map(str.strip, str1.split(';'))))
        skl2 = set(map(str.lower, map(str.strip, str2.split(';'))))
        return bool(skl1 & skl2)

    log.debug(f'select all skils for scope {scope}')

    pdf = get_pdFrame()[['user_id', 'first_name', 'full_name', 'user_url',
                         'scope', 'prof', 'skils', 'lndin', 'portf', 'mention', 'experience']]
    if scope not in ('ВСЕ', None, ''):
        pdf = pdf[pdf['scope'].str.contains(r'\b{}\b'.format(scope), case=False, na=False, regex=True)]
    if skils not in ('ВСЕ', None, ''):
        pdf = pdf[pdf.apply(lambda x: compare(x['skils'], skils), axis=1)]

    return pdf

def get_pdFrame(dblink=dynamodb, table=USER_TABLE):
    tbl = connect_db(linkdb=dblink).Table(table)
    data = tbl.scan()
    if 'Items' in data:
        pdf = pd.DataFrame(data['Items'])
        pdf = pdf[pdf['full_name'].notna()]
        pdf = pdf[pdf['lndin'].notna() | pdf['portf'].notna()]
        pdf = pdf[(pdf['lndin'] != '') | (pdf['portf'] != '')]
        return pdf
    else:
        return None
