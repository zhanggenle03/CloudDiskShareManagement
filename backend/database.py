"""
数据持久化层 - SQLite
"""
import sqlite3
import os
from datetime import datetime
from logger import setup_logger

log = setup_logger('database')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'shares.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表结构"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS shares (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT    NOT NULL,          -- 'baidu' | 'quark'
            name        TEXT    NOT NULL,           -- 文件/分享名称
            url         TEXT    NOT NULL,           -- 分享链接
            pwd         TEXT,                       -- 提取码
            share_time  TEXT,                       -- 分享时间
            expire      TEXT,                       -- 有效期/状态
            parent_dir  TEXT,                       -- 所在目录（夸克专有）
            view_count  INTEGER DEFAULT -1,         -- 浏览次数（夸克专有）
            tags        TEXT    DEFAULT '',         -- 自定义标签，逗号分隔
            notes       TEXT    DEFAULT '',         -- 备注
            account_name TEXT    DEFAULT '',         -- 数据来源账号名称（最长7字符）
            is_deleted  INTEGER DEFAULT 0,          -- 软删除
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            updated_at  TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_shares_source   ON shares(source);
        CREATE INDEX IF NOT EXISTS idx_shares_expire   ON shares(expire);
        CREATE INDEX IF NOT EXISTS idx_shares_name     ON shares(name);
        CREATE INDEX IF NOT EXISTS idx_shares_deleted  ON shares(is_deleted);

        CREATE TABLE IF NOT EXISTS import_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            source      TEXT,
            total       INTEGER,
            imported    INTEGER,
            skipped     INTEGER,
            import_time TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS tag_colors (
            name  TEXT PRIMARY KEY,  -- 标签名称
            color TEXT NOT NULL DEFAULT '#4F6EF7'  -- 标签颜色（hex）
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            platform    TEXT    NOT NULL,          -- 'baidu' | 'quark'
            name        TEXT    NOT NULL DEFAULT '', -- 账号名称(用户自定义)
            cookie      TEXT    DEFAULT '',         -- 网盘Cookie
            uk          TEXT    DEFAULT '',         -- 百度网盘用户ID（仅百度需要）
            is_valid    INTEGER DEFAULT 0,          -- Cookie是否有效 0未知 1有效 -1无效
            remark      TEXT    DEFAULT '',         -- 备注
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            updated_at  TEXT    DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()

    # 数据库迁移：给 accounts 表添加 remark 字段
    try:
        c = conn.cursor()
        c.execute("SELECT remark FROM accounts LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE accounts ADD COLUMN remark TEXT DEFAULT ''")
        conn.commit()
        log.info('数据库迁移：accounts 表添加 remark 字段')

    # 数据库迁移：给 accounts 表添加 uk 字段（百度网盘用户ID）
    try:
        c = conn.cursor()
        c.execute("SELECT uk FROM accounts LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE accounts ADD COLUMN uk TEXT DEFAULT ''")
        conn.commit()
        log.info('数据库迁移：accounts 表添加 uk 字段')

    # 数据库迁移：给 accounts 表添加 last_verified_at 字段（验证时间戳）
    try:
        c = conn.cursor()
        c.execute("SELECT last_verified_at FROM accounts LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE accounts ADD COLUMN last_verified_at INTEGER DEFAULT 0")
        conn.commit()
        log.info('数据库迁移：accounts 表添加 last_verified_at 字段')

    # 数据库迁移：给 shares 表添加 account_name 字段（数据来源账号名称）
    try:
        c = conn.cursor()
        c.execute("SELECT account_name FROM shares LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE shares ADD COLUMN account_name TEXT DEFAULT ''")
        conn.commit()
        log.info('数据库迁移：shares 表添加 account_name 字段')

    # 数据库迁移：给 shares 表添加 share_id 字段（网盘端分享ID，用于取消分享等操作）
    try:
        c = conn.cursor()
        c.execute("SELECT share_id FROM shares LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE shares ADD COLUMN share_id TEXT DEFAULT ''")
        conn.commit()
        log.info('数据库迁移：shares 表添加 share_id 字段')

    # 数据库迁移：给 shares 表添加 account_id 字段（关联账号ID，用于取消分享时查找Cookie）
    try:
        c = conn.cursor()
        c.execute("SELECT account_id FROM shares LIMIT 0")
    except Exception:
        c = conn.cursor()
        c.execute("ALTER TABLE shares ADD COLUMN account_id INTEGER DEFAULT 0")
        conn.commit()
        log.info('数据库迁移：shares 表添加 account_id 字段')

    conn.close()
    log.info('数据库初始化完成')
    
    # 初始化资源表（文件夹视图）
    init_resource_tables()


def upsert_share(share: dict) -> dict:
    """
    插入或更新分享记录（按 url 去重）
    
    更新策略（2026-04-03）：
    - 如果新数据的提取码为空，保留数据库中已有的提取码（不覆盖）
    - 如果新数据有提取码，使用新数据的提取码
    - 其他字段正常更新（name, expire, view_count等）
    - 如果记录已存在但被软删除（is_deleted=1），视为"新增"而非"更新"
    
    这样可以保留CSV导入时的提取码，同时通过API更新状态
    """
    conn = get_conn()
    c = conn.cursor()
    # 检查是否已存在（包括被软删除的）
    c.execute("SELECT id, pwd, is_deleted, account_name, share_id, account_id FROM shares WHERE url = ?", (share['url'],))
    row = c.fetchone()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 提取 account_name（最长7字符），仅在新记录提供时更新；否则保留已有值
    new_account_name = share.get('account_name', '')
    if new_account_name:
        new_account_name = new_account_name[:7]

    # 提取 share_id（网盘端分享ID）和 account_id（关联账号ID）
    new_share_id = share.get('share_id', '')
    new_account_id = share.get('account_id', 0) or 0

    if row:
        # 如果记录被软删除，视为"新增"（重新激活）
        if row['is_deleted'] == 1:
            log.debug(f'重新激活已删除的分享: {share.get("name")[:30]}..., url={share.get("url")[:50]}...')
            c.execute("""
                UPDATE shares SET source=?, name=?, pwd=?, share_time=?, expire=?,
                    parent_dir=?, view_count=?, account_name=?, share_id=?, account_id=?,
                    is_deleted=0, updated_at=?
                WHERE url=?
            """, (
                share.get('source'), share.get('name'), share.get('pwd'),
                share.get('share_time'), share.get('expire'), share.get('parent_dir'),
                share.get('view_count', -1), new_account_name, new_share_id, new_account_id, now, share['url']
            ))
            conn.commit()
            conn.close()
            log.info(f'重新激活分享: {share.get("name")[:30]}..., url={share.get("url")[:50]}...')
            return {'action': 'inserted', 'id': row['id']}
        
        # 智能合并提取码：如果新数据为空，保留旧数据
        existing_pwd = row['pwd'] if 'pwd' in row.keys() else ''
        new_pwd = share.get('pwd', '')

        # 如果新提取码为空，但数据库中有提取码，保留数据库中的
        if not new_pwd and existing_pwd:
            final_pwd = existing_pwd
            log.debug(f'保留原有提取码: {existing_pwd}')
        else:
            final_pwd = new_pwd

        # account_name 智能合并：新数据有值则用新值，否则保留已有值
        existing_account_name = row['account_name'] or ''
        final_account_name = new_account_name if new_account_name else existing_account_name

        # share_id 智能合并：新数据有值则用新值，否则保留已有值
        existing_share_id = row['share_id'] or ''
        final_share_id = new_share_id if new_share_id else existing_share_id

        # account_id 智能合并：新数据有值则用新值，否则保留已有值
        existing_account_id = row['account_id'] or 0
        final_account_id = new_account_id if new_account_id else existing_account_id

        c.execute("""
            UPDATE shares SET name=?, pwd=?, share_time=?, expire=?,
                parent_dir=?, view_count=?, account_name=?, share_id=?, account_id=?,
                is_deleted=0, updated_at=?
            WHERE url=?
        """, (
            share.get('name'), final_pwd, share.get('share_time'),
            share.get('expire'), share.get('parent_dir'), share.get('view_count', -1),
            final_account_name, final_share_id, final_account_id, now, share['url']
        ))
        conn.commit()
        conn.close()
        log.info(f'更新分享: {share.get("name")[:30]}..., url={share.get("url")[:50]}...')
        return {'action': 'updated', 'id': row['id']}
    else:
        log.debug(f'插入分享: {share.get("name")[:30]}..., url={share.get("url")[:50]}...')
        c.execute("""
            INSERT INTO shares (source, name, url, pwd, share_time, expire, parent_dir, view_count, account_name, share_id, account_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            share.get('source'), share.get('name'), share.get('url'),
            share.get('pwd'), share.get('share_time'), share.get('expire'),
            share.get('parent_dir'), share.get('view_count', -1), new_account_name, new_share_id, new_account_id
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return {'action': 'inserted', 'id': new_id}


def get_shares(source=None, expire_filter=None, keyword=None, tag=None,
               page=1, page_size=20, sort='share_time', order='desc'):
    conn = get_conn()
    c = conn.cursor()

    conditions = ["is_deleted = 0"]
    params = []

    if source and source != 'all':
        conditions.append("source LIKE ?")
        params.append(f'{source}%')

    if expire_filter == 'valid':
        conditions.append("expire NOT IN ('已失效', '分享已过期', '分享失败') AND expire != ''")
    elif expire_filter == 'limited':
        # 限时有效: 未失效且非永久有效
        conditions.append("expire NOT IN ('已失效', '分享已过期', '分享失败', '永久有效') AND expire != ''")
    elif expire_filter == 'expired':
        conditions.append("expire IN ('已失效', '分享已过期', '分享失败')")
    elif expire_filter == 'permanent':
        conditions.append("expire = '永久有效'")

    if keyword:
        conditions.append("(name LIKE ? OR url LIKE ? OR notes LIKE ?)")
        kw = f'%{keyword}%'
        params.extend([kw, kw, kw])

    if tag:
        conditions.append("(',' || tags || ',') LIKE ?")
        params.append(f'%,{tag},%')

    where = " AND ".join(conditions)

    # 总数
    c.execute(f"SELECT COUNT(*) as cnt FROM shares WHERE {where}", params)
    total = c.fetchone()['cnt']

    # 排序白名单
    sort_col = sort if sort in ('share_time', 'name', 'expire', 'created_at', 'view_count') else 'share_time'
    order_dir = 'DESC' if order.lower() == 'desc' else 'ASC'

    offset = (page - 1) * page_size
    c.execute(
        f"SELECT * FROM shares WHERE {where} ORDER BY {sort_col} {order_dir} LIMIT ? OFFSET ?",
        params + [page_size, offset]
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {'total': total, 'page': page, 'page_size': page_size, 'data': rows}


def update_share(share_id: int, fields: dict):
    allowed = {'name', 'pwd', 'expire', 'tags', 'notes', 'is_deleted', 'account_name', 'share_id', 'account_id'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f"{k}=?" for k in updates)
    conn = get_conn()
    conn.execute(f"UPDATE shares SET {set_clause} WHERE id=?",
                 list(updates.values()) + [share_id])
    conn.commit()
    conn.close()
    return True


def delete_share(share_id: int, hard=False):
    conn = get_conn()
    if hard:
        conn.execute("DELETE FROM shares WHERE id=?", (share_id,))
    else:
        conn.execute("UPDATE shares SET is_deleted=1, updated_at=datetime('now','localtime') WHERE id=?",
                     (share_id,))
    conn.commit()
    conn.close()


def batch_delete(ids: list, hard=False):
    conn = get_conn()
    placeholders = ','.join('?' * len(ids))
    if hard:
        conn.execute(f"DELETE FROM shares WHERE id IN ({placeholders})", ids)
    else:
        conn.execute(f"UPDATE shares SET is_deleted=1 WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def get_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN source LIKE 'baidu%' THEN 1 ELSE 0 END) as baidu_count,
            SUM(CASE WHEN source LIKE 'quark%' THEN 1 ELSE 0 END) as quark_count,
            SUM(CASE WHEN expire='永久有效' THEN 1 ELSE 0 END) as permanent,
            SUM(CASE WHEN expire IN ('已失效','分享已过期','分享失败') THEN 1 ELSE 0 END) as expired,
            SUM(CASE WHEN expire NOT IN ('已失效','分享已过期','分享失败','永久有效') AND expire != '' THEN 1 ELSE 0 END) as expiring
        FROM shares WHERE is_deleted=0
    """)
    row = dict(c.fetchone())
    # 获取所有标签
    c.execute("SELECT tags FROM shares WHERE is_deleted=0 AND tags != ''")
    all_tags = []
    for r in c.fetchall():
        all_tags.extend([t.strip() for t in r['tags'].split(',') if t.strip()])
    tag_counts = {}
    for t in all_tags:
        tag_counts[t] = tag_counts.get(t, 0) + 1
    row['tags'] = tag_counts
    conn.close()
    return row


def log_import(filename, source, total, imported, skipped):
    conn = get_conn()
    conn.execute(
        "INSERT INTO import_log (filename, source, total, imported, skipped) VALUES (?,?,?,?,?)",
        (filename, source, total, imported, skipped)
    )
    conn.commit()
    conn.close()


def get_import_logs():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM import_log ORDER BY import_time DESC LIMIT 20")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def clear_import_logs():
    """清空所有导入记录"""
    conn = get_conn()
    conn.execute("DELETE FROM import_log")
    conn.commit()
    conn.close()


# ── 标签颜色管理 ────────────────────────────────────────────

def get_all_tag_colors():
    """获取所有标签颜色配置"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name, color FROM tag_colors")
    result = {row['name']: row['color'] for row in c.fetchall()}
    conn.close()
    return result


def set_tag_color(name: str, color: str):
    """设置标签颜色（upsert）"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO tag_colors (name, color) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET color=excluded.color
    """, (name, color))
    conn.commit()
    conn.close()


def delete_tag_color(name: str):
    """删除标签颜色配置"""
    conn = get_conn()
    conn.execute("DELETE FROM tag_colors WHERE name=?", (name,))
    conn.commit()
    conn.close()


def get_stats_with_colors():
    """获取统计信息，包含标签及其颜色"""
    stats = get_stats()
    colors = get_all_tag_colors()
    # 为每个标签添加颜色
    colored_tags = {}
    for tag, count in stats['tags'].items():
        colored_tags[tag] = {'count': count, 'color': colors.get(tag, '')}
    stats['tags'] = colored_tags
    return stats


# ── 用户设置持久化 ─────────────────────────────────────────

def get_setting(key: str, default: str = ''):
    """读取设置项"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str):
    """写入设置项（upsert）"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    """获取所有设置"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    result = {row['key']: row['value'] for row in c.fetchall()}
    conn.close()
    return result


# ── 网盘账号管理 ──────────────────────────────────────────────

def add_account(platform: str, name: str, cookie: str = '', remark: str = '') -> int:
    """添加网盘账号"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO accounts (platform, name, cookie, remark) VALUES (?, ?, ?, ?)",
        (platform, name, cookie, remark)
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    log.info(f'添加账号: platform={platform}, name={name}')
    return new_id


def get_accounts(platform: str = None) -> list:
    """获取账号列表"""
    conn = get_conn()
    c = conn.cursor()
    if platform:
        c.execute("SELECT id, platform, name, cookie, is_valid, remark, created_at, updated_at FROM accounts WHERE platform=? ORDER BY updated_at DESC", (platform,))
    else:
        c.execute("SELECT id, platform, name, cookie, is_valid, remark, created_at, updated_at FROM accounts ORDER BY platform, updated_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_account(account_id: int) -> dict:
    """获取单个账号(包含cookie)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM accounts WHERE id=?", (account_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_account(account_id: int, fields: dict) -> bool:
    """更新账号信息"""
    allowed = {'name', 'cookie', 'is_valid', 'remark', 'last_verified_at'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f"{k}=?" for k in updates)
    conn = get_conn()
    conn.execute(f"UPDATE accounts SET {set_clause} WHERE id=?",
                 list(updates.values()) + [account_id])
    conn.commit()
    conn.close()
    log.info(f'更新账号: id={account_id}, 字段={list(updates.keys())}')
    return True


def delete_account(account_id: int) -> bool:
    """删除账号"""
    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()
    conn.close()
    log.info(f'删除账号: id={account_id}')
    return True


# ── 资源文件夹管理（文件夹视图）─────────────────────────────

def init_resource_tables():
    """创建资源表和资源-分享关联表"""
    conn = get_conn()
    c = conn.cursor()

    # 资源表：用户自建的资源分组
    c.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,           -- 资源名称
            notes       TEXT    DEFAULT '',         -- 备注
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            updated_at  TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()

    # 资源-分享关联表
    c.execute("""
        CREATE TABLE IF NOT EXISTS resource_shares (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,           -- 关联的资源ID
            share_id    INTEGER NOT NULL,           -- 关联的分享ID
            sort_order  INTEGER DEFAULT 0,          -- 排序顺序
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            UNIQUE(resource_id, share_id),
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
            FOREIGN KEY (share_id) REFERENCES shares(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # 创建索引
    c.execute("CREATE INDEX IF NOT EXISTS idx_rs_resource ON resource_shares(resource_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rs_share ON resource_shares(share_id)")

    conn.close()
    log.info('资源表初始化完成')


# ── 资源 CRUD ─────────────────────────────────────────────

def add_resource(name: str, notes: str = '') -> dict:
    """添加资源"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO resources (name, notes) VALUES (?, ?)", (name, notes))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log.info(f'添加资源: name={name}, id={new_id}')
    return {'id': new_id, 'name': name, 'notes': notes}


def get_resources(keyword: str = '', sort: str = 'updated_at', order: str = 'desc',
                  page: int = 1, page_size: int = 50) -> list:
    """获取所有资源列表（含关联分享），支持排序和分页"""
    conn = get_conn()
    c = conn.cursor()
    
    # 排序字段映射
    sort_field_map = {'name': 'name', 'updated_at': 'updated_at', 'created_at': 'created_at'}
    sort_field = sort_field_map.get(sort, 'updated_at')
    order = 'ASC' if order == 'asc' else 'DESC'
    
    # 先获取总数
    if keyword:
        c.execute("SELECT COUNT(*) FROM resources WHERE name LIKE ?", (f'%{keyword}%',))
    else:
        c.execute("SELECT COUNT(*) FROM resources")
    total = c.fetchone()[0]
    
    # 分页
    offset = (page - 1) * page_size
    if keyword:
        c.execute(f"SELECT * FROM resources WHERE name LIKE ? ORDER BY {sort_field} {order} LIMIT ? OFFSET ?",
                   (f'%{keyword}%', page_size, offset))
    else:
        c.execute(f"SELECT * FROM resources ORDER BY {sort_field} {order} LIMIT ? OFFSET ?",
                   (page_size, offset))
    rows = [dict(r) for r in c.fetchall()]
    
    # 为每个资源加载关联的分享
    for resource in rows:
        c.execute("""
            SELECT s.*, rs.sort_order
            FROM resource_shares rs
            JOIN shares s ON rs.share_id = s.id AND s.is_deleted = 0
            WHERE rs.resource_id = ?
            ORDER BY rs.sort_order ASC
        """, (resource['id'],))
        resource['shares'] = [dict(r) for r in c.fetchall()]
    
    conn.close()
    return {'data': rows, 'total': total, 'page': page, 'page_size': page_size}


def get_resource(resource_id: int) -> dict:
    """获取单个资源详情"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM resources WHERE id=?", (resource_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    resource = dict(row)
    
    # 获取关联的分享列表
    c.execute("""
        SELECT s.*, rs.sort_order 
        FROM resource_shares rs
        JOIN shares s ON rs.share_id = s.id AND s.is_deleted = 0
        WHERE rs.resource_id = ?
        ORDER BY rs.sort_order ASC
    """, (resource_id,))
    resource['shares'] = [dict(r) for r in c.fetchall()]
    
    # 统计各平台数量
    platforms = set()
    for s in resource['shares']:
        platform = s.get('source', '')
        if platform and ':' in platform:
            platform = platform.split(':')[0]
        if platform:
            platforms.add(platform)
    resource['platforms'] = list(platforms)
    
    conn.close()
    return resource


def update_resource(resource_id: int, fields: dict) -> bool:
    """更新资源信息"""
    allowed = {'name', 'notes'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f"{k}=?" for k in updates)
    conn = get_conn()
    conn.execute(f"UPDATE resources SET {set_clause} WHERE id=?",
                 list(updates.values()) + [resource_id])
    conn.commit()
    conn.close()
    log.info(f'更新资源: id={resource_id}, 字段={list(updates.keys())}')
    return True


def delete_resource(resource_id: int) -> bool:
    """删除资源（级联删除关联）"""
    conn = get_conn()
    # 先删除关联
    conn.execute("DELETE FROM resource_shares WHERE resource_id=?", (resource_id,))
    # 再删除资源
    conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()
    log.info(f'删除资源: id={resource_id}')
    return True


# ── 资源-分享关联管理 ─────────────────────────────────────

def add_share_to_resource(resource_id: int, share_ids: list) -> int:
    """为资源添加分享关联，返回新增的关联数"""
    conn = get_conn()
    added = 0
    for sid in share_ids:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO resource_shares (resource_id, share_id) VALUES (?, ?)",
                (resource_id, sid)
            )
            if conn.total_changes > 0:
                added += 1
        except Exception:
            pass
    # 更新资源的updated_at
    conn.execute(
        "UPDATE resources SET updated_at=datetime('now','localtime') WHERE id=?",
        (resource_id,)
    )
    conn.commit()
    conn.close()
    log.info(f'资源 {resource_id} 新增 {added} 个分享关联')
    return added


def remove_share_from_resource(resource_id: int, share_id: int) -> bool:
    """移除资源的某个分享关联"""
    conn = get_conn()
    conn.execute(
        "DELETE FROM resource_shares WHERE resource_id=? AND share_id=?",
        (resource_id, share_id)
    )
    conn.execute(
        "UPDATE resources SET updated_at=datetime('now','localtime') WHERE id=?",
        (resource_id,)
    )
    conn.commit()
    conn.close()
    log.info(f'资源 {resource_id} 移除分享关联 {share_id}')
    return True


def update_resource_shares(resource_id: int, share_ids: list):
    """更新资源的全部关联（替换模式）"""
    conn = get_conn()
    # 删除旧关联
    conn.execute("DELETE FROM resource_shares WHERE resource_id=?", (resource_id,))
    # 添加新关联
    for i, sid in enumerate(share_ids):
        try:
            conn.execute(
                "INSERT OR IGNORE INTO resource_shares (resource_id, share_id, sort_order) VALUES (?, ?, ?)",
                (resource_id, sid, i)
            )
        except Exception:
            pass
    conn.execute(
        "UPDATE resources SET updated_at=datetime('now','localtime') WHERE id=?",
        (resource_id,)
    )
    conn.commit()
    conn.close()


# ── 可选分享列表（用于关联选择）────────────────────────────

def get_available_shares(keyword: str = '', source: str = None, page: int = 1, page_size: int = 50):
    """获取可关联的有效分享列表（排除已删除的）"""
    conn = get_conn()
    c = conn.cursor()
    
    conditions = ["is_deleted = 0"]
    params = []
    
    if keyword:
        conditions.append("(name LIKE ? OR url LIKE ?)")
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    
    if source and source != 'all':
        conditions.append("source LIKE ?")
        params.append(f'{source}%')
    
    where = " AND ".join(conditions)
    
    # 总数
    c.execute(f"SELECT COUNT(*) as cnt FROM shares WHERE {where}", params)
    total = c.fetchone()['cnt']
    
    offset = (page - 1) * page_size
    c.execute(
        f"SELECT * FROM shares WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset]
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {'total': total, 'data': rows}
