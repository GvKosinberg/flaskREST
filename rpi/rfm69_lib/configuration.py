#from __future__ import division, absolute_import, print_function, unicode_literals
from collections import OrderedDict
from .constants import Register, RF
from .register_value import RegisterValue


class OpMode(RegisterValue):
    REGISTER = 0x01
    FORMAT = [('disable_sequencer', 1), ('listen', 1), ('listen_abort', 1), ('mode', 3), (0b00, 2)]

    Sleep = 0b000
    Standby = 0b001
    FS = 0b010
    TX = 0b011
    RX = 0b100

    def __init__(self):
        self.disable_sequencer = False
        self.listen = False
        self.listen_abort = False
        self.mode = self.Standby


class DataModulation(RegisterValue):
    REGISTER = 0x02
    FORMAT = [(False, 1), ('data_mode', 2), ('modulation_type', 2), (False, 1), ('modulation_shaping', 2)]

    ModePacket           = 0b00
    ModeContinuousSync   = 0b10
    ModeContinuousNoSync = 0b11

    TypeFSK              = 0b00
    TypeOOK              = 0b01

    def __init__(self):
        self.data_mode = self.ModePacket
        self.modulation_type = self.TypeFSK
        self.modulation_shaping = 0b00

class RSSIConfig(RegisterValue):
    REGISTER = 0x23
    FORMAT = [(False, 6), ('rssi_done', 1), ('rssi_start', 1)]

    def __init__(self):
        self.rssi_done = True
        self.rssi_start = False


class IRQFlags1(RegisterValue):
    REGISTER = 0x27
    FORMAT = [('mode_ready', 1), ('rx_ready', 1), ('tx_ready', 1), ('pll_lock', 1), ('rssi', 1),
              ('timeout', 1), ('auto_mode', 1), ('sync_address_match', 1)]

    def __init__(self):
        self.mode_ready = True
        self.rx_ready = False
        self.tx_ready = False
        self.pll_lock = False
        self.rssi = False
        self.timeout = False
        self.auto_mode = False
        self.sync_address_match = False


class IRQFlags2(RegisterValue):
    REGISTER = 0x28
    FORMAT = [('fifo_full', 1), ('fifo_not_empty', 1), ('fifo_level', 1), ('fifo_overrun', 1), ('packet_sent', 1),
              ('payload_ready', 1), ('crc_ok', 1), (False, 1)]

    def __init__(self):
        self.fifo_full = False
        self.fifo_not_empty = False
        self.fifo_level = False
        self.fifo_overrun = False
        self.packet_sent = False
        self.payload_ready = False
        self.crc_ok = False


class PacketConfig1(RegisterValue):
    REGISTER = 0x37
    FORMAT = [('variable_length', 1), ('dc_free', 2), ('crc', 1), ('crc_auto_clear_off', 1), ('address_filtering', 2),
              (False, 1)]

    DCFreeOff           = 0b00
    DCFreeManchester    = 0b01
    DCFreeWhitening     = 0b10

    def __init__(self):
        self.variable_length = True
        self.dc_free = self.DCFreeOff
        self.crc = True
        self.crc_auto_clear_off = False
        self.address_filtering = 0b10


class Temperature1(RegisterValue):
    REGISTER = 0x4E
    FORMAT = [(False, 4), ('start', 1), ('running', 1), (0b01, 2)]

    def __init__(self):
        self.start = False
        self.running = False


class RFM69Configuration(object):
    """ An object to hold to represent the configuration of the RFM69. There's quite a bit of it.

        Some of the most-used registers are RegisterValue objects which remove the need for bitwise arithmetic.
    """
    def __init__(self, chan_num):
        """ Defaults here are *mostly* the same as the defaults on the RFM69W """
        self.opmode = OpMode()
        self.data_modulation = DataModulation()

        self.bitrate_msb = 0x05
        self.bitrate_lsb = 0x00

        self.fdev_msb = 0x01
        self.fdev_lsb = 0x3F

        #CUSTOM RLDA FREQ
        freq = (int(((chan_num-3)*100000)/61)+0x6C5B45)
        self.frf_msb = (freq >> 16) & 0xFF
        self.frf_mid = (freq >> 8) & 0xFF
        self.frf_lsb = freq & 0xFF

        self.afc_ctl = RF.AFCLOWBETA_OFF

        #self.pa_level = RF.PALEVEL_PA0_ON | RF.PALEVEL_PA1_OFF | RF.PALEVEL_PA2_OFF | 0x18
        self.pa_level = (0x40 | (28))
        self.pa_ramp = RF.PARAMP_40

        self.ocp = RF.OCP_ON | RF.OCP_TRIM_95
        self.lna = 0x80
        self.rx_bw = 0x44
        self.afc_fei = RF.AFCFEI_AFCAUTO_OFF | RF.AFCFEI_AFCAUTOCLEAR_OFF

        self.dio_mapping_1 = 0x11
        self.dio_mapping_2 = 0x77

        self.rssi_threshold = -114 #XXX:prepare to fix

        self.rx_timeout_1 = 0
        self.rx_timeout_2 = 0

        self.sync_config = RF.SYNC_RLDA
        self.sync_value_1 = (0x0105>>8)
        self.sync_value_2 = 0x0105
        self.sync_value_3 = 0
        self.sync_value_4 = 0
        self.sync_value_5 = 0
        self.sync_value_6 = 0
        self.sync_value_7 = 0
        self.sync_value_8 = 0

        self.packet_config_1 = PacketConfig1()
        self.payload_length = 0x40

        self.fifo_threshold = 0x8F
        self.packet_config_2 = 0x02 #RLDA
        self.test_dagc = 0x30
        self.test_afc = 0x0E

        #test afc bw
        self.afc_bw = 0x8A

    def get_registers(self):
        regs = OrderedDict()
        regs[Register.OPMODE] = self.opmode.pack()
        regs[Register.DATAMODUL] = self.data_modulation.pack()
        regs[Register.BITRATEMSB] = self.bitrate_msb
        regs[Register.BITRATELSB] = self.bitrate_lsb
        regs[Register.FDEVMSB] = self.fdev_msb
        regs[Register.FDEVLSB] = self.fdev_lsb
        regs[Register.FRFMSB] = self.frf_msb
        regs[Register.FRFMID] = self.frf_mid
        regs[Register.FRFLSB] = self.frf_lsb
        regs[Register.AFCCTRL] = self.afc_ctl
        regs[Register.PALEVEL] = self.pa_level
        regs[Register.PARAMP] = self.pa_ramp
        regs[Register.OCP] = self.ocp
        regs[Register.LNA] = self.lna
        regs[Register.RXBW] = self.rx_bw
        regs[Register.AFCFEI] = self.afc_fei
        regs[Register.DIOMAPPING1] = self.dio_mapping_1
        regs[Register.DIOMAPPING2] = self.dio_mapping_2
        regs[Register.RSSITHRESH] = self.rssi_threshold
        regs[Register.RXTIMEOUT1] = self.rx_timeout_1
        regs[Register.RXTIMEOUT2] = self.rx_timeout_2
        regs[Register.SYNCCONFIG] = self.sync_config
        regs[Register.SYNCVALUE1] = self.sync_value_1
        regs[Register.SYNCVALUE2] = self.sync_value_2
        regs[Register.SYNCVALUE3] = self.sync_value_3
        regs[Register.SYNCVALUE4] = self.sync_value_4
        regs[Register.SYNCVALUE5] = self.sync_value_5
        regs[Register.SYNCVALUE6] = self.sync_value_6
        regs[Register.SYNCVALUE7] = self.sync_value_7
        regs[Register.SYNCVALUE8] = self.sync_value_8
        regs[Register.PACKETCONFIG1] = self.packet_config_1.pack()
        regs[Register.PAYLOADLENGTH] = self.payload_length
        regs[Register.FIFOTHRESH] = self.fifo_threshold
        regs[Register.PACKETCONFIG2] = self.packet_config_2
        regs[Register.TESTDAGC] = self.test_dagc
        regs[Register.TESTAFC]  = self.test_afc
        #test afc bw
        regs[Register.OSC1] = 0x40
        regs[Register.AFCBW] = self.afc_bw
#        regs[Register.NODEADRS] = 0
#        regs[Register.BROADCASTADRS] = 0xFF
#        regs[104] = 0x11
#        regs[105] = 0x15
#        regs[107] = 0x1b
#        regs[112] = 0
#        regs[113] = 0
        regs[255] = 0
        return regs
