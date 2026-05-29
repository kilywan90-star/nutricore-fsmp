#!/usr/bin/env python3
"""用Playwright将HTML图表逐张导出为JPG — 使用元素级截图"""
import os
from playwright.sync_api import sync_playwright

HTML_FILE = "E:/claude/output/charts/核心架构图集.html"
OUTPUT_DIR = "E:/claude/output/charts/jpg"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 980, "height": 900})
    page.goto(f"file:///{HTML_FILE.replace(chr(92), '/')}")
    page.wait_for_timeout(1500)

    # 获取所有 .chart 元素
    chart_elements = page.query_selector_all('.chart')
    print(f"Found {len(chart_elements)} chart elements")

    for i, el in enumerate(chart_elements):
        # 获取标题
        h2 = el.query_selector('h2')
        title_text = h2.inner_text() if h2 else f'chart_{i+1}'
        safe_title = title_text.replace('/', '_').replace('\\', '_').replace(':', '_').replace('"', '_').replace('*', '_').replace('?', '_')[:100]

        # 滚动到元素
        el.scroll_into_view_if_needed()
        page.wait_for_timeout(400)

        filename = f"图{i+1:02d}_{safe_title}.jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # 元素级截图
        el.screenshot(path=filepath, type='jpeg', quality=92)
        size_kb = os.path.getsize(filepath) / 1024
        print(f"✅ {filename} ({size_kb:.0f}KB)")

    browser.close()

print(f"\nDone! {len(chart_elements)} charts saved to {OUTPUT_DIR}")
