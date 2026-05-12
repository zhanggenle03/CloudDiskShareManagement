"""
分享链接有效性检测模块

夸克网盘 — 两步 API 验证:
  1. POST sharepage/token → 获取 stoken
  2. GET  sharepage/detail → 获取文件列表
  有效条件: status=200, code=0, stoken 非空, list 非空

百度网盘 — 两步 API 验证:
  1. POST share/verify → 验证提取码，获取 randsk (BDCLND)
  2. GET  share/list → 检查 errno
  有效条件: errno=0

UC 网盘 — 页面内容分析:
  访问分享页面 → 关键词匹配
"""
import re
import time as _time
import concurrent.futures
from dataclasses import dataclass, asdict
from typing import Optional

import requests

from logger import setup_logger

log = setup_logger('checker')

# ── 请求配置 ──
TIMEOUT = 15
MAX_WORKERS = 5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36"
)

# ── 数据结构 ──

@dataclass
class CheckResult:
    """检测结果"""
    valid: bool
    failure_reason: str = ""
    duration_ms: int = 0
    status_code: int = 0
    error: Optional[str] = None
    is_rate_limited: bool = False


# ── 辅助函数 ──

def _elapsed_ms(start: float) -> int:
    """返回从 start 到现在的毫秒数"""
    return int((_time.time() - start) * 1000)


def _extract_clean_url(text: str) -> str:
    """从混合文本中提取干净 URL（如"链接：https://..."）"""
    for p in [
        r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
        r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
        r'https?://drive\.uc\.cn/s/[a-zA-Z0-9]+',
    ]:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return text


def detect_platform(url: str) -> Optional[str]:
    """根据 URL 识别分享链接所属平台"""
    url = _extract_clean_url(url.strip() if url else '')
    if re.match(r'https?://pan\.baidu\.com/s/', url):
        return 'baidu'
    if re.match(r'https?://pan\.quark\.cn/s/', url):
        return 'quark'
    if re.match(r'https?://drive\.uc\.cn/s/', url):
        return 'uc'
    return None


# ── 夸克网盘检测 ──

def _quark_extract_params(url: str):
    from urllib.parse import urlparse, parse_qs
    clean_url = _extract_clean_url(url)
    parsed = urlparse(clean_url)
    path = parsed.path
    if not path.startswith('/s/'):
        return None, None
    pwd_id = path.removeprefix('/s/').split('/')[0]
    passcode = parse_qs(parsed.query).get('pwd', [None])[0]
    return pwd_id or None, passcode


def _quark_check(pwd_id: str, passcode: str):
    stoken = None
    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Origin': 'https://pan.quark.cn',
        'Referer': 'https://pan.quark.cn/',
    }
    # 第1步：获取 stoken
    try:
        resp = requests.post(
            'https://drive-h.quark.cn/1/clouddrive/share/sharepage/token',
            json={'pwd_id': pwd_id, 'passcode': passcode or '', 'support_visit_limit_private_share': True},
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 200 and data.get('code') == 0:
                stoken = data.get('data', {}).get('stoken')
    except Exception:
        pass

    if not stoken:
        return CheckResult(False, failure_reason='分享链接失效或不存在')

    # 第2步：获取文件列表
    try:
        resp = requests.get(
            'https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail',
            params={'pwd_id': pwd_id, 'stoken': stoken, 'ver': '2', 'pr': 'ucpro'},
            headers={**headers, 'Accept': 'application/json'},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return CheckResult(False, failure_reason=f'HTTP错误: {resp.status_code}')
        data = resp.json()
        if data.get('status') != 200 or data.get('code') != 0:
            return CheckResult(False, failure_reason='API返回错误')
        if not data.get('data', {}).get('list'):
            return CheckResult(False, failure_reason='分享文件列表为空')
        return CheckResult(True)
    except requests.exceptions.Timeout:
        return CheckResult(True)  # 超时保守判定有效
    except Exception as e:
        return CheckResult(False, failure_reason=f'请求异常: {str(e)[:50]}')


def check_quark(url: str, pwd: str = '') -> CheckResult:
    start = _time.time()
    pwd_id, passcode = _quark_extract_params(url)
    if not pwd_id:
        return CheckResult(False, failure_reason='无法提取分享ID', duration_ms=_elapsed_ms(start))
    result = _quark_check(pwd_id, passcode or pwd)  # passcode优先URL提取，其次传入参数
    result.duration_ms = _elapsed_ms(start)
    return result


# ── 百度网盘检测 ──

def _baidu_extract_params(url: str):
    from urllib.parse import urlparse, parse_qs
    clean_url = _extract_clean_url(url)
    parsed = urlparse(clean_url)
    path = parsed.path
    if '/s/' in path:
        surl = path.split('/s/')[1].split('/')[0].split('?')[0]
    elif '/share/init' in path:
        surl = parse_qs(parsed.query).get('surl', [None])[0]
        if surl and surl.startswith('/'):
            surl = surl[1:]
    else:
        return None, None
    pwd = parse_qs(parsed.query).get('pwd', [None])[0]
    return surl, pwd


BAIDU_ERRNO_REASONS = {
    -12: '缺少提取码',
    -9:  '提取码错误',
    -8:  '分享文件已过期',
    -62: '请求接口受限（频率限制）',
    9019: '需要提取码',
}


def check_baidu(url: str, pwd: str = '') -> CheckResult:
    start = _time.time()
    surl, url_pwd = _baidu_extract_params(url)
    if not surl:
        return CheckResult(False, failure_reason='无法提取分享ID', duration_ms=_elapsed_ms(start))

    shorturl = surl[1:] if len(surl) > 1 else surl
    effective_pwd = pwd or url_pwd  # 优先使用传入的pwd，其次URL中提取的

    # 第1步：验证提取码
    randsk = None
    if effective_pwd:
        from urllib.parse import quote as _quote
        try:
            resp = requests.post(
                f'https://pan.baidu.com/share/verify?surl={_quote(shorturl)}&pwd={_quote(effective_pwd)}',
                data={'pwd': effective_pwd, 'vcode': '', 'vcode_str': ''},
                headers={
                    'User-Agent': USER_AGENT,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f'https://pan.baidu.com/s/{shorturl}',
                },
                timeout=TIMEOUT,
            )
            data = resp.json()
            if data.get('errno') == 0:
                randsk = data.get('randsk')
        except Exception as e:
            log.debug(f'百度 verify 失败: {e}')

        if randsk is None:
            return CheckResult(False, failure_reason='验证提取码失败', duration_ms=_elapsed_ms(start))

    # 第2步：获取分享列表
    try:
        from urllib.parse import quote as _quote
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
        if randsk:
            headers['Cookie'] = f'BDCLND={randsk}'
        resp = requests.get(
            f'https://pan.baidu.com/share/list?web=5&app_id=250528&desc=1&showempty=0'
            f'&page=1&num=20&order=time&shorturl={_quote(shorturl)}'
            f'&root=1&view_mode=1&channel=chunlei&web=1&clienttype=0',
            headers=headers, timeout=TIMEOUT,
        )
        data = resp.json()
        errno = data.get('errno', -1)
        elapsed = _elapsed_ms(start)
        if errno == 0:
            return CheckResult(True, duration_ms=elapsed)
        reason = BAIDU_ERRNO_REASONS.get(errno, f'分享链接无效 (errno: {errno})')
        return CheckResult(False, failure_reason=reason, duration_ms=elapsed, is_rate_limited=(errno == -62))
    except Exception as e:
        return CheckResult(False, failure_reason=f'请求失败: {str(e)[:80]}', duration_ms=_elapsed_ms(start))


# ── UC 网盘检测 ──

UC_FAILURE_KW = ['失效', '不存在', '违规', '删除', '已过期', '被取消']
UC_VALID_KW = ['文件', '分享']


def check_uc(url: str) -> CheckResult:
    start = _time.time()
    m = re.search(r'drive\.uc\.cn/s/([a-zA-Z0-9]+)', _extract_clean_url(url))
    if not m:
        return CheckResult(False, failure_reason='无法提取分享ID', duration_ms=_elapsed_ms(start))

    share_id = m.group(1)
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 10; SM-G975F) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/87.0.4280.101 Mobile Safari/537.36'
        ),
    }
    try:
        resp = requests.get(f'https://drive.uc.cn/s/{share_id}', headers=headers, timeout=TIMEOUT)
        elapsed = _elapsed_ms(start)
        if resp.status_code != 200:
            return CheckResult(False, failure_reason=f'HTTP状态码: {resp.status_code}',
                              status_code=resp.status_code, duration_ms=elapsed)

        text = resp.text
        for kw in UC_FAILURE_KW:
            if kw in text:
                return CheckResult(False, failure_reason='链接已失效', status_code=200, duration_ms=elapsed)
        for kw in UC_VALID_KW:
            if kw in text:
                return CheckResult(True, status_code=200, duration_ms=elapsed)
        return CheckResult(False, failure_reason='无法判断链接有效性', status_code=200, duration_ms=elapsed)
    except requests.exceptions.Timeout:
        return CheckResult(True, duration_ms=_elapsed_ms(start))
    except requests.exceptions.ConnectionError:
        return CheckResult(True, duration_ms=_elapsed_ms(start))
    except Exception as e:
        return CheckResult(False, failure_reason=f'请求失败: {str(e)[:100]}', duration_ms=_elapsed_ms(start))


# ── 统一入口 ──

PLATFORM_CHECKERS = {
    'baidu': check_baidu,
    'quark': check_quark,
    'uc':    check_uc,
}


def check_share_url(url: str, pwd: str = '') -> CheckResult:
    """检测单个分享链接的有效性"""
    if not url:
        return CheckResult(False, failure_reason='链接为空')
    platform = detect_platform(url)
    if not platform:
        return CheckResult(False, failure_reason='无法识别网盘平台')
    if platform == 'baidu':
        return check_baidu(url, pwd)
    if platform == 'quark':
        return check_quark(url, pwd)
    if platform == 'uc':
        return check_uc(url)
    return CheckResult(False, failure_reason='该平台检测器未实现')


def batch_check(shares: list) -> dict:
    """
    批量检测分享链接有效性（并发）

    shares: list of dict，每个元素至少含 'id', 'url', 'name', 'source'
    返回: { total, valid_count, invalid_count, results: [...] }
    """
    total = len(shares)
    results = [None] * total
    valid_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {}
        for idx, share in enumerate(shares):
            f = pool.submit(check_share_url, share.get('url', ''), share.get('pwd', ''))
            future_map[f] = idx

        for f in concurrent.futures.as_completed(future_map):
            idx = future_map[f]
            s = shares[idx]
            try:
                r = f.result()
            except Exception as e:
                r = CheckResult(False, failure_reason=f'检测异常: {str(e)[:100]}')
            item = {
                'id': s.get('id'),
                'source': s.get('source', ''),
                'name': s.get('name', ''),
                'url': s.get('url', ''),
                'pwd': s.get('pwd', ''),
                'valid': r.valid,
                'failure_reason': r.failure_reason,
                'duration_ms': r.duration_ms,
                'status_code': r.status_code,
                'is_rate_limited': r.is_rate_limited,
            }
            results[idx] = item
            if r.valid:
                valid_count += 1

    invalid_count = total - valid_count
    log.info(f'有效性检测完成: 总计 {total}, 有效 {valid_count}, 失效 {invalid_count}')
    return {
        'total': total,
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'results': results,
    }
