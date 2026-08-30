#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import urllib.error

EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"

# 统一术语约束
GLOSSARY_PROMPT = """
【统一术语规则】:
- Workflow -> 工作流
- Node -> 节点
- Credentials -> 凭据
- Execution -> 执行 / 运行
- Trigger -> 触发器
- Canvas -> 画布
- Pin Data -> 固定数据
- Expression -> 表达式
- Insights -> 数据洞察
- Webhook/API/JSON/HTTP -> 保留大写专有名词，不进行翻译
"""

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...", flush=True)
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def batch_refactor_ai(batch_items, api_key, api_base, model):
    """
    接收对比数据: {"key": {"en": "...", "zh": "..."}}
    由 AI 结合英文上下文与原中文进行润色、校对与术语对齐
    """
    prompt = f"""你是一个专业的前端本地化与文案润色专家。请对以下 n8n 自动化工作流软件的前端词条进行【深度校对与重构翻译】。

待校对数据格式为：
"Key": {{ "en": "英文原句", "current": "当前中文" }}

{GLOSSARY_PROMPT}

【校对要求】:
1. 严禁丢失或修改任何占位符！如 {{time}}、{{name}}、{{count}}、{0}、HTML标签 <b> 等必须100%原样保留。
2. 消除生硬的机翻腔，使其符合中国开发者的软件交互习惯（语句自然通顺、动词/名词专业）。
3. 如果现有翻译已十分准确且符合术语，予以保留；若存在语病、术语冲突或直译，进行重新翻译润色。
4. 返回格式必须为纯 JSON 字典格式: {{ "Key": "校对后的中文" }}，严禁包含任何 Markdown 格式或额外说明文字。

待校对数据:
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

    # 筛选待校对的目标（包含全部官方存在的词条）
    all_keys = [k for k in en_data.keys()]
    total_count = len(all_keys)
    print(f"📊 官方基准有效词条: {total_count} 项，准备启动全量校对重构...", flush=True)

    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        api_key = gemini_key
        api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        model = "gemini-2.0-flash-lite"
        print(f"🌟 使用 Google Gemini 极速模型: {model}", flush=True)
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
        print("❌ 未检测到 API_KEY 环境变量！", flush=True)
        sys.exit(1)

    # 分批大小 (每批 100 条)
    batch_size = 100
    total_batches = (total_count + batch_size - 1) // batch_size
    print(f"🚀 开始全量逐批校对 (共 {total_batches} 批)...", flush=True)

    refactored_data = dict(zh_data)
    success_count = 0

    for i in range(0, total_count, batch_size):
        batch_keys = all_keys[i:i + batch_size]
        batch_idx = i // batch_size + 1
        
        # 组装英文原文与当前中文对照包
        batch_payload = {}
        for k in batch_keys:
            batch_payload[k] = {
                "en": en_data[k],
                "current": zh_data.get(k, "")
            }

        print(f"  -> [批次 {batch_idx}/{total_batches}] 正在校对润色 {len(batch_payload)} 个词条...", flush=True)

        for attempt in range(1, 4):
            try:
                polished_chunk = batch_refactor_ai(batch_payload, api_key, api_base, model)
                refactored_data.update(polished_chunk)
                success_count += len(polished_chunk)
                print(f"     ✅ 批次 {batch_idx} 校对完成 ({len(polished_chunk)} 项)", flush=True)
                
                # 每完成一批，立即增量写回磁盘，确保随时可中断且不丢进度
                with open(ZH_FILE, "w", encoding="utf-8") as f:
                    json.dump(refactored_data, f, ensure_ascii=False, indent=2)
                break
            except Exception as e:
                print(f"     ⚠️ 批次 {batch_idx} 第 {attempt} 次异常: {e}", flush=True)
                if attempt < 3:
                    time.sleep(2 * attempt)
                else:
                    print(f"     ❌ 批次 {batch_idx} 失败，保留当前原样", flush=True)

    print(f"\n🎉 全量校对完成！共重构校对词条: {success_count}/{total_count} 项！", flush=True)

if __name__ == "__main__":
    main()
