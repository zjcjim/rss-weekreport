# RSS 日报与周报生成器

使用 GitHub Actions 在云端定时采集 RSS，并调用 DeepSeek V4 Flash 生成中文日报和周报。生成结果可以通过 GitHub Pages 作为 RSS 源订阅，电脑无需保持开机。

## 工作方式

- 每天北京时间 08:15、14:15、18:15 采集 RSS。
- 使用稳定条目标识去重，将新增条目追加到 `data/items.jsonl`。
- 每天北京时间 19:00 生成 `reports/daily/YYYY-MM-DD.md` 日报。
- 每周日北京时间 19:00 额外生成 `reports/weekly/YYYY-Www.md` 周报。
- 每次出刊同步更新 `docs/feed.xml`、HTML 阅读页面和报告索引。
- RSS 内容只在生成日报或周报时发送给 DeepSeek；日常采集不消耗模型 Token。

GitHub 的定时任务可能延迟，以上时间不是严格实时保证。

## 配置

### 1. 添加 RSS 源

编辑 `feeds.yaml`：

```yaml
timezone: Asia/Shanghai
site_url: https://你的用户名.github.io/rss-weekreport
daily_lookback_days: 1
weekly_lookback_days: 7
daily_max_items: 50
weekly_max_items: 80

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
3. 手动运行 `Generate Daily Report` 和 `Generate Weekly Report`。
4. 确认 `reports/` 中出现日报和周报，`docs/feed.xml` 已生成。

当前 `feeds.yaml` 中导入的订阅已经启用。

## 本地验证

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/python src/rss_weekreport.py collect
```

生成日报或周报前临时设置 Key：

```bash
export DEEPSEEK_API_KEY="你的 API Key"
.venv/bin/python src/rss_weekreport.py generate --period daily
.venv/bin/python src/rss_weekreport.py generate --period weekly
```

## 在手机上订阅

程序会生成日报、周报两个独立的 RSS 2.0 Feed，并保留一个包含全部简报的综合 Feed。要让手机访问它们，需要启用 GitHub Pages：

1. 进入仓库 `Settings → Pages`。
2. 在 `Build and deployment` 中选择 `Deploy from a branch`。
3. Branch 选择 `main`，目录选择 `/docs`，保存。
4. 等待首次部署完成。

本仓库对应的订阅地址是：

```text
日报：https://zjcjim.github.io/rss-weekreport/daily/feed.xml
周报：https://zjcjim.github.io/rss-weekreport/weekly/feed.xml
全部：https://zjcjim.github.io/rss-weekreport/feed.xml
```

把需要的地址添加到 NetNewsWire、Reeder、Feedly 等手机 RSS 阅读器即可。每篇简报也有独立 HTML 阅读页面。

注意：启用 GitHub Pages 后，`docs/` 中发布的简报内容会公开访问，即使源代码仓库是私有的。DeepSeek Key、`feeds.yaml` 和 `data/items.jsonl` 不会由 Pages 发布。

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
- GitHub Free 对私有仓库的 Pages 可用性取决于账户方案；如果仓库设置中没有 Pages 发布选项，需要升级方案或使用单独的公开发布仓库。
