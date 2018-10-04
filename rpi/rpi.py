#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

# TODO: import stuff
import threading
from time import sleep, time

from .sencors import *
from .devices import *
from .firebase import fireBase
from . import sql
from .rfm69_lib.rfm69 import RFM69 as rfm69
from .rfm69_lib.configuration import RFM69Configuration as rfm_config

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


class Group(object):
    """ Класс группы устройств (кухня/улица и т.п.) """
    def __init__(self, name):
        self.name = name
        self.sencors = []
        self.devices = []


@singleton
class rpiHub(object):
    """ Класс-одиночка хаба Raspberry """
    def __init__(self):
        # Средства работы с Google Firebase
        self.firebase = fireBase()
        # Список групп устройств
        self.group_list = []
        # Список датчиков
        self.snc_list = []
        # TODO: add get sencors from db
        # Список устройств
        self.dvc_list = []
        # TODO: add get devices from db
        self.restore_settings_from_db()
        # rfm69hw module
        __config = rfm_config()
        self.rfm = rfm69(dio0_pin=24,
        reset_pin=22,
        spi_channel=0,
        config=__config)
        self.rfm.set_rssi_threshold(-114)
        # Инициализировать поток прослушки радиоканала
        self.init_read_sencors()

    # COMMON #

    def reset_fb_creds():
        """ Восстановление параметров входа для Firebase """
        # TODO: send password reset on email
        # TODO: save new email+pass in db
        # TODO: reauth with new email+pass
        pass

    def set_fb_creds(self, email, password):
        """ Установить параметры входа для Firebase """
        response = self.firebase.register_new_user(email, password)
        sql.setFirebaseCredentials(email, password)
        return response

    def restore_settings_from_db(self):
        # 1: Get and initiate groups
        __raw_groups = sql.getGroupNames()
        for raw_group in __raw_groups:
            self.add_group(raw_group[0])

        # 2: Get and initiate sencors
        __raw_sencors = sql.getSencorsSettings()
        log.info(__raw_sencors)
        for raw_snc in __raw_sencors:
            self.add_snc(
                snc_id=raw_snc[0],
                snc_type=raw_snc[1],
                snc_group=raw_snc[2],
                snc_name=raw_snc[3],
                restore=True
            )

        # 3: Get and initiate devices
        __raw_devices = sql.getDevicesSettings()
        log.info(__raw_devices)
        for raw_dvc in __raw_devices:
            self.add_dvc(
                dvc_id=raw_dvc[0],
                dvc_type=raw_dvc[1],
                dvc_group=raw_dvc[2],
                dvc_name=raw_dvc[3],
                restore=True
            )

        for gr in self.group_list:
            log.info(gr.name)

    def read(self):
        # TEMP
        log.info("Read thread initialized")
        try:
            while(True):
                # sleep(5)
                # if len(self.snc_list) == 0:
                #     continue
                # __idx = randint(0, len(self.snc_list)-1)
                # snc = self.snc_list[__idx]
                # snc.get_random_state()
                # log.info("Sencor %s:%s" % (snc.name, snc.value))
                # self.firebase.upd_token(self.group_list, self.device_handler)
                # self.firebase.update_sencor_value(snc)
                __sencor = None
                income = self.rfm.read_with_cb(60)
                if type(income)==tuple:
                    log.info(income[0])
                    __sencor = self.get_sencor_by_id(income[0][1])
                    if __sencor is not None:
                        __sencor.convert_data(income[0])
                        log.info(__sencor.name + ":" + __sencor.data)

                log.critical("===ITER===")
        except KeyboardInterrupt:
            "Got exception kbu"
            for g in self.group_list:
                g.dvc_stream.close()

    def init_read_sencors(self):
        # Инициализировать тред
        self.read_thread = threading.Thread(target=self.read)
        # Установить тред как демон
        self.read_thread.daemon = True
        # Запустить тред
        self.read_thread.start()

    # GROUPS #

    def get_group_by_name(self, name):
        """
            Вспомогательный метод поиска группы в списке по имени.
            При успешном нахождении возвращает экземпляр группы
            При безуспешном поиске возвращает None
        """
        __group = None
        for g in self.group_list:
            if g.name == name:
                __group = g
                break
        return __group

    def get_groups(self):
        """ Метод получения списка имен групп """
        __groups = {}
        for group in self.group_list:
            __groups[group.name] = self.get_group_info(group.name)
        return __groups

    def get_group_info(self, group_name):
        """
            Метод получения словаря с датчиками и устройствами,
            привязанными к группе
            Если группы с данным именем не существует, вернет FAIL (str)
        """
        __group = self.get_group_by_name(group_name)
        if __group is None:
            return "FAIL"
        __snc_output = []
        for sencor in __group.sencors:
            __snc_output.append(sencor.get_info())
        __dvc_output = []
        for device in __group.devices:
            __dvc_output.append(device.get_info())
        response = {
            'sencors': __snc_output,
            'devices': __dvc_output
        }
        return response

    def device_handler(self, message):
        """ Метод-обработчик сообщений от облачной базы Firebase """
        __from = message["stream_id"]
        # __group = self.get_group_by_name(__from)
        # if __group == None:
        #     log.error("Incoming message from non-existing group")
        #     return
        __inc_device_name = (message["path"].split("/"))[1]
        __data = message["data"]
        log.info("GROUP: %s, DEVICE: %s, DATA: %s" % (__from,
                                                      __inc_device_name,
                                                      __data))
        # __device = None

    def add_group(self, group_name):
        """
            Добавить новую группу.
            Если группа с таким именем уже существует, возвращает FAIL (str)
        """
        if self.get_group_by_name(group_name) is not None:
            return "FAIL"

        __new_group = Group(group_name)
        self.group_list.append(__new_group)
        # TODO: subscribe devices
        log.info("Type in set: %s" % type(group_name))
        __devices = self.firebase.root(group_name).child('devices')
        __new_group.dvc_stream = __devices.stream(self.device_handler,
                                                  stream_id=__new_group.name,
                                                  token=self.firebase.token)
        return("OK")

    def remove_group(self, group_name):
        """
            Удалить существующую группу.
            Если группы с таким именем не существует, возвращает FAIL (str)
            Если группа не пуста, возвращает FAIL
        """
        __group = self.get_group_by_name(group_name)
        if __group is None:
            return "FAIL"
        else:
            if len(__group.sencors) > 0:
                return "FAIL"
            if len(__group.devices) > 0:
                return "FAIL"
            try:
                __group.dvc_stream.close()
            except AttributeError:
                pass
            self.firebase.delete_group(__group.name)
            self.group_list.remove(__group)
            return "OK"

    # SENCORS #

    def get_sencor_by_id(self, s_id):
        """
            Вспомогательный метод поиска датчика в списке по типу и id.
            При успешном нахождении возвращает экземпляр датчика
            При безуспешном поиске возвращает None
        """
        __snc = None
        for s in self.snc_list:
            if s.sencor_id == s_id:
                __snc = s
                break
        return __snc

    def add_snc(self, snc_type, snc_id, snc_group, snc_name, restore=False):
        """ Добавить датчик """
        # Проверить, существует ли уже такой датчик
        if self.get_sencor_by_id(snc_id) is not None:
            log.error("Sencor with this type/id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(snc_group)
        if __group is None:
            log.error("Group %s not find" % snc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if snc_type == "Temperature":
            new_sencor = TemperatureSencor(snc_id=snc_id,
                                           group_name=snc_group,
                                           name=snc_name)
        elif snc_type == "Humidity":
            new_sencor = HumiditySencor(snc_id=snc_id,
                                        group_name=snc_group,
                                        name=snc_name)
        elif snc_type == "Luminosity":
            new_sencor = LuminositySencor(snc_id=snc_id,
                                          group_name=snc_group,
                                          name=snc_name)
        else:
            log.error("Unknown sencor type")
            return "FAIL"

        # Если создается новое устройство (не восстанавливается из БД)
        if not restore:
            # Добавить новую запись в БД
            sql.newSencorSettings((snc_id, snc_type, snc_group, snc_name))
        # Добавить новый датчик в список датчиков хаба и группы
        self.snc_list.append(new_sencor)
        __group.sencors.append(new_sencor)
        self.firebase.update_sencor_value(new_sencor)
        return "OK"

    def edit_snc(self, snc_type, snc_id, new_snc_group, new_snc_name):
        """ Редактировать настройки датчика """
        __sencor_for_edit = self.get_sencor_by_id(snc_id)

        __new_group = self.get_group_by_name(new_snc_group)
        if __new_group is None:
            log.error("New group does not exists")
            return "FAIL"

        if __sencor_for_edit is not None:
            __old_group = self.get_group_by_name(__sencor_for_edit.group_name)
            __old_group.sencors.remove(__sencor_for_edit)
            self.firebase.delete_sencor(__sencor_for_edit)

            __sencor_for_edit.group_name = new_snc_group
            __sencor_for_edit.name = new_snc_name
            __new_group.sencors.append(__sencor_for_edit)
            self.firebase.update_sencor_value(__sencor_for_edit)
            sql.editSencor((new_snc_group, new_snc_name, snc_id))
            return "OK"
        else:
            log.error("Sencor for edit not found in list")
            return "FAIL"

    def remove_snc(self, snc_type, snc_id):
        """ Удалить датчик """
        __sencor_for_delete = self.get_sencor_by_id(snc_id)

        if __sencor_for_delete is not None:
            self.snc_list.remove(__sencor_for_delete)
            __group = self.get_group_by_name(__sencor_for_delete.group_name)
            __group.sencors.remove(__sencor_for_delete)
            sql.deleteSencor(snc_id)
            self.firebase.delete_sencor(__sencor_for_delete)
            return "OK"
        else:
            log.error("Sencor for delete not found in list")
            return "FAIL"

    # DEVICES #

    def get_device_by_id(self, d_id):
        """
            Вспомогательный метод поиска устройства в списке по типу и id.
            При успешном нахождении возвращает экземпляр устройства
            При безуспешном поиске возвращает None
        """
        __dvc = None
        for d in self.dvc_list:
            if d.device_id == d_id:
                __dvc = d
                break
        return __dvc

    def add_dvc(self, dvc_type, dvc_id, dvc_group, dvc_name, restore=False):
        """ Добавить устройство """
        # Проверить, существует ли уже такое устройство
        if self.get_device_by_id(dvc_id) is not None:
            log.error("Device with this type/id already exists")
            return "FAIL"

        # Найти экземпляр группы в списке
        __group = self.get_group_by_name(dvc_group)
        if __group is None:
            log.error("Group %s not find" % dvc_group)
            return "FAIL"

        # В зависимости от типа инициализировать новый датчик
        if dvc_type == "Relay":
            new_device = Relay(dvc_id=dvc_id,
                               group_name=dvc_group,
                               name=dvc_name)
        else:
            log.error("Unknown device type")
            return "FAIL"

        # Если создается новое устройство (не восстанавливается из БД)
        if not restore:
            # Добавить новую запись в БД
            sql.newDeviceSettings((dvc_id, dvc_type, dvc_group, dvc_name))
        # Добавить новое устройство в список устройств хаба и группы
        self.dvc_list.append(new_device)
        __group.devices.append(new_device)
        # TODO: init stuff in first/recover send
        self.firebase.update_device_value(new_device)
        return "OK"

    def edit_dvc(self, dvc_type, dvc_id, new_dvc_group, new_dvc_name):
        """ Редактировать настройки устройства """
        __device_for_edit = self.get_device_by_id(dvc_id)

        __new_group = self.get_group_by_name(new_dvc_group)
        if __new_group is None:
            log.error("New group does not exists")
            return "FAIL"

        if __device_for_edit is not None:
            __old_group = self.get_group_by_name(__device_for_edit.group_name)
            __old_group.devices.remove(__device_for_edit)
            self.firebase.delete_device(__device_for_edit)

            __device_for_edit.group_name = new_dvc_group
            __device_for_edit.name = new_dvc_name
            __new_group.devices.append(__device_for_edit)
            self.firebase.update_device_value(__device_for_edit)
            sql.editDevice((new_dvc_group, new_dvc_name, dvc_id))
            return "OK"
        else:
            log.error("Device for edit not found in list")
            return "FAIL"

    def remove_dvc(self, dvc_type, dvc_id):
        """ Удалить устройство """
        __device_for_delete = self.get_device_by_id(dvc_id)

        if __device_for_delete is not None:
            self.dvc_list.remove(__device_for_delete)
            __group = self.get_group_by_name(__device_for_delete.group_name)
            __group.devices.remove(__device_for_delete)
            sql.deleteDevice(dvc_id)
            self.firebase.delete_device(__device_for_delete)
            return "OK"
        else:
            log.error("Device for delete not found in list")
            return "FAIL"
