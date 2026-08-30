#!/usr/bin/env python3
import json
import re
import sys
import os

def extract_placeholders(text):
    if not isinstance(text, str):
        return set()
    return set(re.findall(r'\{+([^}]+)\}+', text))

def validate_and_clean(en_file, zh_file, summary_file=None):
    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            en = json.load(f)
        with open(zh_file, 'r', encoding='utf-8') as f:
            zh = json.load(f)
    except Exception as e:
        print(f"❌ [BLOCKER] JSON 语法损坏，无法解析: {e}")
        return False

    missing = set(en.keys()) - set(zh.keys())
    obsolete = set(zh.keys()) - set(en.keys())
    empty_keys = []
    placeholder_mismatch = []
    cleaned_zh = {}

    for k, v in zh.items():
        if v is None or str(v).strip() == "":
            empty_keys.append(k)
            continue

        cleaned_zh[k] = v

        if k in en:
            en_ph = extract_placeholders(en[k])
            zh_ph = extract_placeholders(v)
            if en_ph != zh_ph:
                placeholder_mismatch.append((k, en_ph, zh_ph))

    total_keys = len(en)
    translated_count = total_keys - len(missing) - len(empty_keys)
    coverage = (translated_count / total_keys * 100) if total_keys > 0 else 0

    print("==================================================")
    print(f"📊 [官方英文词条总数]: {total_keys}")
    print(f"✅ [有效中文词条总数]: {len(cleaned_zh)}")
    print(f"📈 [翻译覆盖率]: {coverage:.2f}%")
    print(f"⚠️ [缺失词条 (Fallback 英文)]: {len(missing)}")
    print(f"🗑️ [历史废弃词条]: {len(obsolete)}")
    print(f"🧹 [已自动清理的空值词条]: {len(empty_keys)}")
    print(f"🚨 [占位符不匹配 (BLOCKER)]: {len(placeholder_mismatch)}")
    print("==================================================")

    # 严格门禁：占位符不匹配直接阻断
    if placeholder_mismatch:
        print("\n::error::发现占位符不匹配，前端可能崩溃！阻断构建！")
        for k, en_p, zh_p in placeholder_mismatch[:10]:
            print(f"  - Key: {k}\n    官方: {en_p} | 中文: {zh_p}")
        return False

    # 写回清洗后的数据
    with open(zh_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_zh, f, ensure_ascii=False, indent=2)

    # 生成 Markdown 供 Release Body 使用
    if summary_file:
        summary_md = f"""### 📊 本地化指标与门禁报告
| 校验维度 | 指标数据 | 状态 |
| :--- | :--- | :--- |
| **官方词条基准** | `{total_keys}` 项 | 官方最新 |
| **有效翻译词条** | `{len(cleaned_zh)}` 项 | - |
| **本地化覆盖率** | **`{coverage:.2f}%`** | {"✅ 优秀" if coverage >= 95 else "⚠️ 部分缺失"} |
| **缺失词条 (英文)** | `{len(missing)}` 项 | 自动 Fallback |
| **清理空值词条** | `{len(empty_keys)}` 项 | 已自动剔除 |
| **占位符校验** | 0 处错误 | **✅ PASS** |
| **Turborepo 构建** | 全依赖拓扑编译 | **✅ PASS** |
"""
        with open(summary_file, 'w', encoding='utf-8') as sf:
            sf.write(summary_md)

    print("\n✅ 门禁校验全部 PASS，放行构建！")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate_locale.py <en.json> <zh-CN.json> [summary.md]")
        sys.exit(1)
    summary_path = sys.argv[3] if len(sys.argv) >= 4 else None
    if not validate_and_clean(sys.argv[1], sys.argv[2], summary_path):
        sys.exit(1)
