from flask_sqlalchemy import SQLAlchemy
from flask_executor import Executor

# ОРМ БД
db = SQLAlchemy()
# для обращения к БД в контексте приложения + в параллельном потоке
executor = Executor()
