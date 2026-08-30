#!/usr/bin/env python3
import json
import re
import sys

def extract_placeholders(text):
    if not isinstance(text, str):
        return set()
    return set(re.findall(r'\{+([^}]+)\}+', text))

def validate_and_clean(en_file, zh_source_file, zh_target_file, summary_file=None):
    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            en = json.load(f)
        with open(zh_source_file, 'r', encoding='utf-8') as f:
            zh = json.load(f)
    except Exception as e:
        print(f"❌ [BLOCKER] JSON 解析失败: {e}")
        return False

    missing = set(en.keys()) - set(zh.keys())
    obsolete = set(zh.keys()) - set(en.keys())
    empty_keys = []
    placeholder_mismatch = []
    cleaned_zh = {}

    for k, v in zh.items():
        # 清洗空值
        if v is None or str(v).strip() == "":
            empty_keys.append(k)
            continue

        cleaned_zh[k] = v

        # 严格校验占位符 (针对官方存在且已翻译的 Key)
        if k in en:
            en_ph = extract_placeholders(en[k])
            zh_ph = extract_placeholders(v)
            if en_ph != zh_ph:
                placeholder_mismatch.append((k, en_ph, zh_ph))

    # 精准覆盖率计算（只对官方当前有效 Key 统计）
    total_keys = len(en)
    translated_count = sum(1 for k in en if k in cleaned_zh)
    coverage = (translated_count / total_keys * 100) if total_keys > 0 else 0

    print("==================================================")
    print(f"📊 [官方有效词条]: {total_keys}")
    print(f"✅ [成功匹配翻译]: {translated_count}")
    print(f"📈 [翻译覆盖率]: {coverage:.2f}%")
    print(f"⚠️ [缺失词条 (Fallback 英文)]: {len(missing)}")
    print(f"🗑️ [历史废弃词条]: {len(obsolete)}")
    print(f"🧹 [已清理空值词条]: {len(empty_keys)}")
    print(f"🚨 [占位符不匹配 (BLOCKER)]: {len(placeholder_mismatch)}")
    print("==================================================")

    # 占位符阻断
    if placeholder_mismatch:
        print("\n::error::发现占位符不匹配，阻断构建以防止前端变量解析崩溃！")
        for k, en_p, zh_p in placeholder_mismatch[:10]:
            print(f"  - Key: {k}\n    官方: {en_p} | 中文: {zh_p}")
        return False

    # 单向写入编译目标路径，不污染源仓库
    with open(zh_target_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_zh, f, ensure_ascii=False, indent=2)

    # 生成 Markdown 门禁基础报告 (不提前断言 Turborepo 构建状态)
    if summary_file:
        summary_md = f"""### 📊 本地化质量门禁报告 (Quality Gate)
| 校验维度 | 指标数据 | 状态 |
| :--- | :--- | :--- |
| **官方词条基准** | `{total_keys}` 项 | 官方最新 |
| **有效匹配词条** | `{translated_count}` 项 | - |
| **本地化覆盖率** | **`{coverage:.2f}%`** | {"✅ 优秀" if coverage >= 95 else "⚠️ 部分缺失"} |
| **缺失词条 (英文)** | `{len(missing)}` 项 | 自动 Fallback |
| **占位符一致性** | `0` 处错误 | **✅ PASS (严格阻断通过)** |
| **语言包状态** | 字典合法注入 | **✅ PASS** |
"""
        with open(summary_file, 'w', encoding='utf-8') as sf:
            sf.write(summary_md)

    print("\n✅ 语言包清洗与校验通过！")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 validate_locale.py <en.json> <zh-source.json> <zh-target.json> [summary.md]")
        sys.exit(1)
    summary_path = sys.argv[4] if len(sys.argv) >= 5 else None
    if not validate_and_clean(sys.argv[1], sys.argv[2], sys.argv[3], summary_path):
        sys.exit(1)
