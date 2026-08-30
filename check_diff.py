#!/usr/bin/env python3
import json
import sys

def check_keys(en_file, zh_file):
    with open(en_file, 'r', encoding='utf-8') as f:
        en = json.load(f)
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    missing_keys = set(en.keys()) - set(zh.keys())
    print(f"📊 英文总词条: {len(en)} | 中文总词条: {len(zh)}")
    print(f"⚠️ 缺失未翻译的词条数: {len(missing_keys)}")

    if missing_keys:
        missing_dict = {k: en[k] for k in list(missing_keys)[:20]}
        print("\n前 20 个待翻译示例:")
        print(json.dumps(missing_dict, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 check_diff.py <官方en.json路径> <你的zh-CN.json路径>")
        sys.exit(1)
    check_keys(sys.argv[1], sys.argv[2])
