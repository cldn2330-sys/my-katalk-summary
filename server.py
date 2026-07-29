import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# Render Environment Variables에서 키를 읽어옵니다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KAKAO_ACCESS_TOKEN = os.environ.get("KAKAO_ACCESS_TOKEN", "")

# Gemini SDK 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

messages_store = []

@app.route('/')
def home():
    return "카톡 요약 서버가 클라우드에서 정상 가동 중입니다! 🚀", 200

# MacroDroid에서 메세지를 수신받는 주소
@app.route('/api/message', methods=['POST'])
def receive_message():
    try:
        data = request.json
        if data:
            messages_store.append(data)
            return jsonify({"status": "success", "message": "Saved"}), 200
        return jsonify({"status": "error", "message": "No data received"}), 400
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

# Gemini 공식 SDK 사용 요약 함수
def call_gemini_api(prompt_text):
    # 가장 기본적이고 안정적인 무료 티어 모델
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt_text)
    
    if response and response.text:
        return response.text
    return "요약 결과를 생성하지 못했습니다."

def summarize_and_send():
    if not messages_store:
        text_to_summarize = "오늘 수집된 새로운 카카오톡 메시지가 없습니다."
    else:
        text_to_summarize = "\n".join([f"[{m.get('sender', '알수없음')}] {m.get('message', '')}" for m in messages_store])
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 Render 환경변수에 설정되지 않았습니다.")

    prompt = f"다음 카카오톡 메시지들을 핵심 내용 위주로 읽기 쉽게 3줄 이내로 요약해줘:\n\n{text_to_summarize}"
    
    # Gemini 요약 생성
    summary_text = call_gemini_api(prompt)

    # 카카오톡 나와의 채팅방 전송 API
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

@app.route('/api/test_summary', methods=['GET'])
def test_summary():
    try:
        result = summarize_and_send()
        return jsonify({"status": "success", "kakao_response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
