import os
import threading

from numpy.ma.core import angle

from src import testO
from src import AngleCheck2
from src import AngleCheckTest3
from src.OPC import OPC
import cv2
from src.Camera import Camera
from datetime import datetime
import time
import json

# 联通
from src import AngleGUI
from src import CleanFiles

# 初始
opc = OPC()
# 状态锁（防重复执行）
left_busy = False
right_busy = False

# 上一帧状态（用于上升沿检测）
last_left = 0
last_right = 0

# 回调函数
callback = None


# 注册
def set_callback(func):
    global callback
    callback = func

def TestFile():
    with open(r"D:\M26003Project\data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    type = "12"
    print(data[f"{type}"]["camera"])


def TestPlc():
    data = opc.GetDataByTagName("PLC", "LeftType")
    data = opc.GetDataByTagName("PLC", "RightType")

    data = opc.GetDataByTagName("PLC", "LeftStartCameraRequest")
    data = opc.GetDataByTagName("PLC", "RightStartCameraRequest")

    data = opc.GetDataByTagName("PLC", "LeftTakePhotoComplete")
    data = opc.GetDataByTagName("PLC", "RightTakePhotoComplete")
    data = opc.GetDataByTagName("PLC", "LeftResult")
    data = opc.GetDataByTagName("PLC", "RightResult")
    data = opc.GetDataByTagName("PLC", "LeftAngle")
    data = opc.GetDataByTagName("PLC", "RightAngle")

    print(data["value"])

# side工位, path相机配置文件地址
def TestCamera(side, camera_path):

    Cam1 = Camera()

    # PLC结果Tag
    result_tag = f"{side}TakePhotoComplete"

    try:
        print(f"[{side}] 相机开始初始化")

        # 1. 加载配置
        Cam1.SetParamFile(camera_path)

        # 2. 打开相机
        Cam1.Open()

        # 3. 触发采集
        Cam1.TriggerOnce()
        img = Cam1.AcqImg()

        # 判空
        if img is None or img.size == 0:
            raise Exception("采集到空图像")

        # 4. 保存图片
        save_dir = f"D:/M26003Project/camImg/{side}"
        os.makedirs(save_dir, exist_ok=True)

        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{side}.jpg"
        filepath = os.path.join(save_dir, filename)

        success = cv2.imwrite(filepath, img)
        if not success:
            raise Exception("图片保存失败")
        print(f"[{side}] 拍照成功: {filepath}")

        # 5. 写PLC成功信号
        opc.SetDataByTagName("PLC", result_tag, 1)


        # 清理过期图片
        CleanFiles.clean_old_images(fr"D:/M26003Project/camImg/{side}")
        CleanFiles.clean_old_images(fr"D:/M26003Project/results/{side}")

        cv2.imwrite(fr"D:\M26003Project\tmp\{side}.jpg",img)

        return img

    except Exception as e:
        print(f"[{side}] 相机异常:", e)
        opc.SetDataByTagName("PLC", result_tag, 0)
        return None

    finally:
        # 关闭相机
        try:
            Cam1.Close()
            print(f"[{side}] 相机已关闭")
        except Exception as e:
            print(f"[{side}] 相机关闭异常:", e)

# ====================plc监听========================================================
def plc_monitor():
    global last_left, last_right, last_mid
    global left_busy, right_busy, mid_busy
    cnt = 0

    while True:
        try:
            # 读取PLC信号
            left_req = opc.GetDataByTagName("PLC", "LeftStartCameraRequest")["value"]
            mid_req = opc.GetDataByTagName("PLC", "MidStartCameraRequest")["value"]
            right_req = opc.GetDataByTagName("PLC", "RightStartCameraRequest")["value"]


            if cnt == 0:
                cnt += 1
            else:
                cnt -= 1

            opc.SetDataByTagName("PLC", "LeftHeartBeat", cnt)
            opc.SetDataByTagName("PLC", "MidHeartBeat", cnt)
            opc.SetDataByTagName("PLC", "RightHeartBeat", cnt)


            # ========= 左触发 =========
            if left_req == 1 and last_left == 0:
                print("检测到 Left 拍照请求")

                if not left_busy:
                    left_busy = True
                    # 上位机完成拍照时置1，收到PLC拍照请求信号时置0
                    print("DB2拍照请求触发")
                    opc.SetDataByTagName("PLC", "LeftTakePhotoComplete", 0)
                    opc.SetDataByTagName("PLC", "LeftResult", 0)
                    opc.SetDataByTagName("PLC", "LeftAngle", 0)

                    threading.Thread(target=handle_left, daemon=True).start()
                else:
                    print("左相机忙，忽略请求")

            # ========= 线圈触发 =========
            if mid_req == 1 and last_mid == 0:
                print("检测到 线圈 拍照请求")

                if not mid_busy:
                    mid_busy = True
                    # 上位机完成拍照时置1，收到PLC拍照请求信号时置0
                    opc.SetDataByTagName("PLC", "MidTakePhotoComplete", 0)
                    opc.SetDataByTagName("PLC", "MidResult", 0)
                    opc.SetDataByTagName("PLC", "MidAngle", 0)

                    threading.Thread(target=handle_mid, daemon=True).start()
                else:
                    print("线圈相机忙，忽略请求")

            # ========= 右触发 =========
            if right_req == 1 and last_right == 0:
                print("检测到 Right 拍照请求")

                if not right_busy:
                    right_busy = True
                    # 上位机完成拍照时置1，收到PLC拍照请求信号时置0
                    opc.SetDataByTagName("PLC", "RightTakePhotoComplete", 0)
                    opc.SetDataByTagName("PLC", "RightResult", 0)
                    opc.SetDataByTagName("PLC", "RightAngle", 0)

                    threading.Thread(target=handle_right, daemon=True).start()
                else:
                    print("右相机忙，忽略请求")

            # 更新状态（用于上升沿检测）
            last_left = left_req
            last_right = right_req

            time.sleep(0.05) # 20Hz轮询

        except Exception as e:
            print("PLC通信异常:", e)
            time.sleep(1)


# ================左相机处理======================================
def handle_left():
    global left_busy
    global callback

    try:
        # 获取型号与相机配置地址
        type = opc.GetDataByTagName("PLC","LeftType")["value"]

        with open(r"D:/M26003Project/data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        camera_path = r"D:/M26003Project/Camera2.json"

        # 相机拍照获取照片
        img = TestCamera("Left", camera_path)


        # 算法返回img, angle
        if type == 4:
            res, angle = AngleCheckTest3.process_image(img)
        else:
            res, angle = AngleCheck2.process_image(img)

            if type == 2:
                angle = angle - 90.0

            # if angle > 30.0 or angle < -30.0:
            #     raise ValueError("角度偏移过大")

        print(f"发送给{type}机器人角度: {angle} ")

        # GUI监视,历史文件记录
        save_dir = r"D:\M26003Project\results\Left"
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = os.path.join(save_dir, filename)
        cv2.imwrite(filepath, res)

        cv2.imwrite(r"D:/M26003Project/tmp/left.jpg", res)


        # 角度结果写入plc
        opc.SetDataByTagName("PLC", "LeftAngle", float(angle))


        # 结果正常
        opc.SetDataByTagName("PLC", "LeftResult", 1)

    except Exception as e:
        opc.SetDataByTagName("PLC", "LeftResult", 2)
        print("左相机异常:", e)

    finally:
        left_busy = False


# ================线圈相机处理====================================
def handle_mid():
    global mid_busy
    global callback

    try:
        # 获取型号与相机配置地址
        type = opc.GetDataByTagName("PLC","MidType")["value"]

        with open(r"D:/M26003Project/data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        camera_path = r"D:/M26003Project/Camera2.json"

        # 相机拍照获取照片
        img = TestCamera("Mid", camera_path)


        # 算法返回img, angle

        res, angle = AngleCheckTest3.process_image(img)

        print(f"发送给{type}机器人角度: {angle} ")

        # GUI监视,历史文件记录
        save_dir = r"D:\M26003Project\results\Mid"
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = os.path.join(save_dir, filename)
        cv2.imwrite(filepath, res)

        cv2.imwrite(r"D:/M26003Project/tmp/mid.jpg", res)


        # 角度结果写入plc
        opc.SetDataByTagName("PLC", "MidAngle", float(angle))


        # 结果正常
        opc.SetDataByTagName("PLC", "MidResult", 1)

    except Exception as e:
        opc.SetDataByTagName("PLC", "MidResult", 2)
        print("线圈相机异常:", e)

    finally:
        left_busy = False


# ================右相机处理======================================
def handle_right():
    global right_busy
    global callback

    try:
        # 获取型号与相机地址
        type = "1"
        with open("D:/M26003Project/data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # camera_path = data[f"{type}"]["camera"]
        camera_path = "D:/M26003Project/Camera1.json"

        # 相机拍照获取照片
        img = TestCamera("Right", camera_path)

        # 算法返回img, angle
        res, angle = AngleGUI.process_image(img, data[f"{type}"])

        # GUI监视,历史文件记录
        save_dir = r"D:/M26003Project/results/Right/"
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = os.path.join(save_dir, filename)
        cv2.imwrite(filepath, res)

        cv2.imwrite("D:/M26003Project/tmp/right.jpg", res)

        # 角度结果写入plc
        opc.SetDataByTagName("PLC", "RightAngle", float(angle))

        # 结果正常
        opc.SetDataByTagName("PLC", "RightResult", 1)


    except Exception as e:
        opc.SetDataByTagName("PLC", "RightResult", 2)
        print("右相机异常:", e)

    finally:
        right_busy = False


if __name__ == '__main__':

    # =========单一测试==============
    # 文件读取测试 Test Accept√
    # TestFile()

    # PLC接口测试 读 Test Accept√
    # TestPlc ()

    # 相机拍照测试 Test Accept√
    # TestCamera("Left", "Camera1.json")

    # ==========集合测试=============

    # PLC监测线程 Test Accept√
    plc_monitor()

    # 相机调用测试 Test ERROR×
    # handle_left()
    # handle_right()


    print("TestComplete!")





