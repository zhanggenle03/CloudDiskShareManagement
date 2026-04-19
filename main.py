"""
CloudDiskShareManagement - 打包入口文件
用于 PyInstaller 打包，替代 start.bat 的功能
"""
import os
import sys

# 确保 backend 目录在 Python 路径中
if getattr(sys, 'frozen', False):
    # PyInstaller 打包环境
    bundle_dir = sys._MEIPASS
    backend_dir = os.path.join(bundle_dir, 'backend')
else:
    # 开发环境
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(bundle_dir, 'backend')

sys.path.insert(0, backend_dir)

# 确保 data 目录存在
if getattr(sys, 'frozen', False):
    data_dir = os.path.join(os.path.dirname(sys.executable), 'data')
else:
    data_dir = os.path.join(bundle_dir, 'data')
os.makedirs(data_dir, exist_ok=True)

# 导入并启动 Flask
from app import app, on_startup, init_db, log

if __name__ == '__main__':
    # 单实例保护 + PID 文件写入
    on_startup()
    
    # 初始化数据库
    init_db()
    
    log.info("=" * 50)
    log.info("  云盘分享管理工具 已启动")
    log.info("  访问地址: http://127.0.0.1:5000")
    log.info("=" * 50)
    
    # 启动应用（单线程）
    app.run(host='127.0.0.1', port=5000, debug=False)
