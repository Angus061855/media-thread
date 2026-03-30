import os
import requests
from google import genai
from datetime import datetime
import time

# ── 環境變數 ──────────────────────────────────────────
GEMINI_API_KEY           = os.environ["GEMINI_API_KEY"]
THREADS_ACCESS_TOKEN     = os.environ["IG_ACCESS_TOKEN"]
THREADS_USER_ID          = os.environ["THREADS_USER_ID"]
NOTION_TOKEN             = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID       = os.environ["NOTION_DATABASE_ID"]
NOTION_PENDING_DB_ID     = os.environ["NOTION_PENDING_DATABASE_ID"]
POST_MODE                = os.environ.get("POST_MODE", "auto")

# ── Gemini 設定 ───────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ══════════════════════════════════════════════════════
# 1. Gemini 生成文章（七段）
# ══════════════════════════════════════════════════════
# ── 範例文章（讓 Gemini 學你的語氣）─────────────────
EXAMPLE_POSTS = """
以下是真實的文章範例，請完全學習這個風格、語氣、句子長度和換行方式：

【範例第一則】
我雖然會經常發文說，哪些行為的經紀不好。

可是有很多事情，妳沒有去做、去認識他，都不會發現。

畢竟好聽話大家都會說，人設大家都會做。

但實際上班之後發生什麼事情，或是私底下的人品如何，都是要接觸後才會知道。

所以我真的想跟妳們說，不要只看網路上的東西。

要實際接觸過，才知道這個經紀到底好不好。

但在妳接觸之前，有些事情妳一定要注意。

不然妳可能會被騙，妳可能會被困住。

【範例第二則】
故事得從三個月前說起。

有個女生來找我，她說她簽了合約。

她之前去面試，那個經紀給她一堆資料要填。

她想說應該都是正常的資料，就沒仔細看，全部簽了。

結果上班一個月後，她發現那個經紀根本不是她想的那樣。

她想換經紀，結果那個經紀說她簽了合約，要付違約金10萬。

我問她，妳有仔細看過那些資料嗎？

她說，沒有，她以為都是正常的資料。

我說，現在知道已經太遲了。
"""

# ── 1. 從 Notion 撈所有已發過的主題 ──────────────────
def get_used_topics():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    used = []
    payload = {}
    while True:
        res = requests.post(url, headers=headers, json=payload).json()
        for page in res.get("results", []):
            props = page.get("properties", {})
            title_list = props.get("主題", {}).get("title", [])
            if title_list:
                used.append(title_list[0]["plain_text"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return used

# ── 2. 產生七則貼文內容 ───────────────────────────────
def generate_post(used_topics, custom_topic=None):
    client = genai.Client(api_key=GEMINI_API_KEY)

    used_str = "\n".join(f"- {t}" for t in used_topics) if used_topics else "（目前沒有已用主題）"

    # 根據是否有指定主題，調整 Prompt 第一步
    if custom_topic:
        topic_instruction = f"""
【主題】
本次主題已指定為：「{custom_topic}」
請直接用這個主題寫文章，不需要自己想題材。
第一行輸出「主題：{custom_topic}」
"""
    else:
        topic_instruction = f"""
【第一步：自己想題材】
以下是已經用過的主題，【全部禁止重複】：
{used_str}

請根據以下方向，自由發揮，想一個還沒用過、有吸引力的新主題。
可以從真實情境、常見誤解、心理操控、財務陷阱、職場安全、合約漏洞、入行心態等任何角度切入。
只要是能幫助女生保護自己的題材，都可以。
第一行輸出「主題：[你選的主題]」
"""

    prompt = f"""
你是一位在八大行業做了7年的男性經紀人，現在在 Threads 上連續發文，目的是幫助想入行或已經在行業裡的女生保護自己、避免被黑心經紀騙。

{topic_instruction}

{EXAMPLE_POSTS}

【角色設定】
- 性別：男
- 身份：八大經紀人，做了7年
- 口吻：像一個有經驗的前輩在跟朋友說話，不說教、不高高在上
- 定位：誠實、透明、敢講真話、保護小姐

【文章結構】（七則連發）
- 第一則：衝擊性開場，打破常見認知，製造懸念，引發好奇，最後用一個懸念結尾
- 第二則：具體案例故事，用「有個小姐」「有個女生」帶出，有時間點、有對話、有細節
- 第三則：深化觀點，解釋現象背後的原因和機制
- 第四則：第二個案例，繼續用「有個小姐」「有個女生」，加深複雜度
- 第五則：實用建議，條列式，越細節越好，可操作
- 第六則：第三個案例或強化論點，有對話、有結果
- 第七則：收尾昇華，重複核心觀念三次，引導留言或私訊

【字數規則】
- 每則嚴格控制在 130-150 個中文字以內
- 寧可寫少，絕對不要超過 150 字

【語言風格 ── 非常重要】
- 完全模仿上面的範例文章風格
- 每一句話都要獨立一行，句號後換行，再空一行
- 短句為主，每句不超過20字
- 台灣口語，說人話，不用專業術語
- 用「妳」稱呼讀者，用「她」稱呼案例中的人
- 對話格式：「我問她，○○？」「她說，○○。」「我說，○○。」
- 重要觀念重複三次，例如「不要簽合約，不要簽合約，不要簽合約。」

【寫作規則 ── 嚴格遵守】
1. 禁止使用任何人名（小琪、小芳、阿美等全部禁止），一律用「有個小姐」「有個女生」「她」代替
2. 禁止使用：「——」、任何引用來源符號、emoji、粗體、斜體
3. 標點符號全部使用全形（，。？！：）
4. 禁止 AI 感用語：他笑著搖搖頭、我愣住了、他苦笑著說、頓了頓、深吸一口氣、若有所思

【格式規則】
- 直接輸出文章內容，不要用任何 codeblock 包起來
- 每則開頭單獨一行寫「§1」「§2」...「§7」作為分隔標記
- 只輸出文章內容，不要加任何說明、標題、編號

【行動呼籲】
- 最後一則結尾引導「如果妳需要，可以來找我聊聊」
- 語氣是邀請，不是推銷

輸出格式：
第一行輸出「主題：[主題內容]」，空一行後開始輸出七則貼文內容。
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()

# ══════════════════════════════════════════════════════
# 2. 解析預寫內容（七段）
# ══════════════════════════════════════════════════════
def parse_preset_content(content: str) -> list[str]:
    segments = []
    parts = content.split("§")
    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        if len(lines) == 2:
            segments.append(lines[1].strip())
        elif len(lines) == 1:
            segments.append(lines[0].strip())
    return segments

# ══════════════════════════════════════════════════════
# 3. 從 Notion 待發清單撈一筆「待發」資料
# ══════════════════════════════════════════════════════
def get_pending_post():
    url = f"https://api.notion.com/v1/databases/{NOTION_PENDING_DB_ID}/query"
    payload = {
        "filter": {
            "property": "狀態",
            "select": {"equals": "待發"}
        },
        "page_size": 1
    }
    res = requests.post(url, headers=NOTION_HEADERS, json=payload)
    data = res.json()
    results = data.get("results", [])
    if not results:
        return None
    page = results[0]
    page_id = page["id"]
    props = page["properties"]

    topic = props["主題"]["title"][0]["text"]["content"] if props["主題"]["title"] else ""
    preset = ""
    if props.get("預寫內容") and props["預寫內容"].get("rich_text"):
        preset = props["預寫內容"]["rich_text"][0]["text"]["content"]

    return {"page_id": page_id, "topic": topic, "preset": preset}

# ══════════════════════════════════════════════════════
# 4. 把 Notion 待發清單該筆改成「已發」
# ══════════════════════════════════════════════════════
def mark_as_posted(page_id: str):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "狀態": {"select": {"name": "已發"}}
        }
    }
    requests.patch(url, headers=NOTION_HEADERS, json=payload)

# ══════════════════════════════════════════════════════
# 5. 發佈到 Threads（七段輪流發）
# ══════════════════════════════════════════════════════
def post_to_threads(segments: list[str], topic: str):
    post_ids = []
    base_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"

    for i, segment in enumerate(segments):
        # Step 1：建立 container
        container_url = f"{base_url}/threads"
        container_payload = {
            "media_type": "TEXT",
            "text": segment,
            "access_token": THREADS_ACCESS_TOKEN
        }
        container_res = requests.post(container_url, data=container_payload)
        container_data = container_res.json()
        creation_id = container_data.get("id")

        if not creation_id:
            print(f"❌ 第 {i+1} 段建立失敗：{container_data}")
            continue

        # 等待 container 處理完成
        time.sleep(5)

        # Step 2：發佈
        publish_url = f"{base_url}/threads_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": THREADS_ACCESS_TOKEN
        }
        publish_res = requests.post(publish_url, data=publish_payload)
        publish_data = publish_res.json()
        post_id = publish_data.get("id")

        if post_id:
            post_ids.append(post_id)
            print(f"✅ 第 {i+1} 段發佈成功，ID：{post_id}")
        else:
            print(f"❌ 第 {i+1} 段發佈失敗：{publish_data}")

        # 每段之間等待，避免頻率限制
        time.sleep(10)

    return post_ids

# ══════════════════════════════════════════════════════
# 6. 儲存發文紀錄到 Notion 已發文資料庫
# ══════════════════════════════════════════════════════
def save_to_notion(topic: str, segments: list[str], post_ids: list[str]):
    url = "https://api.notion.com/v1/pages"
    full_content = "\n\n".join([f"§{i+1}\n{s}" for i, s in enumerate(segments)])
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "主題": {"title": [{"text": {"content": topic}}]},
            "貼文內容": {"rich_text": [{"text": {"content": full_content[:2000]}}]},
            "貼文 ID": {"rich_text": [{"text": {"content": ", ".join(post_ids)}}]},
            "發文時間": {"date": {"start": datetime.utcnow().isoformat()}}
        }
    }
    res = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if res.status_code == 200:
        print(f"✅ 已儲存到 Notion 紀錄")
    else:
        print(f"❌ 儲存 Notion 失敗：{res.json()}")

# ══════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════
def main():
    print(f"🚀 發文模式：{POST_MODE}")

    if POST_MODE == "pending":
        pending = get_pending_post()
        if not pending:
            print("⚠️ 待發清單沒有資料，跳過本次發文")
            return

        topic = pending["topic"]
        preset = pending["preset"]
        page_id = pending["page_id"]

        if preset.strip():
            print(f"📝 使用預寫內容，主題：{topic}")
            segments = parse_preset_content(preset)
        else:
            print(f"🤖 Gemini 生成文章，主題：{topic}")
            segments = generate_post(topic)

        post_ids = post_to_threads(segments, topic)
        save_to_notion(topic, segments, post_ids)
        mark_as_posted(page_id)

    else:
        print("🤖 自動模式，Gemini 自由發揮")
        topic_prompt = "請給我一個適合 Threads 的貼文主題，只需要主題名稱，不需要其他說明。"
        topic_res = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=topic_prompt
        )
        topic = topic_res.text.strip()
        print(f"💡 自動主題：{topic}")
        segments = generate_post(topic)
        post_ids = post_to_threads(segments, topic)
        save_to_notion(topic, segments, post_ids)

if __name__ == "__main__":
    main()
