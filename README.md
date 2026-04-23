# 云盘分享管理工具

一个轻量级的网盘分享链接管理工具，支持分享链接集中管理、搜索、标签分类和有效期监控。<br>
主要是在做网盘分享的时候发现链接不太好管理，就想着做个工具来管理。

PS：全程使用AI编写的一个小工具包括该README，可能存在不对的情况

## 功能特性

- **多方式导入** — 支持 Cookie 自动导入 、 CSV 导入
- **链接管理** — 查看、编辑、删除、批量操作，按来源/有效期/标签筛选
- **标签系统** — 自定义标签分类，支持自定义颜色
- **有效期监控** — 自动识别有效/即将过期/已失效状态
- **账号管理** — 管理多个网盘账号的 Cookie，验证账号状态

## 支持列表

| 网盘平台 | 网盘同步 | CSV导入 |
|--------|------|--------|
| 百度网盘 | ✅ | ✅ |
| 夸克网盘 | ✅ | ✅ |
| UC网盘 | ✅ | 平台无CSV |

## 快速开始

### 🔴 程序运行

下载Releases中打包好的压缩包

双击 `CloudDiskShareManagement.exe` 运行，自动打开浏览器管理界面

### 🔴 源码运行

#### 环境要求

- Windows 7+
- Python 3.8+

#### 安装与启动

**一键启动**

双击 `start.bat`，自动完成：
1. 检查Python环境并安装依赖
2. 清理旧进程（自动删除app.pid）
3. 启动后端服务（静默模式，pythonw）
4. 打开本地启动页面（`frontend\launch.html`）
5. 自动检测服务状态并跳转到主界面


> 首次启动可能需要 5-10 秒，请耐心等待。

## 项目结构

```
CloudDiskShareManagement/
├── start.bat                          # Windows 一键启动（推荐）
├── main.py                            # PyInstaller 打包入口
├── CloudDiskShareManagement.spec      # PyInstaller 打包配置
├── requirements.txt                   # Python 依赖
├── README.md
│
├── backend/                           # Flask 后端
│   ├── app.py                         # API 路由
│   ├── database.py                    # SQLite 数据操作层
│   ├── parser.py                      # CSV 解析（百度/夸克格式自动识别）
│   ├── logger.py                      # 日志配置
│   ├── paths.py                       # 路径配置模块
│   ├── quark_api.py                   # 夸克网盘 API 封装
│   ├── baidu_api.py                   # 百度网盘 API 封装
│   ├── uc_api.py                      # UC网盘 API 封装
│   ├── sync_manager.py                # 网盘同步管理器（支持夸克/百度/UC）
│   └── process_manager.py             # 进程管理模块
│
├── frontend/                          # 前端页面
│   ├── launch.html                    # 启动页面（启动动画+自动检测）
│   ├── index.html                     # 单页应用（侧边栏+卡片/列表布局）
│   └── app-icon.jpg                   # 应用图标
│
└── data/                              # 运行时数据（自动生成）
    ├── shares.db                      # SQLite 数据库
    └── logs/                          # 日志文件
        └── app.log                    # 应用日志
```

## 技术栈

- **后端**：Python + Flask + SQLite
- **前端**：原生 HTML/CSS/JS（无框架依赖）
- **通信**：RESTful API + CORS

## 常见问题

**Q: 启动页面一直显示"检测服务状态"？**<br>
A: 请排查：
1. Python环境：`python --version`
2. 端口占用：`netstat -ano | findstr ":5000"`
3. 日志文件：`data/logs/app.log`
4. 手动启动：`python backend/app.py` 查看错误
5. 尝试重新双击 `start.bat`

**Q: 关闭网页后进程还在？**<br>
A: 仅关闭标签页不会关闭项目进程，通过退出按钮关闭进程。如果失败：
1. 删除 `app.pid` 文件
2. 任务管理器结束 `pythonw.exe`
3. 重新启动

**Q: 启动失败如何调试？**<br>
A: 查看日志和错误信息：
- 应用日志：`data/logs/app.log`
