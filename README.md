# RSS 周报生成器

使用 GitHub Actions 在云端定时采集 RSS，并调用 DeepSeek V4 Flash 生成中文 Markdown 周报。电脑无需保持开机。

## 工作方式

- 每天北京时间 08:15、14:15、20:15 采集 RSS。
- 使用稳定条目标识去重，将新增条目追加到 `data/items.jsonl`。
- 每周日北京时间 20:30 收集最新条目并生成 `reports/YYYY-Www.md`。
- RSS 内容只在周报生成时发送给 DeepSeek；日常采集不消耗模型 Token。

GitHub 的定时任务可能延迟，以上时间不是严格实时保证。

## 配置

### 1. 添加 RSS 源

编辑 `feeds.yaml`：

```yaml
timezone: Asia/Shanghai
lookback_days: 7
max_items_per_report: 80

feeds:
  - name: Example Tech
    url: https://example.com/feed.xml
    category: 科技
    enabled: true
```

建议使用私有仓库，因为订阅列表、历史条目和周报都会提交到仓库。

### 2. 添加 DeepSeek API Key

在 GitHub 仓库中打开：

`Settings → Secrets and variables → Actions → New repository secret`

创建：

- Name：`DEEPSEEK_API_KEY`
- Secret：你的 DeepSeek API Key

不要把 Key 写进 `feeds.yaml`、工作流或任何提交文件。

### 3. 启用写入权限

打开：

`Settings → Actions → General → Workflow permissions`

选择 `Read and write permissions`。如果默认分支启用了禁止机器人直接推送的保护规则，需要允许 GitHub Actions 推送，或者改为通过 Pull Request 保存周报。

### 4. 首次验证

进入仓库的 `Actions` 页面：

1. 手动运行 `Collect RSS`。
2. 确认 `data/items.jsonl` 出现新增条目。
3. 手动运行 `Generate Weekly Report`。
4. 确认 `reports/` 中出现本周 Markdown 文件。

当前示例源默认禁用；至少启用一个真实 RSS 源后才会采集数据。

## 本地验证

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/python src/rss_weekreport.py collect
```

生成周报前临时设置 Key：

```bash
export DEEPSEEK_API_KEY="你的 API Key"
.venv/bin/python src/rss_weekreport.py generate
```

## 模型配置

默认调用：

- Base URL：`https://api.deepseek.com`
- Model：`deepseek-v4-flash`
- Thinking：关闭，降低简单编辑任务的延迟和输出成本

如需使用兼容代理，可在 Actions 中额外配置环境变量 `DEEPSEEK_BASE_URL`。不要把带凭据的 URL 提交到仓库。

## 已知边界

- 第一版使用 RSS 自带标题和摘要，不主动抓取网页全文。
- 部分 RSS 源可能屏蔽 GitHub Runner 的云端 IP。
- `data/items.jsonl` 会长期增长；数据量明显增大后应按月份归档。
- 第一版将周报保存到仓库，尚未配置邮件或其他消息推送。
