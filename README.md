# 🌐 n8n-chinese: 自动化 n8n 简体中文前端构建流水线

> 专为 n8n 打造的自动化简体中文（zh-CN）构建与发布流水线。基于官方源码与 Turborepo 拓扑编译，提供严格 1:1 版本匹配的前端本地化补丁包。

[![Build & Release](https://github.com/zdaben/n8n-chinese/actions/workflows/build.yml/badge.svg)](https://github.com/zdaben/n8n-chinese/actions/workflows/build.yml)
[![GitHub release](https://img.shields.io/github/v/release/zdaben/n8n-chinese?include_prereleases&color=brightgreen)](https://github.com/zdaben/n8n-chinese/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Installer](https://img.shields.io/badge/Installer-zdaben%2Fn8n__install-orange)](https://github.com/zdaben/n8n_install)

---

## 🌟 项目特色

* 🔄 **无人值守自动化追踪**：GitHub Actions 每 6 小时自动比对 n8n 官方 `stable` 版本，发现新版本自动触发编译与发布。
* 🧱 **Turborepo 拓扑编译**：严格根据官方源码环境（动态探测 Node/pnpm 版本），递归编译 `@n8n/i18n` 等前置依赖，保证产物 100% 稳定可靠。
* 🛡️ **智能多语言门禁（Quality Gate）**：内置 `validate_locale.py`，自动清洗空值词条，严格校验插值占位符（如 `{{time}}`），杜绝因格式错误导致的前端渲染崩溃。
* 📦 **开箱即用 Releases**：每次构建自动发布 `release/X.Y.Z` Tag，提供即插即用的 `editor-ui.tar.gz` 产物。

---

## 🚀 快速使用

### 方式一：使用配套一键管理工具（推荐）

配合配套的 [zdaben/n8n_install](https://github.com/zdaben/n8n_install) CLI 工具，可实现官方引擎与汉化补丁的自动匹配、热更新与安全降级：

```bash
curl -fsSL https://raw.githubusercontent.com/zdaben/n8n_install/main/n8n.sh -o /usr/local/bin/n8n && chmod +x /usr/local/bin/n8n && n8n install
```

---

### 方式二：手动在 Docker Compose 中挂载使用

如果你已有运行中的官方 n8n 容器，可通过目录挂载方式直接替换前端 UI：

#### 1. 下载对应版本的汉化包并解压
假设你的 n8n 版本为 `2.36.8`：
```bash
# 创建前端目录
mkdir -p /root/n8n/n8n_ui

# 下载对应版本的 editor-ui.tar.gz
curl -fsSL "https://github.com/zdaben/n8n-chinese/releases/download/release%2F2.36.8/editor-ui.tar.gz" -o /tmp/editor-ui.tar.gz

# 解压并赋予权限 (n8n 容器内部运行 UID 为 1000)
tar -xzf /tmp/editor-ui.tar.gz -C /root/n8n/n8n_ui
chown -R 1000:1000 /root/n8n/n8n_ui
rm -f /tmp/editor-ui.tar.gz
```

#### 2. 在 `docker-compose.yml` 中挂载
```yaml
services:
  n8n:
    image: n8nio/n8n:2.36.8
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_DEFAULT_LOCALE=zh-CN      # 启用中文本地化
      - GENERIC_TIMEZONE=Asia/Shanghai
      - TZ=Asia/Shanghai
    volumes:
      - ./n8n_data:/home/node/.n8n
      # 挂载替换官方前端静态文件
      - /root/n8n/n8n_ui/dist:/usr/local/lib/node_modules/n8n/node_modules/n8n-editor-ui/dist
```

#### 3. 重启容器
```bash
docker compose up -d
```

---

## ⚙️ 手动触发特定版本构建

如果需要为历史版本或测试版本单独构建汉化补丁：

1. 进入本仓库的 **[Actions](../../actions/workflows/build.yml)** 页面。
2. 点击左侧 **Build & Release n8n Chinese UI**。
3. 点击右侧 **Run workflow** 下拉框，输入目标版本号（例如 `2.33.7` 或 `2.36.8`）。
4. 等待 4~5 分钟构建完成，即可在 **[Releases](../../releases)** 页面下载产物。

---

## 🛠️ 词条维护与本地校验

欢迎提交 PR 补充或修正翻译！词条文件位于 `languages/zh-CN.json`。

### 本地校验词条语法与覆盖率
在提交修改前，可运行仓库内置的门禁脚本检查格式：

```bash
# 语法与占位符校验
python3 scripts/validate_locale.py <官方en.json路径> languages/zh-CN.json
```

**门禁规则说明**：
* ❌ **阻断错误 (Blocker)**：JSON 语法错误、插值占位符 `{param}` 不匹配、空值词条（阻断构建，防止前端崩溃）。
* ⚠️ **警告提醒 (Warning)**：新增待翻译词条、已废弃旧词条（输出统计报告，允许正常打包并 Fallback 显示英文）。

---

## 📂 仓库结构

```text
zdaben/n8n-chinese
├── .github/
│   └── workflows/
│       └── build.yml          # GitHub Actions 自动化检测与构建工作流
├── languages/
│   └── zh-CN.json             # 简体中文核心翻译字典
├── scripts/
│   └── validate_locale.py     # 多语言质量门禁与清洗校验脚本
├── LICENSE                    # MIT 开源许可证
└── README.md
```

---

## 🔗 相关项目

* **一键管理与部署 CLI**：[zdaben/n8n_install](https://github.com/zdaben/n8n_install)
* **n8n 官方仓库**：[n8n-io/n8n](https://github.com/n8n-io/n8n)

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。
```
