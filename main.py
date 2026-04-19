"""
CloudDiskShareManagement - 打包入口文件
用于 PyInstaller 打包，替代 start.bat 的功能
"""
import os
import sys
import webbrowser
import threading

# ── 设置路径（支持 PyInstaller 打包）─────────────────────
if getattr(sys, 'frozen', False):
    # PyInstaller 打包环境
    BUNDLE_DIR = sys._MEIPASS        # _internal/ 目录
    APP_DIR = os.path.dirname(sys.executable)  # exe 所在目录
    BACKEND_DIR = os.path.join(BUNDLE_DIR, 'backend')
else:
    # 开发环境
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
    BACKEND_DIR = os.path.join(APP_DIR, 'backend')

sys.path.insert(0, BACKEND_DIR)

# ── 确保用户数据目录存在（exe 旁边） ──
DATA_DIR = os.path.join(APP_DIR, 'data')
LOG_DIR = os.path.join(DATA_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# ── 导入并启动 Flask ──
from app import app, on_startup, init_db, log

def open_browser():
    """延迟打开浏览器"""
    import time
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # 单实例保护 + PID 文件写入
    on_startup()
    
    # 初始化数据库
    init_db()
    
    log.info("=" * 50)
    log.info("  云盘分享管理工具 已启动")
    log.info("  访问地址: http://127.0.0.1:5000")
    log.info("=" * 50)
    
    # 启动后自动打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 启动应用
    app.run(host='127.0.0.1', port=5000, debug=False)
