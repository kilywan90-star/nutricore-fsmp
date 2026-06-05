import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.llm_service import (
    detect_template_intent,
    fill_slots_streaming,
    final_review,
    extract_structured_data,
)

app = FastAPI(title="Ultrasound AI Voice Report Service - Streaming")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

THRESHOLDS = [20, 40, 60, 80, 100, 140, 180, 220, 260, 300]
CONFIDENCE_LOCK = 95


@app.websocket("/api/v1/stream-report")
async def stream_report(ws: WebSocket):
    await ws.accept()
    print("[WS] Accepted")

    accumulated_text = ""
    is_template_locked = False
    locked_template = None
    last_checked_threshold_idx = -1
    last_slot_result = {}

    async def broadcast(event_type: str, payload: dict):
        try:
            await ws.send_json({"type": event_type, **payload})
        except Exception as e:
            print(f"[WS] broadcast error: {e}")

    async def try_template_detect():
        nonlocal last_checked_threshold_idx, is_template_locked, locked_template
        current_len = len(accumulated_text)
        print(f"[WS] detect: len={current_len} locked={is_template_locked}")

        for i, threshold in enumerate(THRESHOLDS):
            if current_len >= threshold and i > last_checked_threshold_idx:
                last_checked_threshold_idx = i
                print(f"[WS] calling LLM intent detect...")
                result = await detect_template_intent(accumulated_text)
                template = result.get("template", "none")
                confidence = result.get("confidence", 0)
                print(f"[WS] intent result: template={template} conf={confidence}")

                if template in (None, "none"):
                    await broadcast("INTENT_PENDING", {
                        "msg": f"已累计{current_len}字，暂未匹配到明确科室，继续聆听中...",
                        "text_length": current_len,
                    })
                    print("[WS] sent INTENT_PENDING (none)")
                    return

                if confidence >= CONFIDENCE_LOCK:
                    is_template_locked = True
                    locked_template = template
                    await broadcast("TEMPLATE_LOCKED", {
                        "template": template,
                        "confidence": confidence,
                        "msg": f"已智能匹配并锁定模板: {template} (置信度: {confidence}%)",
                    })
                    print(f"[WS] sent TEMPLATE_LOCKED {template}")
                    slots = await fill_slots_streaming(accumulated_text, template)
                    last_slot_result.clear()
                    last_slot_result.update(slots)
                    await broadcast("SLOT_UPDATES", {"slots": slots})
                    print("[WS] sent SLOT_UPDATES after lock")
                    return

                await broadcast("INTENT_PENDING", {
                    "msg": f"检测到潜在科室: {template} (置信度: {confidence}%, 尚不足锁定，继续聆听...)",
                    "candidate": template,
                    "confidence": confidence,
                    "text_length": current_len,
                })
                print(f"[WS] sent INTENT_PENDING ({template} {confidence})")
                return

    async def do_streaming_fill():
        nonlocal last_slot_result
        if not is_template_locked or locked_template is None:
            return
        print("[WS] stream fill...")
        slots = await fill_slots_streaming(accumulated_text, locked_template)
        last_slot_result.clear()
        last_slot_result.update(slots)
        await broadcast("SLOT_UPDATES", {"slots": slots})
        print("[WS] sent SLOT_UPDATES")

    try:
        while True:
            raw = await ws.receive_text()
            print(f"[WS] recv: {raw[:80]}")
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "text_update":
                new_text = msg.get("text", "")
                accumulated_text = new_text
                print(f"[WS] text_update len={len(new_text)}")

                if not is_template_locked:
                    await try_template_detect()
                else:
                    await do_streaming_fill()

            elif msg_type == "finish":
                print("[WS] finish requested")
                if is_template_locked and locked_template:
                    slots = await fill_slots_streaming(accumulated_text, locked_template)
                    review = await final_review(slots, locked_template)
                    await broadcast("FINAL_REVIEW", {
                        "template": locked_template,
                        "slots": slots,
                        "review": review,
                    })
                else:
                    await broadcast("FINAL_REVIEW", {
                        "template": None,
                        "slots": last_slot_result,
                        "review": "未能锁定模板，无法进行结构化提取。请重新录制。",
                    })
                print("[WS] closing after finish")
                await ws.close()
                return

            elif msg_type == "reset":
                accumulated_text = ""
                is_template_locked = False
                locked_template = None
                last_checked_threshold_idx = -1
                last_slot_result = {}
                await broadcast("RESET", {"msg": "状态已重置"})

            else:
                await broadcast("ERROR", {"msg": f"未知消息类型: {msg_type}"})

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.close()
        except Exception:
            pass


@app.post("/api/v1/analyze-voice")
async def analyze_voice(
    audio: UploadFile = File(...),
    exam_part: str = Query(..., description="template type: breast / abdominal"),
):
    if not audio:
        return {"is_valid": False, "msg": "音频文件为空"}
    if exam_part == "breast":
        raw_text = "左边乳腺看到一个2公分的低回声结节，边界不清，考虑BI-RADS 4a类。"
    elif exam_part == "abdominal":
        raw_text = "肝脏实质回声增强，形态还是正常的，胆囊壁有些粗糙。"
    else:
        raw_text = "没有识别到特定部位的有效口述内容。"
    structured_data = await extract_structured_data(raw_text, exam_part)
    return {
        "is_valid": True,
        "raw_text": raw_text,
        "exam_part": exam_part,
        "extracted_slots": structured_data,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
