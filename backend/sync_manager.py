"""
网盘同步管理器 - 支持夸克和百度网盘
支持手动同步
"""
import os
import traceback
from typing import Optional
from logger import setup_logger
from quark_api import QuarkShareManager
from baidu_api import BaiduShareManager
from database import upsert_share, get_setting, set_setting, log_import

log = setup_logger('sync_manager')


class SyncManager:
    """网盘同步管理器 - 支持夸克和百度网盘"""

    def __init__(self, app_instance=None):
        self.app = app_instance

    # ==================== 夸克网盘相关方法 ====================
    def get_cookie(self) -> Optional[str]:
        """从设置中获取夸克cookie"""
        cookie = get_setting('quark_cookie', '')
        if not cookie or len(cookie) < 50:
            return None
        return cookie

    def set_cookie(self, cookie: str) -> bool:
        """保存夸克cookie到设置"""
        try:
            set_setting('quark_cookie', cookie)
            log.info("Cookie 已保存")
            return True
        except Exception as e:
            log.error(f"保存Cookie失败: {e}")
            return False

    def delete_cookie(self) -> bool:
        """删除夸克cookie"""
        try:
            set_setting('quark_cookie', '')
            log.info("Cookie 已删除")
            return True
        except Exception as e:
            log.error(f"删除Cookie失败: {e}")
            return False

    def has_cookie(self) -> bool:
        """检查是否已配置夸克cookie"""
        return self.get_cookie() is not None

    # ==================== 同步方法 ====================
    def sync_now(self) -> dict:
        """立即执行一次同步（使用全局Cookie，仅夸克）"""
        cookie = self.get_cookie()
        if not cookie:
            return {'success': False, 'message': '请先配置夸克Cookie'}
        
        return self.sync_quark_with_cookie(cookie)
    
    def sync_quark_with_cookie(self, cookie: str, account_name: str = None, account_id: int = 0) -> dict:
        """使用指定Cookie执行夸克网盘同步"""
        if not cookie or len(cookie) < 50:
            return {'success': False, 'message': 'Cookie未配置或格式不正确'}

        try:
            log.info("开始同步夸克分享...")
            # 创建分享管理器（新API只需Cookie）
            share_manager = QuarkShareManager(cookie)

            # 获取所有分享
            shares = share_manager.fetch_all_shares()
            if shares is None:
                return {'success': False, 'message': 'Cookie已失效，请重新登录后获取新Cookie'}

            log.info(f"获取到 {len(shares)} 条分享记录")

            # 解析并导入每条分享
            imported = 0
            updated = 0
            errors = 0

            # 确定source格式：如果有账号名称，使用"quark:账号名称"
            source = 'quark'
            if account_name and account_name.strip():
                source = f"quark:{account_name.strip()}"

            for share_data in shares:
                try:
                    share_info = share_manager.parse_share_info(share_data)
                    if not share_info:
                        errors += 1
                        continue

                    # 设置source
                    share_info['source'] = source

                    # 设置账号名称（来自同步账号）
                    if account_name and account_name.strip():
                        share_info['account_name'] = account_name.strip()[:7]

                    # 设置网盘端share_id（夸克用share_id字段）
                    quark_share_id = share_data.get('share_id') or share_data.get('id') or ''
                    if quark_share_id:
                        share_info['share_id'] = str(quark_share_id)

                    # 设置account_id（关联账号ID）
                    if account_id:
                        share_info['account_id'] = account_id

                    result = upsert_share(share_info)
                    if result['action'] == 'inserted':
                        imported += 1
                    else:
                        updated += 1

                except Exception as e:
                    log.warning(f"处理分享失败: {e}")
                    errors += 1

            log.info(f"同步完成: 新增 {imported}, 更新 {updated}, 错误 {errors}")

            # 记录到导入日志
            log_display = '网盘同步'
            if account_name and account_name.strip():
                log_display = f'网盘同步-{account_name.strip()}'

            log_import(
                filename=log_display,
                source=source,
                total=len(shares),
                imported=imported,
                skipped=updated
            )

            return {
                'success': True,
                'total': len(shares),
                'new_count': imported,
                'update_count': updated,
                'error_count': errors,
                'message': f'同步完成：新增 {imported} 条，更新 {updated} 条'
            }

        except Exception as e:
            log.error(f"同步失败: {e}")
            return {'success': False, 'message': f'同步失败: {str(e)}'}

    def sync_baidu_with_cookie(self, cookie: str, account_name: str = None, account_id: int = 0) -> dict:
        """使用指定Cookie执行百度网盘同步"""
        if not cookie or len(cookie) < 50:
            return {'success': False, 'message': 'Cookie未配置或格式不正确'}

        try:
            log.info("开始同步百度分享...")
            # 创建百度分享管理器
            share_manager = BaiduShareManager(cookie)

            # 获取所有分享
            shares = share_manager.fetch_all_shares()
            if shares is None:
                return {'success': False, 'message': 'Cookie已失效，请重新登录后获取新Cookie'}

            log.info(f"获取到 {len(shares)} 条分享记录")

            # 解析并导入每条分享
            imported = 0
            updated = 0
            errors = 0

            # 确定source格式：如果有账号名称，使用"baidu:账号名称"
            source = 'baidu'
            if account_name and account_name.strip():
                source = f"baidu:{account_name.strip()}"

            for share_data in shares:
                try:
                    share_info = share_manager.parse_share_info(share_data)
                    if not share_info:
                        errors += 1
                        continue

                    # 设置source
                    share_info['source'] = source

                    # 设置账号名称（来自同步账号）
                    if account_name and account_name.strip():
                        share_info['account_name'] = account_name.strip()[:7]

                    # 设置网盘端share_id（百度用shareId字段）
                    baidu_share_id = share_data.get('shareId') or ''
                    if baidu_share_id:
                        share_info['share_id'] = str(baidu_share_id)

                    # 设置account_id（关联账号ID）
                    if account_id:
                        share_info['account_id'] = account_id

                    result = upsert_share(share_info)
                    if result['action'] == 'inserted':
                        imported += 1
                    else:
                        updated += 1

                except Exception as e:
                    log.warning(f"处理分享失败: {e}")
                    errors += 1

            log.info(f"同步完成: 新增 {imported}, 更新 {updated}, 错误 {errors}")

            # 记录到导入日志
            log_display = '网盘同步'
            if account_name and account_name.strip():
                log_display = f'网盘同步-{account_name.strip()}'

            log_import(
                filename=log_display,
                source=source,
                total=len(shares),
                imported=imported,
                skipped=updated
            )

            return {
                'success': True,
                'total': len(shares),
                'new_count': imported,
                'update_count': updated,
                'error_count': errors,
                'message': f'同步完成：新增 {imported} 条，更新 {updated} 条'
            }

        except Exception as e:
            log.error(f"百度同步失败: {e}")
            log.error(traceback.format_exc())
            return {'success': False, 'message': f'同步失败: {str(e)}'}

    def sync_with_cookie(self, platform: str, cookie: str, account_name: str = None, account_id: int = 0) -> dict:
        """
        通用同步方法，根据平台选择同步方式
        :param platform: 平台类型 ('quark' 或 'baidu')
        :param cookie: Cookie字符串
        :param account_name: 账号名称（可选）
        :param account_id: 账号ID（可选，用于关联分享记录）
        :return: 同步结果
        """
        if platform == 'quark':
            return self.sync_quark_with_cookie(cookie, account_name, account_id)
        elif platform == 'baidu':
            return self.sync_baidu_with_cookie(cookie, account_name, account_id)
        else:
            return {'success': False, 'message': f'不支持的平台类型: {platform}'}

    def get_status(self) -> dict:
        """获取同步状态"""
        return {
            'has_cookie': self.has_cookie()
        }


# 全局同步管理器实例
_global_sync_manager = None


def get_sync_manager(app=None) -> SyncManager:
    """获取全局同步管理器实例"""
    global _global_sync_manager
    if _global_sync_manager is None:
        _global_sync_manager = SyncManager(app)
    return _global_sync_manager
