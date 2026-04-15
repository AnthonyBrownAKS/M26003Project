import sys, os

import datetime
import numpy as np
from MvImport.MvCameraControl_class import *
from MvImport.CameraParams_header import *
from MvImport.PixelType_header import *
import cv2
import json
from ctypes import WINFUNCTYPE
winfun_ctype = WINFUNCTYPE
from datetime import datetime

class CameraError(Exception):
	pass


def CheckReturn(Val, Msg):
	if Val != 0:
		raise CameraError("%s errcode=0x%08X" % (Msg, Val))

ExceptionCallBack = winfun_ctype(None, c_uint, c_void_p)

class Camera:
	__ExposureTime = 0
	__IsOpened = False
	__Ip = ""

	def __init__(self):
		self.img_buff = None
		self.stConvertParam = None
		self.SharedFlag = False
		self.CALL_BACK_FUN = ExceptionCallBack(self.event_callback)

	def event_callback(self, pEventInfo, pUser):
		print("0x%08X"%pEventInfo)
		if pEventInfo == 0x00008001:
			self.__IsOpened = False

	def SetParamFile(self, ConfigFileName: str):
		with open(ConfigFileName, "r") as ConfigFile:
			self.__CameraConfig = json.load(ConfigFile)
		self.__Ip = self.__CameraConfig["Ip"]

	def Open(self) -> bool:

		if self.__IsOpened:
			return True
		CameraConfig = self.__CameraConfig

		deviceList = MV_CC_DEVICE_INFO_LIST()
		tlayerType = MV_GIGE_DEVICE

		ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
		if ret != 0:
			raise CameraError("enum devices fail! errcode=0x%08X" % (ret))

		if deviceList.nDeviceNum == 0:
			raise CameraError("find no device! errcode=0x%08X" % (ret))

		Device = None
		for i in range(deviceList.nDeviceNum):
			mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
			nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
			nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
			nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
			nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
			tmpIP = "%d.%d.%d.%d" % (nip1, nip2, nip3, nip4)
			if tmpIP == self.__Ip:
				Device = mvcc_dev_info
				break
		# raise CameraError('find no camera! errcode=0x%08X' % (ret))

		if Device == None:
			raise CameraError('find no camera!')

		self.obj_cam = MvCamera()
		ret = self.obj_cam.MV_CC_CreateHandle(Device)
		if ret != 0:
			self.obj_cam.MV_CC_DestroyHandle()
			raise CameraError('create handle fail! errcode=0x%08X' % (ret))

		ret = self.obj_cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
		if ret != 0:
			raise CameraError('open device fail！ errcode=0x%08X' % (ret))

		ret = self.obj_cam.MV_CC_RegisterExceptionCallBack(self.CALL_BACK_FUN, None)
		if ret != 0:
			raise CameraError('Register Exception CallBack fail！ errcode=0x%08X' % (ret))


		ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_ON)
		if ret != 0:
			raise CameraError('set trigger mode fail! errcode=0x%08X' % (ret))

		ret = self.obj_cam.MV_CC_SetEnumValue("AcquisitionMode", MV_ACQ_MODE_CONTINUOUS)
		if ret != 0:
			raise CameraError('set acquisition mode fail! errcode=0x%08X' % (ret))

		ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource", MV_TRIGGER_SOURCE_SOFTWARE)
		if ret != 0:
			raise CameraError('set trigger source fail！ errcode=0x%08X' % (ret))

		self.SetParameter(CameraConfig)

		ret = self.obj_cam.MV_CC_StartGrabbing()
		if ret != 0:
			raise CameraError('Start Grabbing fail! errcode=0x%08X' % (ret))
		self.__IsOpened = True

		return True

	def GetIp(self):
		return self.__Ip

	def Close(self):
		if self.__IsOpened:
			self.__IsOpened = False
			self.obj_cam.MV_CC_CloseDevice()
			self.obj_cam.MV_CC_DestroyHandle()

	def SetParameter(self, Config: dict):
		CheckReturn(self.obj_cam.MV_CC_SetIntValue("Height", Config["Height"]), "set height fail!")
		CheckReturn(self.obj_cam.MV_CC_SetIntValue("Width", Config["Width"]), "set width fail!")
		CheckReturn(self.obj_cam.MV_CC_SetIntValue("OffsetX", Config["OffsetX"]), "set OffsetX fail!")
		CheckReturn(self.obj_cam.MV_CC_SetIntValue("OffsetY", Config["OffsetY"]), "set OffsetY fail!")
		CheckReturn(self.obj_cam.MV_CC_SetFloatValue("ExposureTime", Config["ExposureTime"]), "set ExposureTime fail!")
		CheckReturn(self.obj_cam.MV_CC_SetFloatValue("Gain", Config["Gain"]), "set gain fail!")
		CheckReturn(self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate", Config["FrameRate"]),
		            "set acquisition frame rate fail!")

	def SetExposureTime(self, ExposureTime: int) -> bool:
		if not self.__ExposureTime == ExposureTime:
			self.__ExposureTime = ExposureTime
			ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime", float(ExposureTime))
			if ret != 0:
				raise CameraError('set exposure time fail errcode=0x%08X' % (ret))
		return True

	def TriggerOnce(self):
		ret = self.obj_cam.MV_CC_SetCommandValue("TriggerSoftware")
		if ret != 0:
			raise CameraError('trigger software fail! errcode=0x%08X' % (ret))

	def AcqImg(self) -> object:
		stOutFrame = MV_FRAME_OUT()
		# img_buff = None
		buf_cache = None
		ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 10000)
		if not ret == 0:
			raise CameraError("get image fail! errcode=0x%08X" % (ret))

		stFrameInfo = stOutFrame.stFrameInfo
		nConvertSize = stFrameInfo.nWidth * stFrameInfo.nHeight * 3
		# 转换像素结构体赋值
		if self.stConvertParam is None:

			if self.img_buff is None:
				self.img_buff = (c_ubyte * nConvertSize)()

			self.stConvertParam = MV_CC_PIXEL_CONVERT_PARAM()
			memset(byref(self.stConvertParam), 0, sizeof(self.stConvertParam))
			self.stConvertParam.nWidth = stFrameInfo.nWidth
			self.stConvertParam.nHeight = stFrameInfo.nHeight
			self.stConvertParam.nSrcDataLen = stFrameInfo.nFrameLen
			self.stConvertParam.enSrcPixelType = stFrameInfo.enPixelType
			self.stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
			self.stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
			self.stConvertParam.nDstBufferSize = nConvertSize

		self.stConvertParam.pSrcData = cast(stOutFrame.pBufAddr, POINTER(c_ubyte))
		# RGB直接显示
		if PixelType_Gvsp_RGB8_Packed == stFrameInfo.enPixelType:
			img_buff = np.frombuffer(buf_cache, count=int(stFrameInfo.nWidth * stFrameInfo.nHeight * 3), dtype=np.uint8)
			numArray = img_buff.reshape(stFrameInfo.nHeight, stFrameInfo.nWidth, 3)
		# 如果是彩色且非RGB则转为RGB后显示
		else:

			ret = self.obj_cam.MV_CC_ConvertPixelType(self.stConvertParam)
			if ret != 0:
				raise CameraError("convert pixel fail! errcode=0x%08X" % (ret))
			cdll.msvcrt.memcpy(byref(self.img_buff), self.stConvertParam.pDstBuffer, nConvertSize)
			img_buff = np.frombuffer(self.img_buff, count=nConvertSize, dtype=np.uint8)
			numArray = img_buff.reshape(stFrameInfo.nHeight, stFrameInfo.nWidth, 3)
		nRet = self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
		return cv2.cvtColor(numArray, cv2.COLOR_RGB2BGR)

	def SaveImage(self,FileName:str):
		img = self.AcqImg()
		if not os.path.exists(os.path.dirname(FileName)):
			os.makedirs(os.path.dirname(FileName))
		cv2.imwrite(FileName, img)
		return True


# def Color_numpy(self, data, nWidth, nHeight):
# 	img_buff = np.frombuffer(data, count=int(nWidth * nHeight * 3), dtype=np.uint8)
# 	return img_buff.reshape(nHeight, nWidth, 3)
#
#
# 	data_ = np.frombuffer(data, count=int(nWidth * nHeight * 3), dtype=np.uint8, offset=0)
# 	data_r = data_[0:nWidth * nHeight * 3:3]
# 	data_g = data_[1:nWidth * nHeight * 3:3]
# 	data_b = data_[2:nWidth * nHeight * 3:3]
#
# 	data_r_arr = data_r.reshape(nHeight, nWidth)
# 	data_g_arr = data_g.reshape(nHeight, nWidth)
# 	data_b_arr = data_b.reshape(nHeight, nWidth)
# 	numArray = np.zeros([nHeight, nWidth, 3], "uint8")
#
# 	numArray[:, :, 0] = data_r_arr
# 	numArray[:, :, 1] = data_g_arr
# 	numArray[:, :, 2] = data_b_arr
# 	return numArray


# 相机测试:
if __name__ == "__main__":

	Cam1 = Camera()

	# 1. 加载配置
	Cam1.SetParamFile("Camera2.json")

	# 2. 打开相机
	Cam1.Open()

	# 3. 设置参数
	# Cam1.SetExposureTime(300000)

	# 4. 采集
	Cam1.TriggerOnce()
	img = Cam1.AcqImg()
	cv2.imshow("img", img)
	cv2.waitKey(0)

	save_dir = r"C:\Users\Administrator\Desktop\OpenCV_PROJECT\camImg"
	filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
	filepath = os.path.join(save_dir, filename)
	cv2.imwrite(filepath, img)

	Cam1.Close()
