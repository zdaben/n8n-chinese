#!/usr/bin/env python3
import json
import re
import sys

def extract_placeholders(text):
    if not isinstance(text, str):
        return set()
    # 精确匹配真正的 i18n 变量名 (如 {{time}}, {{name}}, {count})，排除示例 JSON
    double_brace = set(re.findall(r'\{\{\s*([a-zA-Z0-9_$]+)\s*\}\}', text))
    single_brace = set(re.findall(r'\{([a-zA-Z0-9_$]+)\}', text))
    return double_brace | single_brace

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
        # 1. 过滤空值
        if v is None or str(v).strip() == "":
            empty_keys.append(k)
            continue

        # 2. 校验占位符 (针对官方存在的 Key)
        if k in en:
            en_ph = extract_placeholders(en[k])
            zh_ph = extract_placeholders(v)
            
            # 若变量占位符不匹配，剔除该 Key，自动回退官方英文，保证 100% 运行安全
            if en_ph != zh_ph:
                placeholder_mismatch.append((k, en_ph, zh_ph))
                continue

        cleaned_zh[k] = v

    total_keys = len(en)
    translated_count = sum(1 for k in en if k in cleaned_zh)
    coverage = (translated_count / total_keys * 100) if total_keys > 0 else 0

    print("==================================================")
    print(f"📊 [官方有效词条基准]: {total_keys}")
    print(f"✅ [通过校验的中文词条]: {translated_count}")
    print(f"📈 [有效翻译覆盖率]: {coverage:.2f}%")
    print(f"⚠️ [缺失词条 (自动英文)]: {len(missing)}")
    print(f"🗑️ [历史废弃词条]: {len(obsolete)}")
    print(f"🧹 [已清理空值词条]: {len(empty_keys)}")
    print(f"🛡️ [占位符异常词条 (已自动降级为官方英文)]: {len(placeholder_mismatch)}")
    print("==================================================")

    if placeholder_mismatch:
        print("\n[风险词条隔离详情 (前 5 项已自动降级为英文)]:")
        for k, en_p, zh_p in placeholder_mismatch[:5]:
            print(f"  - Key: {k}\n    官方占位符: {en_p} | 中文占位符: {zh_p}")

    # 写入清洗后的安全字典
    with open(zh_target_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_zh, f, ensure_ascii=False, indent=2)

    # 输出 Markdown 报告供 Release 页面展示
    if summary_file:
        summary_md = f"""### 📊 Localization Quality Report
| Metric | Count / Status | Note |
| :--- | :--- | :--- |
| **Official Keys** | `{total_keys}` keys | Upstream latest |
| **Active Translations** | `{translated_count}` keys | Verified |
| **Coverage Rate** | **`{coverage:.2f}%`** | {"✅ Excellent" if coverage >= 95 else "⚠️ Partial"} |
| **Fallback Keys (EN)** | `{len(missing)}` keys | Missing in locale |
| **Sanitized Keys** | `{len(empty_keys)}` keys | Empty values stripped |
| **Placeholder Guard** | `{len(placeholder_mismatch)}` keys auto-isolated | **✅ 100% Crash-Proof** |
"""
        with open(summary_file, 'w', encoding='utf-8') as sf:
            sf.write(summary_md)

    print("\n✅ 语言包安全过滤完成，门禁放行！")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 validate_locale.py <en.json> <zh-source.json> <zh-target.json> [summary.md]")
        sys.exit(1)
    summary_path = sys.argv[4] if len(sys.argv) >= 5 else None
    if not validate_and_clean(sys.argv[1], sys.argv[2], sys.argv[3], summary_path):
        sys.exit(1)
