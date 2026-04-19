# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# 项目根目录
root_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[root_dir],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('data', 'data'),
        ('backend', 'backend'),
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'chardet',
        'sqlite3',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
        'requests',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
        # 标准库模块（PyInstaller 可能遗漏）
        'logging',
        'logging.handlers',
        'logging.config',
        'datetime',
        'json',
        'sqlite3',
        'sqlite3.dbapi2',
        'signal',
        'subprocess',
        'threading',
        'traceback',
        'email',
        'email.mime',
        'email.mime.text',
        'http',
        'http.client',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'collections',
        'hashlib',
        'hmac',
        'tempfile',
        'importlib',
        'importlib.resources',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CloudDiskShareManagement',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed mode, no console
    icon='app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CloudDiskShareManagement',
)
