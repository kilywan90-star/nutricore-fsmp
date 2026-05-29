from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime
from db.sqlite import get_db, Knowledge, DATA_DIR
from core.parser import extract_text_from_file
from db.chroma import add_document
router = APIRouter()
# 上传文件存储目录
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
# Pydantic模型
class KnowledgeResponse(BaseModel):
    id: int
    name: str
    file_type: str
    category: str
    size: int
    status: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
@router.get("/", response_model=List[KnowledgeResponse])
def get_knowledge_list(db: Session = Depends(get_db)):
    """获取知识库文件列表"""
    knowledges = db.query(Knowledge).order_by(Knowledge.created_at.desc()).all()
    return knowledges
@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传文件到知识库"""
    try:
        # 保存文件到本地
        file_ext = os.path.splitext(file.filename)[1].lower()
        file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)
        # 创建数据库记录
        db_knowledge = Knowledge(
            name=file.filename,
            file_path=file_path,
            file_type=file_ext.lstrip("."),
            size=file_size,
            status="indexing"
        )
        db.add(db_knowledge)
        db.commit()
        db.refresh(db_knowledge)
        # 异步处理：提取文本内容并建立索引
        # 这里暂时同步处理，后续改为异步
        try:
            content = extract_text_from_file(file_path, file_ext.lstrip("."))
            db_knowledge.content = content
            db_knowledge.status = "indexed"
            db.commit()
            # 添加到向量库
            add_document(
                doc_id=str(db_knowledge.id),
                content=content,
                metadata={
                    "name": db_knowledge.name,
                    "type": db_knowledge.file_type,
                    "category": db_knowledge.category
                }
            )
        except Exception as e:
            db_knowledge.status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

        return {"status": "success", "data": KnowledgeResponse.from_orm(db_knowledge)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
@router.delete("/{knowledge_id}")
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    """删除知识库文件"""
    knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not knowledge:
        raise HTTPException(status_code=404, detail="文件不存在")
    # 删除本地文件
    try:
        if os.path.exists(knowledge.file_path):
            os.remove(knowledge.file_path)
    except Exception as e:
        print(f"删除本地文件失败: {e}")
    # 删除向量库记录
    from db.chroma import delete_document
    delete_document(str(knowledge_id))
    # 删除数据库记录
    db.delete(knowledge)
    db.commit()
    return {"status": "success", "message": "删除成功"}
