#!/usr/bin/env python3
import json
import re
import sys

def extract_placeholders(text):
    if not isinstance(text, str):
        return set()
    # 匹配 {{param}} 或 {param}
    return set(re.findall(r'\{+([^}]+)\}+', text))

def validate_and_clean(en_file, zh_file):
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

    # 遍历清洗与校验
    for k, v in zh.items():
        # 如果是空值，剔除该 key 以便官方 fallback 英文，避免渲染空白
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
    print(f"⚠️ [缺失词条 (自动显示英文)]: {len(missing)}")
    print(f"🗑️ [冗余/历史废弃词条]: {len(obsolete)}")
    print(f"🧹 [已自动清理的空值词条]: {len(empty_keys)}")
    print(f"🔍 [占位符差异提示 (非阻断)]: {len(placeholder_mismatch)}")
    print("==================================================")

    if placeholder_mismatch:
        print("\n[占位符差异参考 (前 5 个)]:")
        for k, en_p, zh_p in placeholder_mismatch[:5]:
            print(f"  - Key: {k}\n    官方: {en_p} | 中文: {zh_p}")

    # 将清洗后的 JSON 写回，确保编译使用干净的字典
    with open(zh_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_zh, f, ensure_ascii=False, indent=2)

    print("\n✅ 语言包清洗完成，门禁放行！")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate_locale.py <en.json> <zh-CN.json>")
        sys.exit(1)
    if not validate_and_clean(sys.argv[1], sys.argv[2]):
        sys.exit(1)
