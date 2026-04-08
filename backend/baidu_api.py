"""
百度网盘 API 封装模块 - 支持分享链接获取和管理

字段对照表（2026-04-05 更新）:
- shareId: 分享唯一ID
- shortlink: 完整分享链接（https://pan.baidu.com/s/xxx）
- shorturl: 短链接后缀（如 1xxx）
- passwd: 提取码（4位字符串），需 is_batch=1 参数才能获取；公开分享为空字符串
- typicalPath: 文件路径（如 /文件名.mp4，已过期时显示"分享已过期"）
- ctime: 分享创建时间戳（秒）
- expiredType: 当前状态类型（服务端实时计算）
  - 0 = 未过期（还有剩余时间）
  - 1 = 永久有效
  - -1 = 已过期/已失效
- **expiredTime: ⚠️ 动态倒计时剩余秒数（不是固定有效期！）**
  - 每次请求API都会递减（实测：5秒内减少约6秒）
  - 正确用法: 过期时间 = 当前时间 + expiredTime
  - ⚠️ 错误用法: ctime + expiredTime（之前的错误理解）
- oriExpiredType: 原始有效期类型（创建时设定的有效期限类型）
  - 1 = 永久有效
  - 7 = 7天有效期（最常见）
- status: 分享状态（0=正常, 1=已取消, 10/9=已失效）
- vCnt: 浏览次数

关键参数（2026-04-05 发现）:
- /share/record 接口添加 is_batch=1 参数后，返回数据中包含 passwd 提取码字段
- 不加此参数时 passwd 始终为空

关键发现（2026-04-05 验证）:
- expiredTime 是动态倒计时剩余秒数，不是固定值！
- 通过两次API请求（间隔5秒）验证：expiredTime 减少量 ≈ 经过的时间

常见错误码：
- errno: 0   → 成功
- errno: -6  → 登录过期，需要重新登录
- errno: 111 → 鉴权失败（Cookie无效）
- errno: 104 → 参数错误（缺少channel、page等）
"""
import requests
import json
import time
import re
from datetime import datetime
import traceback
from logger import setup_logger

log = setup_logger('baidu_api')


class BaiduShareManager:
    """百度网盘分享管理类"""

    def __init__(self, cookie):
        """
        初始化分享管理类
        :param cookie: 登录百度网盘后的cookie
        """
        self.cookie = cookie
        self.headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'DNT': '1',
            'Origin': 'https://pan.baidu.com',
            'Pragma': 'no-cache',
            'Referer': 'https://pan.baidu.com/disk/home',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        self.base_params = {
            'channel': 'chunlei',
            'clienttype': '0',
            'web': '1',
        }
        # 禁用代理，避免代理导致的SSL错误
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {'http': None, 'https': None}

    def get_share_list(self, page=1, page_size=100, order='ctime', desc=1):
        """
        获取我的分享列表
        接口地址: https://pan.baidu.com/share/record

        关键参数说明（2026-04-05 更新）:
        - is_batch=1：批量模式，会返回 passwd（提取码）字段
          不加此参数时 passwd 始终为空字符串
        - channel=chunlei：百度网盘Web端渠道代码

        :param page: 页码，从1开始
        :param page_size: 每页数量
        :param order: 排序方式：ctime (时间)、name (名称)
        :param desc: 是否降序：1 (是)、0 (否)
        :return: (share_list, next_page) 元组，None表示认证失败
        """
        url = 'https://pan.baidu.com/share/record'
        params = self.base_params.copy()
        params.update({
            'page': str(page),
            'num': str(page_size),
            'order': order,
            'desc': str(desc),
            'is_batch': '1',  # 批量模式：触发返回提取码(passwd)字段
        })

        try:
            response = self.session.get(url, headers=self.headers, params=params, timeout=30)
            
            result = response.json()

            # errno为0表示成功
            if result.get('errno') == 0:
                # list 在顶层，不是 data.list
                share_list = result.get('list', [])
                # nextpage 字段控制分页（0=无下一页）
                next_page = result.get('nextpage', 0)
                
                return share_list, next_page
            elif result.get('errno') == -6:
                log.error("Cookie已失效，需要重新登录(errno=-6)")
                return None
            elif result.get('errno') == 112:
                log.error("登录已过期，需要重新登录(errno=112)")
                return None
            else:
                log.warning(f"获取分享列表失败: errno={result.get('errno')}, errmsg={result.get('errmsg', '未知错误')}")
                return None
        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP错误: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except json.JSONDecodeError as e:
            log.error(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            log.error(f"获取分享列表出错: {e}")
            log.error(traceback.format_exc())
            return None

    def fetch_all_shares(self, page_size=100):
        """
        获取所有分享链接（支持分页）
        :param page_size: 每页数量
        :return: 所有分享列表，None表示认证失败
        """
        all_shares = []
        page = 1
        
        while True:
            log.info(f"正在获取分享列表第 {page} 页...")
            result = self.get_share_list(page=page, page_size=page_size)
            
            if result is None:
                log.error("Cookie认证失败，请重新配置Cookie")
                return None
            
            share_list, next_page = result
            
            if not share_list:
                break
            
            all_shares.extend(share_list)
            
            # nextpage为0表示没有下一页
            if not next_page:
                break
            
            page = next_page

        log.info(f"获取分享列表完成，共 {len(all_shares)} 条")
        return all_shares

    def parse_share_info(self, share_data):
        """
        解析百度网盘分享数据为标准格式
        :param share_data: 分享数据（来自API）
        :return: 标准化的分享信息
        """
        try:
            # 获取分享ID（注意大写I: shareId）
            share_id = share_data.get('shareId')
            if not share_id:
                log.warning(f"分享数据缺少shareId: {share_data.get('shareId')}")
                return None

            # 获取分享链接 - 使用 shortlink（完整URL）
            share_url = share_data.get('shortlink', '')
            if not share_url:
                # 如果没有 shortlink，用 share_id 拼接
                share_url = f'https://pan.baidu.com/s/1{share_id}'

            # 获取提取码
            # 注意（2026-04-05 更新）：通过在 /share/record 接口中添加 is_batch=1 参数，
            # API 现在会正常返回 passwd 字段（提取码）。公开分享为空字符串。
            pwd = share_data.get('passwd', '')

            # 获取文件名/分享名（优先使用 server_filename，而不是 typicalPath）
            share_title = share_data.get('server_filename', '')
            if not share_title:
                # 如果没有 server_filename，再用 typicalPath
                typical_path = share_data.get('typicalPath', '')
                if typical_path:
                    share_title = typical_path.split('/')[-1]

            # 如果还是为空，使用默认名称
            if not share_title:
                share_title = f'分享_{share_id}'

            # 解析创建时间 - 秒级时间戳
            ctime = share_data.get('ctime', 0)
            if isinstance(ctime, (int, float)) and ctime > 0:
                share_time = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
            else:
                share_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 解析有效期
            expire_info = self._parse_expire_info(share_data)

            # 访问次数（vCnt 字段）
            visit_count = share_data.get('vCnt', -1)

            # 父目录
            parent_dir = ''
            if typical_path:
                parts = typical_path.split('/')
                if len(parts) > 1:
                    parent_dir = '/'.join(parts[:-1])

            return {
                'source': 'baidu',
                'name': share_title,
                'url': share_url,
                'pwd': pwd,
                'share_time': share_time,
                'expire': expire_info,
                'parent_dir': parent_dir,
                'view_count': visit_count if visit_count >= 0 else -1
            }
        except Exception as e:
            log.error(f"解析分享信息出错: {e}")
            log.error(f"数据: {json.dumps(share_data, ensure_ascii=False)[:300]}")
            return None

    def validate_cookie(self):
        """
        验证当前Cookie是否有效
        调用API获取分享列表第一页来验证Cookie有效性
        :return: True=有效, False=无效, None=验证失败（网络错误等）
        """
        try:
            result = self.get_share_list(page=1, page_size=1)
            
            if result is None:
                # get_share_list 返回 None 表示认证失败
                log.warning('Cookie验证失败：API返回None')
                return False
            
            share_list, next_page = result
            
            # 返回列表（包括空列表）表示Cookie有效
            if isinstance(share_list, list):
                log.info('百度Cookie验证成功')
                return True
            
            # 其他情况视为无效
            log.warning(f'Cookie验证失败：返回未知类型: {type(share_list).__name__}')
            return False
            
        except Exception as e:
            log.error(f'验证Cookie时出错: {e}')
            log.error(traceback.format_exc())
            return None

    def _parse_expire_info(self, share_data):
        """
        解析百度网盘分享过期信息
        
        关键发现（2026-04-05 实验验证）:
        - expiredTime 是**动态倒计时剩余秒数**（每次API请求都在递减），不是固定有效期总长度
          - 5秒内两次请求，expiredTime 减少约6秒 → 确认为倒计时
        - 正确计算方式: 过期时间点 = 当前服务器时间 + expiredTime（剩余秒数）
        - oriExpiredType: 原始有效期类型
          - 1 = 永久有效
          - 7 = 7天有效期限
          - 其他值待确认
        - expiredType: 当前状态类型（由服务端实时计算）
          - 0 = 未过期（还有剩余时间）
          - 1 = 永久有效
          - -1 = 已过期/已失效
        - status: 分享状态
          - 0 = 正常
          - 1 = 已取消
          - 10/9 = 已失效
        
        ⚠️ 注意：不能用 ctime + expiredTime 计算过期时间！这是之前的错误理解。
        """
        try:
            expired_type = share_data.get('expiredType', 0)
            expired_time = share_data.get('expiredTime', 0)
            status = share_data.get('status', 0)
            
            # 先判断状态（已取消也算已失效）
            if status in [1, 10, 9, 2]:
                return '已失效'
            
            # 已过期（expiredType = -1）
            if expired_type == -1:
                return '已失效'
            
            # 永久有效（expiredType = 1）
            if expired_type == 1:
                return '永久有效'
            
            # 有期限（expiredType = 0）→ expiredTime 为倒计时剩余秒数
            if expired_type == 0 and isinstance(expired_time, (int, float)) and expired_time > 0:
                try:
                    # 正确计算：过期时间点 = 当前时间 + 剩余秒数
                    current_time = int(time.time())
                    expired_timestamp = current_time + int(expired_time)
                    
                    # 计算剩余时间
                    remaining_seconds = int(expired_time)
                    remaining_days = int(remaining_seconds / 86400)
                    remaining_hours = int((remaining_seconds % 86400) / 3600)
                    
                    if remaining_days > 0:
                        return f'{remaining_days}天后过期'
                    elif remaining_hours > 0:
                        return f'{remaining_hours}小时后过期'
                    else:
                        remaining_minutes = int(remaining_seconds / 60)
                        if remaining_minutes > 0:
                            return f'{remaining_minutes}分钟后过期'
                        return '即将过期'
                except (ValueError, TypeError):
                    log.warning(f"时间计算错误: expiredTime={expired_time}")
            
            # expiredType=0 但 expiredTime<=0，视为已失效
            if expired_type == 0:
                return '已失效'
            
            # 其他情况默认永久有效
            return '永久有效'
        except Exception as e:
            log.warning(f"解析过期信息出错: {e}")
            return '永久有效'
