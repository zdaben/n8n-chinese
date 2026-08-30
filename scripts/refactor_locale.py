#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import urllib.error

EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...", flush=True)
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def batch_translate_ai(texts_dict, api_key, api_base, model):
    prompt = f"""你是一个专业的前端国际化翻译专家。请对以下 n8n 自动化软件的前端 JSON 英文词条进行【统一术语标准化翻译与文案润色】。
要求：
1. 严禁修改或遗漏任何变量占位符，如 {{time}}、{{name}}、{{count}}、{{0}}、HTML标签 <b> 等必须100%原样保留。
2. 保持专业规范术语（Workflow -> 工作流，Node -> 节点，Credentials -> 凭据，Execution -> 执行，Canvas -> 画布，Pin Data -> 固定数据，Insights -> 数据洞察，Webhook/API/JSON -> 保留大写）。
3. 只返回严格合法的 JSON 格式字典: {{ "key": "润色后的中文" }}，不要输出任何 Markdown 标记或解释文字。

待翻译 JSON:
{json.dumps(texts_dict, ensure_ascii=False)}
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
    items = list(en_data.items())
    total_count = len(items)
    print(f"📊 官方基准有效词条: {total_count} 项，启动全量标准化校对重构...", flush=True)

    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        api_key = gemini_key
        api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        model = "gemini-flash-lite-latest"
        print(f"🌟 使用 Google AI Studio: {model}", flush=True)
    elif deepseek_key:
        api_key = deepseek_key
        api_base = "https://api.deepseek.com/v1"
        model = "deepseek-chat"
        print(f"🌟 使用 DeepSeek: {model}", flush=True)
    elif openai_key:
        api_key = openai_key
        api_base = "https://api.openai.com/v1"
        model = "gpt-4o-mini"
        print(f"🌟 使用 OpenAI: {model}", flush=True)
    else:
        print("❌ 未检测到任何 API_KEY！", flush=True)
        sys.exit(1)

    batch_size = 100
    total_batches = (total_count + batch_size - 1) // batch_size
    print(f"🤖 开始分批全量校对 (共 {total_batches} 批，每批 {batch_size} 条)...", flush=True)

    refactored_data = dict(zh_data)
    success_count = 0

    for i in range(0, total_count, batch_size):
        chunk = dict(items[i:i + batch_size])
        batch_idx = i // batch_size + 1
        print(f"  -> [批次 {batch_idx}/{total_batches}] 正在校对重构 {len(chunk)} 个词条...", flush=True)
        
        for attempt in range(1, 4):
            try:
                translated_chunk = batch_translate_ai(chunk, api_key, api_base, model)
                refactored_data.update(translated_chunk)
                success_count += len(translated_chunk)
                print(f"     ✅ 批次 {batch_idx} 完成，已处理 {len(translated_chunk)} 条", flush=True)
                
                # 增量实时写回，保证安全
                with open(ZH_FILE, "w", encoding="utf-8") as f:
                    json.dump(refactored_data, f, ensure_ascii=False, indent=2)
                
                time.sleep(0.5)
                break
            except Exception as e:
                print(f"     ⚠️ 批次 {batch_idx} 第 {attempt} 次重试异常: {e}", flush=True)
                if attempt < 3:
                    time.sleep(3 * attempt)
                else:
                    print(f"     ❌ 批次 {batch_idx} 失败，保留当前原样", flush=True)

    print(f"\n🎉 全量重构校对完成！成功校对: {success_count}/{total_count} 项！", flush=True)

if __name__ == "__main__":
    main()
