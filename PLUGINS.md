# AstrbotPlugins 插件索引

> 此文件由 `scripts/generate-plugin-index.ps1` / `scripts/generate-plugin-index.mjs` 自动生成。

这个页面用于统一展示仓库内所有 AstrBot 插件。

## 索引总表

| 分类 | 插件名 | 目录 | 状态 | 简介 | 文档 | 源码 | 下载 |
|---|---|---|---|---|---|---|---|
| RSS | RSS 群组订阅桥接 | `rss/astrbot_plugin_rss_bridge` | 可用 | 为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。 | [README](./rss/astrbot_plugin_rss_bridge/README.md) | [目录](https://github.com/zzzwannasleep/AstrbotPlugins/tree/main/rss/astrbot_plugin_rss_bridge) | [ZIP](https://github.com/zzzwannasleep/AstrbotPlugins/releases/download/plugins-latest/astrbot_plugin_rss_bridge.zip) |

## 分类索引

### RSS

#### 1. RSS 群组订阅桥接 (astrbot_plugin_rss_bridge)

- 路径：`rss/astrbot_plugin_rss_bridge`
- 版本：v0.4.7
- 作者：OpenAI
- 简介：为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。
- 支持平台：
  - OneBot V11
  - Telegram
- 文档：[README](./rss/astrbot_plugin_rss_bridge/README.md)
- 源码目录：[打开](https://github.com/zzzwannasleep/AstrbotPlugins/tree/main/rss/astrbot_plugin_rss_bridge)
- 下载链接：[astrbot_plugin_rss_bridge.zip](https://github.com/zzzwannasleep/AstrbotPlugins/releases/download/plugins-latest/astrbot_plugin_rss_bridge.zip)
- 安装目录：`AstrBot/data/plugins/astrbot_plugin_rss_bridge`

## 自动化说明

仓库中的 GitHub Actions 会在推送到 `main` 或手动触发时自动：

1. 运行 `scripts/generate-plugin-index.mjs` 刷新索引
2. 打包所有插件 ZIP
3. 发布/覆盖 `plugins-latest` 下的下载包

本地手动执行仅用于预览。
