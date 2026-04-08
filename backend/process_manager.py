"""
进程管理模块
提供单实例保护、优雅关闭、强制终止、重启等功能
"""
import os
import sys
import signal
import subprocess
import time

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
PID_FILE = os.path.join(BASE_DIR, 'app.pid')


def get_logger():
    """延迟获取 logger，避免循环导入"""
    try:
        from logger import setup_logger
        return setup_logger('process_manager')
    except Exception:
        # 如果 logger 未初始化，使用简单的 print
        class SimpleLogger:
            def debug(self, msg): print(f"[DEBUG] {msg}")
            def info(self, msg): print(f"[INFO] {msg}")
            def warning(self, msg): print(f"[WARN] {msg}")
            def error(self, msg): print(f"[ERROR] {msg}")
        return SimpleLogger()


# ── PID 文件操作 ──────────────────────────────────────────

def write_pid():
    """写入当前进程 PID 到文件"""
    log = get_logger()
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        log.debug(f'PID文件已写入: {os.getpid()}')
    except Exception as e:
        log.warning(f'写入PID文件失败: {e}')


def read_pid():
    """读取 PID 文件中的进程号，失败返回 None"""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except (ValueError, IOError):
        pass
    return None


def remove_pid():
    """删除 PID 文件"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass


# ── 进程状态检查 ──────────────────────────────────────────

def is_process_alive(pid):
    """检查进程是否存活"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # 信号 0 不发送任何信号，但能检测进程是否存在
        return True
    except OSError:
        return False


def is_same_process(pid):
    """检查 PID 是否是当前进程"""
    return pid == os.getpid()


# ── 进程终止 ──────────────────────────────────────────────

def kill_process(pid):
    """
    终止指定进程（Windows 专用版本）

    Args:
        pid: 进程ID

    Returns:
        bool: 是否成功终止
    """
    log = get_logger()

    if pid is None:
        return True

    # Windows: 使用 taskkill 强制终止
    try:
        # /T 表示终止进程及其所有子进程
        # /F 表示强制终止
        result = subprocess.run(
            f'taskkill /F /T /PID {pid}',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            log.info(f'进程已终止: pid={pid}')
            return True
        else:
            log.warning(f'taskkill 返回: {result.returncode}, stderr: {result.stderr}')
            return False
    except Exception as e:
        log.error(f'终止进程失败: {e}')
        return False


def terminate_process(pid, timeout=3.0):
    """
    终止指定进程（优雅终止 + 超时强制终止）

    Args:
        pid: 进程ID
        timeout: 超时时间（秒）

    Returns:
        bool: 是否成功终止
    """
    log = get_logger()

    if pid is None or not is_process_alive(pid):
        log.debug(f'进程 {pid} 不存在，无需终止')
        return True

    log.info(f'正在终止进程: pid={pid}')

    # 阶段1: 优雅终止 (SIGTERM)
    try:
        os.kill(pid, signal.SIGTERM)
        log.debug(f'已发送 SIGTERM 到进程 {pid}')
    except OSError as e:
        log.warning(f'SIGTERM 失败: {e}')

    # 阶段2: 等待进程退出
    start_time = time.time()
    check_interval = 0.1

    while time.time() - start_time < timeout:
        if not is_process_alive(pid):
            log.info(f'进程已退出: pid={pid}')
            return True
        time.sleep(check_interval)

    # 阶段3: 超时，强制终止
    log.warning(f'进程未响应 SIGTERM，执行强制终止: pid={pid}')
    if kill_process(pid):
        return True

    return False


# ── 单实例保护 ────────────────────────────────────────────

def ensure_single_instance():
    """
    确保只有一个实例运行
    清理残留的旧进程

    Returns:
        bool: True 表示继续启动，False 表示应该退出
    """
    log = get_logger()
    old_pid = read_pid()

    if old_pid is None:
        log.debug('无残留 PID 文件，继续启动')
        return True

    if is_same_process(old_pid):
        log.debug('当前进程 PID 与文件一致，继续启动')
        return True

    # 旧进程存在，尝试清理
    if is_process_alive(old_pid):
        log.info(f'发现旧进程正在运行: pid={old_pid}，正在终止...')
        if terminate_process(old_pid, timeout=3.0):
            log.info('旧进程已清理完毕')
        else:
            log.warning('旧进程清理超时，将继续尝试启动')
    else:
        log.info(f'旧进程已不存在 (pid={old_pid})，清理残留 PID 文件')

    remove_pid()
    return True


# ── 服务关闭 ──────────────────────────────────────────────

def shutdown_service():
    """
    关闭服务（同步执行，直接终止当前进程）
    这是最终的关闭手段，确保进程必定退出
    """
    log = get_logger()
    pid = os.getpid()

    log.info(f'正在关闭服务: pid={pid}')

    # 清理 PID 文件
    remove_pid()

    # 强制终止当前进程（最可靠的方式）
    log.info('服务即将关闭')
    os._exit(0)


def graceful_shutdown():
    """
    优雅关闭服务
    发送 SIGTERM 信号，让进程自行清理后退出
    """
    log = get_logger()
    pid = os.getpid()

    log.info(f'准备优雅关闭: pid={pid}')

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass  # 进程可能已经退出

    return True


# ── 服务重启 ──────────────────────────────────────────────

def _do_restart():
    """
    执行重启的具体逻辑（在后台线程中执行）
    """
    log = get_logger()
    old_pid = os.getpid()
    log.info(f'当前进程: pid={old_pid}')

    # 阶段1: 启动新进程（先启动，确保服务不中断）
    log.info('阶段 1/2: 启动新进程...')
    app_path = os.path.join(BACKEND_DIR, 'app.py')

    # 选择合适的 Python 解释器
    python_exe = sys.executable
    if sys.platform == 'win32':
        pythonw = python_exe.replace('python.exe', 'pythonw.exe')
        if os.path.exists(pythonw):
            python_exe = pythonw

    new_process = None
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        new_process = subprocess.Popen(
            [python_exe, app_path],
            cwd=BASE_DIR,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log.info(f'新进程已启动: PID={new_process.pid}')
    except Exception as e:
        log.error(f'启动新进程失败: {e}')
        return

    # 给新进程一点时间初始化
    time.sleep(1.5)

    # 阶段2: 终止旧进程
    log.info('阶段 2/2: 终止旧进程...')
    terminate_process(old_pid, timeout=3.0)

    log.info('旧进程即将退出')
    os._exit(0)


def restart_service():
    """
    重启服务（在后台线程中执行）
    先启动新进程，再终止旧进程（保证服务不中断）
    """
    import threading
    log = get_logger()
    log.info('=' * 40)
    log.info('  准备重启服务')
    log.info('=' * 40)

    # 在后台线程执行重启逻辑，让 Flask 能先返回响应
    t = threading.Thread(target=_do_restart, daemon=True)
    t.start()


# ── 启动钩子 ──────────────────────────────────────────────

def on_startup():
    """
    应用启动时的初始化
    调用此函数完成单实例保护和 PID 文件写入
    """
    remove_pid()  # 先清理可能的残留
    ensure_single_instance()
    write_pid()


def on_shutdown():
    """
    应用关闭时的清理
    """
    remove_pid()
    get_logger().info('PID 文件已清理')
