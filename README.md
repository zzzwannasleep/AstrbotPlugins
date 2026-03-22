# AstrbotPlugins

> 此文件由 `scripts/generate-plugin-index.ps1` / `scripts/generate-plugin-index.mjs` 自动生成。

这是一个用于集中存放多个 AstrBot 插件的仓库。

## 插件索引

完整索引页见：[`PLUGINS.md`](./PLUGINS.md)

## 分类总览

- `rss/`：RSS 类插件（1 个）

## 插件一览

### RSS 类

| 插件名 | 简介 | 平台 | 源码 | 下载 |
|---|---|---|---|---|
| RSS 群组订阅桥接 | 为 OneBot V11 和 Telegram 群组提供按群隔离的 RSS 订阅与自动推送能力。 | OneBot V11 / Telegram | [目录](https://github.com/zzzwannasleep/AstrbotPlugins/tree/main/rss/astrbot_plugin_rss_bridge) | [ZIP](https://github.com/zzzwannasleep/AstrbotPlugins/releases/download/plugins-latest/astrbot_plugin_rss_bridge.zip) |

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

## 自动化

仓库已支持 GitHub Actions：

- 自动刷新 `README.md` 和 `PLUGINS.md`
- 自动打包每个插件为 `<插件目录名>.zip`
- 自动发布到 GitHub Releases 的 `plugins-latest` 标签下

如果你在本地预览，也可以手动运行：

```powershell
.\scripts\generate-plugin-index.ps1
```
