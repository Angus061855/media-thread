import os
import re
import time
import requests
import datetime
from google import genai

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN       = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
GEMINI_API_KEY     = os.environ["GEMINI_API_KEY"]
THREADS_USER_ID    = os.environ["THREADS_USER_ID"]
THREADS_TOKEN      = os.environ["IG_ACCESS_TOKEN"]

# ── 範例文章 ──────────────────────────────────────────
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

def generate_post(used_topics):
    client = genai.Client(api_key=GEMINI_API_KEY)
    used_str = "\n".join(f"- {t}" for t in used_topics) if used_topics else "（目前沒有已用主題）"

    prompt = f"""
你是一位在八大行業做了7年的男性經紀人，現在在 Threads 上連續發文，目的是幫助想入行或已經在行業裡的女生保護自己、避免被黑心經紀騙。

【第一步：自己想題材】
以下是已經用過的主題，【全部禁止重複】：
{used_str}

請根據以下方向，自由發揮，想一個還沒用過、有吸引力的新主題。
可以從真實情境、常見誤解、心理操控、財務陷阱、職場安全、合約漏洞、入行心態等任何角度切入。
只要是能幫助女生保護自己的題材，都可以。
第一行輸出「主題：[你選的主題]」

{EXAMPLE_POSTS}

【角色設定】
- 性別：男
- 身份：八大經紀人，做了7年
- 口吻：像一個有經驗的前輩在跟朋友說話，不說教、不高高在上
- 定位：誠實、透明、敢講真話、保護小姐

【文章結構】（5到7則，依內容自行決定幾則最合適）
- 第一則：衝擊性開場，打破常見認知，製造懸念，引發好奇
- 第二則：具體案例故事，用「有個小姐」「有個女生」帶出，有時間點、有對話、有細節
- 第三則：深化觀點，延續案例，說明後果與心情
- 第四則：解釋現象背後的原因和機制，批評亂象
- 第五則：實用建議或第二個案例，越細節越好
- 第六則（選用）：強化論點或第三個案例
- 最後一則：收尾昇華，引導留言或私訊

【字數規則】
- 每則嚴格控制在 200-280 個中文字以內
- 寧可寫少，絕對不要超過 280 字

【語言風格 ── 非常重要】
- 完全模仿上面的範例文章風格
- 每一句話都要獨立一行，句號後換行，再空一行
- 短句為主，每句不超過 30 字
- 台灣口語，說人話，不用專業術語
- 適度使用「超」「根本」「整個」「直接」等台灣口語
- 用「妳」稱呼讀者，用「她」稱呼案例中的人
- 對話格式：「我問她，○○？」「她說，○○。」「我說，○○。」
- 重要觀念可以重複強調

【寫作規則 ── 嚴格遵守】
1. 禁止使用任何人名，一律用「有個小姐」「有個女生」「她」代替
2. 禁止使用：「——」、任何引用來源符號、emoji、粗體、斜體
3. 標點符號全部使用全形（，。？！：）
4. 禁止 AI 感用語：他笑著搖搖頭、我愣住了、他苦笑著說、頓了頓、深吸一口氣、若有所思、眼神黯淡下來
5. 禁止句型：「不是⋯而是⋯」「更扯的是」「意味著」「在此情境下」「我們可以觀察到」

【格式規則】
- 直接輸出文章內容，不要用任何 codeblock 包起來
- 每則開頭單獨一行寫「§1」「§2」...作為分隔標記
- 只輸出文章內容，不要加任何說明、標題、編號

【情緒曲線設計】
- 第一則：震撼 → 第二則：同情 → 第三則：憤怒 → 第四則：恐懼 → 第五則以後：希望＋警惕 → 最後一則：信任＋行動呼籲

輸出格式：第一行輸出「主題：[主題內容]」，空一行後開始輸出貼文內容。
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip()

def extract_topic(post_text):
    for line in post_text.strip().split("\n"):
        if line.startswith("主題："):
            return line.replace("主題：", "").strip()
    return "未知主題"

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
    first_published_id = ""

    for i, text in enumerate(posts):
        text = text.replace("\\n", "\n")
        while len(text.encode('utf-8')) > 480:
            text = text[:-1]

        print(f"🚀 建立第 {i+1} 則 container...")
        create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        data = {"media_type": "TEXT", "text": text, "access_token": THREADS_TOKEN}
        if last_published_id:
            ddata["reply_to_id"] = first_published_id

        res = requests.post(create_url, data=data).json()
        creation_id = res.get("id")
        if not creation_id:
            raise Exception(f"建立 container 失敗（第 {i+1} 則）：{res}")
        time.sleep(5)

        print(f"📤 發布第 {i+1} 則...")
        pub_res = requests.post(
            f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
            data={"creation_id": creation_id, "access_token": THREADS_TOKEN}
        ).json()
        published_id = pub_res.get("id", "")
        if i == 0:
            first_published_id = published_id
        print(f"第 {i+1} 則結果：", pub_res)
        time.sleep(3)

def save_to_notion(topic, post_text):
    lines = post_text.strip().split("\n")
    content_lines = []
    skip_topic = True
    for line in lines:
        if skip_topic and line.startswith("主題："):
            skip_topic = False
            continue
        content_lines.append(line)
    clean_content = "\n".join(content_lines).strip()

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "主題": {"title": [{"text": {"content": topic}}]},
            "預寫內容": {"rich_text": [{"text": {"content": clean_content[:2000]}}]},
            "狀態": {"status": {"name": "已發"}}
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    print("Notion 回應：", res.status_code)

if __name__ == "__main__":
    print("=== _1 自動生成模式 ===")
    used_topics = get_used_topics()
    print(f"共 {len(used_topics)} 個已用主題")
    post_text = generate_post(used_topics)
    print("貼文內容：\n", post_text)
    topic = extract_topic(post_text)
    print("📌 主題：", topic)
    post_to_threads(post_text)
    save_to_notion(topic, post_text)
    print("✅ 完成！")
