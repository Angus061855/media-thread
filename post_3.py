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

# ── Telegram 通知 ─────────────────────────────────────
def send_telegram(message):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message},
        timeout=30
    )

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
        res = requests.post(url, headers=headers, json=payload, timeout=30).json()
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
- 所有問題的來源只有一個：黑心經紀人，跟店家無關，不要提店家

【文章結構】（5到7則，依內容自行決定幾則最合適）

- 第一則：衝擊性開場，打破常見認知，製造懸念，引發好奇
公式：
- 拋出一個常見認知或問題
- 立即用反轉句推翻它
- 製造懸念，但不立刻揭曉答案
範例句型：
「大部分人以為 [常見認知]，但這個答案其實 [反轉]」
「我花了 [時間/金錢]，才從 [權威角色] 口中聽到 [顛覆性觀點]」
「[權威角色] 突然說，[出乎意料的結論]」
關鍵：
- 第一句必須能獨立成立，吸引滑手機的人停下來
- 不要在開場就給答案，保持神秘感

- 第二則：具體案例故事，帶出真實情境
公式：
- 用時間點開場，交代背景
- 帶出人物，說明她遇到什麼狀況
- 用對話推進，讓讀者感覺身歷其境
範例句型：
「上個月，有個小姐跑來找我，她說 [遭遇]」
「三個月前，有個女生去找別的經紀，後來跑來找我，她說 [遭遇]」
「她說她那時候根本不知道 [問題所在]，因為 [原因]」
關鍵：
- 我的角色是幫助她、給她建議的人，不是害她的人
- 黑心經紀才是問題來源，不要讓我的角色有任何負面行為
- 要有具體時間點、對話內容、細節描述

- 第三則：深化觀點，延續案例，說明後果與心情
公式：
- 延續第二則的故事，說明事情後來怎麼了
- 描述她的心理狀態與情緒
- 點出這件事的嚴重性
範例句型：
「她跟我說，哥我現在真的很後悔，因為 [原因]」
「她說她現在每天都 [心理狀態]，怕 [後果]」
「後來她才發現，[事情的真相]」
關鍵：
- 情緒要真實，不要誇張
- 讓讀者對她產生同情，同時對黑心經紀感到憤怒

- 第四則：解釋現象背後的原因和機制
公式：
- 說明為什麼這種事會一直發生
- 點出黑心經紀的操作手法或邏輯
- 讓讀者理解這不是個案，是系統性問題
範例句型：
「這種事會一直發生，原因其實很簡單，[原因]」
「黑心經紀之所以敢這樣做，是因為 [機制]」
「很多女生不知道的是，[行業潛規則或黑幕]」
關鍵：
- 批評對象只能是黑心經紀，不要提店家
- 要有具體的機制說明，不能只是情緒性批評

- 第五則：實用建議或行動指南
公式：
- 直接給出可以執行的步驟或判斷標準
- 越具體越好，最好有數字或條件
- 讓讀者知道遇到這種情況該怎麼辦
範例句型：
「如果妳遇到 [情況]，第一件事就是 [行動]」
「判斷一個經紀有沒有問題，最簡單的方法是 [方法]」
「有幾件事妳一定要先確認：[條列清單]」
關鍵：
- 建議要實際可行，不要太抽象
- 讀者看完要有「我知道該怎麼做了」的感覺

- 第六則：第二個案例或強化論點
公式：
- 帶出另一個類似但角度不同的案例
- 或是用數據、對比來強化前面說的論點
- 讓讀者感受到這真的很普遍
範例句型：
「同樣的事，我還遇過另一個版本，[案例]」
「不只她，我身邊至少有 [數量] 個小姐遇過一樣的事」
「跟她相比，另一個小姐的狀況更慘，因為 [原因]」
關鍵：
- 案例細節要和第二則不同，不要重複
- 目的是讓讀者覺得「這真的很常見，我要小心」

- 第七則：收尾昇華，引導留言或私訊
公式：
- 從個案拉高到更大的視角或價值觀
- 給讀者一個帶走的核心觀念
- 引導有需要的人來找我
範例句型：
「做這行七年，我看過太多這種事，[感悟]」
「妳值得被好好對待，這不是理所當然，而是 [觀點]」
「如果妳現在也有類似的困惑，可以直接私訊我，[承諾]」
關鍵：
- 不要用「姐妹們」開頭
- 結尾要有溫度，不要說教
- 讓讀者覺得我是真的在幫她，不是在賣東西


【字數規則】每則嚴格控制在 200-280 個中文字以內
- 寧可寫少，絕對不要超過 280 字
- 一行不超過25個字 超過可以換行接著寫
- 同一個概念的句子不空行，直接換行接著寫
- 只有在概念完全切換時才空一行
- 禁止每句話後面都空行
- 上班就說上班，或是來八大行業上班，不要說進場什麼的

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
1. 【絕對禁止】使用任何人名、英文名、中文名、暱稱，一律只能用「有個小姐」「有個女生」「她」代替，違反此規則整篇作廢
2. 禁止使用：「——」、任何引用來源符號、emoji、粗體、斜體
3. 標點符號全部使用全形（，。？！：）
4. 禁止 AI 感用語：他笑著搖搖頭、我愣住了、他苦笑著說、頓了頓、深吸一口氣、若有所思、眼神黯淡下來
5. 禁止句型：「不是⋯而是⋯」「更扯的是」「意味著」「在此情境下」「我們可以觀察到」
6. 禁止出現謾罵「店家」「酒店」等字眼，所有問題來源只能是「黑心經紀」或「經紀人」
7. 禁止出現「姐妹們」「姊妹們」「妹子」「進場」類似這種很不專業的詞語
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

【格式規則 ── 非常重要】
- 直接輸出文章內容，不要用任何 codeblock 包起來
- 每則開頭單獨一行寫「§1」「§2」「§3」...（§符號後面緊接數字，中間絕對不可有空格）
- §標記前後不能有任何其他符號、標點、空格、星號
- 只輸出文章內容，不要加任何說明、標題、編號
- 禁止在文章中出現 ---、***、** 等任何 Markdown 符號

【情緒曲線設計】
- 第一則：震撼 → 第二則：同情 → 第三則：憤怒 → 第四則：恐懼 → 第五則：希望＋警惕 → 第六則：強化警惕 → 第七則：信任＋行動呼籲

輸出格式：第一行輸出「主題：[主題內容]」，空一行後開始輸出貼文內容。
"""

    for attempt in range(3):
        try:
            print(f"🤖 第 {attempt+1} 次呼叫 Gemini...")
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options={"timeout": 300000}
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = response.text.strip()
            cleaned = clean_text(raw)

            # ── 發布前檢查：若有人名則重試 ──
            if contains_person_name(cleaned):
                print(f"⚠️ 偵測到人名，第 {attempt+1} 次重試...")
                if attempt < 2:
                    time.sleep(10)
                    continue
                else:
                    raise Exception("Gemini 持續生成人名，已超過重試次數")

            return cleaned
        except Exception as e:
            print(f"第 {attempt+1} 次失敗：{e}")
            if attempt < 2:
                print("等待 30 秒後重試...")
                time.sleep(30)
            else:
                raise

def contains_person_name(text):
    """
    偵測是否含有人名（英文名或中文人名模式）
    英文大寫開頭單字（非句首）視為潛在人名
    """
    # 偵測英文人名：單獨大寫英文單字（如 Katie、Amy、Lisa）
    english_names = re.findall(r'(?<![.!?。！？\n])\b[A-Z][a-z]{1,10}\b', text)
    if english_names:
        print(f"⚠️ 偵測到疑似英文人名：{english_names}")
        return True
    return False

def extract_topic(post_text):
    for line in post_text.strip().split("\n"):
        if line.startswith("主題："):
            return line.replace("主題：", "").strip()
    return "未知主題"

def clean_text(text):
    # 移除 Gemini 可能產生的 --- 分隔線（各種變體）
    text = re.sub(r'\n?-{2,}\n?', '\n', text)
    # 移除 *** 或 ** 粗體標記
    text = re.sub(r'\*{2,}', '', text)
    # 移除單個 * 斜體標記（不影響中文）
    text = re.sub(r'(?<!\*)\*(?!\*)', '', text)
    # 移除引用符號 >
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # 移除多餘空白行（超過兩個換行壓縮成兩個）
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 清理每行行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()

def truncate_to_chars(text, max_chars=480):
    """依照字元數截斷，保留完整句子"""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_break = max(
        truncated.rfind('。'),
        truncated.rfind('！'),
        truncated.rfind('？'),
        truncated.rfind('\n')
    )
    if last_break > max_chars * 0.7:
        return truncated[:last_break + 1]
    return truncated

def split_posts(content):
    """
    切割 §1 §2 ... 段落，支援各種格式變體：
    §1 / § 1 / §１ / **§1** 等
    """
    # 統一清除 § 前後可能的星號或空白
    content = re.sub(r'\*{0,3}\s*§\s*([０-９\d]+)\s*\*{0,3}', r'\n§SPLIT§\1\n', content)
    parts = content.split('\n§SPLIT§')
    posts = []
    for part in parts:
        # 去掉段落編號那一行
        lines = part.split('\n')
        # 第一行是數字，跳過
        if lines and re.match(r'^[０-９\d]+$', lines[0].strip()):
            lines = lines[1:]
        text = '\n'.join(lines).strip()
        if text:
            posts.append(text)
    return posts

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

    posts = split_posts(content)

    if len(posts) < 3:
        raise Exception(
            f"段落切割異常，只切出 {len(posts)} 則，請檢查 Gemini 輸出格式。\n"
            f"原始內容前500字：\n{content[:500]}"
        )

    last_published_id = ""
    first_published_id = ""

    for i, text in enumerate(posts):
        text = clean_text(text)
        text = text.replace("\\n", "\n")
        text = truncate_to_chars(text, max_chars=480)

        if not text:
            print(f"⚠️ 第 {i+1} 則內容為空，跳過")
            continue

        print(f"🚀 建立第 {i+1} 則 container（{len(text)} 字元）...")
        create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        data = {
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_TOKEN
        }
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

        last_published_id = pub_res["id"]
        if i == 0:
            first_published_id = last_published_id

        print(f"✅ 第 {i+1} 則發布成功：{last_published_id}")
        time.sleep(8)

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
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    print("Notion 回應：", res.status_code)

# ── 主程式 ────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print("=== 自動生成模式 ===")
        used_topics = get_used_topics()
        print(f"共 {len(used_topics)} 個已用主題")
        post_text = generate_post(used_topics)
        print("貼文內容：\n", post_text)
        topic = extract_topic(post_text)
        print("📌 主題：", topic)
        post_to_threads(post_text)
        save_to_notion(topic, post_text)
        print("✅ 完成！")
        send_telegram(f"✅ 自動發文成功！\n主題：{topic}")

    except Exception as e:
        error_msg = f"❌ 發文失敗！\n錯誤原因：{str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        raise
