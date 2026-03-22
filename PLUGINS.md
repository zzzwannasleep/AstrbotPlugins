# AstrbotPlugins 插件索引

这个页面用于统一展示仓库内所有 AstrBot 插件。

## 索引总表

| 分类 | 插件名 | 目录 | 状态 | 简介 | 文档 |
|---|---|---|---|---|---|
| RSS | RSS 群组订阅桥接 | `rss/astrbot_plugin_rss_bridge` | 可用 | 支持 OneBot V11 / Telegram、按群隔离订阅、管理员权限控制、模板美化与自定义 | [README](./rss/astrbot_plugin_rss_bridge/README.md) |

## 分类索引

### RSS

#### 1. astrbot_plugin_rss_bridge

- 路径：`rss/astrbot_plugin_rss_bridge`
- 状态：可用
- 支持平台：
  - OneBot V11
  - Telegram Bot
- 主要功能：
  - RSS 订阅添加、删除、重命名
  - 按群组隔离配置
  - 后台轮询自动推送
  - 群管理员权限控制
  - 推送模板美化与自定义

安装时请将该插件目录单独复制到：

```text
AstrBot/data/plugins/astrbot_plugin_rss_bridge
```

## 索引维护规则

后续新增插件时，建议同步更新以下内容：

1. 仓库根目录 `README.md`
2. 本文件 `PLUGINS.md`
3. 插件自身目录下的 `README.md`
