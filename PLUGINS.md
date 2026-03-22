# AstrbotPlugins 插件索引

> 此文件由 `scripts/generate-plugin-index.ps1` / `scripts/generate-plugin-index.mjs` 自动生成。

这个页面用于统一展示仓库内所有 AstrBot 插件。

## 索引总表

| 分类 | 插件名 | 目录 | 状态 | 简介 | 文档 |
|---|---|---|---|---|---|
| RSS | RSS 群组订阅桥接 | `rss/astrbot_plugin_rss_bridge` | 可用 | 为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。 | [README](./rss/astrbot_plugin_rss_bridge/README.md) |

## 分类索引

### RSS

#### 1. RSS 群组订阅桥接 (astrbot_plugin_rss_bridge)

- 路径：`rss/astrbot_plugin_rss_bridge`
- 版本：v0.2.0
- 作者：OpenAI
- 简介：为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。
- 支持平台：
  - OneBot V11
  - Telegram
- 文档：[README](./rss/astrbot_plugin_rss_bridge/README.md)
- 安装目录：`AstrBot/data/plugins/astrbot_plugin_rss_bridge`

## 索引维护规则

后续新增插件时，建议同步检查以下内容：

1. 插件目录中是否包含 `main.py`、`metadata.yaml`、`README.md` 等必要文件
2. 运行 `.\scripts\generate-plugin-index.ps1` 刷新索引
3. 提交生成后的 `README.md` 与 `PLUGINS.md`
