import datetime
from dataclasses import dataclass

# свободно имеем доступ к нашему объекту БД
from app.extensions import db


# моделька для единственной таблички
# dataclass чтобы не вызывать jsonify у объектов-сущностей и не делать сериализатор
@dataclass(init=True)
class Logs(db.Model):
    id: int
    message: str
    created_at: datetime.datetime

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message = db.Column(db.String(255))
    # логаем время записи
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    # меняем вид, чтобы на view в компактном виде наблюдать за логами
    def __repr__(self):
        return f'<log {self.id} - {self.message}>'
