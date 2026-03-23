# AstrBot RSS 群组订阅插件

支持：

- OneBot V11
- Telegram Bot
- 按群组隔离 RSS 配置
- 自定义 RSS 名称
- 群管理员权限控制
- 可切换/自定义推送模板
- 支持多种图片模板预览
- 可选用 AstrBot 文转图生成图片推送
- 支持按群自定义模板风格
- 支持预览某个已订阅 RSS 的真实内容样式
- 图片模板会根据标题长度自动优化字号与换行
- 自动轮询并推送更新
- 支持直接订阅 `https://bangumi.tv/calendar`，自动转换为 Bangumi 每日放送聚合推送
- 支持直接订阅 `https://yuc.wiki/new/` 或 `https://yuc.wiki/atom.xml`，自动拆分为 YUC 单番剧更新推送
- 兼容 AstrBot 在仅传入 `context` 时的插件初始化方式
- 兼容 AstrBot 在 `get_astrbot_data_path()` 返回字符串时的路径处理方式

## 命令

```text
/rss add <名称> <RSS链接>
/rss del <名称>
/rss rename <旧名称> <新名称>
/rss list
/rss check [名称]
/rss style
/rss style text <风格>
/rss style image <风格>
/rss style render <text|image>
/rss style preview <text|image>
/rss style reset
/rss preview [风格] [text|image]
/rss preview <订阅名称> [text|image]
/rss preview feed <订阅名称> [text|image]
/rss preview all image
/rss help
```

名称中如果有空格，请加引号：

```text
/rss add "少数派" https://sspai.com/feed
```

Bangumi 每日放送示例：

```text
/rss add "Bangumi今日放送" https://bangumi.tv/calendar
/rss check "Bangumi今日放送"
```

> 添加 `https://bangumi.tv/calendar` 后，插件会在北京时间每天 `08:00` 定时推送当天的“今日放送”聚合消息。若要立即补发今天内容，可执行 `/rss check "Bangumi今日放送"`。

YUC 新番卫星观测站示例：

```text
/rss add "YUC新番" https://yuc.wiki/new/
/rss check "YUC新番"
```

> 也可以直接填 `https://yuc.wiki/atom.xml`。插件会自动按 `https://yuc.wiki/new/` 页面拆分为“每个新增/变更番剧 1 条消息”，并在摘要里带上栏目名，例如“备战2027”。

## 配置项

- `poll_interval_seconds`：轮询间隔，默认 300 秒
- `request_timeout_seconds`：请求超时，默认 15 秒
- `summary_max_length`：摘要最大长度，默认 180
- `image_summary_max_length`：图片模式摘要最大长度，默认 0（不截断，可输出长图）
- `max_entries_per_push`：每次最多推送的新增条目数，默认 3
- `admin_only_commands`：是否仅允许群管理员执行管理命令，默认开启
- `admin_only_list`：是否连 `list/help` 也限制为管理员，默认关闭
- `admin_denied_message`：非管理员执行命令时的提示语
- `message_render_mode`：实际推送模式，支持 `text` / `image`
- `preview_render_mode`：预览命令默认模式
- `template_style`：推送模板风格，支持 `classic` / `pretty` / `compact` / `custom`
- `image_template_style`：图片模板风格，支持 `aurora` / `newspaper` / `glass` / `minimal`
- `image_render_scale`：图片渲染缩放，推荐 `device`
- `image_render_timeout_ms`：图片渲染超时时间
- `image_compression_quality`：图片压缩质量，范围 80-100
- `custom_message_template`：自定义单条推送模板
- `custom_overflow_template`：一次更新过多时的汇总模板
- `user_agent`：抓取 RSS 的请求头 User-Agent

## 说明

- 插件会把每个群的订阅独立存储。
- 每个群都可以单独覆盖文本模板、图片模板、推送模式和预览模式。
- 新增订阅时会把当前 feed 内容记录为基线，不会立即补发历史消息。
- `https://bangumi.tv/calendar` 属于特殊适配源：插件会在北京时间每天 `08:00` 定时推送当天的“今日放送”聚合内容；如果机器人在 `08:00` 后启动，且当天还没推送过，会在启动后补发一次。
- `https://yuc.wiki/new/` / `https://yuc.wiki/atom.xml` 属于特殊适配源：插件会解析页面栏目与单个番剧卡片；后续只要新增番剧，或番剧的栏目/档期等信息发生变化，就会单独推送 1 条。
- 默认只有群管理员可以管理订阅，普通成员默认可查看列表和帮助。
- 图片模式依赖 AstrBot 自带文转图能力；若失败会自动回退为文本推送。
- 为提升清晰度，插件会使用 PNG + `scale=device` + 更宽画布进行渲染。
- 文转图会先生成高清原图；当 `image_compression_quality` 小于 100 时，再压缩为高质量 JPEG 发送。
- 图片模式默认不截断摘要，因此可以输出更长的长图；如果你想限制长度，可把 `image_summary_max_length` 调成非 0。
- 如果你希望 Bangumi 每日放送尽量完整展示，建议把群推送模式设为图片：`/rss style render image`
- 图片模式下会采用“图片 + 外部来源链接”的形式：链接不再放进图片内部，图片底部显示北京时间。
- 标题过长时，图片模板会自动减小字号并优化换行，减少拥挤和断行难看的问题。
- 插件状态文件保存在 `data/plugin_data/astrbot_plugin_rss_bridge/state.json`。

## 模板变量

自定义模板可使用这些变量：

- 通用：`{alias}`、`{feed_title}`、`{title}`、`{published}`、`{summary}`、`{link}`
- 现成行片段：`{feed_title_line}`、`{title_line}`、`{published_line}`、`{summary_line}`、`{link_line}`
- 美化行片段：`{feed_title_pretty}`、`{title_pretty}`、`{published_pretty}`、`{summary_pretty}`、`{link_pretty}`
- 汇总模板：`{new_count}`、`{sent_count}`、`{skipped_count}`

可通过 `/rss preview` 直接预览当前模板效果。

## 预览模板

文本风格：

- `classic`
- `pretty`
- `compact`

图片风格：

- `aurora`
- `newspaper`
- `glass`
- `minimal`

示例：

```text
/rss preview
/rss preview "少数派"
/rss preview glass image
/rss preview all image
```

## 按群自定义模板

你可以在不同群里设置不同风格：

```text
/rss style
/rss style text pretty
/rss style image glass
/rss style render image
/rss style preview image
```

恢复为全局默认：

```text
/rss style reset
```

> 如果订阅名称刚好和风格名冲突，例如叫 `pretty`，可以使用：
>
> ```text
> /rss preview feed "pretty" image
> ```

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
