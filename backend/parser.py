"""
CSV 解析器 - 支持百度网盘和夸克网盘导出格式
"""
import csv
import re
import io
import chardet
from logger import setup_logger

log = setup_logger('parser')


def detect_encoding(raw: bytes) -> str:
    result = chardet.detect(raw)
    enc = result.get('encoding') or 'utf-8'
    # 常见中文编码映射
    enc_map = {'gb2312': 'gbk', 'gb18030': 'gbk'}
    result_enc = enc_map.get(enc.lower(), enc)
    log.debug(f'检测文件编码: {result_enc}')
    return result_enc


def read_csv_content(file_content: bytes) -> list:
    """读取CSV内容，自动检测编码"""
    encoding = detect_encoding(file_content)
    try:
        text = file_content.decode(encoding)
    except Exception:
        log.warning(f'文件解码失败({encoding})，降级使用utf-8')
        text = file_content.decode('utf-8', errors='replace')
    return text


def parse_baidu_csv(text: str) -> list:
    """
    百度网盘格式：
    文件名, 链接, 提取码, 分享时间, 有效期
    """
    records = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        name = (row.get('文件名') or '').strip()
        url = (row.get('链接') or '').strip()
        pwd = (row.get('提取码') or '').strip()
        share_time = (row.get('分享时间') or '').strip()
        expire = (row.get('有效期') or '').strip()

        if not url or not url.startswith('http'):
            continue

        # 标准化过期状态
        expire = normalize_expire(expire)

        records.append({
            'source': 'baidu',
            'name': name if name else '未知文件',
            'url': url,
            'pwd': pwd,
            'share_time': share_time,
            'expire': expire,
            'parent_dir': '',
            'view_count': -1,
        })
    return records


def parse_quark_csv(text: str) -> list:
    """
    夸克网盘格式：
    分享文件上一级目录名称, 分享名, 分享地址, 提取码, 分享时间, 浏览次数, 分享状态
    分享地址字段是多行文本，链接藏在 "链接：https://..." 中
    """
    records = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        parent_dir = (row.get('分享文件上一级目录名称') or '').strip()
        name = (row.get('分享名') or '').strip()
        share_text = (row.get('分享地址') or '').strip()
        pwd = (row.get('提取码') or '').strip()
        share_time = (row.get('分享时间') or '').strip()
        view_count_str = (row.get('浏览次数') or '-1').strip()
        expire = (row.get('分享状态') or '').strip()

        # 从多行文本中提取链接
        url = extract_quark_url(share_text)
        if not url:
            continue

        try:
            view_count = int(view_count_str)
        except ValueError:
            view_count = -1

        expire = normalize_expire(expire)

        records.append({
            'source': 'quark',
            'name': name if name else '未知文件',
            'url': url,
            'pwd': pwd,
            'share_time': share_time,
            'expire': expire,
            'parent_dir': parent_dir,
            'view_count': view_count,
        })
    return records


def extract_quark_url(text: str) -> str:
    """从夸克分享地址字段中提取URL"""
    # 优先匹配 "链接：https://..."
    m = re.search(r'链接[：:]\s*(https?://[^\s\n]+)', text)
    if m:
        return m.group(1).strip()
    # 降级：直接找 URL
    m = re.search(r'(https?://pan\.quark\.cn/s/[A-Za-z0-9]+)', text)
    if m:
        return m.group(1).strip()
    return ''


def normalize_expire(expire: str) -> str:
    """标准化有效期字段"""
    expire = expire.strip()
    expired_keywords = ['已失效', '分享已过期', '分享失败']
    if any(k in expire for k in expired_keywords):
        return '已失效'
    return expire


def auto_detect_and_parse(file_content: bytes, filename: str = '') -> tuple:
    """
    自动检测网盘类型并解析
    返回: (records: list, source: str)
    """
    text = read_csv_content(file_content)

    # 通过表头判断类型
    first_line = text.split('\n')[0] if text else ''

    if '分享文件上一级目录名称' in first_line or '分享状态' in first_line:
        log.info(f'识别为夸克网盘格式: {filename}')
        return parse_quark_csv(text), 'quark'
    elif '文件名' in first_line and '有效期' in first_line:
        log.info(f'识别为百度网盘格式: {filename}')
        return parse_baidu_csv(text), 'baidu'
    else:
        # 通过URL特征猜测
        if 'pan.quark.cn' in text:
            log.info(f'通过URL特征识别为夸克网盘: {filename}')
            return parse_quark_csv(text), 'quark'
        elif 'pan.baidu.com' in text:
            log.info(f'通过URL特征识别为百度网盘: {filename}')
            return parse_baidu_csv(text), 'baidu'
        else:
            raise ValueError(f"无法识别CSV格式，文件名: {filename}")
