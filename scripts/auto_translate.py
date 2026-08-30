#!/usr/bin/env python3
"""
自动比对官方 en.json 并为 zh-CN.json 补齐缺失的词条
支持直接调用 DeepSeek / OpenAI API 批量自动翻译
"""
#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
import urllib.error

EN_URL = "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/@n8n/i18n/src/locales/en.json"
ZH_FILE = "languages/zh-CN.json"

def fetch_official_en():
    print("🔍 正在拉取官方最新的 en.json 基准字典...")
    req = urllib.request.Request(EN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def batch_translate_ai(texts_dict, api_key, api_base="https://api.deepseek.com/v1", model="deepseek-chat"):
    prompt = f"""你是一个专业的前端国际化翻译助手。请将以下 n8n 工作流软件的前端 JSON 英文词条翻译成简体中文。
要求：
1. 严禁修改或遗漏任何变量占位符，如 {{time}}、{{name}}、{{count}}、{{0}} 等必须原样保留。
2. 保持专业术语（Workflow -> 工作流，Node -> 节点，Credential -> 凭据，Execution -> 执行，Canvas -> 画布）。
3. 只返回严格合法的 JSON 格式字典，不要输出任何 Markdown 标记或多余文字。

待翻译 JSON:
{json.dumps(texts_dict, ensure_ascii=False)}
"""
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        content = res["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())

def main():
    if not os.path.exists(ZH_FILE):
        print(f"❌ 未找到本地字典: {ZH_FILE}")
        sys.exit(1)

    with open(ZH_FILE, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    en_data = fetch_official_en()
    missing = {k: en_data[k] for k in en_data if k not in zh_data}

    print(f"📊 官方词条总数: {len(en_data)} | 本地已有: {len(zh_data)}")
    print(f"🔍 待补全缺失词条: {len(missing)}")

    if not missing:
        print("🎉 恭喜！当前翻译覆盖率已是 100%！")
        return

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        api_base = "https://api.deepseek.com/v1" if os.getenv("DEEPSEEK_API_KEY") else "https://api.openai.com/v1"
        model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"
        
        # 按每批 100 条切片翻译，防止 Token 超限
        items = list(missing.items())
        batch_size = 100
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        print(f"🤖 开始调用 AI 分批翻译 (共 {total_batches} 批)...")
        for i in range(0, len(items), batch_size):
            chunk = dict(items[i:i + batch_size])
            print(f"  -> 正在翻译第 {i//batch_size + 1}/{total_batches} 批...")
            try:
                translated_chunk = batch_translate_ai(chunk, api_key, api_base, model)
                zh_data.update(translated_chunk)
            except Exception as e:
                print(f"  ⚠️ 本批翻译遇到异常: {e}，跳过保留英文")
    else:
        # 兜底内置高频菜单
        common_patches = {
            "workflow.editDescriptionAndTags": "编辑描述与标签",
            "workflow.exportJson": "导出 JSON",
            "workflow.import": "导入",
            "workflow.versionHistory": "版本历史",
            "workflow.productionChecklist": "投产就绪检查",
            "workflow.settings": "工作流设置",
            "generic.insights": "洞察与指标",
            "sidebar.insights": "数据洞察",
            "nodeView.editDescription": "编辑描述",
            "nodeView.openDetails": "打开详情"
        }
        zh_data.update(common_patches)
        print("⚠️ 未配置 API_KEY，已自动写入高频菜单补丁！")

    with open(ZH_FILE, "w", encoding="utf-8") as f:
        json.dump(zh_data, f, ensure_ascii=False, indent=2)

    print(f"💾 字典更新完成！当前有效词条: {len(zh_data)}")

if __name__ == "__main__":
    main()
