import os
import re
import time
import random
import requests

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN_2     = os.environ["NOTION_TOKEN_2"]
NOTION_POST_DB_ID  = os.environ["NOTION_DATABASE_ID_3"]
THREADS_USER_ID    = os.environ["THREADS_USER_ID"]
THREADS_TOKEN      = os.environ["IG_ACCESS_TOKEN"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN_2}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Telegram 通知 ─────────────────────────────────────
def send_telegram(message):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message},
        timeout=30
    )

# ── 清除 AI 雜訊 ──────────────────────────────────────
def clean_text(text):
    # 移除 --- 分隔線
    text = re.sub(r'\n?-{2,}\n?', '\n', text)
    # 移除 *** 分隔線
    text = re.sub(r'\n?\*{2,}\n?', '\n', text)
    # 移除粗體標記 **文字**
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 移除斜體標記 *文字*
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # 移除引用符號 >
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # 超過兩個連續空行，壓縮成一個空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 清理行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()

# ── 安全截斷：不超過 480 字元，在標點處切斷 ──────────
def truncate_to_chars(text, max_chars=480):
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    for punct in ['。', '！', '？', '\n']:
        idx = truncated.rfind(punct)
        if idx > max_chars * 0.7:
            return truncated[:idx+1]
    return truncated

# ── 切割段落（支援所有 § 格式變體）─────────────────────
def split_posts(content):
    """
    切割 §1 §2 ... 段落，支援各種格式變體：
    §1 / § 1 / §１ / **§1** 等
    """
    content = re.sub(r'\*{0,3}\s*§\s*([０-９\d]+)\s*\*{0,3}', r'\n§SPLIT§\1\n', content)
    parts = content.split('\n§SPLIT§')
    posts = []
    for part in parts:
        lines = part.split('\n')
        # 第一行是數字，跳過
        if lines and re.match(r'^[０-９\d]+$', lines[0].strip()):
            lines = lines[1:]
        text = '\n'.join(lines).strip()
        if text:
            posts.append(text)
    return posts

# ── 撈所有待發 ────────────────────────────────────────
def get_pending_posts():
    url = f"https://api.notion.com/v1/databases/{NOTION_POST_DB_ID}/query"
    payload = {
        "filter": {
            "property": "狀態",
            "status": {"equals": "待發"}
        }
    }
    res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
    print("HTTP 狀態碼：", res.status_code)
    data = res.json()

    if data.get("object") == "error":
        print("❌ API 錯誤：", data)
        return []

    results = data.get("results", [])
    print(f"篩選後待發筆數：{len(results)}")
    return results

# ── 讀取內容：直接讀 rich_text 欄位 ───────────────────
def get_content_from_property(page):
    rich_text = page["properties"].get("內容", {}).get("rich_text", [])
    content = "".join([t["plain_text"] for t in rich_text])
    print(f"✅ 讀到內容，長度：{len(content)}")
    return content

# ── 更新 Notion 狀態 ───────────────────────────────────
def update_status(page_id, status="已發"):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    requests.patch(
        url,
        headers=NOTION_HEADERS,
        json={"properties": {"狀態": {"status": {"name": status}}}},
        timeout=30
    )

# ── 將純文字內容轉換成正確的換行格式 ────────────────────
def normalize_content_format(content):
    """
    Notion rich_text 讀出來的內容可能缺少換行，
    根據全形句號、問號、驚嘆號自動補換行，
    確保每句話獨立一行。
    """
    # 先做基本清理
    content = clean_text(content)

    # 如果已經有 § 分隔符號，代表格式正常，直接返回
    if '§' in content:
        return content

    # 沒有 § 的話，嘗試根據句號補換行
    # 在全形句號、驚嘆號、問號後面加換行（如果後面不是換行）
    content = re.sub(r'([。！？])\s*(?!\n)', r'\1\n', content)
    # 壓縮多餘空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()

# ── 發文到 Threads ─────────────────────────────────────
def post_to_threads(content):
    # 先清除雜訊並正規化格式
    content = clean_text(content)
    content = normalize_content_format(content)

    # 切割段落
    posts = split_posts(content)

    print(f"📝 共分成 {len(posts)} 則發文")

    # 切割失敗保護：少於 2 則直接報錯，不發文
    if len(posts) < 2:
        raise Exception(
            f"段落切割失敗，只切出 {len(posts)} 則，"
            f"內容預覽：{repr(content[:300])}"
        )

    last_published_id = ""

    for i, text in enumerate(posts):
        text = text.replace("\\n", "\n")
        text = truncate_to_chars(text, 480)

        if not text.strip():
            print(f"⚠️ 第 {i+1} 則內容為空，跳過")
            continue

        print(f"🚀 建立第 {i+1} 則 container（{len(text)} 字元）...")
        create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        data = {"media_type": "TEXT", "text": text, "access_token": THREADS_TOKEN}
        if last_published_id:
            data["reply_to_id"] = last_published_id

        res = requests.post(create_url, data=data, timeout=30).json()
        creation_id = res.get("id")
        if not creation_id:
            raise Exception(f"建立 container 失敗（第 {i+1} 則）：{res}")
        time.sleep(8)

        pub_res = None
        for attempt in range(3):
            print(f"📤 發布第 {i+1} 則（第 {attempt+1} 次嘗試）...")
            pub_res = requests.post(
                f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
                data={"creation_id": creation_id, "access_token": THREADS_TOKEN},
                timeout=30
            ).json()

            if pub_res.get("id"):
                break
            elif pub_res.get("error", {}).get("is_transient"):
                print(f"暫時性錯誤，等待 15 秒後重試...")
                time.sleep(15)
            else:
                raise Exception(f"發布失敗（第 {i+1} 則）：{pub_res}")

        if not pub_res or not pub_res.get("id"):
            raise Exception(f"發布失敗超過重試次數（第 {i+1} 則）：{pub_res}")

        last_published_id = pub_res.get("id", "")
        print(f"✅ 第 {i+1} 則發布成功：{last_published_id}")

        wait = random.randint(10, 20)
        print(f"⏳ 等待 {wait} 秒後發下一則...")
        time.sleep(wait)

# ── 主程式 ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== _3 段落直接發模式 ===")

    posts = get_pending_posts()
    if not posts:
        print("沒有待發內容，結束。")
        exit(0)

    # 過濾出有內容的筆，再隨機挑一筆
    valid_posts = []
    for page in posts:
        content = get_content_from_property(page)
        if content.strip():
            valid_posts.append((page, content))

    if not valid_posts:
        print("所有待發筆內容都是空的，結束。")
        exit(0)

    target_page, target_content = random.choice(valid_posts)
    page_id = target_page["id"]
    print(f"🎲 隨機選中第幾筆（共 {len(valid_posts)} 筆有內容）")
    print(f"讀到的內容預覽：{repr(target_content[:200])}")

    try:
        print("📄 找到待發內容，開始發文...")
        post_to_threads(target_content)
        update_status(page_id, "已發")
        print("✅ 完成！")
        send_telegram("✅ media 給文章 發文成功！")

    except Exception as e:
        error_msg = f"❌ media 給文章 發文失敗！\n錯誤原因：{str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        raise
