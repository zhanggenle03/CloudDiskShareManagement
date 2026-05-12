"""
Token Bucket 限流器 — 按平台隔离，平滑限制检测请求频率

每个平台独立桶实例，请求到达先获取令牌，令牌不够则阻塞等待。
桶容量(capacity) = 该平台线程数（从 settings 读取），速率(refill_rate)控制持续吞吐。

配置来源：settings 表（key 前缀 check_），fallback 到代码默认值。
"""

import time
import threading


class TokenBucket:
    """令牌桶"""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity          # 桶最大容量（= 线程数）
        self.refill_rate = refill_rate    # 每秒补充令牌数
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """
        获取 tokens 个令牌，令牌不够时阻塞等待。
        返回 True 表示成功获取。
        """
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                need = tokens - self._tokens
                sleep_time = need / self.refill_rate if self.refill_rate > 0 else 1.0
            time.sleep(sleep_time)

    @property
    def available(self) -> float:
        """当前可用令牌数（近似）"""
        with self._lock:
            self._refill()
            return self._tokens


def _load_platform_config(key_prefix: str, default_threads: int, default_rate: float):
    """
    从 settings 表读取平台配置，返回 (threads, rate)。
    bucket capacity = threads（不再单独配置容量）。
    """
    try:
        from database import get_conn
        conn = get_conn()
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (f'{key_prefix}_threads',)
        ).fetchone()
        threads = int(row['value']) if row else default_threads
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (f'{key_prefix}_rate',)
        ).fetchone()
        rate = float(row['value']) if row else default_rate
        conn.close()
        return max(1, threads), max(0.1, rate)
    except Exception:
        return default_threads, default_rate


def _load_global_config():
    """加载全局配置（重试相关）"""
    settings = {}
    keys = ['check_retry_count', 'check_baidu_cooldown']
    try:
        from database import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN ({})".format(
                ','.join('?' for _ in keys)
            ),
            keys
        ).fetchall()
        conn.close()
        for r in rows:
            settings[r['key']] = r['value']
    except Exception:
        pass

    return {
        'retry_count': int(settings.get('check_retry_count', '2')),
        'baidu_cooldown': int(settings.get('check_baidu_cooldown', '15')),
    }


# 初始加载全局配置
_global_config = _load_global_config()

# ── 全局桶实例（模块导入时从 DB 读取配置）───────────────────
baidu_threads, baidu_rate = _load_platform_config('check_baidu', 5, 1.0)
quark_threads, quark_rate = _load_platform_config('check_quark', 5, 2.0)
uc_threads, uc_rate = _load_platform_config('check_uc', 5, 1.5)

buckets = {
    'baidu': TokenBucket(capacity=baidu_threads, refill_rate=baidu_rate),
    'quark': TokenBucket(capacity=quark_threads, refill_rate=quark_rate),
    'uc':    TokenBucket(capacity=uc_threads, refill_rate=uc_rate),
}

# ── 导出各平台线程数（供 checker.py 使用）───────────────────
platform_threads = {
    'baidu': baidu_threads,
    'quark': quark_threads,
    'uc':    uc_threads,
}

# ── 导出常用配置常量（简化 checker.py 访问）────────────────
RetryCount = _global_config['retry_count']
BaiduCooldown = _global_config['baidu_cooldown']


def get_platform_threads(platform: str) -> int:
    """获取指定平台的线程数"""
    return platform_threads.get(platform, 5)


def reload_config():
    """
    重新加载所有配置（设置保存后调用）
    更新全局桶参数和配置常量。
    """
    global _global_config, RetryCount, BaiduCooldown
    global baidu_threads, baidu_rate, quark_threads, quark_rate, uc_threads, uc_rate
    global buckets, platform_threads

    _global_config = _load_global_config()
    RetryCount = _global_config['retry_count']
    BaiduCooldown = _global_config['baidu_cooldown']

    baidu_threads, baidu_rate = _load_platform_config('check_baidu', 5, 1.0)
    quark_threads, quark_rate = _load_platform_config('check_quark', 5, 2.0)
    uc_threads, uc_rate = _load_platform_config('check_uc', 5, 1.5)

    platform_threads['baidu'] = baidu_threads
    platform_threads['quark'] = quark_threads
    platform_threads['uc'] = uc_threads

    buckets['baidu'] = TokenBucket(capacity=baidu_threads, refill_rate=baidu_rate)
    buckets['quark'] = TokenBucket(capacity=quark_threads, refill_rate=quark_rate)
    buckets['uc'] = TokenBucket(capacity=uc_threads, refill_rate=uc_rate)
