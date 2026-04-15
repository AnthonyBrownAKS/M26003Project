
#PLC DB 配置
db_variables = [
    {
        'db': 110,
        'vars': [
            # Bool类型信号
            {'name': 'CheckInRequest', 'offset': 0, 'bit': 1, 'type': 'Bool'},
            {'name': 'TorqueUploadRequest', 'offset': 0, 'bit': 2, 'type': 'Bool'},
            {'name': 'UploadRequest', 'offset': 0, 'bit': 3, 'type': 'Bool'},
            {'name': 'LabelRequest', 'offset': 0, 'bit': 4, 'type': 'Bool'},
            {'name': 'Heartbeat_PLC_MES', 'offset': 0, 'bit': 0, 'type': 'Bool'},

            # Int类型信号
            {'name': 'CheckInFinish', 'offset': 302, 'type': 'Int'},
            {'name': 'CheckInResult', 'offset': 312, 'type': 'Int'},
            {'name': 'ScrewGunCircles', 'offset': 212, 'type': 'Int'},
            {'name': 'ScrewGunResult', 'offset': 206, 'type': 'Int'},
            {'name': 'TorqueUploadFinish', 'offset': 304, 'type': 'Int'},
            {'name': 'TorqueUploadResult', 'offset': 314, 'type': 'Int'},
            {'name': 'ProductionResult', 'offset': 214, 'type': 'Int'},
            {'name': 'UploadFinish', 'offset': 306, 'type': 'Int'},
            {'name': 'UploadResult', 'offset': 316, 'type': 'Int'},
            {'name': 'DeviceStatus', 'offset': 216, 'type': 'Int'},
            {'name': 'DeviceStatusUploadFinish', 'offset': 308, 'type': 'Int'},
            {'name': 'DeviceStatusUploadResult', 'offset': 318, 'type': 'Int'},
            {'name': 'LabelFinish', 'offset': 310, 'type': 'Int'},
            {'name': 'Heartbeat_PC_PLC', 'offset': 300, 'type': 'Int'},

            # Float类型信号
            {'name': 'ScrewGunTorque', 'offset': 208, 'type': 'Float'},

            # String类型信号
            {'name': 'PCBCode', 'offset': 104, 'length': 50, 'type': 'String'},
            {'name': 'LabelQRCode', 'offset': 2, 'length': 31, 'type': 'String'},

            # Angle检测类型信号
            {'name': 'Type', 'offset': 104, 'length': 50, 'type': 'String'},
            {'name': 'StartCamera', 'offset': 2, 'length': 31, 'type': 'String'},
            {'name': 'AngleOutput', 'offset': 2, 'length': 31, 'type': 'String'},
            {'name': 'Result', 'offset': 2, 'length': 31, 'type': 'String'}
        ]
    }
]
