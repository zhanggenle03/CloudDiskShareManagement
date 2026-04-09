"""
Flask 后端 API
"""
import os
import sys
import traceback
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from logger import setup_logger
from database import (
    init_db, upsert_share, get_shares, update_share,
    delete_share, batch_delete, get_stats, log_import, get_import_logs, clear_import_logs,
    get_all_tag_colors, set_tag_color, delete_tag_color, get_stats_with_colors,
    get_setting, set_setting, get_all_settings,
    add_account, get_accounts, get_account, update_account, delete_account,
    add_resource, get_resources, get_resource, update_resource, delete_resource,
    add_share_to_resource, remove_share_from_resource, update_resource_shares,
    get_available_shares, get_conn
)
from parser import auto_detect_and_parse
from sync_manager import get_sync_manager
from process_manager import on_startup, on_shutdown, graceful_shutdown, restart_service, remove_pid, terminate_process, shutdown_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
FRONTEND_DIST_DIR = os.path.join(BASE_DIR, 'frontend-dist')

# 优先使用 Vue 构建产物，不存在则回退到原始 frontend 目录
if os.path.isdir(FRONTEND_DIST_DIR) and os.path.exists(os.path.join(FRONTEND_DIST_DIR, 'index.html')):
    STATIC_DIR = FRONTEND_DIST_DIR
else:
    STATIC_DIR = FRONTEND_DIR

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app)

# ── 日志 ──
log = setup_logger('app')

# ─── 静态前端 ────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

# ─── 导入 CSV ────────────────────────────────────────────────
@app.route('/api/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
    f = request.files['file']
    if not f.filename.endswith('.csv'):
        return jsonify({'error': '请上传CSV文件'}), 400

    raw = f.read()
    account_name = (request.form.get('account_name') or '').strip()[:7]  # 最长7字符

    try:
        records, source = auto_detect_and_parse(raw, f.filename)
    except ValueError as e:
        log.warning(f'CSV解析失败: {f.filename}, 原因: {e}')
        return jsonify({'error': str(e)}), 400

    total = len(records)
    imported = skipped = 0
    for rec in records:
        if account_name:
            rec['account_name'] = account_name
        result = upsert_share(rec)
        if result['action'] == 'inserted':
            imported += 1
        else:
            skipped += 1

    # 构建导入记录的"数据来源"显示名称
    if account_name:
        log_display = f'CSV导入-{account_name}'
    else:
        # 无账号名时用文件名（去掉.csv后缀）
        log_display = f'CSV导入-{f.filename[:-4] if f.filename.endswith(".csv") else f.filename}'

    log_import(log_display, source, total, imported, skipped)
    log.info(f'CSV导入完成: {f.filename}, 来源={source}, 总计={total}, 新增={imported}, 更新={skipped}')
    return jsonify({
        'success': True,
        'source': source,
        'total': total,
        'imported': imported,
        'skipped': skipped,
        'message': f'导入完成：新增 {imported} 条，更新 {skipped} 条'
    })

# ─── 查询列表 ────────────────────────────────────────────────
@app.route('/api/shares', methods=['GET'])
def list_shares():
    source = request.args.get('source', 'all')
    expire_filter = request.args.get('expire', '')
    keyword = request.args.get('keyword', '')
    tag = request.args.get('tag', '')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort = request.args.get('sort', 'share_time')
    order = request.args.get('order', 'desc')

    result = get_shares(source, expire_filter, keyword, tag, page, page_size, sort, order)
    return jsonify(result)

# ─── 单条详情 ────────────────────────────────────────────────
@app.route('/api/shares/<int:share_id>', methods=['GET'])
def get_share(share_id):
    result = get_shares(page=1, page_size=1)  # 简化，实际按id查
    conn = get_conn()
    row = conn.execute("SELECT * FROM shares WHERE id=? AND is_deleted=0", (share_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '记录不存在'}), 404
    return jsonify(dict(row))

# ─── 更新 ────────────────────────────────────────────────────
@app.route('/api/shares/<int:share_id>', methods=['PUT'])
def update(share_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求体'}), 400
    ok = update_share(share_id, data)
    if not ok:
        log.warning(f'更新失败，无有效字段: share_id={share_id}')
        return jsonify({'error': '无有效字段可更新'}), 400
    log.info(f'更新分享: id={share_id}, 字段={list(data.keys())}')
    return jsonify({'success': True})

# ─── 软删除单条 ──────────────────────────────────────────────
@app.route('/api/shares/<int:share_id>', methods=['DELETE'])
def delete(share_id):
    hard = request.args.get('hard', 'false').lower() == 'true'
    log.info(f'删除分享: id={share_id}, hard={hard}')
    delete_share(share_id, hard=hard)
    return jsonify({'success': True})

# ─── 批量删除 ────────────────────────────────────────────────
@app.route('/api/shares/batch_delete', methods=['POST'])
def batch_del():
    data = request.get_json()
    ids = data.get('ids', [])
    hard = data.get('hard', False)
    if not ids:
        return jsonify({'error': '未指定ID'}), 400
    log.info(f'批量删除: count={len(ids)}, hard={hard}')
    batch_delete(ids, hard=hard)
    return jsonify({'success': True, 'count': len(ids)})

# ─── 统计 ────────────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(get_stats_with_colors())

# ─── 导入日志 ────────────────────────────────────────────────
@app.route('/api/import_logs', methods=['GET'])
def import_logs():
    return jsonify(get_import_logs())

@app.route('/api/import_logs', methods=['DELETE'])
def clear_logs():
    """清空所有导入记录"""
    log.info('清空导入记录')
    clear_import_logs()
    return jsonify({'success': True, 'message': '已清空导入记录'})

# ─── 批量打标签 ─────────────────────────────────────────────
@app.route('/api/shares/batch_tag', methods=['POST'])
def batch_tag():
    data = request.get_json()
    ids = data.get('ids', [])
    tag = data.get('tag', '').strip()
    action = data.get('action', 'add')  # 'add' | 'remove'
    if not ids or not tag:
        return jsonify({'error': '参数缺失'}), 400
    log.info(f'批量标签: action={action}, tag={tag}, count={len(ids)}')
    conn = get_conn()
    for sid in ids:
        row = conn.execute("SELECT tags FROM shares WHERE id=?", (sid,)).fetchone()
        if not row:
            continue
        existing = [t.strip() for t in row['tags'].split(',') if t.strip()]
        if action == 'add' and tag not in existing:
            existing.append(tag)
        elif action == 'remove' and tag in existing:
            existing.remove(tag)
        conn.execute("UPDATE shares SET tags=? WHERE id=?", (','.join(existing), sid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── 获取所有标签颜色 ───────────────────────────────────────
@app.route('/api/tag_colors', methods=['GET'])
def get_tag_colors():
    return jsonify(get_all_tag_colors())

# ─── 设置标签颜色 ───────────────────────────────────────────
@app.route('/api/tag_colors', methods=['PUT'])
def update_tag_color():
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '').strip()
    if not name or not color:
        return jsonify({'error': '参数缺失'}), 400
    set_tag_color(name, color)
    log.info(f'设置标签颜色: {name}={color}')
    return jsonify({'success': True})

# ─── 删除标签颜色配置 ───────────────────────────────────────
@app.route('/api/tag_colors/<path:tag_name>', methods=['DELETE'])
def remove_tag_color(tag_name):
    delete_tag_color(tag_name)
    return jsonify({'success': True})

# ─── 删除某个标签（从所有记录中移除 + 删除颜色配置） ───────
@app.route('/api/tags/<path:tag_name>', methods=['DELETE'])
def delete_tag(tag_name):
    """从所有记录中移除该标签，并删除颜色配置"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, tags FROM shares WHERE is_deleted=0")
    for row in c.fetchall():
        existing = [t.strip() for t in row['tags'].split(',') if t.strip()]
        if tag_name in existing:
            existing.remove(tag_name)
            conn.execute("UPDATE shares SET tags=? WHERE id=?", (','.join(existing), row['id']))
    conn.execute("DELETE FROM tag_colors WHERE name=?", (tag_name,))
    conn.commit()
    conn.close()
    log.info(f'删除标签: {tag_name}')
    return jsonify({'success': True})


# ─── 用户设置 API ─────────────────────────────────────────────
@app.route('/api/settings', methods=['GET'])
def read_settings():
    """获取所有设置"""
    return jsonify(get_all_settings())


@app.route('/api/settings', methods=['PUT'])
def write_settings():
    """批量写入设置"""
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({'error': '无效请求体'}), 400
    for key, val in data.items():
        set_setting(key, str(val))
    return jsonify({'success': True})


@app.route('/api/settings/<path:key>', methods=['GET'])
def read_one_setting(key):
    """获取单个设置项"""
    default = request.args.get('default', '')
    return jsonify({'key': key, 'value': get_setting(key, default)})


@app.route('/api/settings/<path:key>', methods=['PUT'])
def write_one_setting(key):
    """设置单个配置项"""
    data = request.get_json()
    value = data.get('value', '') if data else ''
    set_setting(key, str(value))
    return jsonify({'success': True})


@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """安全关闭服务"""
    log.info('收到退出请求，正在关闭服务...')

    # 直接调用 shutdown_service，它会：
    # 1. 清理 PID 文件
    # 2. 调用 os._exit(0) 强制终止进程
    # 这样最可靠，不依赖线程执行
    shutdown_service()

    # 这行代码不会执行，因为 shutdown_service 是同步的
    return jsonify({'success': True, 'message': '服务正在关闭...'})


@app.route('/api/restart', methods=['POST'])
def restart():
    """重启服务"""
    log.info('收到重启请求，正在重启服务...')
    restart_service()
    return jsonify({'success': True, 'message': '服务正在重启...'})


# ─── 夸克网盘同步 API ───────────────────────────────────────

# ─── 网盘账号管理 API ─────────────────────────────────────────

@app.route('/api/accounts', methods=['GET'])
def list_accounts():
    """获取账号列表，可按平台过滤"""
    platform = request.args.get('platform', None)
    return jsonify(get_accounts(platform))


@app.route('/api/accounts', methods=['POST'])
def create_account():
    """添加账号"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求体'}), 400
    platform = data.get('platform', '').strip()
    name = data.get('name', '').strip()
    cookie = data.get('cookie', '').strip()
    remark = data.get('remark', '').strip()
    if not platform or platform not in ('baidu', 'quark'):
        return jsonify({'error': '平台参数无效，应为 baidu 或 quark'}), 400
    if not name:
        return jsonify({'error': '请输入账号名称'}), 400
    account_id = add_account(platform, name, cookie, remark)
    return jsonify({'success': True, 'id': account_id})


@app.route('/api/accounts/<int:account_id>', methods=['GET'])
def read_account(account_id):
    """获取单个账号详情(包含cookie)"""
    account = get_account(account_id)
    if not account:
        return jsonify({'error': '账号不存在'}), 404
    return jsonify(account)


@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def edit_account(account_id):
    """更新账号信息"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求体'}), 400
    account = get_account(account_id)
    if not account:
        return jsonify({'error': '账号不存在'}), 404
    ok = update_account(account_id, data)
    if not ok:
        return jsonify({'error': '无有效字段可更新'}), 400
    return jsonify({'success': True})


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def remove_account(account_id):
    """删除账号"""
    account = get_account(account_id)
    if not account:
        return jsonify({'error': '账号不存在'}), 404
    delete_account(account_id)
    return jsonify({'success': True})


@app.route('/api/accounts/<int:account_id>/test', methods=['POST'])
def test_account_cookie(account_id):
    """测试账号Cookie是否有效"""
    account = get_account(account_id)
    if not account:
        return jsonify({'error': '账号不存在'}), 404

    cookie = account.get('cookie', '').strip()
    platform = account.get('platform', '')
    last_verified_at = account.get('last_verified_at', 0)  # 上次验证时间戳（秒）

    # 也允许通过请求体传入新的cookie来测试
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    if data.get('cookie', '').strip():
        cookie = data['cookie'].strip()
        # 如果传入了新的Cookie，忽略验证间隔
        last_verified_at = 0

    if not cookie or len(cookie) < 50:
        result = {'valid': False, 'message': 'Cookie未配置或格式不正确'}
        # Cookie为空时，设置为0（未验证），而不是-1（已失效）
        update_account(account_id, {'is_valid': 0, 'last_verified_at': int(time.time())})
        return jsonify(result)

    # 验证间隔：30分钟（1800秒）
    VERIFICATION_INTERVAL = 1800
    current_time = int(time.time())
    
    if last_verified_at > 0:
        time_since_last = current_time - last_verified_at
        if time_since_last < VERIFICATION_INTERVAL:
            remaining = VERIFICATION_INTERVAL - time_since_last
            minutes = int(remaining / 60)
            seconds = remaining % 60
            msg = f'验证过于频繁，请等待{minutes}分{seconds}秒后再试'
            log.info(f'账号 {account_id} 验证间隔不足: {time_since_last}秒 < {VERIFICATION_INTERVAL}秒')
            
            # 直接返回当前验证状态，不重新验证
            is_valid = account.get('is_valid', 0)
            status_msg = 'Cookie有效' if is_valid == 1 else 'Cookie无效' if is_valid == -1 else 'Cookie未验证'
            return jsonify({
                'valid': is_valid == 1,
                'message': f'{status_msg}（{msg}）',
                'cached': True,
                'last_verified': last_verified_at
            })

    if platform == 'quark':
        # 先检查Cookie格式：不能包含非ASCII字符（会导致requests库编码错误）
        try:
            cookie.encode('latin-1')
            log.info(f'夸克Cookie编码检查通过: {len(cookie)}字符')
        except UnicodeEncodeError as e:
            log.warning(f'夸克Cookie包含非ASCII字符: {e}')
            update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
            return jsonify({'valid': False, 'message': 'Cookie格式错误：包含非法字符（如中文符号），请重新复制正确的Cookie'})
        
        try:
            from quark_api import QuarkShareManager
            share_manager = QuarkShareManager(cookie)
            shares = share_manager.get_share_list(1, 1)

            # 严格规则：只有返回列表（包括空列表）才认为有效，None表示无效
            if shares is None:
                log.warning(f'夸克Cookie验证失败: API返回None')
                update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
                return jsonify({'valid': False, 'message': 'Cookie已失效或格式错误，请重新登录后获取新Cookie'})

            # 返回空列表[]也表示有效（只是没有分享记录）
            if isinstance(shares, list):
                log.info(f'夸克Cookie验证成功, 分享条数: {len(shares)}')
                update_account(account_id, {'is_valid': 1, 'last_verified_at': current_time})
                return jsonify({'valid': True, 'message': 'Cookie有效'})

            # 其他情况（如返回字典、字符串等）都视为无效
            log.error(f'夸克Cookie验证失败: API返回未知类型: {type(shares).__name__}')
            update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
            return jsonify({'valid': False, 'message': 'Cookie验证失败：返回数据格式异常'})
        except Exception as e:
            log.error(f'验证夸克Cookie失败: {e}')
            update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
            return jsonify({'valid': False, 'message': f'验证失败: {str(e)}'})
    elif platform == 'baidu':
        # 百度网盘在线验证
        try:
            from baidu_api import BaiduShareManager
            share_manager = BaiduShareManager(cookie)
            
            # 调用 validate_cookie 方法验证
            is_valid = share_manager.validate_cookie()
            
            if is_valid is None:
                # 验证过程中出错（网络问题等）
                log.error('百度Cookie验证失败：验证过程中出错')
                update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
                return jsonify({'valid': False, 'message': '验证失败：网络错误或服务器无响应'})
            elif is_valid:
                # Cookie有效
                log.info('百度Cookie验证成功')
                update_account(account_id, {'is_valid': 1, 'last_verified_at': current_time})
                return jsonify({'valid': True, 'message': 'Cookie有效'})
            else:
                # Cookie无效
                log.warning('百度Cookie验证失败：Cookie已失效')
                update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
                return jsonify({'valid': False, 'message': 'Cookie已失效，请重新登录后获取新Cookie'})
                
        except Exception as e:
            log.error(f'验证百度Cookie失败: {e}')
            log.error(traceback.format_exc())
            update_account(account_id, {'is_valid': -1, 'last_verified_at': current_time})
            return jsonify({'valid': False, 'message': f'验证失败: {str(e)}'})

    return jsonify({'valid': False, 'message': '不支持的网盘平台'})


@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    """获取同步状态"""
    sync_mgr = get_sync_manager()
    return jsonify(sync_mgr.get_status())


@app.route('/api/sync/cookie', methods=['GET'])
def get_sync_cookie():
    """检查Cookie是否已配置（不返回实际值）"""
    sync_mgr = get_sync_manager()
    has_cookie = sync_mgr.has_cookie()
    return jsonify({'has_cookie': has_cookie})


@app.route('/api/sync/cookie', methods=['PUT'])
def save_sync_cookie():
    """保存Cookie"""
    data = request.get_json()
    if not data or not data.get('cookie'):
        return jsonify({'error': '请提供cookie'}), 400

    cookie = data.get('cookie', '').strip()
    if len(cookie) < 50:
        return jsonify({'error': 'Cookie格式不正确，请检查是否完整'}), 400

    sync_mgr = get_sync_manager()
    if sync_mgr.set_cookie(cookie):
        log.info('夸克Cookie已保存')
        return jsonify({'success': True, 'message': 'Cookie保存成功'})

    return jsonify({'error': 'Cookie保存失败'}), 500


@app.route('/api/sync/cookie', methods=['DELETE'])
def delete_sync_cookie():
    """删除Cookie"""
    sync_mgr = get_sync_manager()
    sync_mgr.delete_cookie()
    return jsonify({'success': True, 'message': 'Cookie已删除'})


@app.route('/api/sync/auth-params', methods=['GET'])
def get_sync_auth_params():
    """获取认证参数状态（不返回实际值）"""
    sync_mgr = get_sync_manager()
    has_params = sync_mgr.has_auth_params()
    return jsonify({'has_auth_params': has_params})


@app.route('/api/sync/auth-params', methods=['PUT'])
def save_sync_auth_params():
    """保存认证参数(kps, sign, vcode)"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供认证参数'}), 400

    sync_mgr = get_sync_manager()
    kps = data.get('kps', '').strip()
    sign = data.get('sign', '').strip()
    vcode = data.get('vcode', '').strip()

    if sync_mgr.set_auth_params(kps=kps, sign=sign, vcode=vcode):
        log.info('夸克认证参数已保存')
        return jsonify({'success': True, 'message': '认证参数保存成功'})

    return jsonify({'error': '认证参数保存失败'}), 500


@app.route('/api/sync/auth-params', methods=['DELETE'])
def delete_sync_auth_params():
    """删除认证参数"""
    sync_mgr = get_sync_manager()
    sync_mgr.delete_auth_params()
    return jsonify({'success': True, 'message': '认证参数已删除'})




@app.route('/api/sync/now', methods=['POST'])
def sync_now():
    """立即执行一次同步"""
    data = request.get_json() or {}
    account_id = data.get('account_id')
    platform = data.get('platform')  # 可选，指定平台（quark/baidu）
    
    # 如果提供了account_id，从账号表获取Cookie和名称
    if account_id:
        account = get_account(account_id)
        if not account:
            return jsonify({'success': False, 'error': '账号不存在'}), 404
        
        cookie = account.get('cookie', '')
        account_name = account.get('name', '')
        platform = account.get('platform', platform)  # 从账号信息中获取平台类型
        
        if not cookie or len(cookie) < 50:
            return jsonify({'success': False, 'error': '该账号Cookie未配置或格式不正确'}), 400
        
        if not platform or platform not in ('baidu', 'quark'):
            return jsonify({'success': False, 'error': '账号平台类型无效'}), 400
        
        sync_mgr = get_sync_manager()
        result = sync_mgr.sync_with_cookie(platform, cookie, account_name)
    else:
        # 兼容旧逻辑：使用全局Cookie（仅夸克）
        sync_mgr = get_sync_manager()
        result = sync_mgr.sync_now()
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/sync/test', methods=['POST'])
def test_cookie():
    """测试Cookie是否有效"""
    data = request.get_json() or {}
    cookie = data.get('cookie', '').strip()
    platform = data.get('platform', 'quark')  # 默认测试夸克网盘

    if not cookie:
        sync_mgr = get_sync_manager()
        cookie = sync_mgr.get_cookie()

    if not cookie or len(cookie) < 50:
        return jsonify({'valid': False, 'message': 'Cookie未配置或格式不正确'})

    try:
        if platform == 'quark':
            from quark_api import QuarkShareManager
            share_manager = QuarkShareManager(cookie)
            shares = share_manager.get_share_list(1, 1)
            if shares is None:
                return jsonify({'valid': False, 'message': 'Cookie已失效，请重新登录后获取新Cookie'})
            if isinstance(shares, list) and len(shares) >= 0:
                return jsonify({'valid': True, 'message': 'Cookie有效'})
            return jsonify({'valid': False, 'message': '无法获取分享列表'})
        
        elif platform == 'baidu':
            from baidu_api import BaiduShareManager
            share_manager = BaiduShareManager(cookie)
            shares = share_manager.get_share_list(page=1, page_size=1)
            if shares is None:
                return jsonify({'valid': False, 'message': 'Cookie已失效，请重新登录后获取新Cookie'})
            if isinstance(shares, list) and len(shares) >= 0:
                return jsonify({'valid': True, 'message': 'Cookie有效'})
            return jsonify({'valid': False, 'message': '无法获取分享列表'})
        
        else:
            return jsonify({'valid': False, 'message': f'不支持的平台类型: {platform}'})
            
    except Exception as e:
        return jsonify({'valid': False, 'message': f'验证失败: {str(e)}'})


# ── 资源管理 API（文件夹视图）──────────────────────────────

@app.route('/api/resources', methods=['GET'])
def list_resources():
    """获取所有资源列表"""
    keyword = request.args.get('keyword', '')
    sort = request.args.get('sort', 'updated_at')
    order = request.args.get('order', 'desc')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    resources = get_resources(keyword, sort, order, page, page_size)
    return jsonify(resources)


@app.route('/api/resources', methods=['POST'])
def create_resource():
    """创建新资源"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求体'}), 400
    name = data.get('name', '').strip()
    notes = data.get('notes', '').strip()
    if not name:
        return jsonify({'error': '请输入资源名称'}), 400
    result = add_resource(name, notes)
    log.info(f'创建资源: {name}')
    return jsonify(result)


@app.route('/api/resources/<int:resource_id>', methods=['GET'])
def read_resource(resource_id):
    """获取资源详情（含关联分享列表）"""
    resource = get_resource(resource_id)
    if not resource:
        return jsonify({'error': '资源不存在'}), 404
    return jsonify(resource)


@app.route('/api/resources/<int:resource_id>', methods=['PUT'])
def edit_resource(resource_id):
    """更新资源信息"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求体'}), 400
    ok = update_resource(resource_id, data)
    if not ok:
        return jsonify({'error': '无有效字段可更新'}), 400
    log.info(f'更新资源: id={resource_id}')
    return jsonify({'success': True})


@app.route('/api/resources/<int:resource_id>', methods=['DELETE'])
def remove_resource(resource_id):
    """删除资源（级联删除关联）"""
    delete_resource(resource_id)
    log.info(f'删除资源: id={resource_id}')
    return jsonify({'success': True})


@app.route('/api/resources/<int:resource_id>/shares', methods=['PUT'])
def update_resource_shares_api(resource_id):
    """更新资源的全部关联分享"""
    data = request.get_json()
    share_ids = (data or {}).get('share_ids', [])
    # 验证每个share_id是否有效
    conn = get_conn()
    valid_ids = []
    for sid in share_ids:
        row = conn.execute("SELECT id FROM shares WHERE id=? AND is_deleted=0", (sid,)).fetchone()
        if row:
            valid_ids.append(sid)
    conn.close()
    update_resource_shares(resource_id, valid_ids)
    log.info(f'更新资源关联: id={resource_id}, 分享数={len(valid_ids)}')
    return jsonify({'success': True, 'count': len(valid_ids)})


@app.route('/api/resources/<int:resource_id>/shares/<int:share_id>', methods=['DELETE'])
def remove_share_from_resource_api(resource_id, share_id):
    """从资源中移除某个分享关联"""
    remove_share_from_resource(resource_id, share_id)
    return jsonify({'success': True})


@app.route('/api/available_shares', methods=['GET'])
def list_available_shares():
    """获取可关联的分享列表（用于选择器）"""
    keyword = request.args.get('keyword', '')
    source = request.args.get('source', '')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 50)), 200)
    result = get_available_shares(keyword, source, page, page_size)
    return jsonify(result)


if __name__ == '__main__':
    # 单实例保护 + PID 文件写入
    on_startup()

    init_db()
    log.info("=" * 50)
    log.info("  云盘分享管理工具 已启动")
    log.info("  访问地址: http://127.0.0.1:5000")
    log.info("=" * 50)

    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        on_shutdown()
