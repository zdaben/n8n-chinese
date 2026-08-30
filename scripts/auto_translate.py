#!/usr/bin/env python3
"""
自动比对官方 en.json 并为 zh-CN.json 补齐缺失的词条
支持直接调用 DeepSeek / OpenAI API 批量自动翻译
"""
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
    prompt = f"""你是一个专业的前端国际化翻译助手。请将以下 n8n 工作流软件的前端 JSON 英文词条翻译成简体中文。
要求：
1. 严禁修改或遗漏任何变量占位符，如 {{time}}、{{name}}、{{count}}、{{0}} 等必须原样保留。
2. 保持专业术语（Workflow -> 工作流，Node -> 节点，Credentials -> 凭据，Execution -> 执行，Canvas -> 画布，Insights -> 洞察与指标）。
3. 只返回严格合法的 JSON 格式字典: {{ "key": "翻译后的中文" }}，不要输出任何 Markdown 标记或多余文字。

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
    missing = {k: en_data[k] for k in en_data if k not in zh_data}

    print(f"📊 官方有效词条: {len(en_data)} | 本地已有: {len(zh_data)}", flush=True)
    print(f"🔍 待补全缺失词条: {len(missing)}", flush=True)

    if not missing:
        print("🎉 恭喜！当前翻译覆盖率已是 100%，无缺失词条！", flush=True)
        return

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

    items = list(missing.items())
    batch_size = 100
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    print(f"🤖 开始极速增量翻译 (共 {total_batches} 批)...", flush=True)
    success_count = 0

    for i in range(0, len(items), batch_size):
        chunk = dict(items[i:i + batch_size])
        batch_idx = i // batch_size + 1
        print(f"  -> [批次 {batch_idx}/{total_batches}] 正在翻译 {len(chunk)} 个词条...", flush=True)
        
        for attempt in range(1, 4):
            try:
                translated_chunk = batch_translate_ai(chunk, api_key, api_base, model)
                zh_data.update(translated_chunk)
                success_count += len(translated_chunk)
                print(f"     ✅ 批次 {batch_idx} 完成 ({len(translated_chunk)} 条)", flush=True)
                time.sleep(0.5)
                break
            except Exception as e:
                print(f"     ⚠️ 批次 {batch_idx} 第 {attempt} 次重试异常: {e}", flush=True)
                if attempt < 3:
                    time.sleep(2 * attempt)
                else:
                    print(f"     ❌ 批次 {batch_idx} 失败，跳过该批", flush=True)

    with open(ZH_FILE, "w", encoding="utf-8") as f:
        json.dump(zh_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 字典增量更新完成！本次新增: {success_count} 条，总有效词条数: {len(zh_data)}", flush=True)

if __name__ == "__main__":
    main()
