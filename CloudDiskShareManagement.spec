# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 项目根目录
root_dir = os.path.dirname(os.path.abspath(SPEC))

# 收集这些包的全部文件（包括子模块、数据文件等）
requests_datas, requests_binaries, requests_hiddenimports = collect_all('requests')
flask_datas, flask_binaries, flask_hiddenimports = collect_all('flask')
werkzeug_datas, werkzeug_binaries, werkzeug_hiddenimports = collect_all('werkzeug')
jinja2_datas, jinja2_binaries, jinja2_hiddenimports = collect_all('jinja2')
certifi_datas, certifi_binaries, certifi_hiddenimports = collect_all('certifi')
chardet_datas, chardet_binaries, chardet_hiddenimports = collect_all('chardet')
charset_normalizer_datas, charset_normalizer_binaries, charset_normalizer_hiddenimports = collect_all('charset_normalizer')
idna_datas, idna_binaries, idna_hiddenimports = collect_all('idna')
urllib3_datas, urllib3_binaries, urllib3_hiddenimports = collect_all('urllib3')

a = Analysis(
    ['main.py'],
    pathex=[root_dir],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('backend', 'backend'),
    ] + requests_datas + flask_datas + werkzeug_datas + jinja2_datas + certifi_datas + chardet_datas + charset_normalizer_datas + idna_datas + urllib3_datas,
    hiddenimports=[
        'flask',
        'flask_cors',
        'chardet',
        'sqlite3',
        'sqlite3.dbapi2',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.compat',
        'requests.cookies',
        'requests.exceptions',
        'requests.hooks',
        'requests.models',
        'requests.packages',
        'requests.sessions',
        'requests.structures',
        'requests.utils',
        'werkzeug',
        'werkzeug.routing',
        'werkzeug.serving',
        'werkzeug.debug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
        # 标准库模块
        'logging',
        'logging.handlers',
        'logging.config',
        'datetime',
        'json',
        'signal',
        'subprocess',
        'threading',
        'traceback',
        'http',
        'http.client',
        'http.server',
        'email',
        'email.mime',
        'email.mime.text',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'collections',
        'hashlib',
        'hmac',
        'tempfile',
        'importlib',
        'importlib.resources',
        'html',
        'html.parser',
        'html.entities',
        'urllib',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'urllib.response',
        'csv',
        're',
        'io',
        'webbrowser',
    ] + requests_hiddenimports + flask_hiddenimports + werkzeug_hiddenimports + jinja2_hiddenimports + certifi_hiddenimports + chardet_hiddenimports + charset_normalizer_hiddenimports + idna_hiddenimports + urllib3_hiddenimports,
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
    console=True,  # 先用 console 模式方便调试，确认无误后改 False
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
