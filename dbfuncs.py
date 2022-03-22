"""
Функции работы с базой данных
База данных - облачная, яндексовская, не-sql (boto3 - Amazon AWS)
Специфика работы бота телеграмма не позволяет иметь временные переменные для хранения текущего, несохраненного ввода пользователя
Поэтому, для хранениея таких данных, используется запись пользователя в БД. Каждому значимому полю в БД соответствует такое же поле, к имени которого добавлен префикс tmp_
При старте бота в поля tmp_ тся данные из соотв. постоянных полей
при вводе пользователя работа происходит с полями tmp_ (добавление новых записей, удаление, и т.д.)
при команде /save бота записи из полей tmp_ переносятся в соотв. постоянные поля (поля tmp_ теоретически можно удалить)
"""

import boto3

import keys

table_name = 'Users'
dynamodb = None
logger = None


def connect_db(linkdb=dynamodb):
    """
    Проверяет наличие установленной связи с БД, если нет - создает из: при отладке из данных в файле keys
    при работе - из системных переменных яндекс-функции
    :param linkdb: объект-коннекш к БД или None
    :return: объект-коннекш к БД
    """
    if not linkdb:
        # в "боевой" версии подключение надо будет поменять - ключи будут читаться из системных переменных яндекс-функции
        return boto3.resource('dynamodb',
                              endpoint_url=keys.USER_STORAGE_URL,
                              region_name=keys.REGION,
                              aws_access_key_id=keys.ID,
                              aws_secret_access_key=keys.SECRET
                              )
    else:
        return linkdb


def create_user_table(t_name: str = table_name, linkdb=dynamodb):
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


def loc_user(dblink=dynamodb, log=logger, user_id: str = None) -> str:
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
    table = connect_db(linkdb=dblink).Table(table_name)
    response = table.get_item(
        Key={'user_id': user_id}
    )
    try:
        fname = response['Item']['first_name']
        log.debug(f'user first_name = {fname}')
        return response['Item']
    except KeyError:
        log.debug(f'user not found - create new')
        table.put_item(
            Item={'user_id': user_id}
        )
        response = table.get_item(
            Key={'user_id': user_id}
        )
    return response['Item']


def delete_user(dblink=dynamodb, log=logger, user_id: str = None):
    """
    Удаление пользователя по ID (id пользователя в базе данных совпадает с  зователя в телеграме)
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return:
    """
    assert user_id
    # log.debug(f'delete user {user_id}')
    table = connect_db(linkdb=dblink).Table(table_name)
    table.delete_item(Key={'user_id': user_id})


def update_user(dblink=dynamodb, log=logger, user_id: str = None, values=dict()):
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
    table = connect_db(linkdb=dblink).Table(table_name)
    expression = [f'{k} = :{k}' for k in values.keys()]
    strExp = 'SET {}'.format(', '.join(expression))
    vals = {f':{k}': v for k, v in values.items()}
    table.update_item(
        Key={'user_id': user_id},
        UpdateExpression=strExp,
        ExpressionAttributeValues=vals
    )


def init_user_edit(dblink=dynamodb, log=logger, user_id: str = None):
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
    exist_data = loc_user(user_id=user_id, log=log)
    log.debug(f'init temp fileds for user {user_id}')
    lst_exclude = ['user_id', 'first_name', 'AT_WORK']
    tmp_dict = {f'tmp_{k}': v for k, v in exist_data.items() if (k not in lst_exclude) and not (k.startswith('tmp_'))}

    tmp_dict.update({'AT_WORK': ''})
    update_user(dblink=dynamodb, log=log, user_id=user_id, values=tmp_dict)


def save_user_data(dblink=dynamodb, log=logger, user_id: str = None):
    """
    Переписывает данные текущего ввода (поля с префиком tmp_ в соотв. постоянные поля записи пользователя в БД)
    :param dblink: коннект к базе данных
    :param log: объект логгера
    :param user_id: строка, в которой ИД пользователя из телеграмма - число
    :return:
    """
    assert user_id
    dct = loc_user(dblink=dblink, log=log, user_id=user_id)
    tmp_fld = [k for k in dct if k.startswith('tmp_')]
    for tk in tmp_fld:
        new_k = tk[4:]
        dct.setdefault(new_k, dct[tk])
        dct[new_k] = dct[tk]

    update_user(dblink=dblink, log=log, user_id=user_id, values={k[4:]: v for k, v in dct.items() if k in tmp_fld})
