import os
import threading

from src.OPC import OPC
import cv2
from Camera import Camera
from datetime import datetime
import time
import json

# 联通
from src import Project_414

# 初始
opc = OPC()
# 状态锁（防重复执行）
left_busy = False
right_busy = False

# 上一帧状态（用于上升沿检测）
last_left = 0
last_right = 0

def TestFile():
    with open("../data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    type = "单圆工件"
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
    result_tag = f"{side}Result"

    try:
        print(f"[{side}] 相机开始初始化")

        # 1. 加载配置
        Cam1.SetParamFile(camera_path)

        # 2. 打开相机
        Cam1.Open()

        # 3. 触发采集
        Cam1.TriggerOnce()
        img = Cam1.AcqImg()

        # 判空（非常关键！）
        if img is None or img.size == 0:
            raise Exception("采集到空图像")

        # 4. 保存图片
        save_dir = r"C:\Users\Administrator\Desktop\OpenCV_PROJECT\camImg"
        os.makedirs(save_dir, exist_ok=True)

        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{side}.jpg"
        filepath = os.path.join(save_dir, filename)

        success = cv2.imwrite(filepath, img)
        if not success:
            raise Exception("图片保存失败")

        print(f"[{side}] 拍照成功: {filepath}")

        # 5. 写PLC成功信号
        opc.SetDataByTagName("PLC", result_tag, 1)

        return img

    except Exception as e:
        print(f"[{side}] 相机异常:", e)

        # 写PLC失败信号
        try:
            opc.SetDataByTagName("PLC", result_tag, 2)
        except Exception as plc_err:
            print(f"[{side}] PLC写入失败:", plc_err)

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
    global last_left, last_right
    global left_busy, right_busy

    while True:
        try:
            # 读取PLC信号
            left_req = opc.GetDataByTagName("PLC", "LeftStartCameraRequest")["value"]
            right_req = opc.GetDataByTagName("PLC", "RightStartCameraRequest")["value"]

            # ========= 左触发 =========
            if left_req == 1 and last_left == 0:
                print("检测到 Left 拍照请求")


                if not left_busy:
                    left_busy = True
                    # 上位机完成拍照时置1，收到PLC拍照请求信号时置0
                    opc.SetDataByTagName("PLC", "LeftTakePhotoComplete", 0)

                    threading.Thread(target=handle_left, daemon=True).start()
                else:
                    print("左相机忙，忽略请求")

            # ========= 右触发 =========
            if right_req == 1 and last_right == 0:
                print("检测到 Right 拍照请求")

                if not right_busy:
                    right_busy = True
                    # 上位机完成拍照时置1，收到PLC拍照请求信号时置0
                    opc.SetDataByTagName("PLC", "LeftTakePhotoComplete", 0)

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

    try:
        # 获取型号与相机配置地址
        type = opc.GetDataByTagName("PLC", "LeftType")["value"]
        with open("../data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        camera_path = data[f"{type}"]["camera"]

        # 相机拍照获取照片
        img = TestCamera("Left",camera_path)

        # 算法返回img, angle
        _, angle = Project_414.process_image(img, data[f"{type}"])

        # 角度结果写入plc ==============错误点×=====================
        opc.SetDataByTagName("PLC", "LeftAngle", 1.2)

        # 处理完成，左侧拍照完成信号 : 上位机完成拍照时置1，收到PLC拍照请求信号时置0
        opc.SetDataByTagName("PLC", "LeftTakePhotoComplete", 1)

    except Exception as e:
        print("左相机异常:", e)

    finally:
        left_busy = False


# ================右相机处理======================================
def handle_right():
    global right_busy

    try:
        # 获取型号与相机地址
        type = opc.GetDataByTagName("PLC", "RightType")["value"]
        with open("../data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        camera_path = data[f"{type}"]["camera"]

        # 相机拍照获取照片
        print(camera_path)
        img = TestCamera("Right", camera_path)

        # 算法返回img, angle
        _, angle = Project_414.process_image(img, data[f"{type}"])

        # 角度结果写入plc
        opc.SetDataByTagName("PLC", "RightAngle", float(angle))

        # 处理完成，右侧拍照完成信号 : 上位机完成拍照时置1，收到PLC拍照请求信号时置0
        opc.SetDataByTagName("PLC", "RightTakePhotoComplete", 1)

    except Exception as e:
        print("右相机异常:", e)

    finally:
        right_busy = False


if __name__ == '__main__':

    # =========单一测试==============
    # 文件读取测试 Test Accept√
    # TestFile()

    # PLC接口测试 读 Test Accept√
    # TestPlc()

    # 相机拍照测试 Test Accept√
    # TestCamera("Left", "Camera1.json")

    # ==========集合测试=============

    # PLC监测线程 Test Accept√
    plc_monitor()

    # 相机调用测试 Test ERROR×
    # handle_left()
    # handle_right()





