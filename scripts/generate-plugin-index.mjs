import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..");
const backtick = "`";
const fence = "```";
const defaultReleaseTag = process.env.PLUGIN_RELEASE_TAG || "plugins-latest";

function toPosix(p) {
  return p.split(path.sep).join("/");
}

function unquote(value) {
  const text = String(value ?? "").trim();
  if (
    (text.startsWith('"') && text.endsWith('"')) ||
    (text.startsWith("'") && text.endsWith("'"))
  ) {
    return text.slice(1, -1);
  }
  return text;
}

function parseSimpleYaml(filePath) {
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  const result = {};
  let currentListKey = null;

  for (const line of lines) {
    if (!line.trim() || /^\s*#/.test(line)) continue;

    const keyMatch = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (keyMatch) {
      const [, key, rawValue] = keyMatch;
      if (!rawValue.trim()) {
        result[key] = [];
        currentListKey = key;
      } else {
        result[key] = unquote(rawValue);
        currentListKey = null;
      }
      continue;
    }

    if (currentListKey) {
      const itemMatch = line.match(/^\s*-\s*(.+?)\s*$/);
      if (itemMatch) {
        result[currentListKey].push(unquote(itemMatch[1]));
      }
    }
  }

  return result;
}

function categoryDisplayName(categoryKey) {
  switch ((categoryKey || "").toLowerCase()) {
    case "rss":
      return "RSS";
    case "admin":
      return "管理";
    case "tools":
      return "工具";
    case "fun":
      return "娱乐";
    case "utility":
      return "实用";
    default:
      return categoryKey ? categoryKey[0].toUpperCase() + categoryKey.slice(1) : "未分类";
  }
}

function categorySortWeight(categoryKey) {
  switch ((categoryKey || "").toLowerCase()) {
    case "rss":
      return 10;
    case "admin":
      return 20;
    case "tools":
      return 30;
    case "fun":
      return 40;
    case "utility":
      return 50;
    default:
      return 100;
  }
}

function platformDisplayName(platform) {
  switch ((platform || "").toLowerCase()) {
    case "aiocqhttp":
      return "OneBot V11";
    case "telegram":
      return "Telegram";
    case "qq":
      return "QQ";
    case "wechat":
      return "WeChat";
    case "discord":
      return "Discord";
    default:
      return platform || "未声明";
  }
}

function walkForMetadata(dirPath, found = []) {
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === "node_modules") continue;
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      walkForMetadata(fullPath, found);
    } else if (entry.isFile() && entry.name === "metadata.yaml") {
      found.push(fullPath);
    }
  }
  return found;
}

function getRepoSlug() {
  if (process.env.GITHUB_REPOSITORY) {
    return process.env.GITHUB_REPOSITORY.trim();
  }

  try {
    const remoteUrl = execSync("git remote get-url origin", {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    const normalized = remoteUrl
      .replace(/^git@github\.com:/, "https://github.com/")
      .replace(/\.git$/, "");
    const match = normalized.match(/github\.com\/([^/]+\/[^/]+)$/i);
    if (match) return match[1];
  } catch {}

  for (const metadataPath of walkForMetadata(repoRoot)) {
    const metadata = parseSimpleYaml(metadataPath);
    const repo = String(metadata.repo || "").trim().replace(/\.git$/, "");
    const match = repo.match(/github\.com\/([^/]+\/[^/]+)$/i);
    if (match) return match[1];
  }

  return "";
}

function getPlugins() {
  const metadataFiles = walkForMetadata(repoRoot);
  const plugins = [];
  const repoSlug = getRepoSlug();

  for (const metadataPath of metadataFiles) {
    const pluginDir = path.dirname(metadataPath);
    const relativePath = toPosix(path.relative(repoRoot, pluginDir));
    const segments = relativePath.split("/");
    if (segments.length < 2) continue;

    const metadata = parseSimpleYaml(metadataPath);
    const categoryKey = segments[0];
    const dirName = segments[segments.length - 1];
    const name = metadata.display_name || metadata.name || dirName;
    const platformList = Array.isArray(metadata.support_platforms)
      ? metadata.support_platforms.map(platformDisplayName)
      : metadata.support_platforms
        ? [platformDisplayName(metadata.support_platforms)]
        : [];

    plugins.push({
      categoryKey,
      categoryName: categoryDisplayName(categoryKey),
      categoryWeight: categorySortWeight(categoryKey),
      relativePath,
      dirName,
      name,
      desc: metadata.desc || "",
      version: metadata.version || "",
      author: metadata.author || "",
      platforms: platformList.length > 0 ? platformList.join(" / ") : "未声明",
      platformList,
      readmePath: `${relativePath}/README.md`,
      installDirectory: dirName,
      sourceUrl: repoSlug ? `https://github.com/${repoSlug}/tree/main/${relativePath}` : "",
      downloadUrl: repoSlug
        ? `https://github.com/${repoSlug}/releases/download/${defaultReleaseTag}/${dirName}.zip`
        : "",
    });
  }

  return plugins.sort((a, b) => {
    if (a.categoryWeight !== b.categoryWeight) return a.categoryWeight - b.categoryWeight;
    if (a.categoryName !== b.categoryName) return a.categoryName.localeCompare(b.categoryName, "zh-CN");
    return a.name.localeCompare(b.name, "zh-CN");
  });
}

function groupPlugins(plugins) {
  const groups = new Map();
  for (const plugin of plugins) {
    if (!groups.has(plugin.categoryKey)) groups.set(plugin.categoryKey, []);
    groups.get(plugin.categoryKey).push(plugin);
  }
  return [...groups.entries()]
    .map(([categoryKey, items]) => ({
      categoryKey,
      categoryName: items[0].categoryName,
      categoryWeight: items[0].categoryWeight,
      items: [...items].sort((a, b) => a.name.localeCompare(b.name, "zh-CN")),
    }))
    .sort((a, b) => a.categoryWeight - b.categoryWeight || a.categoryName.localeCompare(b.categoryName, "zh-CN"));
}

function buildReadme(plugins) {
  const groups = groupPlugins(plugins);
  const lines = [];

  lines.push("# AstrbotPlugins");
  lines.push("");
  lines.push(`> 此文件由 ${backtick}scripts/generate-plugin-index.ps1${backtick} / ${backtick}scripts/generate-plugin-index.mjs${backtick} 自动生成。`);
  lines.push("");
  lines.push("这是一个用于集中存放多个 AstrBot 插件的仓库。");
  lines.push("");
  lines.push("## 插件索引");
  lines.push("");
  lines.push(`完整索引页见：[${backtick}PLUGINS.md${backtick}](./PLUGINS.md)`);
  lines.push("");
  lines.push("## 分类总览");
  lines.push("");

  for (const group of groups) {
    lines.push(`- ${backtick}${group.categoryKey}/${backtick}：${group.categoryName} 类插件（${group.items.length} 个）`);
  }

  lines.push("");
  lines.push("## 插件一览");
  lines.push("");

  for (const group of groups) {
    lines.push(`### ${group.categoryName} 类`);
    lines.push("");
    lines.push("| 插件名 | 简介 | 平台 | 源码 | 下载 |");
    lines.push("|---|---|---|---|---|");
    for (const plugin of group.items) {
      const sourceCell = plugin.sourceUrl ? `[目录](${plugin.sourceUrl})` : `${backtick}${plugin.relativePath}${backtick}`;
      const downloadCell = plugin.downloadUrl ? `[ZIP](${plugin.downloadUrl})` : "待生成";
      lines.push(`| ${plugin.name} | ${plugin.desc} | ${plugin.platforms} | ${sourceCell} | ${downloadCell} |`);
    }
    lines.push("");
  }

  lines.push("## 安装方式");
  lines.push("");
  lines.push("这个仓库是 **多插件源码仓库**。");
  lines.push("");
  lines.push("实际部署到 AstrBot 时，请把具体插件目录单独放到：");
  lines.push("");
  lines.push(`${fence}text`);
  lines.push("AstrBot/data/plugins/<插件目录名>");
  lines.push(fence);
  lines.push("");
  if (plugins[0]) {
    lines.push("例如当前插件应放到：");
    lines.push("");
    lines.push(`${fence}text`);
    lines.push(`AstrBot/data/plugins/${plugins[0].installDirectory}`);
    lines.push(fence);
    lines.push("");
  }

  lines.push("## 自动化");
  lines.push("");
  lines.push("仓库已支持 GitHub Actions：");
  lines.push("");
  lines.push("- 自动刷新 `README.md` 和 `PLUGINS.md`");
  lines.push(`- 自动打包每个插件为 ${backtick}<插件目录名>.zip${backtick}`);
  lines.push(`- 自动发布到 GitHub Releases 的 ${backtick}${defaultReleaseTag}${backtick} 标签下`);
  lines.push("");
  lines.push("如果你在本地预览，也可以手动运行：");
  lines.push("");
  lines.push(`${fence}powershell`);
  lines.push(".\\scripts\\generate-plugin-index.ps1");
  lines.push(fence);

  return `${lines.join("\n")}\n`;
}

function buildPluginsPage(plugins) {
  const groups = groupPlugins(plugins);
  const lines = [];

  lines.push("# AstrbotPlugins 插件索引");
  lines.push("");
  lines.push(`> 此文件由 ${backtick}scripts/generate-plugin-index.ps1${backtick} / ${backtick}scripts/generate-plugin-index.mjs${backtick} 自动生成。`);
  lines.push("");
  lines.push("这个页面用于统一展示仓库内所有 AstrBot 插件。");
  lines.push("");
  lines.push("## 索引总表");
  lines.push("");
  lines.push("| 分类 | 插件名 | 目录 | 状态 | 简介 | 文档 | 源码 | 下载 |");
  lines.push("|---|---|---|---|---|---|---|---|");
  for (const plugin of plugins) {
    const sourceCell = plugin.sourceUrl ? `[目录](${plugin.sourceUrl})` : `${backtick}${plugin.relativePath}${backtick}`;
    const downloadCell = plugin.downloadUrl ? `[ZIP](${plugin.downloadUrl})` : "待生成";
    lines.push(`| ${plugin.categoryName} | ${plugin.name} | ${backtick}${plugin.relativePath}${backtick} | 可用 | ${plugin.desc} | [README](./${plugin.readmePath}) | ${sourceCell} | ${downloadCell} |`);
  }
  lines.push("");
  lines.push("## 分类索引");
  lines.push("");

  for (const group of groups) {
    lines.push(`### ${group.categoryName}`);
    lines.push("");
    group.items.forEach((plugin, index) => {
      lines.push(`#### ${index + 1}. ${plugin.name} (${plugin.dirName})`);
      lines.push("");
      lines.push(`- 路径：${backtick}${plugin.relativePath}${backtick}`);
      if (plugin.version) lines.push(`- 版本：${plugin.version}`);
      if (plugin.author) lines.push(`- 作者：${plugin.author}`);
      if (plugin.desc) lines.push(`- 简介：${plugin.desc}`);
      lines.push("- 支持平台：");
      if (plugin.platformList.length > 0) {
        for (const platform of plugin.platformList) {
          lines.push(`  - ${platform}`);
        }
      } else {
        lines.push("  - 未声明");
      }
      lines.push(`- 文档：[README](./${plugin.readmePath})`);
      if (plugin.sourceUrl) lines.push(`- 源码目录：[打开](${plugin.sourceUrl})`);
      if (plugin.downloadUrl) lines.push(`- 下载链接：[${plugin.installDirectory}.zip](${plugin.downloadUrl})`);
      lines.push(`- 安装目录：${backtick}AstrBot/data/plugins/${plugin.installDirectory}${backtick}`);
      lines.push("");
    });
  }

  lines.push("## 自动化说明");
  lines.push("");
  lines.push("仓库中的 GitHub Actions 会在推送到 `main` 或手动触发时自动：");
  lines.push("");
  lines.push(`1. 运行 ${backtick}scripts/generate-plugin-index.mjs${backtick} 刷新索引`);
  lines.push(`2. 打包所有插件 ZIP`);
  lines.push(`3. 发布/覆盖 ${backtick}${defaultReleaseTag}${backtick} 下的下载包`);
  lines.push("");
  lines.push("本地手动执行仅用于预览。");

  return `${lines.join("\n")}\n`;
}

const plugins = getPlugins();
if (plugins.length === 0) {
  throw new Error("未发现任何插件 metadata.yaml，无法生成索引。");
}

fs.writeFileSync(path.join(repoRoot, "README.md"), buildReadme(plugins), "utf8");
fs.writeFileSync(path.join(repoRoot, "PLUGINS.md"), buildPluginsPage(plugins), "utf8");

console.log("已生成：");
console.log(` - ${path.join(repoRoot, "README.md")}`);
console.log(` - ${path.join(repoRoot, "PLUGINS.md")}`);
