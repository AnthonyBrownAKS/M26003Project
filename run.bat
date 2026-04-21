@echo off
:: 1. 切换到 D 盘
d:

:: 2. 切换到项目根目录 (这对 -m 参数至关重要)
cd D:\M26003Project

:: 3. 使用指定的虚拟环境解释器，以模块方式运行
:: 注意：路径已用双引号包裹，防止路径中有空格导致报错
"D:\M26003Project\.venv\Scripts\python.exe" -m src.PLC_Control

:: 4. 运行结束后暂停，方便查看日志
pause