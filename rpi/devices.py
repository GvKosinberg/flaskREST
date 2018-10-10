#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA
from time import time

import logging

log = logging.getLogger(__name__)


class Device(object):
    """ Родительский класс устройств """
    def __init__(self):
        self.last_response = time()

    def get_info(self):
        response = {
            'dvc_id': self.device_id,
            'dvc_type': self.type,
            'group_name': self.group_name,
            'name': self.name
        }
        return response


class Relay(Device):
    """ Класс реле """
    def __init__(self, dvc_id, group_name, name, ch0name, ch1name, last_val):
        self.device_id = dvc_id
        self.group_name = group_name
        self.name = name

        self.type = 'Relay'
        super(Relay, self).__init__()

        self.ch0name = ch0name
        self.ch1name = ch1name

        if last_val == None:
            self.ch0val = False
            self.ch1val = False
        else:
            self.ch0val = (last_val & 1) == 1
            self.ch1val = ((last_val >> 1) & 1) == 1
            log.info('RELAY %s: RESTORED VALS: %s, %s' %(self.name, self.ch0val, self.ch1val))

    def get_info(self):
        response = {
            'dvc_id': self.device_id,
            'dvc_type': self.type,
            'group_name': self.group_name,
            'name': self.name,
            'ch0name': self.ch0name,
            'ch1name': self.ch1name
        }
        return response

    def form_cmd(self, data2parse):
        if self.ch0name in data2parse:
            self.ch0val = data2parse[self.ch0name]
        elif self.ch1name in data2parse:
            self.ch1val = data2parse[self.ch1name]

        cmd = [0, 0, 0, 0, 0]
        cmd[0] = int.self.device_id
        cmd[1] = 0
        cmd[2] = 14
        cmd[3] = 123

        cmd[4] = (0b10 if self.ch1val else 0b00) + (0b01 if self.ch0val else 0b00)

        return cmd

    def check_response(self, income):
        log.info(income)
        return True
