from configparser import ConfigParser
import time
import threading

import app
from singleton import singleton
from app.extensions import db, executor
from app.models import Logs

# парсим файл конфигурации.
# вынес в глобальный скоуп чтобы обращаться из разных методов
config = ConfigParser()
config.read('config.ini')


# чтоб иметь лишь один экземпляр класса "Электрический чайник"
@singleton
class ElectricKettle:
    def __init__(self):
        # в аттрибуты класса возьмем инстанс нашего приложения
        self.app = app.create_app()
        # сохраним ссылку на сессию бд, что обращаться к аттрибуту класса
        self.session = db.session

        # приводим значения некоторых аттрибутов к значениям, заданным в config.ini
        self._reset_config()

        # начальные показатели чайник - выключен и пуст
        self._water_amount = 0.0
        self._status = 'off'

        # поток мониторинга температуры чайника (кипения)
        self._boil_thread = None

    # получить данные из конфигурации
    def get_config(self):
        config_data = {'max_water_amount': self.max_water_amount,
                       'switch_off_temperature': self.switch_off_temperature,
                       'boiling_time': self.boiling_time,
                       'base_temperature': self._temperature}

        return config_data

    # переконфигурировать чайник
    def reconfigure(self, max_water_amount, switch_off_temperature, boiling_time, base_temperature):
        self.max_water_amount = float(max_water_amount)
        self.switch_off_temperature = float(switch_off_temperature)
        self.boiling_time = float(boiling_time)
        self._temperature = float(base_temperature)

        message = 'Чайник переконфигурирован'
        self.log(message)

        return message

    # возврат значений конфигурации чайника к базовым (из файла)
    def reset_config(self):
        self.log('Выключаем чайник и сбрасываем всю конфигурацию')

        self.turn_off()

        self._reset_config()

    # протектед метод, чтоб вызывать его в методе инициализации и не логать
    def _reset_config(self):
        # устанавливаем параметры нашего чайника из файла с конфигами config.ini в корне проекта
        self.max_water_amount = float(config['kettle']['max_water_amount'])
        self.switch_off_temperature = float(config['kettle']['switch_off_temperature'])
        self.boiling_time = float(config['kettle']['boiling_time'])
        self._temperature = float(config['kettle']['base_temperature'])

    # своеобразный метод логирования приложения
    def log(self, message):
        # т.к. изначально задача была сделать консольное приложение, будем логировать и stdout
        print(message)

        # новая инстанс записи в нашу табличку логирования
        new_log = Logs(message=message)
        self.session.add(new_log)
        self.session.commit()

    # получаем состояние чайника
    def get_status(self):
        return self._status

    # получаем текущее кол-во воды в чайнике
    def get_water_amount(self):
        return self._water_amount

    # выливаем всю воду из чайника
    def empty(self):
        self.log('Выключаем чайник и выливаем всю воду')

        self.turn_off()

        self._water_amount = 0.

    # получаем значение температуры
    def get_temperature(self):
        return self._temperature

    # выключаем чайник и принудительно создаем ситуацию остывания
    def reset_temperature(self):
        self.turn_off()
        self.log('Чайник остыл')

        self._temperature = float(config['kettle']['base_temperature'])

    # метод наливания воды в чайник
    def pour_water(self, water_amount):
        # проверяем, выключен ли чайник
        if self._status != 'on':
            # подсчитываем новый показатель воды в чайнике
            new_water_amount = self._water_amount + water_amount

            # учитываем вместимость чайника
            if new_water_amount > self.max_water_amount:
                self.log('Превышен лимит кол-ва воды в чайнике!')
                # сколько нальем в случае полного заполнение
                will_fill = self.max_water_amount - self._water_amount
                self._water_amount = self.max_water_amount
            else:
                # нальем столько, сколько указали
                will_fill = water_amount
                self._water_amount = new_water_amount

            message = f'Налито {will_fill:.3f} литров воды'
        else:
            message = 'Нельзя наливать воду в чайник, пока он включен!'

        self.log(message)

    # включить чайник
    def turn_on(self):
        # проверяем, есть ли вода в чайнике
        if self._water_amount == 0.0:
            self.log('Нельзя включать чайник без воды внутри - это чревато поломкой!')
            return

        # проверяем, не кипит ли уже вода
        if self._temperature == self.switch_off_temperature:
            self.log('Нет смысла включать чайник, он уже вскипел!')
            return

        # проверяем, не включен ли уже чайник
        if self._status != 'on':
            self._status = 'on'

            self.log('Чайник включен')

            # объявляем демон-поток и запускаем его
            self._boil_thread = threading.Thread(target=self._boil_loop, daemon=True)
            self._boil_thread.start()
        else:
            self.log('Чайник уже ВКЛЮЧЕН! Нет нужды включать его повторно')

    # выключить чайник
    def turn_off(self):
        if self._status != 'off':
            self._status = 'off'

            self.log('Чайник выключен')

            # попытка передать управление из потока с кипением
            if self._boil_thread and self._boil_thread.is_alive():
                self._boil_thread.join()
        else:
            self.log('Чайник и так выключен')

    # нагревание чайника
    def _boil_loop(self):
        # запускаем в контексте запроса, потому что по-другому не работает executor мультипроцессинга flask
        with self.app.test_request_context():
            # определяем шаг, с которым будет меняться температура
            temperature_increase_step = (self.switch_off_temperature - self._temperature) / self.boiling_time
            executor.submit(self.log(f'Запущен мониторинг температуры чайника.'))
            # фиксируем стартовую температуру
            executor.submit(self.log(f'Температура чайника: {self._temperature:.1f}°C'))

            # кипим до температуры кипению
            # скобки для лучшей читаемости кода
            while self._status == 'on' and (self._temperature < self.switch_off_temperature):
                # меняем температуру с вычисленным шагом
                self._temperature += temperature_increase_step
                # на глаз создадим имитацию выкипания части воды :)
                self._water_amount -= self._water_amount / 170

                time.sleep(1)

                executor.submit(self.log(f'Температура чайника: {self._temperature:.1f}°C'))

            # вода закипела, меняем статус на "вскипел"
            if self._status == 'on':
                self.boiled()

    # чайник вскипел
    def boiled(self):
        self._status = 'boiled'

        self.log('Чайник вскипел!')

        # опустошаем ссылку на поток кипения
        self._boil_thread = None

        self.log('Остановлен мониторинг температуры чайника')
