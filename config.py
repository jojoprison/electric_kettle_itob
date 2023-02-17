import configparser
import os

basedir = os.path.abspath(os.path.dirname(__file__))

# файл конфига
class Config:
    config = configparser.ConfigParser()
    config.read('config.ini')

    db_name = config['database']['name']
    # настройка для возможности мультитрединга в sqlite (с этим в sqlite плохо)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, db_name) + \
                              '?check_same_thread=False'

    # чтоб приложение понимало русский чарсет, когда возвращает dataclass на фронт
    JSON_AS_ASCII = False
    # меньше расходуем память
    SQLALCHEMY_TRACK_MODIFICATIONS = False
