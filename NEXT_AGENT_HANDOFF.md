# Hermes Chat Viewer Handoff

更新时间：2026-05-14

## 当前项目状态

项目位置：

```text
/Users/qlqwpy/Documents/游乐园/hermes-chat-viewer
```

GitHub：

```text
https://github.com/wang-yzh/hermes-chat-viewer
```

当前主线是本地 HTML/Python viewer：

```bash
python3 server.py --open
```

或双击：

```text
Open Hermes Chat Viewer.command
```

`server.py` 会读取：

```text
~/.hermes/sessions
~/.hermes/profiles/*/sessions
```

前端入口是：

```text
index.html
```

## 重要更正：macOS App 其实能用

之前误判 App “打不开”。实际情况是：App 启动后只在 macOS 菜单栏出现图标，不会弹出窗口，所以用户误以为没启动。

App 封装相关文件目前被移动到了：

```text
legacy/
```

包括：

```text
legacy/macos/
legacy/assets/
legacy/scripts/build-macos-app.sh
```

下一步需要把 App wrapper 从 `legacy/` 恢复/同步到主线，让它继续跟随最新 `index.html` 和 `server.py`。

## 已完成能力

- 自动索引 Hermes 默认 profile 和所有 profiles 的 sessions。
- 渲染 JSON/JSONL 聊天记录。
- 支持中文/英文 UI 切换，默认中文。
- 左侧边栏可折叠。
- 支持按 profile、角色、关键词过滤。
- 支持工具调用/工具结果卡片化显示。
- 标题形如 `主题 #2`、`主题 #3` 的会话会按主题分组。
- 无编号同名会话会被当作 `#1` 收进分组。
- 分组展开顺序已经改成新到旧。
- 默认有“忽略无意义对话”过滤，但规则还不够好。

## 当前问题

### 1. 左侧按钮仍然不够紧凑

用户反馈：

- “折叠边栏”按钮占了整整一行，不够紧凑。
- 退出按钮、刷新按钮、工具详情按钮都还可以更小。
- 左侧历史列表应该尽可能早出现，不要被控制区挤掉。

建议方向：

- 把 sidebar toggle 放到 header 右上角，做成绝对定位或 header 内联小按钮。
- 退出按钮改成小型 ghost/danger button，不要独占太高。
- `刷新索引`、`折叠/展开工具详情` 可以变成一行小按钮。
- 控制区整体压缩高度，优先保证 session list 可见。

### 2. “忽略无意义对话”规则不足

目前规则在 `index.html` 的 `isNoiseSession(item)`：

```js
function isNoiseSession(item) {
  const title = String(item.title || "").trim();
  const preview = String(item.preview || "").trim();
  const file = String(item.file || "");
  if (file.startsWith("request_dump_") && (item.message_count || 0) <= 6) return true;
  if (!title && (item.message_count || 0) <= 4) return true;
  if (!title && preview.startsWith("# Hermes Agent Persona")) return true;
  return false;
}
```

用户指出还有很多“支离破碎的头”：通常是 resume 后没有继续说话就退出，导致留下短 session。这些也应该默认过滤。

建议增加规则：

- 无标题。
- preview 以 `\resume` 开头。
- message_count 很低，或只有 LCM/resume/system scaffold。
- 没有有效 user 消息，或首条/主体基本都是 `[Note: This conversation uses Lossless Context Management...]`。

注意：`/api/sessions` 当前只返回 summary，不返回完整消息。若要准确判断“没有有效 user 消息”，需要：

- 在 `server.py` 的 `session_summary()` 里多读取一小段消息结构，提取 `meaningful_user_count`。
- 或在前端只用 preview/message_count 做启发式过滤。

### 3. App wrapper 需要恢复到主线

既然 App 实际能用，下一步应该：

- 把 `legacy/macos/` 移回 `macos/`。
- 把 `legacy/assets/` 移回 `assets/`。
- 把 `legacy/scripts/build-macos-app.sh` 移回 `scripts/`。
- README 恢复 App 构建说明，但明确说明：启动后只在菜单栏出现图标，不会弹窗。
- App 启动后可以考虑自动打开浏览器，或者菜单栏提供 `Open Viewer`。

### 4. 下一阶段大功能：修复/合并对话

用户下一步想做的是“修复对话”：从多个碎片 session 里整理出一个完整对话。

方向建议：

- 基于 `parent_session_id` 和 title `#n` 构建 conversation chain。
- 读取同一 chain 下多个 session 的 messages。
- 去重重复消息，尤其是 resume/LCM scaffold。
- 合并为一个虚拟 conversation view，不一定写回 Hermes 原文件。
- UI 上可以新增：
  - `查看合并对话`
  - `导出合并 Markdown`
  - `导出合并 JSON`

合并排序建议：

- 优先按 parent chain。
- 其次按 title 编号 `#1 -> #n`。
- 最后按 mtime/session_start。

## 验证命令

JS 语法：

```bash
node -e 'const fs=require("fs"); const html=fs.readFileSync("index.html","utf8"); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log("script syntax ok")'
```

启动服务：

```bash
python3 server.py --port 8765
```

检查页面/API：

```bash
curl -sS --max-time 5 http://127.0.0.1:8765/
curl -sS --max-time 5 http://127.0.0.1:8765/api/sessions
```

停止残留服务：

```bash
lsof -ti tcp:8765
kill -TERM <pid>
```

## 最近的 commit

最后一次提交是：

```text
1788965 Archive app wrapper and fix sidebar layout
```

如果恢复 App wrapper，需要在此基础上新提交。
