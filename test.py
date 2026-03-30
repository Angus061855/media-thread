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
def generate_post(topic: str) -> list[str]:
    prompt = f"""
你是一位專業的 Instagram 文案寫手，請根據主題「{topic}」撰寫一篇 Instagram 貼文。

規則：
- 全文分成 7 段，每段用 §1 §2 §3 §4 §5 §6 §7 標記開頭
- 第一句必須能獨立成立，吸引滑手機的人停下來
- 不要在開場就給答案，保持神秘感
- 禁止用「——」
- 禁止用「他笑著搖搖頭」「我愣住了」等 AI 感用語
- 最後一段必須包含一個開放式問題引發討論
- 語言自然，像在跟朋友聊天
- 標點符號使用全形：「，」「。」「？」「：」
- 文章內不得出現引用來源符號

格式範例：
§1
第一段內容

§2
第二段內容

（以此類推到 §7）
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    raw = response.text.strip()
    segments = []
    parts = raw.split("§")
    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        if len(lines) == 2:
            segments.append(lines[1].strip())
        elif len(lines) == 1:
            segments.append(lines[0].strip())
    return segments

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
