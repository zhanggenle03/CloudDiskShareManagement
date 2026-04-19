# 云盘分享管理工具

一个轻量级的网盘分享链接管理工具，支持百度网盘和夸克网盘的分享链接集中管理、搜索、标签分类和有效期监控。
PS：全程使用AI编写的一个小工具包括该README，可能存在不对的情况

## 功能特性

- **多源导入** — 支持百度网盘、夸克网盘 CSV 导入，自动识别格式
- **链接管理** — 查看、编辑、删除、批量操作，按来源/有效期/标签筛选
- **标签系统** — 自定义标签分类，支持自定义颜色，右键菜单管理
- **有效期监控** — 自动识别有效/即将过期/已失效状态，颜色标记一目了然
- **网盘同步** — 通过 Cookie 连接百度/夸克网盘，手动同步最新分享列表
- **账号管理** — 管理多个网盘账号的 Cookie，验证账号状态
- **暗黑模式** — 支持亮色/暗色主题切换
- **设置持久化** — 所有偏好设置保存在服务端，刷新不丢失

## 快速开始

### 环境要求

- Windows 7+
- Python 3.8+

### 安装与启动

**一键启动（推荐）**

双击 `start.bat`，自动完成：
1. 检查Python环境并安装依赖
2. 清理旧进程（自动删除app.pid）
3. 启动后端服务（静默模式，pythonw）
4. 打开本地启动页面（`frontend\launch.html`）
5. 自动检测服务状态并跳转到主界面

**启动特点：**
- ✅ launch.html 是完全独立的静态页面（file://协议访问）
- ✅ JavaScript自动检测服务状态，无需手动刷新
- ✅ 30秒超时保护，失败显示详细错误信息
- ✅ 提供"重试"和"手动打开"按钮

**访问地址**：http://127.0.0.1:5000

> 首次启动可能需要 5-10 秒，请耐心等待。如遇到问题，查看 `启动流程说明.md`。

## 项目结构

```
CloudDiskShareManagement_v0.2/
├── start.bat             # Windows 一键启动（推荐）
├── requirements.txt      # Python 依赖
├── README.md
│
├── backend/              # Flask 后端
│   ├── app.py            # API 路由 + 进程管理
│   ├── database.py       # SQLite 数据操作层
│   ├── parser.py         # CSV 解析（百度/夸克格式自动识别）
│   ├── logger.py         # 日志配置
│   ├── quark_api.py      # 夸克网盘 API 封装
│   ├── baidu_api.py      # 百度网盘 API 封装
│   ├── sync_manager.py   # 网盘同步管理器（支持夸克/百度）
│   └── process_manager.py # 进程管理模块
│
├── frontend/             # 前端页面
│   ├── launch.html       # 启动页面（启动动画+自动检测）
│   └── index.html        # 单页应用（侧边栏+卡片/列表布局）
│
└── data/                 # 运行时数据（自动生成）
    ├── shares.db         # SQLite 数据库
    └── logs/             # 日志文件
        └── app.log       # 应用日志
```

## CSV 导入格式

### 百度网盘

文件需包含以下列（表头不限语言）：

| 文件名 | 链接 | 提取码 | 分享时间 | 有效期 |
|--------|------|--------|----------|--------|

### 夸克网盘

文件需包含以下列（`分享地址` 字段可能为多行文本，程序会自动提取链接）：

| 分享文件上一级目录名称 | 分享名 | 分享地址 | 提取码 | 分享时间 | 浏览次数 | 分享状态 |
|------------------------|--------|----------|--------|----------|----------|----------|

## 网盘同步

### 夸克网盘同步

1. 进入夸克网盘网页版，登录账号
2. 复制浏览器的 Cookie
3. 在「操作」→「网盘同步」中粘贴 Cookie 并保存
4. 点击「验证 Cookie」确认可用
5. 点击「立即同步」拉取最新分享列表

> Cookie 有效期有限，失效后需重新获取。

### 百度网盘同步

1. 进入百度网盘网页版（https://pan.baidu.com），登录账号
2. 按 F12 打开开发者工具，切换到 Network（网络）标签页
3. 刷新页面，任意点击一个请求，复制 Cookie 请求头
4. 在「账号管理」中添加百度网盘账号：
   - 粘贴 Cookie
5. 点击「验证 Cookie」确认可用
6. 在「操作」→「网盘同步」中选择百度账号，点击「立即同步」

> 百度网盘 Cookie 通常包含 `BDUSS`、`STOKEN` 等关键字段，请确保复制完整。

> 多账号同步：可同时选择多个账号（支持混合平台），系统会逐个同步并显示进度。

## 技术栈

- **后端**：Python + Flask + SQLite
- **前端**：原生 HTML/CSS/JS（无框架依赖）
- **通信**：RESTful API + CORS

## 常见问题

**Q: 启动时显示"无法访问该网页"？**
A: 此问题已修复。launch.html 现在通过 `file://` 协议访问，不依赖后端服务。启动流程：
1. 双击 `start.bat` 启动服务
2. 自动打开 `frontend\launch.html`（本地文件）
3. 显示启动动画并检测服务状态
4. 服务就绪后自动跳转

**Q: 启动页面一直显示"检测服务状态"？**
A: 请排查：
1. Python环境：`python --version`
2. 端口占用：`netstat -ano | findstr ":5000"`
3. 日志文件：`data/logs/app.log`
4. 手动启动：`python backend/app.py` 查看错误
5. 尝试重新双击 `start.bat`

**Q: 如何跳过启动页面？**
A: 等服务启动后（约5-10秒），直接访问：
- 主界面：http://127.0.0.1:5000/index.html
- 注意：如果服务未就绪，会显示"无法访问该网页"

**Q: 关闭网页后进程还在？**
A: 正常情况下会自动关闭。如果失败：
1. 删除 `app.pid` 文件
2. 任务管理器结束 `pythonw.exe`
3. 重新启动

**Q: launch.html 可以独立使用吗？**
A: 可以！直接双击 `frontend/launch.html` 即可打开。但需确保服务已启动，否则会显示连接失败。

**Q: 启动失败如何调试？**
A: 查看日志和错误信息：
- 应用日志：`data/logs/app.log`
- 启动说明：`启动流程说明.md`
- 手动启动：命令行运行 `python backend/app.py` 查看实时输出

## 自动构建 (CI/CD)

### GitHub Actions 自动打包

每次推送到 `main` 分支时，会自动构建 Windows 可执行文件：

1. **触发条件**：`push` 或 `pull_request` 到 `main`/`master` 分支
2. **构建产物**：
   - `CloudDiskShareManagement-Windows/` — 解压版（目录）
   - `CloudDiskShareManagement-Windows-Zip/` — 压缩包
3. **下载位置**：GitHub Actions 构建页面或 Release 页面

### 构建产物说明

构建完成后会生成：
- `CloudDiskShareManagement.exe` — 主程序（双击运行）
- `frontend/` — 前端资源
- `data/` — 数据目录（首次运行自动创建）
- `README.txt` — 使用说明

### 使用打包版本

1. 下载并解压 ZIP 文件
2. 双击 `CloudDiskShareManagement.exe`
3. 无需安装 Python 或任何依赖

### 创建 Release

当推送带 `v*.*.*` 标签时，会自动创建 GitHub Release：
```bash
git tag v1.0.0
git push origin v1.0.0
```
