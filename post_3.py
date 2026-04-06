import os
import re
import time
import requests
from google import genai

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN_2       = os.environ["NOTION_TOKEN_2"]
NOTION_PENDING_DB_ID = os.environ["NOTION_DATABASE_ID_2"]
GEMINI_API_KEY       = os.environ["GEMINI_API_KEY"]
THREADS_USER_ID      = os.environ["THREADS_USER_ID"]
THREADS_TOKEN        = os.environ["IG_ACCESS_TOKEN"]

# ── Telegram 通知 ─────────────────────────────────────
def send_telegram(message):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message}
    )

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
        "Authorization": f"Bearer {NOTION_TOKEN_2}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {"filter": {"property": "狀態", "status": {"equals": "待發"}}}
    res = requests.post(url, headers=headers, json=payload).json()

    print("Notion API 回傳：", res)
    print("找到筆數：", len(res.get("results", [])))

    return res.get("results", [])

def update_status(page_id, status="已發"):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN_2}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    requests.patch(url, headers=headers, json={"properties": {"狀態": {"status": {"name": status}}}})

def generate_post(custom_topic):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
你是一位在八大行業做了7年的男性經紀人，現在在 Threads 上連續發文，目的是幫助想入行或已經在行業裡的女生保護自己、避免被黑心經紀騙。

【主題】
本次主題已指定為：「{custom_topic}」
請直接用這個主題寫文章，不需要自己想題材。
可以從真實情境、常見誤解、心理操控、財務陷阱、職場安全、合約漏洞、入行心態等任何角度切入。
只要是能幫助女生保護自己的題材，都可以。
第一行輸出「主題：{custom_topic}」

{EXAMPLE_POSTS}

【角色設定】
- 性別：男
- 身份：八大經紀人，做了7年
- 口吻：像一個有經驗的前輩在跟朋友說話，不說教、不高高在上
- 定位：誠實、透明、敢講真話、保護小姐
- 所有問題的來源只有一個：黑心經紀人，跟店家無關，不要提店家

【文章結構】（5到7則，依內容自行決定幾則最合適）
- 第一則：衝擊性開場，打破常見認知，製造懸念，引發好奇
- 第二則：具體案例故事，可以用「有個小姐來找我」或帶出，我的角色是幫助她、給她建議的人，不是害她的人，有時間點、有對話、有細節
或是「有個女生去找別的經紀，後來跑來找我」別的經紀的角色是黑心的 害了小姐，我的角色是幫助她、給她建議的人，不是害她的人，有時間點、有對話、有細節
- 第三則：深化觀點，延續案例，說明後果與心情
- 第四則：解釋現象背後的原因和機制，批評黑心經紀亂象
- 第五則：實用建議或行動指南，越細節越好
- 第六則：第二個案例或強化論點，進一步說明危害
- 第七則：收尾昇華，引導留言或私訊，不要用「姐妹們」開頭

【字數規則】每則嚴格控制在 200-280 個中文字以內
- 寧可寫少，絕對不要超過 280 字

【語言風格 ── 非常重要】
- 完全模仿上面的範例文章風格
- 每一句話都要獨立一行，句號後換行，再空一行
- 短句為主，每句不超過 30 字
- 台灣口語，說人話，不用專業術語，但也不要太過口語
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
6. 禁止出現謾罵「店家」「酒店」等字眼，所有問題來源只能是「黑心經紀」或「經紀人」
7. 禁止出現「姐妹們」「姊妹們」類似這種很不專業的詞語
8. 如果講到比較艱深的術語，例如「壓檔」＝壓薪水 「節薪」＝10分鐘的薪水 需要簡單解釋

【行業術語對照表】
以下是八大行業的專業術語，請在寫作時自然使用，不需要解釋它們的意思：

━━ 薪資排班 ━━
- 酒店合約 ＝ 無限期 但無法律效應 只有在八大行業有效 並且違約更換經紀人需要付費5萬元起
- 一節：台北酒店以 10 分鐘為一個單位
- 節薪：每一節給的薪水，台北便服店或禮服店通常落在 230 到 290 元之間
- 打卡：上班時會給一張卡片，放入打卡機成功打卡後再交給控台
- 報班：帶台會詢問下禮拜有哪幾天可以上班，只報確定能上班的天數
- 門禁：告訴控台今天要在幾點前下班回家
- 一檔：酒店專用上班期間單位，每一個禮拜叫做一檔，薪水會在下一檔時拿到，一個月有四檔
- 壓檔：公司沒有給上一檔的薪水，屬於侵犯公關權益的行為
- 薪水看天數：薪水按上班天數調漲，例如一檔三天班節薪 230，四天班 240，五天班 250
- 薪水直走：不管上幾天班，薪水都是固定的，不會因為直走就變少
- 現領：當天上班當天下班就領薪水，或隔天匯款
- 上卡：來這家店上班，面試通過後取好名字並填好資料
- 下卡：在這家店離職
- 休檔：休息一陣子不上班，但沒有離職

━━ 店家類型 ━━
- 禮服店：商務會館，穿著正式小禮服，強調氣質談吐，服務包含聊天、喝酒、唱歌，互動尺度中等，建議新人先從禮服店磨練
- 小框店／便服店：對素質要求很高，不由客人排排站挑選，而是由幹部帶入包廂，被框機率較高
- 大框店／便服店：酒店業界頂端，進場客人經濟實力極強，核心制度在於全場買斷，客人中意通常直接框到底；有些又被稱作砲店

━━ 絕對拒簽的合約條款 ━━
遇到以下任何一條，立刻離開，不要猶豫：
- 要求簽賣身契或任何形式的人身約束合約
- 要求繳交保證金、押金、服裝費才能上班
- 要求提供身分證正本或讓對方保管證件
- 合約中有違約金條款，且金額高得離譜
- 要求簽署出場同意書或任務相關文件
- 對方不讓妳帶走合約副本或拒絕讓妳看清楚內容
- 要求妳交出手機或限制人身自由

【格式規則】
- 每則開頭單獨一行寫「§1」「§2」...
- 只輸出文章內容，不要加任何說明

【情緒曲線設計】
- 第一則：震撼 → 第二則：同情 → 第三則：憤怒 → 第四則：恐懼 → 第五則：希望＋警惕 → 第六則：強化警惕 → 第七則：信任＋行動呼籲

輸出格式：第一行輸出「主題：{custom_topic}」，空一行後開始輸出貼文內容。
"""
    response = client.models.generate_content(model="gemma-4-31b-it", contents=prompt)
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
        while len(text.encode('utf-8')) > 1500:
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

# ── 主程式 ────────────────────────────────────────────
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

    try:
        print(f"📌 主題：{custom_topic}")
        post_text = generate_post(custom_topic)
        print("貼文內容：\n", post_text)
        post_to_threads(post_text)
        update_status(page_id, "已發")
        print("✅ 完成！")
        send_telegram(f"✅ 帳號B 發文成功！\n主題：{custom_topic}")

    except Exception as e:
        error_msg = f"❌ 帳號B 發文失敗！\n主題：{custom_topic}\n錯誤原因：{str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        raise
