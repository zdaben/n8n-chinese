#!/usr/bin/env python3
import json
import re
import sys

def extract_placeholders(text):
    if not isinstance(text, str):
        return set()
    # 匹配 {{param}} 或 {param}
    return set(re.findall(r'\{+([^}]+)\}+', text))

def validate(en_file, zh_file):
    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            en = json.load(f)
        with open(zh_file, 'r', encoding='utf-8') as f:
            zh = json.load(f)
    except Exception as e:
        print(f"❌ [BLOCKER] JSON 文件解析失败: {e}")
        return False

    missing = set(en.keys()) - set(zh.keys())
    obsolete = set(zh.keys()) - set(en.keys())
    empty = []
    placeholder_mismatch = []

    for k, v in zh.items():
        if v is None or str(v).strip() == "":
            empty.append(k)
        elif k in en:
            en_ph = extract_placeholders(en[k])
            zh_ph = extract_placeholders(v)
            if en_ph != zh_ph:
                placeholder_mismatch.append((k, en_ph, zh_ph))

    total_keys = len(en)
    translated_count = total_keys - len(missing)
    coverage = (translated_count / total_keys * 100) if total_keys > 0 else 0

    print("==================================================")
    print(f"📊 [词条统计] 官方英文: {total_keys} | 中文翻译: {len(zh)}")
    print(f"📈 [翻译覆盖率]: {coverage:.2f}% ({translated_count}/{total_keys})")
    print(f"⚠️ [WARNING] 缺失词条 (自动降级英文): {len(missing)}")
    print(f"🗑️ [WARNING] 冗余/已废弃词条: {len(obsolete)}")
    print(f"❌ [BLOCKER] 空翻译词条: {len(empty)}")
    print(f"❌ [BLOCKER] 插值占位符错误: {len(placeholder_mismatch)}")
    print("==================================================")

    has_blocker = False

    if empty:
        has_blocker = True
        print("\n[错误详情] 存在空翻译词条 (前 5 个):")
        for k in empty[:5]:
            print(f"  - Key: {k}")

    if placeholder_mismatch:
        has_blocker = True
        print("\n[错误详情] 占位符不一致 (会导致前端变量解析崩溃):")
        for k, en_p, zh_p in placeholder_mismatch[:5]:
            print(f"  - Key: {k}\n    官方: {en_p}\n    中文: {zh_p}")

    if has_blocker:
        print("\n::error::存在阻断级错误 (BLOCKER)，终止构建！")
        return False

    print("\n✅ 门禁校验通过，允许继续打包。")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate_locale.py <en.json> <zh-CN.json>")
        sys.exit(1)
    if not validate(sys.argv[1], sys.argv[2]):
        sys.exit(1)
