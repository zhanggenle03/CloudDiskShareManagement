"""
UC网盘API封装 - 支持分享链接获取和管理
接口地址: https://pc-api.uc.cn/1/clouddrive/share/mypage/detail
"""
import requests
import json
import time
from datetime import datetime
from logger import setup_logger

log = setup_logger('uc_api')


class UCShareManager:
    """UC网盘分享管理器"""

    # UC网盘API基础地址
    BASE_URL = 'https://pc-api.uc.cn'
    SHARE_LIST_URL = f'{BASE_URL}/1/clouddrive/share/mypage/detail'

    def __init__(self, cookie: str):
        self.cookie = cookie
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cookie': cookie,
            'Referer': 'https://drive.uc.cn/',
            'Origin': 'https://drive.uc.cn',
        })
        # 禁用代理
        self.session.trust_env = False
        self.session.proxies = {'http': None, 'https': None}

    def validate_cookie(self):
        """
        验证Cookie是否有效
        通过请求分享列表接口来验证，返回数据则Cookie有效
        
        Returns:
            True: Cookie有效
            False: Cookie无效（401或认证失败）
            None: 验证过程中出错（网络问题等）
        """
        try:
            shares = self.get_share_list(page=1, page_size=1)
            if shares is None:
                return False
            return True
        except Exception as e:
            log.error(f'UC Cookie验证异常: {e}')
            return None

    def get_share_list(self, page: int = 1, page_size: int = 50):
        """
        获取分享列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            list: 分享列表（空列表也算有效，表示没有分享记录）
            None: Cookie无效或请求失败
        """
        params = {
            'pr': 'UCBrowser',
            'fr': 'pc',
            '_page': str(page),
            '_size': str(page_size),
            '_fetch_total': '1',
        }

        try:
            response = self.session.get(self.SHARE_LIST_URL, params=params, timeout=30)
            result = response.json()

            status = result.get('status')
            code = result.get('code')

            if status == 200 and code == 0:
                data = result.get('data', {})
                share_list = data.get('list', [])

                # 严格验证：data为空或不含list字段则Cookie无效
                if data is None:
                    log.error('UC API返回data为None，Cookie无效')
                    return None
                if not data and 'list' not in data:
                    log.error('UC API返回data为空字典，Cookie无效')
                    return None

                # 空列表合法（表示没有分享记录）
                if share_list:
                    log.info(f'获取UC分享列表成功，本页 {len(share_list)} 条')

                return share_list
            elif status == 401 or code == 31001:
                # Cookie失效: {"status":401,"code":31001,"message":"require login [guest]"}
                log.error('UC Cookie已失效(401)')
                return None
            else:
                log.warning(f'获取UC分享列表失败: status={status}, code={code}, message={result.get("message", "未知")}')
                return None

        except requests.exceptions.JSONDecodeError as e:
            log.error(f'UC API JSON解析失败，Cookie可能无效: {e}')
            return None
        except Exception as e:
            log.error(f'获取UC分享列表出错: {e}')
            return None

    def fetch_all_shares(self):
        """
        获取所有分享记录（自动翻页）
        
        Returns:
            list: 所有分享记录
            None: Cookie无效或请求失败
        """
        try:
            all_shares = []
            page = 1
            page_size = 50

            while True:
                log.info(f'正在获取UC分享列表第 {page} 页...')
                shares = self.get_share_list(page=page, page_size=page_size)
                if shares is None:
                    # 认证失败
                    log.error('UC Cookie认证失败，请重新配置Cookie')
                    return None
                if not shares:
                    break
                all_shares.extend(shares)
                # 如果本页数据不足一页，说明没有更多了
                if len(shares) < page_size:
                    break
                page += 1

            log.info(f'获取UC分享列表完成，共 {len(all_shares)} 条')
            return all_shares
        except Exception as e:
            log.error(f'获取UC所有分享失败: {e}')
            return None

    def parse_share_info(self, share_data: dict) -> dict:
        """
        解析单条分享数据为标准格式
        
        UC网盘API返回字段映射:
            title       → 分享名称
            share_url   → 分享链接
            passcode    → 提取码
            share_id    → 网盘端分享ID
            created_at  → 创建时间（毫秒时间戳）
            expired_type → 有效期类型 (1=永久有效, 4=限时有效)
            expired_days → 有效天数
            expired_left → 剩余毫秒数
            first_file.file_name → 文件名（title为空时的备选）
            save_pv + download_pv → 访问次数
        
        Args:
            share_data: API返回的单条分享数据
            
        Returns:
            dict: 标准化的分享信息
        """
        try:
            share_id = share_data.get('share_id', '')
            if not share_id:
                log.warning(f'UC分享数据缺少share_id: {share_data}')
                return None

            # 分享链接
            share_url = share_data.get('share_url', '')
            # 确保链接完整
            if share_url and not share_url.startswith('http'):
                share_url = f'https://drive.uc.cn/s/{share_url}'

            # 提取码: url_type=2表示有提取码，passcode字段存在
            share_pwd = share_data.get('passcode', '') or ''

            # 分享名称: title优先，其次first_file.file_name
            share_title = share_data.get('title', '')
            if not share_title:
                first_file = share_data.get('first_file', {})
                if first_file:
                    share_title = first_file.get('file_name', '')
            if not share_title:
                share_title = f'分享_{share_id[:8]}'

            # 创建时间: 毫秒时间戳
            create_time = share_data.get('created_at', 0) or 0
            if isinstance(create_time, (int, float)):
                if create_time > 1e12:  # 毫秒转秒
                    create_time = create_time / 1000
                share_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S') if create_time > 0 else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(create_time, str):
                share_time = create_time
            else:
                share_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 有效期
            expire_info = self._parse_expire_info(share_data)

            # 访问次数: UC网盘没有直接的浏览次数字段，用 save_pv + download_pv 替代
            save_pv = share_data.get('save_pv', 0) or 0
            download_pv = share_data.get('download_pv', 0) or 0
            view_count = save_pv + download_pv if (save_pv > 0 or download_pv > 0) else -1

            return {
                'source': 'uc',
                'name': share_title,
                'url': share_url,
                'pwd': share_pwd,
                'share_time': share_time,
                'expire': expire_info,
                'parent_dir': '',  # UC API不返回父目录信息
                'view_count': view_count,
                'share_id': str(share_id),
            }
        except Exception as e:
            log.error(f'解析UC分享信息出错: {e}')
            log.error(f'数据: {json.dumps(share_data, ensure_ascii=False)[:300]}')
            return None

    def _parse_expire_info(self, share_data: dict) -> str:
        """
        解析过期信息
        
        UC网盘 expired_type 含义:
            1 = 永久有效
            4 = 限时有效（需结合 expired_days 和 expired_left 字段）
        
        其他字段:
            expired_left: 剩余毫秒数
            expired_days: 有效天数
            expired_at: 过期时间戳（毫秒）
        
        Args:
            share_data: 分享数据
            
        Returns:
            str: 过期状态字符串
        """
        try:
            expired_type = share_data.get('expired_type', 1) or 1
            expired_days = share_data.get('expired_days', 0) or 0
            expired_left = share_data.get('expired_left', 0) or 0  # 剩余毫秒数
            expired_at = share_data.get('expired_at', 0) or 0  # 过期时间戳（毫秒）

            expired_type = int(expired_type)

            if expired_type == 1:
                # 永久有效
                return '永久有效'
            elif expired_type == 4:
                # 限时有效
                if expired_left <= 0:
                    return '已失效'
                remaining_days = int(expired_left / (86400 * 1000))
                if remaining_days > 0:
                    return f'{expired_days}天有效'
                else:
                    return '今天失效'
            else:
                # 其他类型，检查expired_at判断是否过期
                if expired_at > 0:
                    current_ms = int(time.time() * 1000)
                    if current_ms >= expired_at:
                        return '已失效'
                    remaining_ms = expired_at - current_ms
                    remaining_days = int(remaining_ms / (86400 * 1000))
                    if remaining_days > 0:
                        return f'{remaining_days}天有效'
                    else:
                        return '今天失效'
                return '永久有效'  # 默认

        except Exception as e:
            log.warning(f'解析UC过期信息出错: {e}')
            return '永久有效'

    def cancel_share(self, share_ids: list) -> dict:
        """
        取消分享
        
        UC网盘取消分享接口（与夸克网盘结构相似）:
        POST https://pc-api.uc.cn/1/clouddrive/share/delete?pr=UCBrowser&fr=pc
        Body: {"share_ids": ["share_id1", "share_id2", ...]}
        
        Args:
            share_ids: 要取消的分享ID列表
            
        Returns:
            dict: {
                'success': bool,
                'message': str,
                'cancelled': int,
                'failed': int
            }
        """
        if not share_ids:
            return {'success': False, 'message': '未指定要取消的分享ID', 'cancelled': 0, 'failed': 0}

        url = f'{self.BASE_URL}/1/clouddrive/share/delete'
        params = {
            'pr': 'UCBrowser',
            'fr': 'pc',
        }

        cancelled = 0
        failed = 0
        errors = []

        # 逐个取消，避免批量接口的一次性失败
        for sid in share_ids:
            data = {"share_ids": [sid]}
            try:
                response = self.session.post(url, params=params, json=data, timeout=30)
                result = response.json()

                status = result.get('status')
                code = result.get('code')

                if status == 200 and code == 0:
                    cancelled += 1
                    log.info(f'UC取消分享成功: share_id={sid}')
                elif status == 401:
                    log.error(f'UC取消分享失败: Cookie已失效(401), share_id={sid}')
                    failed += 1
                    errors.append(f'share_id={sid}: Cookie已失效')
                    # Cookie失效，后续也会失败，直接中断
                    break
                else:
                    msg = result.get('message', '未知错误')
                    log.warning(f'UC取消分享失败: share_id={sid}, status={status}, message={msg}')
                    failed += 1
                    errors.append(f'share_id={sid}: {msg}')
            except Exception as e:
                log.error(f'UC取消分享请求出错: share_id={sid}, error={e}')
                failed += 1
                errors.append(f'share_id={sid}: 请求出错')

        success = cancelled > 0
        message = f'取消完成：成功 {cancelled} 条'
        if failed > 0:
            message += f'，失败 {failed} 条'
        if errors:
            message += f'（{"; ".join(errors[:3])}）'

        return {
            'success': success,
            'message': message,
            'cancelled': cancelled,
            'failed': failed
        }
