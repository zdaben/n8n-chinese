#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import urllib.error

EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"

# 精简版术语表，降低 Prompt Token 消耗
GLOSSARY_PROMPT = """
【术语规范】: Workflow->工作流, Node->节点, Credentials->凭据, Execution->执行, Trigger->触发器, Canvas->画布, Pin Data->固定数据, Expression->表达式, Insights->数据洞察, 保留大写专有名词(Webhook/API/JSON/HTTP)。
"""

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...", flush=True)
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def batch_refactor_ai(batch_items, api_key, api_base, model):
    prompt = f"""你是一个专业的前端本地化与文案润色专家。请对以下 n8n 自动化软件的前端词条进行【深度校对与重构翻译】。
输入格式: "Key": {{"en": "英文", "zh": "当前中文"}}

{GLOSSARY_PROMPT}

【要求】:
1. 严禁修改或遗漏变量占位符(如 {{time}}, {{name}}, {{count}}, {{0}}, <b> 等必须100%保留)。
2. 消除生硬机翻，符合中文开发者使用习惯；若原翻译已准确且符合术语则保留，若存在语病则重新润色。
3. 严格返回纯 JSON 字典: {{ "Key": "润色后中文" }}，不要输出任何 Markdown 或解释。

数据:
{json.dumps(batch_items, ensure_ascii=False)}
"""
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        content = res["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())

def main():
    if not os.path.exists(ZH_FILE):
        print(f"❌ 未找到本地字典: {ZH_FILE}", flush=True)
        sys.exit(1)

    with open(ZH_FILE, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    en_data = fetch_official_en()

    all_keys = list(en_data.keys())
    total_count = len(all_keys)
    print(f"📊 官方有效基准词条: {total_count} 项，启动全量校对重构...", flush=True)

    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        api_key = gemini_key
        api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        model = "gemini-flash-lite-latest"
        print(f"🌟 使用 Google AI Studio 官方模型: {model}", flush=True)
    elif deepseek_key:
        api_key = deepseek_key
        api_base = "https://api.deepseek.com/v1"
        model = "deepseek-chat"
        print(f"🌟 使用 DeepSeek 深度校对模型: {model}", flush=True)
    elif openai_key:
        api_key = openai_key
        api_base = "https://api.openai.com/v1"
        model = "gpt-4o-mini"
        print(f"🌟 使用 OpenAI: {model}", flush=True)
    else:
        print("❌ 未检测到 API_KEY！", flush=True)
        sys.exit(1)

    # 💡 优化：单批从 100 调整为 50 条，大幅降低单次 Token 峰值，杜绝 429
    batch_size = 50
    total_batches = (total_count + batch_size - 1) // batch_size
    print(f"🚀 开始逐批校对 (共 {total_batches} 批，每批 {batch_size} 条)...", flush=True)

    refactored_data = dict(zh_data)
    success_count = 0

    for i in range(0, total_count, batch_size):
        batch_keys = all_keys[i:i + batch_size]
        batch_idx = i // batch_size + 1
        
        # 紧凑型结构
        batch_payload = {}
        for k in batch_keys:
            batch_payload[k] = {
                "en": en_data[k],
                "zh": zh_data.get(k, "")
            }

        print(f"  -> [批次 {batch_idx}/{total_batches}] 正在校对润色 {len(batch_payload)} 个词条...", flush=True)

        for attempt in range(1, 5):
            try:
                polished_chunk = batch_refactor_ai(batch_payload, api_key, api_base, model)
                refactored_data.update(polished_chunk)
                success_count += len(polished_chunk)
                print(f"     ✅ 批次 {batch_idx} 校对完成 ({len(polished_chunk)} 项)", flush=True)
                
                # 增量实时写回磁盘
                with open(ZH_FILE, "w", encoding="utf-8") as f:
                    json.dump(refactored_data, f, ensure_ascii=False, indent=2)

                # 控速：每批完成后休眠 4 秒
                time.sleep(4.0)
                break
            except Exception as e:
                wait_time = 15 * attempt
                print(f"     ⚠️ 批次 {batch_idx} 第 {attempt} 次遇到限流或异常: {e}，等待 {wait_time} 秒后重试...", flush=True)
                time.sleep(wait_time)
                if attempt == 4:
                    print(f"     ❌ 批次 {batch_idx} 跳过，保留当前翻译", flush=True)

    print(f"\n🎉 全量校对完成！共重构校对: {success_count}/{total_count} 项！", flush=True)

if __name__ == "__main__":
    main()
