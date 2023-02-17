from flask import jsonify, request, redirect, url_for, render_template

from app.main import bp
from app.extensions import db
from app.models import Logs
from electric_kettle import ElectricKettle


# здесь будем следить за основными показателями чайника и последними записями в логировании
@bp.route('/', methods=['GET', 'POST'])
def index():
    # везде будем создавать объект класса, т.к. он у нас синглтон
    kettle = ElectricKettle()

    # пост на главной отвечает только за сброс температуры после закипания
    if request.method == 'POST':
        kettle.reset_temperature()

        # редиректим на себя же
        return redirect(url_for('main.index'))
    else:
        # последние 10 записей
        last_10_logs = Logs.query.order_by(Logs.id.desc()).limit(10)
        kettle_status = kettle.get_status()
        kettle_water = kettle.get_water_amount()
        kettle_temperature = kettle.get_temperature()

        return render_template('index.html',
                               status=kettle_status,
                               water_amount=kettle_water,
                               temperature=kettle_temperature,
                               logs=last_10_logs)


@bp.route('/on', methods=['GET'])
def turn_on():
    # просто включим чайник, весь необходимый функционал внутри него
    ElectricKettle().turn_on()

    return redirect(url_for('main.index'))


@bp.route('/off', methods=['GET'])
def turn_off():
    # просто вырубаем чайник, весь необходимый функционал внутри него
    ElectricKettle().turn_off()

    return redirect(url_for('main.index'))


# наливаем воду на отдельной страничке
@bp.route('/pour', methods=['GET', 'POST'])
def pour_water():
    kettle = ElectricKettle()
    current_water_amount = kettle.get_water_amount()

    if request.method == 'POST':
        # проверяем, какая кнопка нажата - сперва опустошение
        if 'empty' in request.form:
            # выливаем воду
            kettle.empty()
        else:
            # пустое значение input с фронта вызывает ошибку - ставим заглушку
            if request.form.get('water_amount'):
                water_amount = float(request.form.get('water_amount'))
            else:
                water_amount = 0.

            kettle.pour_water(water_amount)

        # редиректим на главную
        return redirect(url_for('main.index'))

    return render_template('pour.html', water_amount=current_water_amount)


# возможность прямо из браузера поменять конфиги чайника ЛИБО вернуться в заводским (что в config.ini)
@bp.route('/config', methods=['GET', 'POST'])
def reconfigure():
    kettle = ElectricKettle()
    kettle_config = kettle.get_config()

    if request.method == 'POST':
        # проверяем, нажата ли кнопка сбросить конфиг?
        if 'reset' in request.form:
            kettle.reset_config()
        # значит нажата "задать новый конфиг"
        else:
            # на фронте почему-то лишние символы залазят в value input'ов - стрипаем!
            max_water_amount = request.form['max_water_amount'].strip()
            switch_off_temperature = request.form['switch_off_temperature'].strip()
            boiling_time = request.form['boiling_time'].strip()
            base_temperature = request.form['base_temperature'].strip()

            kettle.reconfigure(max_water_amount,
                               switch_off_temperature,
                               boiling_time,
                               base_temperature)

        # редиректим эту же страницу конфигов - вдруг что-то опять поменять надо
        return redirect(url_for('main.reconfigure'))

    return render_template('reconfigure.html', kettle_config=kettle_config)


# ну и страничка тестирования логирования. возможность записать новый лог и вывод последних 30 с временем
@bp.route('/logs', methods=['GET', 'POST'])
def logs():
    logs_ = Logs.query.order_by(Logs.id.desc()).limit(30)

    if request.method == 'POST':
        new_log = Logs(message=request.form['message'])

        db.session.add(new_log)
        db.session.commit()

        # остаемся здесь после создания - наблюдаем вверху новосозданную ло-запись
        return redirect(url_for('main.logs'))

    return render_template('logs.html', logs=logs_)
