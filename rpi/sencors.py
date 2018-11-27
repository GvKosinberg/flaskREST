#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

from time import time
from datetime import datetime

# TEMP: # DEBUG: # XXX:
from random import randint

import logging

log = logging.getLogger(__name__)


class Sencor(object):
    """ Родительский класс датчиков """
    def __init__(self, snc_id, group_name, name):
        # Идентификатор
        self.sencor_id = snc_id
        # Имя группы
        self.group_name = group_name
        # Собственное имя
        self.name = name
        # Значение по умолчанию
        self.value = '-'
        # Заряд батареи
        self.battery = '-'
        # Время последнего ответа
        self.last_response = time()

    def get_info(self):
        """ Метод получения информации о датчике """
        response = {
            'snc_id': self.sencor_id,
            'snc_type': self.type,
            'group_name': self.group_name,
            'name': self.name
        }
        return response

    def form_data(self):
        """ Метод формирования пакета данных для передачи в облако """
        # Формат даты/времени
        _format = '%d-%m-%Y %H:%M'
        # Сформировать строковое представление времени последнего ответа
        _time = datetime.fromtimestamp(self.last_response).strftime(_format)
        # Формирование выходного словаря
        data = {
            self.name + '/snc_type': self.type,
            self.name + '/id': self.sencor_id,
            self.name + '/value': self.value,
            self.name + '/battery': self.battery,
            self.name + '/last_response': _time
        }
        # Вернуть выходной пакет данных
        return data

    def check_timeout(self):
        """ Метод проверки таймаута ответа """
        # Если время последнего ответа больше чем текущее на период таймаута
        if (time() - self.last_response >= self.timeout):
            # Установить данные в Таймаут
            self.value = "Таймаут"
            # Вернуть истину
            return True
        else:
            return False

    def convert_battery(self, income):
        """ Метод вычисления процента заряда батареи """
        # Если длина массива достаточная
        if len(income) >= 5:
            # Непосредственное значение напряжения из принятого пакета данных
            __volt_raw = income[4] + 150
            # Номинальное напряжение полного заряда батареи
            __volt_full = 330
            # Номинальное напряжения разряда батареи
            __volt_low = 260
            # Разница полного заряда-разряда
            __volt_range = __volt_full - __volt_low
            # Вычисление процентного соотношения текущего заряда к номиналам
            _volt_calc = int(((__volt_raw - __volt_low)*100)/__volt_range)
            # NOTE: ацп или формула вычисления на устройствах барахлит,
            # поэтому не исключены случаи выхода за границы номиналов,
            # поэтому нужно зафиксировать минимальное и максимальное значения
            if _volt_calc > 100:
                _volt_calc = 100
            elif _volt_calc < 0:
                _volt_calc = 0

            # Вывести значение процента напряжения в лог
            log.info("Battery level of %s: %s" % (self.name, _volt_calc))
            # Установить значение заряда для экземпляра объекта
            self.battery = str(_volt_calc) + " %"


class TemperatureSencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        # Инициализация родительского класса
        super(TemperatureSencor, self).__init__(snc_id, group_name, name)
        # Тип датчика
        # TODO: send type to fb on init to ease data parsing
        self.type = 'Temperature'

        # Таймаут ответа датчика
        self.timeout = 1080

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        # Обновить время последнего ответа от устройства
        self.last_response = time()

        # Младший байт данных
        __data_lb = income_array[5]
        # Старший байт данных
        __data_sb = income_array[6] << 8

        # Побитовое сложение байтов
        __data_sum = (__data_lb | __data_sb) & 0xFFF

        # Если пришли данные с кодом ошибки
        if __data_sum in [0xFF]:
            # Установить ошибку данных
            self.value = "Ошибка датчика"
        else:
            # Строковая конкатенация показаний датчика и единиц измерения
            self.value = str(__data_sum/10.00) + " °C"


class HumiditySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        # Инициализация родительского класса
        super(HumiditySencor, self).__init__(snc_id, group_name, name)
        # Тип датчика
        self.type = 'Humidity'

        # Таймаут ответа
        self.timeout = 1080

    def convert_data(self, income_array):
        # TBD
        pass

    def get_random_state(self):
        """ Debug-метод со случайными занчениями """
        self.value = str(randint(35, 50)) + " %"


class LuminositySencor(Sencor):
    """ Класс датчиков температуры """
    def __init__(self, snc_id, group_name, name):
        # Инициализация родительского класса
        super(LuminositySencor, self).__init__(snc_id, group_name, name)
        # Тип датчика
        self.type = 'Luminosity'

        # Таймаут ответа
        self.timeout = 1080

    def convert_data(self, income_array):
        """
            Конвертация принятых данных
        """
        # Обновить время последнего ответа от датчика
        self.last_response = time()

        # Младший байт данных
        __data_lb = income_array[5]
        # Старший байт данных
        __data_sb = income_array[6] << 8

        # Побитовое сложение
        __data_sum = (__data_lb | __data_sb)

        # Если показания указывают на ошибку измерений
        if __data_sum in [0xFF]:
            self.value = "Ошибка датчика"
        else:
            # Строковая конкатенация данных датчика и единиц измерения
            self.value = str(__data_sum) + " люкс"


class DoorSencor(Sencor):
    """ Класс датчиков открытия двери """
    def __init__(self, snc_id, group_name, name):
        # Инициализация родительского класса
        super(DoorSencor, self).__init__(snc_id, group_name, name)
        # Тип датчика
        self.type = 'Door'

        # Таймаут ответа
        self.timeout = 1080

    def convert_data(self, data):
        # Обновить время последнего ответа от датчика
        self.last_response = time()

        # Младший байт данных
        __data_lb = data[7]

        # Если данные указывают на ошибку датчика
        if __data_lb in [0xFF]:
            self.value = "Ошибка датчика"
        else:
            # Тернарный оператор присвоения строки в зависимости от бита
            self.value = "Закрыто" if __data_lb == 0 else "Открыто"


class PulseSencor(Sencor):
    """ Класс счетчиков импульсов """
    def __init__(self, snc_id, group_name, name):
        # Инициализация родительского класса
        super(PulseSencor, self).__init__(snc_id, group_name, name)
        # Тип датчика
        self.type = 'Pulse'

        # Таймаут ответа
        self.timeout = 3605

        # Предыдущее значение количества импульсов
        self.prev_pulses = 0
        # Мощность
        self.pow = 0.0
        # КВт*ч
        self.kwt = 0.0

    # @override
    def form_data(self):
        """ Перегрузка метода формирования пакета для передачи в Firebase """
        # Формат даты
        _format = '%d-%m-%Y %H:%M'
        # Значение реального времни последнего ответа
        _time = datetime.fromtimestamp(self.last_response).strftime(_format)
        # Формирование выходного словаря
        data = {
            self.name + '/snc_type': self.type,
            self.name + '/id': self.sencor_id,
            self.name + "/КВт*ч": self.kwt,
            self.name + "/Мощность": self.pow,
            self.name + '/battery': self.battery,
            self.name + '/last_response': _time
        }
        # Вернуть сформированный словарь
        return data

    def convert_data(self, data):
        """
            Конвертация принятых данных
        """
        # Период (время между ответами в минутах)
        self.period_pwr = (time() - self.last_response)/60
        # Обновление времени последнего ответа датчика
        self.last_response = time()

        # Количество импульсов
        __pulses = 0
        try:
            # Побитовая конкатенация количества импульсов
            for i in range(0, 4):
                # Текущий бит со смещением
                __tmp = data[5+i] << (8*i)
                # Сложение с предыдущими показаниями
                __pulses = __pulses | __tmp
        except Exception:
            # Обработка исключений
            log.warn("Cant calc total pulses in Pulse:%s" % self.sencor_id)
            log.info("Data length: %s" % len(data))
            return
        finally:
            # Строковое представление КВТ*ч с точностью до 2 знаков после зпт
            self.kwt = "%.2f" % (__pulses/3200.00)
            log.info("kwt: %s" % self.kwt)

            if self.prev_pulses != 0:
                # Если датчик отвечает не в первый раз
                # Посчитать разность показаний двух ответов и поделить на
                # период между ответами
                __pow = (__pulses - self.prev_pulses) * 1.125 / self.period_pwr
                # Строковое представление мощность с единицами измерения
                # Точность: 2 знака после запятой
                self.pow = "%.2f Вт" % (__pow)
            else:
                # Если датчик вещает впервые
                self.pow = "0 Вт"
            # Запомнить последнее значения количества импульсов
            self.prev_pulses = __pulses
            log.info("pow: %s" % self.pow)


class WaterCounter(Sencor):
    """ Клас импульсных счетчиков потребления воды """
    def __init__(self, snc_id, group_name, name):
        super(WaterCounter, self).__init__(snc_id, group_name, name)
        # Тип датчика
        self.type = "Water"

        # Таймаут ответа
        self.timeout = 3605

    def convert_data(self, data):
        """
            Конвертация принятых данных
        """

        # Обновить время последнего ответа
        self.last_response = time()

        # Инициализация значения числа импульсов
        __pulses = 0
        try:
            # Побитовая конкатенация показаний количества импульсов
            for i in range(0, 4):
                # Текущий бит со смещением
                __tmp = data[5+i] << (8*i)
                # Конкатенация с предыдущими показаниями
                __pulses = __pulses | __tmp
        except Exception as e:
            log.error("Cant calculate pulses on water counter: %s" % self.name)

        # Записать строковое значение датчика
        self.value = str(__pulses * 10) + " л"
