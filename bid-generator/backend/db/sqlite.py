import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
# 获取用户数据目录，根据平台不同选择不同位置
def get_user_data_dir():
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        return os.path.join(appdata, "BidGenerator")
    elif sys.platform == "darwin":
        return os.path.join(os.environ.get("HOME", ""), "Library", "Application Support", "BidGenerator")
    else:
        return os.path.join(os.environ.get("HOME", ""), ".bidgenerator")
# 创建数据目录
DATA_DIR = get_user_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)
# 数据库文件路径
DB_PATH = os.path.join(DATA_DIR, "bidgenerator.db")
# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
# 项目模型
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="项目名称")
    type = Column(String(50), comment="项目类型")
    industry = Column(String(50), comment="所属行业")
    description = Column(Text, comment="项目描述")
    deadline = Column(String(20), comment="投标截止日期")
    status = Column(String(20), default="draft", comment="项目状态：draft/ generating/ completed/ archived")
    bid_content = Column(Text, comment="标书内容")
    requirements = Column(JSON, comment="解析后的招标要求")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
# 知识库模型
class Knowledge(Base):
    __tablename__ = "knowledges"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="文件名称")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_type = Column(String(20), comment="文件类型：pdf/docx/xlsx等")
    category = Column(String(50), default="其他", comment="文件分类")
    size = Column(Integer, comment="文件大小，单位字节")
    status = Column(String(20), default="indexing", comment="状态：indexing/indexed/failed")
    content = Column(Text, comment="提取的文本内容")
    created_at = Column(DateTime, default=datetime.now, comment="上传时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
# 模板模型
class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="模板名称")
    industry = Column(String(50), comment="适用行业")
    type = Column(String(50), comment="模板类型")
    description = Column(Text, comment="模板描述")
    content = Column(JSON, comment="模板内容结构")
    is_builtin = Column(Boolean, default=False, comment="是否是内置模板")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
# 系统配置模型
class Config(Base):
    __tablename__ = "configs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置项键")
    value = Column(Text, comment="配置项值")
    description = Column(String(255), comment="配置项描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    # 初始化内置模板
    init_builtin_templates()
def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def init_builtin_templates():
    """初始化内置模板"""
    from sqlalchemy.orm import Session
    db = SessionLocal()
    try:
        # 检查是否已经有内置模板
        existing = db.query(Template).filter(Template.is_builtin == True).first()
        if existing:
            return
        # 添加内置模板
        templates = [
            Template(
                name="政府采购通用标书模板",
                industry="通用",
                type="政府采购",
                description="适用于各类政府采购项目的通用标书模板，包含商务标、技术标、价格标完整结构",
                is_builtin=True,
                content={}
            ),
            Template(
                name="建筑工程类标书模板",
                industry="建筑工程",
                type="工程建设",
                description="适用于房屋建筑、市政工程等建筑类项目的标书模板",
                is_builtin=True,
                content={}
            ),
            Template(
                name="IT信息化项目标书模板",
                industry="IT/互联网",
                type="服务类",
                description="适用于软件开发、系统集成、信息化建设等IT类项目的标书模板",
                is_builtin=True,
                content={}
            )
        ]
        db.add_all(templates)
        db.commit()
    except Exception as e:
        print(f"初始化内置模板失败: {e}")
        db.rollback()
    finally:
        db.close()
