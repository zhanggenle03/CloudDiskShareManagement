"""
日志配置模块 - RotatingFileHandler + 控制台双输出
日志文件: data/logs/app.log
单文件最大 5MB，保留 3 个备份，总共最多约 20MB
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from paths import LOG_DIR

# ── 日志文件路径 ──
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# ── 日志大小配置 ──
MAX_BYTES = 5 * 1024 * 1024   # 单文件最大 5MB
BACKUP_COUNT = 3                # 保留 3 个备份文件

# ── 日志格式 ──
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(name='app', level=logging.INFO):
    """
    创建并返回一个配置好的 logger。

    Args:
        name:  logger 名称（默认 'app'）
        level: 日志级别（默认 INFO）

    Returns:
        logging.Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── 控制台输出（打包时禁用） ──
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # ── 文件输出（带轮转） ──
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
