from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.llm_service import extract_structured_data

app = FastAPI(title="Ultrasound AI Voice Report Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/analyze-voice")
async def analyze_voice(
    audio: UploadFile = File(...),
    exam_part: str = Query(..., description="The template type, e.g., 'breast' or 'abdominal'")
):
    if not audio:
        return {"is_valid": False, "msg": "音频文件为空"}

    # Mock ASR Step: Simulate speech-to-text for local testing
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
        "extracted_slots": structured_data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
