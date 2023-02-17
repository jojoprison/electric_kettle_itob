from flask import Flask

from config import Config
from app.extensions import db, executor
from app.main import bp as main_bp


# сделаем фабрику, чтобы получать инстанс созданного приложения из любого места
def create_app(config_class=Config):
    app = Flask(__name__)
    # конфиг берем с специального файла с конфигами
    app.config.from_object(config_class)

    # расширение разными либами нашего приложения - SQLAlchemy
    db.init_app(app)
    # экзекьютор для запуска потока мониторинга температуры в файле самого чайника
    executor.init_app(app)

    # блюпринты для разделения на компоненты приложения (задел на рост в будущем)
    # юзаю без url_prefix
    app.register_blueprint(main_bp)

    # ну и удостоверимся, что файл с БД и необходимая табличка будет создана
    with app.app_context():
        db.create_all()

    return app
