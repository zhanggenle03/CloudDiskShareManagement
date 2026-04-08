"""
夸克网盘 API 封装模块 - 支持分享链接获取和管理
"""
import requests
import json
import time
import re
from datetime import datetime
from logger import setup_logger

log = setup_logger('quark_api')


class QuarkBase:
    """夸克网盘API基础类"""

    def __init__(self, cookie, kps=None, sign=None, vcode=None):
        """
        初始化基础类
        :param cookie: 登录夸克网盘后的cookie
        :param kps: 可选的kps认证参数(从客户端抓包获取)
        :param sign: 可选的sign认证参数(从客户端抓包获取)
        :param vcode: 可选的vcode认证参数(从客户端抓包获取)
        """
        self.cookie = cookie
        self.kps = kps
        self.sign = sign
        self.vcode = vcode
        self.headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Origin': 'https://pan.quark.cn',
            'Pragma': 'no-cache',
            'Priority': 'u=1, i',
            'Referer': 'https://pan.quark.cn/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        # 添加认证头(如果有的话)
        if self.kps:
            self.headers['x-u-kps-wg'] = self.kps
        if self.sign:
            self.headers['x-u-sign-wg'] = self.sign
        if self.vcode:
            self.headers['x-u-vcode'] = self.vcode
        self.base_params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }
        # 禁用代理，避免代理导致的SSL错误
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {'http': None, 'https': None}

    def _poll_task_status(self, task_id, max_retries=10, retry_interval=1):
        """轮询任务状态"""
        url = 'https://drive-pc.quark.cn/1/clouddrive/task'
        for i in range(max_retries):
            try:
                params = self.base_params.copy()
                params.update({
                    'task_id': task_id,
                    'retry_index': i
                })
                response = self.session.get(url, headers=self.headers, params=params, timeout=30)
                result = response.json()

                if result.get('code') == 0:
                    task_data = result.get('data', {})
                    status = task_data.get('status')
                    if status == 2:
                        log.info(f"任务 {task_id} 成功.")
                        return task_data
                    elif status == 3:
                        log.warning(f"任务 {task_id} 失败: {task_data.get('message', '未知错误')}")
                        return None
                    else:
                        progress = task_data.get('progress', 0)
                        log.debug(f"任务 {task_id} 进行中... {progress}%")

                time.sleep(retry_interval)

            except Exception as e:
                log.warning(f"查询任务 {task_id} 状态出错: {e}")
                time.sleep(retry_interval)

        log.error(f"任务 {task_id} 查询超时.")
        return None


class QuarkShareManager(QuarkBase):
    """夸克网盘分享管理类"""

    def get_share_list(self, page=1, page_size=50):
        """
        获取我的分享列表
        使用 drive-pc.quark.cn 端点（只需Cookie认证）
        :param page: 页码
        :param page_size: 每页数量
        :return: 分享列表
        """
        url = 'https://drive-pc.quark.cn/1/clouddrive/share/mypage/detail'
        params = self.base_params.copy()
        params.update({
            '_page': str(page),
            '_size': str(page_size),
            '_order_field': 'created_at',
            '_order_type': 'desc',
            '_fetch_total': '1',
            '_fetch_notify_follow': '1'
        })

        try:
            response = self.session.get(url, headers=self.headers, params=params, timeout=30)
            
            result = response.json()

            if result.get('status') == 200 or result.get('code') == 0:
                data = result.get('data', {})
                share_list = data.get('list', [])
                # 兼容不同返回结构: 有些是 data.list, 有些是 data.share_list
                if not share_list:
                    share_list = data.get('share_list', [])
                
                # 严格规则：只有data存在且包含list/share_list字段才认为有效
                if data is None:
                    log.error(f"夸克API返回data为None，Cookie无效")
                    return None
                
                if not data:
                    log.error(f"夸克API返回data为空字典，Cookie无效")
                    return None
                
                if 'list' not in data and 'share_list' not in data:
                    log.error(f"夸克API返回data中无list字段，Cookie无效")
                    return None
                
                # 即使是空列表也合法（表示没有分享记录）
                if share_list:
                    log.info(f"获取夸克分享列表成功，本页 {len(share_list)} 条")

                return share_list
            elif result.get('status') == 401:
                log.error("Cookie已失效，需要重新登录(401)")
                return None  # 用 None 表示认证失败
            else:
                # 其他错误状态码，记录详细信息
                log.warning(f"获取分享列表失败: status={result.get('status')}, code={result.get('code')}, message={result.get('message', '未知错误')}")
                # 对于非200状态码，返回None表示认证失败
                return None
        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP错误: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except json.JSONDecodeError as e:
            log.error(f"JSON解析失败，可能是无效的Cookie: {e}")
            return None
        except Exception as e:
            log.error(f"获取分享列表出错: {e}")
            return None

    def get_share_detail(self, share_id):
        """
        获取分享详情（提取码和链接）
        使用 drive-pc.quark.cn 端点
        :param share_id: 分享ID
        :return: 分享详情
        """
        url = 'https://drive-pc.quark.cn/1/clouddrive/share/password'
        params = self.base_params.copy()
        data = {"share_id": share_id}

        try:
            response = self.session.post(url, headers=self.headers, params=params, json=data, timeout=30)
            result = response.json()
            if result.get('status') == 200 or result.get('code') == 0:
                return result.get('data', {})
            else:
                log.warning(f"获取分享详情失败: {result.get('message', '未知错误')}")
                return {}
        except Exception as e:
            log.error(f"获取分享详情出错: {e}")
            return {}

    def fetch_all_shares(self):
        """
        获取所有分享链接
        :return: 所有分享列表，None表示认证失败
        """
        all_shares = []
        page = 1
        page_size = 50

        while True:
            log.info(f"正在获取分享列表第 {page} 页...")
            shares = self.get_share_list(page, page_size)
            if shares is None:
                # 认证失败(Cookie无效)
                log.error("Cookie认证失败，请重新配置Cookie")
                return None
            if not shares:
                break
            all_shares.extend(shares)
            page += 1

        log.info(f"获取分享列表完成，共 {len(all_shares)} 条")
        return all_shares

    def parse_share_info(self, share_data):
        """
        解析分享数据为标准格式
        适配 drive-pc.quark.cn/1/clouddrive/share/mypage/detail 返回格式
        :param share_data: 分享数据
        :return: 标准化的分享信息
        """
        try:
            share_id = share_data.get('share_id') or share_data.get('id')
            if not share_id:
                log.warning(f"分享数据缺少share_id: {share_data}")
                return None

            # 从列表数据中直接获取分享链接和密码
            # mypage/detail 可能直接在列表项中包含这些信息
            share_url = share_data.get('share_url', '')
            share_pwd = share_data.get('passcode', '') or share_data.get('share_pwd', '') or share_data.get('password', '')

            # 如果列表中没有链接，则调用详情接口获取
            if not share_url:
                share_detail = self.get_share_detail(share_id)
                if share_detail:
                    share_url = share_detail.get('share_url', '')
                    share_pwd = share_detail.get('passcode', '') or share_detail.get('share_pwd', '') or share_detail.get('password', '')

            # 构建完整链接(如果只有短链)
            if share_url and not share_url.startswith('http'):
                share_url = f'https://pan.quark.cn/s/{share_url}'

            # 解析分享名称
            share_title = share_data.get('title', '') or share_data.get('share_name', '') or share_data.get('file_name', '')
            if not share_title:
                share_title = f'分享_{share_id}'

            # 解析创建时间 - 兼容时间戳(秒/毫秒)和字符串格式
            create_time = share_data.get('created_at', 0) or share_data.get('create_time', 0) or share_data.get('share_time', 0)
            if isinstance(create_time, (int, float)):
                if create_time > 1e12:  # 毫秒时间戳
                    create_time = create_time / 1000
                share_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S') if create_time > 0 else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(create_time, str):
                share_time = create_time
            else:
                share_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 解析有效期
            expire_info = self._parse_expire_info(share_data)

            # 访问次数
            visit_count = share_data.get('visit_count', -1) or share_data.get('view_count', -1) or -1

            # 父目录
            parent_dir = share_data.get('parent_dir', '') or share_data.get('dir_name', '') or ''

            return {
                'source': 'quark',
                'name': share_title,
                'url': share_url,
                'pwd': share_pwd,
                'share_time': share_time,
                'expire': expire_info,
                'parent_dir': parent_dir,
                'view_count': visit_count if visit_count >= 0 else -1
            }
        except Exception as e:
            log.error(f"解析分享信息出错: {e}")
            log.error(f"数据: {json.dumps(share_data, ensure_ascii=False)[:300]}")
            return None

    def _parse_expire_info(self, share_data):
        """
        解析过期信息
        根据夸克API返回的 expired_type 和 expired_left 字段判断
        :param share_data: 分享数据
        :return: 过期状态字符串
        """
        try:
            expired_type = share_data.get('expired_type', 1) or share_data.get('expire_type', 1)
            expired_days = share_data.get('expired_days', 0) or 0
            expired_left = share_data.get('expired_left', 0) or 0  # 剩余毫秒数
            expired_at = share_data.get('expired_at', 0) or 0  # 过期时间戳（毫秒）
            expire_time = share_data.get('expire_time', 0) or share_data.get('expired_time', 0) or 0

            # expired_type 含义（基于API返回数据验证）：
            # 1 = 永久有效
            # 3 = 限时有效（需结合 expired_days 和 expired_left 字段）
            # 7 = 7天有效（API直接返回）
            if int(expired_type) == 1:
                return '永久有效'
            elif int(expired_type) == 3:
                # 限时有效类型，需要检查是否已经过期
                # expired_left <= 0 表示已过期
                if expired_left <= 0:
                    return '已失效'
                # 否则根据剩余时间计算显示
                remaining_days = int(expired_left / (86400 * 1000))
                if remaining_days > 0:
                    return f'{expired_days}天有效'
                else:
                    return '今天失效'
            elif int(expired_type) == 7:
                # 同样需要检查 expired_left
                if expired_left <= 0:
                    return '已失效'
                return '7天有效'
            elif int(expired_type) == 2 and expire_time > 0:
                # 定时失效，根据过期时间计算剩余天数
                current_time = time.time()
                remaining_seconds = expire_time - current_time
                if remaining_seconds <= 0:
                    return '已失效'
                remaining_days = int(remaining_seconds / 86400)
                if remaining_days == 0:
                    return '今天失效'
                elif remaining_days == 1:
                    return '1天后失效'
                else:
                    return f'{remaining_days}天后失效'
            else:
                return '永久有效'  # 默认当作永久有效
        except Exception as e:
            log.warning(f"解析过期信息出错: {e}")
            return '永久有效'

    def _normalize_status_text(self, text: str) -> str:
        """标准化夸克API返回的状态文本"""
        text = text.strip()
        # 已失效的各种表述
        if any(k in text for k in ['已失效', '分享已过期', '分享失败', 'expired', 'failed']):
            return '已失效'
        # 永久有效
        if any(k in text for k in ['永久有效', 'forever', 'permanent']):
            return '永久有效'
        # 剩余天数（如 "7天后失效"、"6天后失效"）
        match = re.search(r'(\d+)\s*天', text)
        if match:
            days = int(match.group(1))
            if days > 0:
                return f'{days}天后失效'
        # 已经是完整表述（如"1天有效"）
        if '天' in text:
            return text
        return text


class QuarkFileManager(QuarkBase):
    """夸克网盘文件管理类"""

    def get_file_list(self, folder_id='root'):
        """
        获取文件列表
        :param folder_id: 文件夹ID
        :return: 文件列表
        """
        url = 'https://drive-pc.quark.cn/1/clouddrive/file/sort'
        all_files = []
        page = 1
        page_size = 50

        while True:
            params = self.base_params.copy()
            params.update({
                'pdir_fid': folder_id if folder_id != 'root' else '0',
                '_page': str(page),
                '_size': str(page_size),
                '_fetch_total': '1',
                '_fetch_sub_dirs': '0',
                '_sort': 'file_type:asc,updated_at:desc'
            })

            try:
                response = self.session.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()

                if result.get('code') != 0:
                    log.warning(f"获取文件列表失败: {result.get('message', '未知错误')}")
                    return all_files

                current_files = result.get('data', {}).get('list', [])
                if not current_files:
                    break

                all_files.extend(current_files)

                metadata = result.get('data', {}).get('metadata', {})
                total = metadata.get('_total')
                if total is not None and len(all_files) >= total:
                    break

                page += 1

            except Exception as e:
                log.error(f"获取文件列表出错: {e}")
                return all_files

        log.info(f"获取文件列表完成，共 {len(all_files)} 个项目")
        return all_files
