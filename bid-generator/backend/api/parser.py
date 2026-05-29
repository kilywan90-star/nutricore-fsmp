from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime
from db.sqlite import get_db, Project
from core.parser import extract_text_from_file
router = APIRouter()
@router.post("/upload_tender")
async def upload_tender_file(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传招标文件并解析"""
    # 检查项目是否存在
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"status": "error", "message": "项目不存在"}
    try:
        # 保存上传的文件
        file_ext = os.path.splitext(file.filename)[1].lower()
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "tender")
        os.makedirs(upload_dir, exist_ok=True)
        file_name = f"{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # 提取文本内容
        content = extract_text_from_file(file_path, file_ext.lstrip("."))
        # 后续添加AI解析招标要求的功能
        return {
            "status": "success",
            "data": {
                "content_length": len(content),
                "content_preview": content[:500] + "..." if len(content) > 500 else content
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"解析失败: {str(e)}"}
