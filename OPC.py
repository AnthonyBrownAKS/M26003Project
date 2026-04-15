import requests
import json
import time
import os
import logging
from logging.handlers import RotatingFileHandler

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 然后创建 RotatingFileHandler
file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'opc_raw_data.log'),  # 使用 os.path.join 更安全
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)



# 创建独立的logger用于记录OPC请求和响应的原始数据
opc_raw_logger = logging.getLogger('opc_raw')
opc_raw_logger.setLevel(logging.DEBUG)









# 避免重复添加handler
if not opc_raw_logger.handlers:
    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 文件handler - 使用RotatingFileHandler按文件大小分割日志
    # 每个文件最大10MB，保留7个备份文件（约70MB总容量）
    # 当文件超过10MB时自动创建新文件，最多保留8个文件（当前+7个备份）
    file_handler = RotatingFileHandler(
        'logs/opc_raw_data.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,            # 保留7个备份文件
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    opc_raw_logger.addHandler(file_handler)

    # 控制台handler - 可选，如果需要在控制台也显示
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)
    # console_handler.setFormatter(formatter)
    # opc_raw_logger.addHandler(console_handler)

class OPC:
    """
    OPC通信类，用于与OPC服务器进行数据交互
    """

    def __init__(self):
        """
        初始化OPC类
        """
        pass

    # ===================================方法=========================================

    def GetDataByTagName(self, device_name, tag_name, value=""):
        """
        获取设备数据的函数

        :param device_name: 设备名称
        :param tag_name: 标签名称
        :param parameter: 参数
        :return: 统一格式: {"success": True, "value": any, "error_message": str|None}
        """
        # API端点
        url = "http://127.0.0.1:38000/api/Manage/GetData"

        # 查询参数
        params = {
             "TagName": tag_name,
            "DeviceName": device_name,
            "Value": value
        }

        # 请求头
        headers = {
            "accept": "application/json"
        }

        # 记录请求原始数据
        opc_raw_logger.info(f"[GetDataByTagName] 请求 - URL={url}, Params={params}, Headers={headers}")

        try:
            # 发送GET请求
            response = requests.get(url, params=params, headers=headers, timeout=10)

            # 检查响应状态
            response.raise_for_status()

            # 解析JSON响应
            result = response.json()
            # 记录原始返回数据
            opc_raw_logger.info(f"[GetDataByTagName] 响应 - 状态码={response.status_code}, 原始数据={result}")

            # 检查API返回的状态
            if result.get("status") == -1:
                msg = result.get("msg", "未知错误")
                print(f"错误信息: {msg}")
                return {
                    "success": True,
                    "value": None,
                    "error_message": msg
                }
            else:
                # print("请求成功")
                data = result.get("data")
                # print(f"返回数据: {data}")
                return {
                    "success": True,
                    "value": data.get("value"),
                    "error_message": None
                }

        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return {
                "success": False,
                "value": None,
                "error_message": f"请求异常: {str(e)}"
            }
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return {
                "success": False,
                "value": None,
                "error_message": f"响应解析失败: {str(e)}"
            }

    def SetDataByTagName(self, device_name, tag_name, value, max_retries=10):
        """
        设置设备数据的函数

        :param device_name: 设备名称
        :param tag_name: 标签名称
        :param value: 要设置的值
        :param max_retries: 最大重试次数，默认5次
        :return: 统一格式: {"success": True, "value": "1"/"0", "error_message": str|None}
        """
        # API端点
        url = "http://127.0.0.1:38000/api/Manage/SetData"

        for retry_count in range(max_retries):
            payload = {}
            # 请求体数据
            payload = {
                "TagName": tag_name,
                "Value": value,
                "DeviceName": device_name
            }

            # 请求头
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json"
            }

            # 记录请求原始数据
            opc_raw_logger.info(f"[SetDataByTagName] 请求(尝试{retry_count+1}/{max_retries}) - URL={url}, Payload={payload}, Headers={headers}")

            try:
                # 发送PUT请求
                response = requests.put(url, json=payload, headers=headers, timeout=10)

                # 检查响应状态
                response.raise_for_status()

                # 解析JSON响应
                result = response.json()
                # 记录原始返回数据
                opc_raw_logger.info(f"[SetDataByTagName] 响应(尝试{retry_count+1}/{max_retries}) - 状态码={response.status_code}, 原始数据={result}")

                # 检查API返回的状态
                if result.get("status") == -1:
                    msg = result.get("msg", "未知错误")
                    print(f"错误信息: {msg}")

                    # 如果不是最后一次重试，继续重试
                    if retry_count < max_retries - 1:
                        print(f"写入失败，正在重试... ({retry_count+1}/{max_retries})")
                        time.sleep(0.1)
                        continue

                    # 最后一次重试仍然失败
                    return {
                        "success": True,
                        "value": "0",
                        "error_message": f"写入失败，重试{max_retries}次失败: {msg}"
                    }

                # 写入请求成功，验证实际写入值
                print("数据设置请求成功")

                # 延迟一小段时间，等待PLC更新
                time.sleep(0.)

                # 读取验证
                verify_result = self.GetDataByTagName(device_name, tag_name)

                if verify_result.get("value") is None:
                    # 读取失败，尝试重试写入
                    if retry_count < max_retries - 1:
                        print(f"验证读取失败，正在重试写入... ({retry_count+1}/{max_retries})")
                        time.sleep(0.1)
                        continue

                    return {
                        "success": True,
                        "value": "0",
                        "error_message": f"写入失败，验证读取错误: {verify_result.get('error_message')}"
                    }

                # 比较写入值和读取值
                read_value = verify_result.get("value")

                # 转换为浮点数进行比较
                try:
                    write_float = float(value)
                    read_float = float(read_value) if read_value is not None else None

                    if read_float is not None and abs(read_float - write_float) < 0.0001:
                        # 写入验证成功
                        data = result.get("data")
                        print(f"返回数据: {data}")
                        print(f"写入成功，从PLC读取值为: {read_value}")
                        return {
                            "success": True,
                            "value": "1",
                            "error_message": f"写入成功，从PLC读取值为{read_value}"
                        }
                    else:
                        # 值不一致，重试
                        if retry_count < max_retries - 1:
                            print(f"值不一致，写入: {value}, 读取: {read_value}，正在重试... ({retry_count+1}/{max_retries})")
                            time.sleep(0.1)
                            continue

                        # 最后一次重试仍然不一致
                        return {
                            "success": True,
                            "value": "0",
                            "error_message": f"写入失败，重试{max_retries}次失败，最后读取值为: {read_value}"
                        }

                except (ValueError, TypeError) as e:
                    # 类型转换失败
                    if retry_count < max_retries - 1:
                        print(f"值类型转换失败，写入: {value}, 读取: {read_value}，正在重试... ({retry_count+1}/{max_retries})")
                        time.sleep(0.1)
                        continue

                    return {
                        "success": True,
                        "value": "0",
                        "error_message": f"写入失败，重试{max_retries}次失败，值类型转换错误: {str(e)}, 最后读取值为: {read_value}"
                    }

            except requests.exceptions.RequestException as e:
                print(f"请求失败: {e}")
                if retry_count < max_retries - 1:
                    print(f"网络异常，正在重试... ({retry_count+1}/{max_retries})")
                    time.sleep(0.1)
                    continue

                return {
                    "success": True,
                    "value": "0",
                    "error_message": f"写入失败，重试{max_retries}次失败，网络异常: {str(e)}"
                }
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                if retry_count < max_retries - 1:
                    print(f"JSON解析失败，正在重试... ({retry_count+1}/{max_retries})")
                    time.sleep(0.1)
                    continue

                return {
                    "success": True,
                    "value": "0",
                    "error_message": f"写入失败，重试{max_retries}次失败，响应解析失败: {str(e)}"
                }

    # ===================================方法=========================================

    def Open(self):
        """
        打开连接（保持接口兼容性）
        :return: dict
        """
        return {
            "success": True,
            "value": "1",
            "error_message": None
        }

    def Close(self):
        """
        关闭连接（保持接口兼容性）
        :return: dict
        """
        return {
            "success": True,
            "value": "1",
            "error_message": None
        }


# 使用示例
if __name__ == "__main__":
    # 创建OPC实例
    opc = OPC()

    # 调用API
    # print("\nGetData响应:")
    # result1 = opc.GetData("PLC", "testAlarm" )
    # print(result1)
    # # print("==================================================")
    # # result1 = opc.SetData("PLC", "testAlarm", "1")
    # # time.sleep(1)
    # result1 = opc.GetDataByTagName("PLC", "Tray_Loss")
    # print(result1)



    #伺服复位全局 6_自动模式


    #全局自动
    # result1 = opc.SetData("PLC", "Auto", "1")

    # result1 = opc.SetData("PLC", "ServoReset", "1")
    # time.sleep(1)
    # result1 = opc.SetData("PLC", "ServoReset", "0")

    # #设置轴6自动模式
    # # result1 = opc.SetData("PLC", "6_自动模式", "1")


    #设置6轴初始化
    # result1 = opc.SetData("PLC", "ServoInitialization", "1")
    # time.sleep(0.5)
    # result1 = opc.SetData("PLC", "ServoInitialization", "0")

    # #设置轴6使能 6_执行回零 6_速度参数
    # result1 = opc.SetData("PLC", "6_自动使能", "1")


    # result1 = opc.GetData("PLC", "6_就绪信号")

    # result1 = opc.SetData("PLC", "6_执行回零", "1")

    # result1 = opc.GetDataByTagName("PLC", "PalletInspection")

    # print(result1)
    # time.sleep(1)
    # result1 = opc.SetData("PLC", "6_速度参数", "20")

    # result1 = opc.SetData("PLC", "6_位置参数", "50")
    # time.sleep(0.5)

    result1 = opc.SetDataByTagName("PLC", "LeftType", "12")


    #全
    result1 = opc.GetDataByTagName("PLC", "LeftType", "1")
    print(result1)
