import binascii
import ctypes
import struct
import time

import snap7
from snap7.client import error_wrap
# from snap7.common import check_error
from snap7.util import *


class CDevice_SIEMENSException(Exception):
    pass


class MySnap7(snap7.client.Client):
    @error_wrap
    def write_bit(self, area: str, DbNumber, Start, Data):
        Val = struct.pack('B', Data & 0xFF)
        return self._library.Cli_WriteArea(self._pointer, area, DbNumber, Start, 1, snap7.types.S7WLBit, Val)

    def read_bit(self, area: str, DbNumber: int, Port: int):
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        data = (type_ * 1)()
        result = self._library.Cli_ReadArea(self._pointer, area, DbNumber, Port, 1, snap7.types.S7WLBit,
                                            ctypes.byref(data))
        # check_error(result, context="client")
        return data


class CDevice_SIEMENS():
    IsOpen = False
    SiemensPLC = None

    def __StrToHex(self, Str):
        Str = ('').join(Str)
        Rlt = binascii.a2b_hex(Str)
        return Rlt

    def Connect(self, IP, nRock, nSlot):
        if (self.IsOpen):
            self.DisConnect()
        try:
            self.SiemensPLC = MySnap7()
            self.SiemensPLC.connect(IP, nRock, nSlot)
            self.IsOpen = True
            return True
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def DisConnect(self):
        if (self.IsOpen):
            self.SiemensPLC.disconnect()
            self.IsOpen = False
        return True

    def ReadDBBit(self, DBNumber: int, nPort: int, nBit: int):
        try:
            Data = self.SiemensPLC.read_bit(snap7.types.S7AreaDB, DBNumber, nPort * 8 + nBit)
            if Data[0] == 1:
                return True
            return False
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadDBFloat(self, DBNumber: int, nStart: int):
        try:
            nAmout = 4
            Data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nStart, nAmout)
            return struct.unpack("!f", Data)[0]
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadDBInt(self, DBNumber: int, nStart: int):
        try:
            nAmout = 2
            Data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nStart, nAmout)
            Data = binascii.b2a_hex(Data)
            return str(int(Data, 16))
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def WriteDBFloat(self, DBNumber: int, nStartAddr: int, Data: float):
        try:
            Data = struct.pack('>f', Data)
            Val = bytearray(Data)
            self.SiemensPLC.write_area(snap7.types.Areas.DB, DBNumber, nStartAddr, Val)
            return True
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def WriteDBInt(self, DBNumber: int, nStartAddr: int, Data: int):
        try:
            Data1 = '%04X' % int(Data)
            Data1 = self.__StrToHex(Data1)
            Val = bytearray(Data1)
            self.SiemensPLC.write_area(snap7.types.Areas.DB, DBNumber, nStartAddr, Val)
            rel = self.ReadDBInt(DBNumber, nStartAddr)
            #print("write:" + str(Data) + "rel:" + rel[1])
            if int(rel) != Data:
                return False
            return True
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def WriteDBBit(self, DBNumber: int, Port: int, Bit: int, Data: int):
        try:
            Start = Port * 8 + Bit
            self.SiemensPLC.write_bit(snap7.types.S7AreaDB, DBNumber, Start, Data)
            rel = self.ReadDBBit(DBNumber, Port, Bit)
            if rel == bool(Data):
                return True
            else:
                return False
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadDBString(self, DBNumber: int, nStart: int,
                     nAmout: int):  ##111111#R#2#3070#1234#1002#00000000000000000#2204010001#
        try:
            Data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nStart, nAmout)
            # aa = 2 + ord(Data[1:2])
            return Data.decode("utf-8")[2:2 + ord(Data[1:2])].replace("\x00", "").replace(" ", "")[0:nAmout]
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def WriteDBString(self, DBNumber: int, nStart: int, Data: str):
        try:
            data3 = "d" + chr(len(Data)) + Data
            Val = bytearray(data3, "utf-8")
            self.SiemensPLC.write_area(snap7.types.Areas.DB, DBNumber, nStart, Val)
            return True
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadP_FUidData(self, DBNumber: int, nStart: int, nAmout: int):
        try:
            Data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nStart, nAmout)
            Data = Data[2:]
            Data = bytes(Data)
            Data = binascii.b2a_hex(Data)
            Data = Data.upper().decode("utf-8")[0:16]
            return Data
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadDBWord(self, DBNumber: int, nPort: int):
        try:
            nAmout = 2
            Data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nPort, nAmout)
            return ''.join(format(byte, '02x') for byte in Data)
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def WriteDBInt32(self, DBNumber: int, nStartAddr: int, Data: int):
        try:
            data = bytearray(4)
            set_dword(data, 0, Data)
            self.SiemensPLC.write_area(snap7.types.Areas.DB, DBNumber, nStartAddr, data)
            rel = self.ReadDBInt32(DBNumber, nStartAddr)
            print("write:" + str(Data) + "----rel:" + rel[1])
            if int(rel[1]) != Data:
                return False
            return True
        except Exception as ex:
            raise CDevice_SIEMENSException(str(ex))

    def ReadDBInt32(self, DBNumber: int, nStartAddr: int):
        try:
            # 读取 4 字节数据
            data = self.SiemensPLC.read_area(snap7.types.Areas.DB, DBNumber, nStartAddr, 4)
            # 假设 PLC 使用大端字节序
            value = int.from_bytes(data, byteorder='big', signed=True)
            return str(value)
        except Exception as ex:
            return f"Exception occurred: {str(ex)}"

    def ReadDBInput(self, INPNumber, nStart):
        try:
            data = self.SiemensPLC.read_area(snap7.types.Areas.PE, 0, INPNumber, 1)  # S7WLBit可以用1代替
            status = get_bool(data, 0, nStart)
            return status

        except Exception as ex:
            return  f"Exception occurred: {str(ex)}"


# Debug
if __name__ == '__main__':
    PLC_1 = CDevice_SIEMENS()
    # PLC_2 = CDevice_SIEMENS()
    try:
        print(PLC_1.Connect("192.168.0.1", 0, 0))  # DB501.154.1
        # print(PLC_2.Connect("192.168.200.3", 0, 0))  # DB501.154.1
        # print(PLC_1.ReadDBWord(7, 4))
        # print(PLC_1.ReadDBInput(2, 7))
        #print(PLC_1.ReadDBBit(1001, 416, 1))  # BOOL

        # print(Device_SIEMENS.WriteDBInt(13, 0, 0))
        # print(Device_SIEMENS.WriteDBBit(13, 112, 0, 1))
        # time.sleep(6)
        #print(PLC_1.WriteDBBit(1001, 416, 1, 1))

        #print(PLC_1.WriteDBString(1000, 0, 100))
        print(PLC_1.ReadDBFloat(1000, 0))
        #print(PLC_1.WriteDBFloat(1000, 0, 100))

        # print(Device_SIEMENS.WriteDBBit(13, 112, 0, 0))
        # print(Device_SIEMENS.ReadDBBit(13, 2, 0))
        # print(Device_SIEMENS.WriteDBBit(13, 2, 0, 1))
        # time.sleep(1)
        # print(Device_SIEMENS.ReadDBBit(13, 2, 0))
        # while True:
        #     print(1111,PLC_1.ReadDBBit(13, 116, 1))  # BOOL
        #     print(2222,PLC_2.ReadDBBit(15, 0, 0))  # BOOL
        #     print(3333,PLC_2.ReadDBBit(15, 0, 1))  # BOOL
        #     print(4444,PLC_2.ReadDBBit(15, 0, 2))  # BOOL
        #     print(5555,PLC_2.ReadDBBit(15, 0, 3))  # BOOL
        #     time.sleep(1)
        # print(PLC_1.WriteDBFloat(13, 0, 100))  # 启动轴
        # print(PLC_1.WriteDBBit(16, 4, 5, 1))  # 相机位置
        # print(PLC_2.WriteDBFloat(16, 4, 5))  # 相机位置
        # print(PLC_2.WriteDBFloat(16, 0, 215))  # 移动速度
        # print(PLC_2.WriteDBBit(16, 8, 1, 1))  # 启动轴
        # print(PLC_2.WriteDBBit(16, 8, 1, 1))  # 启动轴
    except Exception as ex:
        print(str(ex))
