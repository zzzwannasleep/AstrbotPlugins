# AstrbotPlugins

这是一个用于集中存放多个 AstrBot 插件的仓库。

## 插件索引

完整索引页见：[`PLUGINS.md`](./PLUGINS.md)

### RSS 类

| 插件名 | 路径 | 简介 | 平台 |
|---|---|---|---|
| RSS 群组订阅桥接 | `rss/astrbot_plugin_rss_bridge` | 支持群组隔离、管理员控制、推送模板美化的 RSS 自动推送插件 | OneBot V11 / Telegram |

## 目录约定

- `rss/`：RSS 类插件
- 后续可以继续按功能增加目录，例如：
  - `admin/`
  - `tools/`
  - `fun/`
  - `utility/`

## 安装方式

这个仓库是 **多插件源码仓库**。

实际部署到 AstrBot 时，请把具体插件目录单独放到：

```text
AstrBot/data/plugins/<插件目录名>
```

例如当前插件应放到：

```text
AstrBot/data/plugins/astrbot_plugin_rss_bridge
```

## 当前收录

- [`rss/astrbot_plugin_rss_bridge`](./rss/astrbot_plugin_rss_bridge)
  - 支持 OneBot V11 / Telegram
  - 支持按群隔离 RSS 订阅
  - 支持群管理员权限控制
  - 支持推送模板美化与自定义

## 后续规划

- 每增加一个插件，就在 `PLUGINS.md` 和本页索引表中补充一行
- 保持“一个插件一个独立目录”的结构，便于复制到 AstrBot 插件目录中使用
