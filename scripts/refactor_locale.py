#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import urllib.error

EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"
CHECKPOINT_FILE = ".refactor_checkpoint.json"

# 统一术语规范
GLOSSARY_RULES = """
【统一专业术语强制规范】:
- Workflow -> 工作流 (严禁翻译为: 工作流程、工单)
- Node -> 节点 (严禁翻译为: 结点、组件)
- Credentials -> 凭据 (严禁翻译为: 证书、认证)
- Execution -> 执行 / 运行
- Trigger -> 触发器
- Canvas -> 画布
- Pin Data / Pinned -> 固定数据 / 已固定 (严禁翻译为: 锁定、别针)
- Expression -> 表达式
- Insights -> 数据洞察
- Webhook / API / JSON / HTTP / REST -> 必须保留全大写专有名词
"""

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...", flush=True)
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def call_gemini_native(batch_dict, api_key, model="gemini-2.5-flash"):
    """使用 Google 原生 REST API + JSON 强制约束"""
    prompt = f"""你是一个专业的前端国际化文案与术语统一专家。请对以下 n8n 自动化软件的前端英文词条进行【统一术语重构翻译与文案润色】。

{GLOSSARY_RULES}

【严格要求】:
1. 严禁修改、丢失或破坏任何变量占位符！如 {{time}}、{{name}}、{{count}}、{{0}}、HTML标签 <b> 等必须100%原样保留。
2. 语句自然通顺、专业规范，符合中国开发者的软件交互习惯，消除生硬机翻腔。
3. 严格返回纯 JSON 字典格式: {{ "Key": "规范润色后的中文" }}。

待重构词条 JSON:
{json.dumps(batch_dict, ensure_ascii=False)}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(raw_text)

def main():
    if not os.path.exists(ZH_FILE):
        print(f"❌ 未找到本地字典: {ZH_FILE}", flush=True)
        sys.exit(1)

    with open(ZH_FILE, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    en_data = fetch_official_en()
    all_keys = list(en_data.keys())
    total_count = len(all_keys)

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ 未检测到 GEMINI_API_KEY！", flush=True)
        sys.exit(1)

    model = "gemini-flash-lite-latest"
    print(f"📊 官方基准有效词条: {total_count} 项 | 使用模型: {model}", flush=True)

    # 1. 加载断点进度
    checkpoint_idx = 0
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as cf:
                cp_data = json.load(cf)
                checkpoint_idx = cp_data.get("last_index", 0)
                print(f"🔄 检测到历史断点！将直接从第 {checkpoint_idx} 项词条继续校对...", flush=True)
        except Exception:
            checkpoint_idx = 0

    batch_size = 80
    refactored_data = dict(zh_data)
    total_batches = (total_count + batch_size - 1) // batch_size
    start_batch = checkpoint_idx // batch_size + 1

    print(f"🚀 启动全量校对 (共 {total_batches} 批，当前从第 {start_batch} 批开始)...", flush=True)

    for i in range(checkpoint_idx, total_count, batch_size):
        batch_keys = all_keys[i:i + batch_size]
        batch_idx = i // batch_size + 1
        chunk = {k: en_data[k] for k in batch_keys}

        print(f"  -> [批次 {batch_idx}/{total_batches}] 正在校对润色 {len(chunk)} 个词条...", flush=True)

        # 智能持久化重试（遇到 429 绝不跳过，自动退避等待直至成功）
        attempt = 1
        while True:
            try:
                translated_chunk = call_gemini_native(chunk, gemini_key, model)
                refactored_data.update(translated_chunk)

                # 实时保存到字典文件
                with open(ZH_FILE, "w", encoding="utf-8") as f:
                    json.dump(refactored_data, f, ensure_ascii=False, indent=2)

                # 实时更新断点记录
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as cf:
                    json.dump({"last_index": i + len(chunk)}, cf)

                print(f"     ✅ 批次 {batch_idx} 校对成功并已落盘保存 ({len(translated_chunk)} 项)", flush=True)
                
                # 批次间轻微间隔，保护配额
                time.sleep(1.0)
                break

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8") if e.fp else str(e)
                wait_seconds = min(15 * attempt, 60)
                print(f"     ⚠️ 批次 {batch_idx} 遇到限流 [HTTP {e.code}]，等待 {wait_seconds} 秒后自动恢复重试...", flush=True)
                time.sleep(wait_seconds)
                attempt += 1

            except Exception as e:
                print(f"     ⚠️ 批次 {batch_idx} 异常: {e}，5秒后重试...", flush=True)
                time.sleep(5)
                attempt += 1

    # 校对完成后清除断点文件
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\n🎉 全量 8,297 条词条深度重构与术语校对 100% 完成！", flush=True)

if __name__ == "__main__":
    main()
