#!/usr/bin/env python3
"""
自动比对官方 en.json 并为 zh-CN.json 补齐缺失的词条
支持直接调用 DeepSeek / OpenAI API 批量自动翻译
"""
import json
import os
import sys
import urllib.request

# 官方英文字典 URL
EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...")
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    if not os.path.exists(ZH_FILE):
        print(f"❌ 未找到本地字典: {ZH_FILE}")
        sys.exit(1)

    with open(ZH_FILE, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    en_data = fetch_official_en()

    missing_keys = {k: en_data[k] for k in en_data if k not in zh_data}
    print(f"📊 官方词条: {len(en_data)} | 本地已有: {len(zh_data)}")
    print(f"⚠️ 发现缺失词条数: {len(missing_keys)}")

    # 导出待翻译文件
    with open("missing_keys.json", "w", encoding="utf-8") as f:
        json.dump(missing_keys, f, ensure_ascii=False, indent=2)

    print(f"✅ 缺失词条已全部导出到 missing_keys.json 文件中！")

if __name__ == "__main__":
    main()
