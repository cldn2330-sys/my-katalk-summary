import json
import os
import requests
from flask import Flask, jsonify, request
import google.generativeai as genai

app = Flask(__name__)

# Render 환경 변수
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KAKAO_ACCESS_TOKEN = os.environ.get("KAKAO_ACCESS_TOKEN", "")

# Gemini SDK 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

messages_store = []

@app.get("/")
def home():
    return "카톡 요약 서버가 클라우드에서 정상 가동 중입니다! 🚀", 200

@app.post("/api/message")
def receive_message():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "JSON 객체가 필요합니다."}), 400

    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"status": "error", "message": "message 값이 필요합니다."}), 400

    messages_store.append({
        "sender": str(data.get("sender", "알 수 없음")).strip() or "알 수 없음",
        "message": message,
    })
    return jsonify({"status": "success", "message": "Saved", "count": len(messages_store)}), 200

def call_gemini_api(prompt_text):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 Render 환경변수에 설정되지 않았습니다.")

    try:
        # SDK를 사용하여 가장 안정적으로 모델 호출
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_text)
        if response and response.text:
            return response.text.strip()
        raise RuntimeError("Gemini 요약 결과가 비어 있습니다.")
    except Exception as e:
        raise RuntimeError(f"Gemini API 오류: {str(e)}")

def send_kakao_memo(summary_text):
    if not KAKAO_ACCESS_TOKEN:
        raise ValueError("KAKAO_ACCESS_TOKEN이 Render 환경변수에 설정되지 않았습니다.")

    template_object = {
        "object_type": "text",
        "text": f"[오늘의 카톡 요약 브리핑]\n\n{summary_text}",
        "link": {"web_url": "https://developers.kakao.com"},
    }
    response = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {KAKAO_ACCESS_TOKEN}"},
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=30,
    )
    try:
        response_data = response.json()
    except ValueError:
        response.raise_for_status()
        raise RuntimeError("카카오 API가 JSON이 아닌 응답을 반환했습니다.")

    if not response.ok:
        detail = response_data.get("msg", "알 수 없는 오류")
        raise RuntimeError(f"카카오 API 오류 ({response.status_code}): {detail}")
    return response_data

def summarize_and_send():
    if messages_store:
        text_to_summarize = "\n".join(
            f"[{item['sender']}] {item['message']}" for item in messages_store
        )
    else:
        text_to_summarize = "오늘 수집된 새로운 카카오톡 메시지가 없습니다."

    prompt = (
        "다음 카카오톡 메시지를 핵심 내용 위주로 한국어 3줄 이내로 요약해 주세요. "
        "중요한 일정, 할 일, 결론이 있으면 포함해 주세요.\n\n"
        f"{text_to_summarize}"
    )
    return send_kakao_memo(call_gemini_api(prompt))

@app.get("/api/test_summary")
def test_summary():
    try:
        result = summarize_and_send()
        return jsonify({"status": "success", "kakao_response": result}), 200
    except (ValueError, RuntimeError, requests.RequestException) as error:
        return jsonify({"status": "error", "details": str(error)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
