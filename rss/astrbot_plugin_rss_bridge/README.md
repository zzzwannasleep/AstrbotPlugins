# AstrBot RSS 群组订阅插件

支持：

- OneBot V11
- Telegram Bot
- 按群组隔离 RSS 配置
- 自定义 RSS 名称
- 群管理员权限控制
- 可切换/自定义推送模板
- 自动轮询并推送更新
- 兼容 AstrBot 在仅传入 `context` 时的插件初始化方式

## 命令

```text
/rss add <名称> <RSS链接>
/rss del <名称>
/rss rename <旧名称> <新名称>
/rss list
/rss check [名称]
/rss preview
/rss help
```

名称中如果有空格，请加引号：

```text
/rss add "少数派" https://sspai.com/feed
```

## 配置项

- `poll_interval_seconds`：轮询间隔，默认 300 秒
- `request_timeout_seconds`：请求超时，默认 15 秒
- `summary_max_length`：摘要最大长度，默认 180
- `max_entries_per_push`：每次最多推送的新增条目数，默认 3
- `admin_only_commands`：是否仅允许群管理员执行管理命令，默认开启
- `admin_only_list`：是否连 `list/help` 也限制为管理员，默认关闭
- `admin_denied_message`：非管理员执行命令时的提示语
- `template_style`：推送模板风格，支持 `classic` / `pretty` / `compact` / `custom`
- `custom_message_template`：自定义单条推送模板
- `custom_overflow_template`：一次更新过多时的汇总模板
- `user_agent`：抓取 RSS 的请求头 User-Agent

## 说明

- 插件会把每个群的订阅独立存储。
- 新增订阅时会把当前 feed 内容记录为基线，不会立即补发历史消息。
- 默认只有群管理员可以管理订阅，普通成员默认可查看列表和帮助。
- 插件状态文件保存在 `data/plugin_data/astrbot_plugin_rss_bridge/state.json`。

## 模板变量

自定义模板可使用这些变量：

- 通用：`{alias}`、`{feed_title}`、`{title}`、`{published}`、`{summary}`、`{link}`
- 现成行片段：`{feed_title_line}`、`{title_line}`、`{published_line}`、`{summary_line}`、`{link_line}`
- 美化行片段：`{feed_title_pretty}`、`{title_pretty}`、`{published_pretty}`、`{summary_pretty}`、`{link_pretty}`
- 汇总模板：`{new_count}`、`{sent_count}`、`{skipped_count}`

可通过 `/rss preview` 直接预览当前模板效果。

## 安装

将此目录放入：

```text
AstrBot/data/plugins/astrbot_plugin_rss_bridge
```

然后在 AstrBot WebUI 中安装依赖并启用插件。

本仓库中的源码分类路径为：

```text
rss/astrbot_plugin_rss_bridge
```
