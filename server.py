import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# ================= 설정값 =================
GEMINI_API_KEY = "AQ.Ab8RN6Knppcv6Av2ThW4FdOIagG5mglOrAzvTTHT0bDuH0NsbA"       # Gemini API 키
KAKAO_ACCESS_TOKEN = "GE2WjHb6cdjtwCcr2YvC2rCqe8BU5Q7hAAAAAQoNH9EAAAGfrPY-41R13198v8Zc" # 카카오 Access Token
# ==========================================

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)

# 메시지 저장용 메모리 (임시)
messages_store = []

@app.route('/')
def home():
    return "Kakao Summary Server is running!", 200

# 1. MacroDroid에서 메시지 받는 주소
@app.route('/api/message', methods=['POST'])
def receive_message():
    data = request.json
    if data:
        messages_store.append(data)
        return jsonify({"status": "success", "message": "Saved"}), 200
    return jsonify({"status": "error", "message": "No data"}), 400

# 2. 요약 및 카카오톡 전송 함수
def summarize_and_send():
    if not messages_store:
        text_to_summarize = "오늘 들어온 새로운 메시지가 없습니다."
    else:
        text_to_summarize = "\n".join([f"[{m.get('sender', '알수없음')}] {m.get('message', '')}" for m in messages_store])
    
    # Gemini 요약 생성
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"다음 카카오톡 메시지들을 핵심 위주로 읽기 쉽게 3줄 이내로 요약해줘:\n\n{text_to_summarize}"
    
    response = model.generate_content(prompt)
    summary_text = response.text

    # 카카오톡 나와의 채팅방으로 전송
    kakao_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {KAKAO_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "template_object": f'{{"object_type": "text", "text": "[오늘의 카톡 요약 브리핑]\\n\\n{summary_text}", "link": {{"web_url": "https://developers.kakao.com"}}}}'
    }
    
    res = requests.post(kakao_url, headers=headers, data=payload)
    return res.json()

# 3. 수동 실행 테스트 주소
@app.route('/api/test_summary', methods=['GET'])
def test_summary():
    try:
        result = summarize_and_send()
        return jsonify({"status": "success", "kakao_response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
