#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

import pyrebase
import requests

from time import sleep, time
import threading

from .sql import getFirebaseCredentials, getFirebaseConfig

import logging

log = logging.getLogger(__name__)

def singleton(class_):
    """ Декоратор для класса-одиночки """
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


@singleton
class fireBase():
    """
        Класс объекта-одиночки для работы с облачной базой данных
        Google Firebase
    """
    def __init__(self):
        # Общая конфигурация firebase
        config = getFirebaseConfig()
        # Инициализировать приложение
        firebase = pyrebase.initialize_app(config)
        # Экземпляр базы данных
        self.db = firebase.database()
        # Экземпляр аутентификации
        self.auth = firebase.auth()
        #
        self.is_auth = False
        self.prev_inet_state = False

        creds = getFirebaseCredentials()
        self.email = creds['email']
        self.password = creds['password']

        # TODO: Check with empty rows
        if self.email != None and self.password != None:
            self.authorize(self.email, self.password)

        # TODO: set new thread for internet connection check

    def register_new_user(self, email, password):
        """ Зарегистрировать нового пользователя """
        self.auth.create_user_with_email_and_password(email, password)
        # self.auth.send_email_verification(self.user['idToken'])

    def check_connection(self):
        """ Worker-метод для проверки интернет соединения """
        while True:
            # URL для пинга
            __url = 'http://ww.google.com'
            # Таймаут ответа от URL
            __timeout = 3
            try:
                # Выполнить запрос на заданный URl
                _ = requests.get(__url, timeout=__timeout)
                # Если при предыдущей итерации соединения не было
                if not self.prev_inet_state:
                    # Провести повторную авторизацию
                    self.authorize()
                # Указать состояние для следующей итерации
                self.prev_inet_state = True
            except requests.ConnectionError:
                # Поймать исключение проблемы с соединением
                # Установить значение для следующей итерации
                self.prev_inet_state = False
                # Обнулить флаг аутэнтификации
                self.is_auth = False

    def authorize(self, email, password):
        """ Авторизоваться в системе по почте и паролю """
        try:
            self.user = self.auth.sign_in_with_email_and_password(self.email, self.password)
            self.user = self.auth.refresh(self.user['refreshToken'])
            self.uid = self.user['userId']
            # Лямбда-функция для выделения корневой директории пользователя
            # (dir - имя группы в корневой директории пользователя)
            self.root = lambda dir: self.db.child('users').child(self.uid).child(dir)
            self.token = self.user['idToken']

            self.last_token_upd = time()
            self.is_auth = True
            return "OK"
        except Exception as e:
            self.is_auth = False
            return "FAIL"

    def update_sencor_value(self, sencor):
        """ Обновить данные датчика в облачной базе данных """
        if self.is_auth:
            self.root(sencor.group_name).child("sencors").update({sencor.name:  sencor.value}, self.token)

    def delete_sencor(self, sencor):
        """ Удалить данные сенсора из облачной базы данных """
        if self.is_auth:
            self.root(sencor.group_name).child("sencors").child(sencor.name).remove(self.token)

    def update_device_value(self, device):
        """ Обновить данные устройства в облачной базе данных """
        if self.is_auth:
            self.root(device.group_name).child("devices").update({device.name:  device.value}, self.token)

    def delete_device(self, device):
        """ Удалить данные устройства из облачной базы данных """
        if self.is_auth:
            self.root(device.group_name).child("devices").child(device.name).remove(self.token)

    def delete_group(self, group):
        """ Удалить группу из облачной базы данных """
        if self.is_auth:
            self.root(group).remove(self.token)

    def upd_token(self, group_list, handler):
        """ Обновить токен доступа """
        __t_diff = time() - self.last_token_upd
        if __t_diff > 3300 and self.is_auth:
                log.info("Token expired")
                self.user = self.auth.refresh(self.user['refreshToken'])
                self.token = self.user['idToken']
                for group in group_list:
                    try:
                        group.dvc_stream.close()
                    except AttributeError:
                        log.critical("Stream didn't closed normally. Num of active threads %s" % threading.active_count())
                        pass
                    group.dvc_stream = self.root(group.name).child('devices').stream(handler, stream_id=group.name, token=self.token)
                self.last_token_upd = time()
                log.info("Active threads: %s" % threading.active_count())
