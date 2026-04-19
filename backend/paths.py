"""
路径配置 - 所有后端模块共享
支持 PyInstaller 打包环境
"""
import os
import sys

# 检测是否在打包环境中
FROZEN = getattr(sys, 'frozen', False)

if FROZEN:
    # PyInstaller 打包后的环境
    # sys._MEIPASS 是 PyInstaller 的临时解压目录
    BUNDLE_DIR = sys._MEIPASS
    # 可执行文件所在目录（用于数据存储）
    BASE_DIR = os.path.dirname(sys.executable)
    # 后端代码目录
    BACKEND_DIR = os.path.join(BUNDLE_DIR, 'backend')
else:
    # 普通开发环境
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = BASE_DIR
    BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# 前端目录（打包时在 BUNDLE_DIR，开发时在 BASE_DIR）
FRONTEND_DIR = os.path.join(BUNDLE_DIR, 'frontend')

# 数据目录（始终在 BASE_DIR，即 exe 同级目录）
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(DATA_DIR, 'logs')
DB_PATH = os.path.join(DATA_DIR, 'shares.db')

# PID 文件
PID_FILE = os.path.join(BASE_DIR, 'app.pid')
