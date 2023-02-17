from flask import Blueprint

# объявляем блюпринт
# совершенно необязательно в рамках данного приложения - просто хороший тон
bp = Blueprint('main', __name__)

from app.main import routes
