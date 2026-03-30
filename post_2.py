import os
import re
import time
import requests
from google import genai

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN           = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID     = os.environ["NOTION_DATABASE_ID"]
NOTION_PENDING_DB_ID   = os.environ["NOTION_PENDING_DATABASE_ID"]
GEMINI_API_KEY         = os.environ["GEMINI_API_KEY"]
THREADS_USER_ID        = os.environ["THREADS_USER_ID"]
THREADS_TOKEN          = os.environ["IG_ACCESS_TOKEN"]

EXAMPLE_POSTS = """
以下是真實的發文範例，請完全學習這個風格、語氣、句子長度和換行方式：

【範例第一則】
短影音或IG真的不要再讓小姐入鏡了好嗎。

我知道流量密碼真的都是拍到小姐，我也不管小姐是否同意，畢竟也許小姐當下覺得這行業很好玩，所以同意出鏡。

但過陣子呢。

他們說不定改變想法，想去做一般行業，被身邊認識的人認出來該怎麼辦，你們有想過嗎。

就算打馬賽克還是戴著一半的面具，身上的特徵也很容易找到的。

現在網友真的很厲害，有一點資訊都可以肉搜出來。

【範例第二則】
上個月，有個小姐跑來找我，她說她之前跟她經紀拍了幾支短影音。

她說她那時候覺得很新鮮，而且她經紀跟她說會打馬賽克，不會被認出來。

結果影片發出去之後，不到一個禮拜，她就被她高中同學認出來了。

她說她同學傳訊息給她，問她是不是在做酒店，她當下整個傻眼。

她說她那時候根本不知道該怎麼回，因為她根本沒想到會被認出來。

後來她才發現，她手上有個很明顯的小刺青，而且她的體型跟髮型都很有特色。

她同學就是靠這些特徵認出她的。

【範例第三則】
她跟我說，哥我現在真的很後悔，因為我根本沒想到會這樣。

她說她現在每天都活在恐懼中，怕被更多人認出來，怕被家人發現。

她說她經紀還在那邊沾沾自喜，說那支影片帶了好幾個妹，賺了多少錢。

但她呢，一輩子就這樣被掛上八大小姐的稱號。

她說她問她經紀能不能把影片刪掉，結果她經紀跟她說，影片已經被轉發那麼多次了，刪掉也沒用。

她跟我說，哥我真的很想哭，因為我覺得我的人生就這樣毀了。
"""

def get_pending_topics():
    url = f"https://api.notion.com/v1/databases/{NOTION_PENDING_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {"filter": {"property": "狀態", "status": {"equals": "待發"}}}
    res = requests.post(url, headers=headers, json=payload).json()
    return res.get("results", [])

def update_status(page_id, status="已發"):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    requests.patch(url, headers=headers, json={"properties": {"狀態": {"status": {"name": status}}}})

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

def generate_post(used_topics, custom_topic):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
你是一位在八大行業做了7年的男性經紀人，現在在 Threads 上連續發文，目的是幫助想入行或已經在行業裡的女生保護自己、避免被黑心經紀騙。

【主題】
本次主題已指定為：「{custom_topic}」
請直接用這個主題寫文章，不需要自己想題材。
第一行輸出「主題：{custom_topic}」

{EXAMPLE_POSTS}

【角色設定】
- 性別：男
- 身份：八大經紀人，做了7年
- 口吻：像一個有經驗的前輩在跟朋友說話，不說教、不高高在上
- 定位：誠實、透明、敢講真話、保護小姐

【文章結構】（5到7則）
- 第一則：衝擊性開場
- 第二則：具體案例故事
- 第三則：深化觀點
- 第四則：解釋原因與機制
- 第五則：實用建議或第二個案例
- 第六則（選用）：強化論點
- 最後一則：收尾昇華，引導留言或私訊

【字數規則】每則嚴格控制在 200-280 個中文字以內

【語言風格】
- 每一句話獨立一行，句號後換行，再空一行
- 短句為主，台灣口語
- 用「妳」稱呼讀者，用「她」稱呼案例中的人
- 對話格式：「我問她，○○？」「她說，○○。」

【寫作規則】
1. 禁止使用任何人名，一律用「有個小姐」「有個女生」「她」代替
2. 禁止使用：「——」、emoji、粗體、斜體
3. 標點符號全部使用全形（，。？！：）
4. 禁止 AI 感用語：他笑著搖搖頭、我愣住了、頓了頓、深吸一口氣
5. 禁止句型：「不是⋯而是⋯」「更扯的是」「意味著」

【格式規則】
- 每則開頭單獨一行寫「§1」「§2」...
- 只輸出文章內容，不要加任何說明

輸出格式：第一行輸出「主題：{custom_topic}」，空一行後開始輸出貼文內容。
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip()

def post_to_threads(post_text):
    lines = post_text.strip().split("\n")
    content_lines = []
    skip_topic = True
    for line in lines:
        if skip_topic and line.startswith("主題："):
            skip_topic = False
            continue
        content_lines.append(line)
    content = "\n".join(content_lines).strip()

    posts = re.split(r'§\d+', content)
    posts = [p.strip() for p in posts if p.strip()]
    last_published_id = ""

    for i, text in enumerate(posts):
        text = text.replace("\\n", "\n")
        while len(text.encode('utf-8')) > 480:
            text = text[:-1]

        print(f"🚀 建立第 {i+1} 則 container...")
        create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        data = {"media_type": "TEXT", "text": text, "access_token": THREADS_TOKEN}
        if last_published_id:
            data["reply_to_id"] = last_published_id

        res = requests.post(create_url, data=data).json()
        creation_id = res.get("id")
        if not creation_id:
            raise Exception(f"建立 container 失敗（第 {i+1} 則）：{res}")
        time.sleep(5)

        pub_res = requests.post(
            f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
            data={"creation_id": creation_id, "access_token": THREADS_TOKEN}
        ).json()
        last_published_id = pub_res.get("id", "")
        print(f"第 {i+1} 則結果：", pub_res)
        time.sleep(3)

if __name__ == "__main__":
    print("=== _2 給主題自動發模式 ===")
    pages = get_pending_topics()
    if not pages:
        print("沒有待發主題，結束。")
        exit(0)

    page = pages[0]
    page_id = page["id"]
    props = page.get("properties", {})
    topic_list = props.get("主題", {}).get("title", [])
    custom_topic = topic_list[0]["plain_text"] if topic_list else ""

    if not custom_topic.strip():
        print("主題為空，結束。")
        update_status(page_id, "已發")
        exit(0)

    print(f"📌 主題：{custom_topic}")
    used_topics = get_used_topics()
    post_text = generate_post(used_topics, custom_topic)
    print("貼文內容：\n", post_text)
    post_to_threads(post_text)
    update_status(page_id, "已發")
    print("✅ 完成！")
