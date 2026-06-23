"""
系统托盘模块
启动后最小化到托盘，右击弹出菜单：打开浏览器 / 退出
依赖 pystray + Pillow（可选——缺失时托盘不工作但不影响主程序）
"""
import os
import sys
import webbrowser
from pathlib import Path
from typing import Callable


# ── 路径 ──
BACKEND_DIR = Path(__file__).resolve().parent                     # backend/
PROJECT_ROOT = BACKEND_DIR.parent                                  # 项目根目录
FRONTEND_DIR = PROJECT_ROOT / "frontend"                           # frontend/
ICON_PATH = FRONTEND_DIR / "app-icon.jpg"


def _get_icon_image():
    """
    加载托盘图标
    优先使用 frontend/app-icon.jpg；
    开发版直接读取，打包版从 _MEIPASS/frontend/ 读取；
    找不到则用 PIL 画占位图标
    """
    from PIL import Image, ImageDraw

    # 打包环境：从 BUNDLE_DIR/frontend/ 找
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        pkg_icon = bundle_dir / "frontend" / "app-icon.jpg"
        if pkg_icon.exists():
            return Image.open(str(pkg_icon))

    # 开发环境
    if ICON_PATH.exists():
        return Image.open(str(ICON_PATH)).resize((64, 64), Image.LANCZOS)

    # fallback：生成 64x64 蓝色图标
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=14,
        fill=(39, 112, 237),
    )
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("msyh.ttc", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size // 2, size // 2), "云", fill="white", font=font, anchor="mm")
    return img


def _open_browser():
    """打开浏览器访问应用"""
    webbrowser.open("http://127.0.0.1:5000/")


def _quit_app():
    """退出应用"""
    from process_manager import shutdown_service
    shutdown_service()


def start_tray(on_setup: Callable | None = None):
    """
    启动系统托盘（阻塞运行，通常放子线程）
    on_setup: 图标创建完毕后的回调（可用于设置菜单等）
    """
    import pystray

    img = _get_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("打开浏览器", lambda: _open_browser(), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda: _quit_app()),
    )

    icon = pystray.Icon(
        "CloudDiskShareManagement",
        img,
        "云盘分享管理工具",
        menu,
    )

    if on_setup:
        on_setup(icon)

    icon.run()
