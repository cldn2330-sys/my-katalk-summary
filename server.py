import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# Render의 Environment Variables에서 키를 불러옵니다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
KAKAO_ACCESS_TOKEN = os.environ.get("KAKAO_ACCESS_TOKEN", "YOUR_KAKAO_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
messages_store = []

@app.route('/')
def home():
    return "Kakao Summary Server is Running!", 200

@app.route('/api/message', methods=['POST'])
def receive_message():
    data = request.json
    if data:
        messages_store.append(data)
        return jsonify({"status": "success", "message": "Saved"}), 200
    return jsonify({"status": "error", "message": "No data"}), 400

def summarize_and_send():
    if not messages_store:
        text_to_summarize = "오늘 수집된 메시지가 없습니다. 수동 테스트 진행 중입니다."
    else:
        text_to_summarize = "\n".join([f"[{m.get('sender', '알수없음')}] {m.get('message', '')}" for m in messages_store])
    
    # 무료 티어 쿼터 제한이 없는 가장 안정적인 표준 모델명 사용
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"다음 카카오톡 메시지들을 핵심 위주로 읽기 쉽게 3줄 이내로 요약해줘:\n\n{text_to_summarize}"
    
    response = model.generate_content(prompt)
    summary_text = response.text if response else "요약 생성 실패"

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
