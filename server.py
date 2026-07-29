import sqlite3
import datetime
import requests
from flask import Flask, request, jsonify
from google import genai
import schedule
import time
import threading

app = Flask(__name__)

# --- 설정 영역 ---
GEMINI_API_KEY = "406da757547c15c1b7fe132266d05cf3"       # Gemini API 키
KAKAO_ACCESS_TOKEN = "llVyDdjYDlK0w6s-XkihIeuut8cfRnFpAAAAAQoXBi4AAAGfrPR0nlR13198v8Zc" # 카카오 Access Token
DB_NAME = "katalk_messages.db"

# DB 초기화
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            room TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 1. MacroDroid로부터 메시지 수신 API
@app.route('/api/message', methods=['POST'])
def receive_message():
    data = request.json
    sender = data.get('sender')
    message = data.get('message')
    room = data.get('room', sender) # 단톡방이 없으면 발신자로 설정

    if sender and message:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO messages (sender, message, room) VALUES (?, ?, ?)",
                  (sender, message, room))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Invalid data"}), 400

# 2. 하루 동안 쌓인 메시지 Gemini로 요약
def summarize_and_send():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 오늘 쌓인 메시지 조회
    today = datetime.date.today().strftime('%Y-%m-%d')
    c.execute("SELECT room, sender, message FROM messages WHERE date(timestamp) = ?", (today,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("오늘 수집된 메시지가 없습니다.")
        return

    # AI에 전달할 텍스트 구성
    raw_text = ""
    for room, sender, msg in rows:
        raw_text += f"[{room}] {sender}: {msg}\n"

    # Gemini API 호출
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    다음은 오늘 하루 동안 들어온 카카오톡 메시지 내역입니다.
    중요한 일정, 요청사항, 핵심 대화 내용을 중심으로 카테고리별로 알기 쉽게 요약해 주세요.

    [메시지 내역]
    {raw_text}
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    summary = response.text
    send_kakao_me(f"📅 오늘 하루 카톡 요약 ({today})\n\n{summary}")

# 3. 카카오톡 '나와의 채팅'으로 전송
def send_kakao_me(text):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {KAKAO_ACCESS_TOKEN}"
    }
    payload = {
        "template_object": f'{{"object_type": "text", "text": {repr(text)}, "link": {{"web_url": "https://developers.kakao.com"}}}}'
    }
    res = requests.post(url, headers=headers, data=payload)
    print("카톡 전송 결과:", res.status_code)

# 스케줄러: 매일 밤 10시 30분에 요약 실행
def run_schedule():
    schedule.every().day.at("22:30").do(summarize_and_send)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # 스케줄러 쓰레드 실행
    threading.Thread(target=run_schedule, daemon=True).start()
    # 웹 서버 실행 (같은 와이파이 네트워크 내부 접근 가능하도록 0.0.0.0 설정)
    app.run(host='0.0.0.0', port=5000)
  # 루트 경로(/) 접속 시 안내 문구 출력 (맨 왼쪽에 작성)
@app.route('/', methods=['GET'])
def home():
    return "카톡 요약 서버가 클라우드에서 정상 가동 중입니다! 🚀", 200


if __name__ == '__main__':
    # 스케줄러 쓰레드 실행
    threading.Thread(target=run_schedule, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)

@app.route('/api/test_summary', methods=['GET'])
def test_summary():
    summarize_and_send()
    return jsonify({"status": "success", "message": "요약 발송 완료"}), 200
