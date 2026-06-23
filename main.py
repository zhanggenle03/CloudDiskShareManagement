"""
CloudDiskShareManagement - 打包入口文件
用于 PyInstaller 打包，替代 start.bat 的功能
"""
import os
import sys
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

if __name__ == '__main__':
    # 单实例保护 + PID 文件写入
    on_startup()
    
    # 初始化数据库
    init_db()
    
    log.info("=" * 50)
    log.info("  云盘分享管理工具 已启动")
    log.info("  托盘图标已驻留系统栏，右键可打开浏览器或退出")
    log.info("=" * 50)
    
    # ── 启动系统托盘（子线程） ──
    try:
        from tray_icon import start_tray as start_tray_thread
        _tray_thread = threading.Thread(target=start_tray_thread, daemon=True, name="TrayIcon")
        _tray_thread.start()
        log.info("系统托盘已启动")
    except Exception as e:
        log.warning(f"系统托盘启动失败（可忽略，不影响核心功能）: {e}")
    
    # 启动应用
    app.run(host='127.0.0.1', port=5000, debug=False)
