# Hermes Chat Viewer

本地 Hermes 聊天记录阅读器。它会自动索引默认 profile 和所有 Hermes profiles 的 session 文件，把 JSON / JSONL 聊天记录渲染成接近聊天窗口的视图。

Local reader for Hermes session transcripts. It indexes the default profile plus all Hermes profiles, then renders JSON / JSONL transcripts as a readable chat view.

## 功能 / Features

- 默认中文 UI，可在页面里切换 English。
- 自动读取 `/Users/qlqwpy/.hermes/sessions` 和 `/Users/qlqwpy/.hermes/profiles/*/sessions`。
- 支持按 profile、角色、关键词过滤。
- 左侧边栏可折叠，适合长时间阅读。
- 标题形如 `主题 #1`、`主题 #2` 的连续会话会自动收进同一个组，顶部显示最新，展开后可从早期记录开始读。
- 工具调用和工具返回会被拆成可读卡片。
- 默认隐藏已经被后续 handoff / resume 链路包含的旧记录，可手动取消。
- 提供退出按钮，点击后会关闭本地 Python 服务，不常驻后台。

## 运行 / Run

macOS 下双击：

```text
Open Hermes Chat Viewer.command
```

它会启动本地服务、打开浏览器。也可以手动运行：

```bash
cd /Users/qlqwpy/Documents/游乐园/hermes-chat-viewer
python3 server.py --open
```

然后打开：

```text
http://127.0.0.1:8765
```

## 安全边界 / Safety

服务默认只绑定 `127.0.0.1`，只暴露已知 Hermes session 文件。它不会安装 launchd、不会创建后台常驻服务；退出按钮会调用 `/api/shutdown` 停止服务。

The server binds to `127.0.0.1` by default and only exposes known Hermes session files. It does not install a background daemon; the quit button calls `/api/shutdown`.

## 项目位置 / Project Location

```text
/Users/qlqwpy/Documents/游乐园/hermes-chat-viewer
```
