# AstrbotPlugins

> 此文件由 `scripts/generate-plugin-index.ps1` / `scripts/generate-plugin-index.mjs` 自动生成。

这是一个用于集中存放多个 AstrBot 插件的仓库。

## 插件索引

完整索引页见：[`PLUGINS.md`](./PLUGINS.md)

## 分类总览

- `rss/`：RSS 类插件（1 个）

## 插件一览

### RSS 类

| 插件名 | 路径 | 简介 | 平台 |
|---|---|---|---|
| RSS 群组订阅桥接 | `rss/astrbot_plugin_rss_bridge` | 为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。 | OneBot V11 / Telegram |

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

## 索引维护

当你新增或修改插件后，运行以下命令即可自动刷新仓库索引：

```powershell
.\scripts\generate-plugin-index.ps1
```

建议在提交前执行一次，确保 `README.md` 和 `PLUGINS.md` 与仓库内容保持一致。
