import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# ==========================================
# 🔑 핵심 설정 영역 (본인의 키값으로 수정해주세요)
# ==========================================
# GEMINI_API_KEY = "여기에_GEMINI_API_키"
# KAKAO_ACCESS_TOKEN = "여기에_카카오_ACCESS_TOKEN"
GEMINI_API_KEY = "AQ.Ab8RN6IM_gYDqPSwr2I903EO1q-rBz03ACy8D3dGbkNvs2w20w"       # Gemini API 키
KAKAO_ACCESS_TOKEN = "GE2WjHb6cdjtwCcr2YvC2rCqe8BU5Q7hAAAAAQoNH9EAAAGfrPY-41R13198v8Zc" # 카카오 Access Token
# ==========================================

# Gemini API 설정
genai.configure(api_key=GEMINI_API_KEY)

# 메시지 수집용 메모리 (임시 저장)
messages_store = []

@app.route('/')
def home():
    return "카톡 요약 서버가 클라우드에서 정상 가동 중입니다! 🚀", 200

# 1. MacroDroid에서 메시지 수신받는 주소
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

# 2. 요약 생성 및 카카오톡 나와의 채팅방 발송 함수
def summarize_and_send():
    if not messages_store:
        text_to_summarize = "오늘 수집된 새로운 카카오톡 메시지가 없습니다."
    else:
        formatted_list = []
        for m in messages_store:
            sender = m.get('sender', '알수없음')
            msg = m.get('message', '')
            formatted_list.append(f"[{sender}] {msg}")
        text_to_summarize = "\n".join(formatted_list)
    
    # Gemini AI 요약 생성
   # model = genai.GenerativeModel('gemini-1.5-flash')
    # model = genai.GenerativeModel('gemini-2.5-flash')
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"다음 카카오톡 메시지들을 핵심 내용 위주로 읽기 쉽게 3줄 이내로 요약해줘:\n\n{text_to_summarize}"
    
    response = model.generate_content(prompt)
    summary_text = response.text if response else "요약 생성 실패"

    # 카카오톡 나와의 채팅방 전송 API 호출
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

# 3. 수동 테스트 실행 주소
@app.route('/api/test_summary', methods=['GET'])
def test_summary():
    try:
        result = summarize_and_send()
        return jsonify({"status": "success", "kakao_response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
