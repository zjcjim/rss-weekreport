from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import rss_weekreport


def test_normalize_entry_is_stable_and_strips_html() -> None:
    feed = {"name": "Test", "category": "技术"}
    entry = {
        "id": "entry-1",
        "title": " A title ",
        "link": "https://example.com/1",
        "summary": "<p>Hello &amp; goodbye</p>",
    }
    first = rss_weekreport.normalize_entry(feed, entry, "2026-09-01T00:00:00+00:00")
    second = rss_weekreport.normalize_entry(feed, entry, "2026-09-02T00:00:00+00:00")

    assert first["id"] == second["id"]
    assert first["summary"] == "Hello & goodbye"


def test_collect_deduplicates_existing_items(tmp_path: Path) -> None:
    config = tmp_path / "feeds.yaml"
    config.write_text(
        "feeds:\n  - name: Test\n    url: https://example.com/feed\n    enabled: true\n",
        encoding="utf-8",
    )
    data = tmp_path / "items.jsonl"
    parsed = SimpleNamespace(
        status=200,
        bozo=False,
        entries=[{"id": "1", "title": "One", "link": "https://example.com/1"}],
    )

    with patch.object(rss_weekreport.feedparser, "parse", return_value=parsed):
        assert rss_weekreport.collect(config, data) == 0
        assert rss_weekreport.collect(config, data) == 0

    lines = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1


def test_select_items_uses_collection_time() -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    items = [
        {"id": "old", "collected_at": (now - timedelta(days=8)).isoformat()},
        {"id": "new", "collected_at": (now - timedelta(days=1)).isoformat()},
    ]
    selected = rss_weekreport.select_items(items, now, days=7, maximum=10)
    assert [item["id"] for item in selected] == ["new"]


def test_call_deepseek_uses_v4_flash_non_thinking() -> None:
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "# 周报"}}]}
    response.raise_for_status.return_value = None

    with patch.object(rss_weekreport.requests, "post", return_value=response) as post:
        assert rss_weekreport.call_deepseek("prompt", "secret") == "# 周报"

    request = post.call_args.kwargs
    assert request["json"]["model"] == "deepseek-v4-flash"
    assert request["json"]["thinking"] == {"type": "disabled"}
    assert request["headers"]["Authorization"] == "Bearer secret"


def test_build_prompt_uses_requested_period() -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    daily = rss_weekreport.build_prompt([], now - timedelta(days=1), now, "daily")
    weekly = rss_weekreport.build_prompt([], now - timedelta(days=7), now, "weekly")

    assert "新闻日报" in daily
    assert "今日概览" in daily
    assert "新闻周报" in weekly
    assert "本周概览" in weekly


def test_publish_report_updates_combined_and_period_feeds(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    now = datetime(2026, 9, 1, 19, 0, tzinfo=timezone.utc)
    daily = tmp_path / "reports" / "daily" / "2026-09-01.md"
    weekly = tmp_path / "reports" / "weekly" / "2026-W36.md"

    rss_weekreport.publish_report(
        docs, "https://example.github.io/news", daily, "# 今日日报\n\n内容", "daily", now
    )
    rss_weekreport.publish_report(
        docs, "https://example.github.io/news", weekly, "# 本周周报\n\n内容", "weekly", now
    )
    rss_weekreport.publish_report(
        docs, "https://example.github.io/news", daily, "# 今日日报（更新）", "daily", now
    )

    parsed = rss_weekreport.ET.parse(docs / "feed.xml")
    items = parsed.getroot().find("channel").findall("item")
    assert len(items) == 2
    assert items[0].findtext("title") == "今日日报（更新）"
    daily_items = rss_weekreport.ET.parse(docs / "daily" / "feed.xml").getroot().find("channel").findall("item")
    weekly_items = rss_weekreport.ET.parse(docs / "weekly" / "feed.xml").getroot().find("channel").findall("item")
    assert len(daily_items) == 1
    assert daily_items[0].findtext("title") == "今日日报（更新）"
    assert len(weekly_items) == 1
    assert weekly_items[0].findtext("title") == "本周周报"
    assert (docs / "daily" / "2026-09-01.html").exists()
    assert (docs / "weekly" / "2026-W36.html").exists()
    assert (docs / "index.html").exists()
    parsed_feed = rss_weekreport.feedparser.parse(str(docs / "feed.xml"))
    assert not parsed_feed.bozo
    assert len(parsed_feed.entries) == 2
    assert 'href="https://example.github.io/news/daily/feed.xml"' in (
        docs / "daily" / "2026-09-01.html"
    ).read_text(encoding="utf-8")


def test_write_page_renders_markdown_table(tmp_path: Path) -> None:
    output = tmp_path / "report.html"
    markdown = """# 数据统计

| 指标 | 数值 |
| --- | --- |
| 新闻数量 | 42 |
"""
    rss_weekreport.write_page(output, "数据统计", markdown, "https://example.com/feed.xml")
    page = output.read_text(encoding="utf-8")

    assert "<table>" in page
    assert "<th>指标</th>" in page
    assert "<td>42</td>" in page
    assert "| 指标 | 数值 |" not in page
