import os
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from .sqlite import DATA_DIR
# 向量数据库存储路径
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
os.makedirs(CHROMA_DIR, exist_ok=True)
# 初始化Chroma客户端
client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)
# 获取或创建集合
knowledge_collection = client.get_or_create_collection(
    name="knowledge_base",
    metadata={"description": "知识库文本向量集合"}
)
# 初始化embedding模型，使用中文效果较好的BGE模型
def get_embeddings():
    model_name = "BAAI/bge-small-zh-v1.5"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}
    embeddings = HuggingFaceBgeEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return embeddings
# 添加文档到向量库
def add_document(doc_id: str, content: str, metadata: dict = None):
    """
    添加文档到向量库
    :param doc_id: 文档ID，对应knowledge表的ID
    :param content: 文档文本内容
    :param metadata: 元数据
    """
    embeddings = get_embeddings()
    vector = embeddings.embed_query(content)
    knowledge_collection.add(
        ids=[str(doc_id)],
        embeddings=[vector],
        documents=[content],
        metadatas=[metadata or {}]
    )
# 搜索相似文档
def search_similar(query: str, top_k: int = 5):
    """
    搜索相似文档
    :param query: 查询文本
    :param top_k: 返回最相似的k个结果
    :return: 相似文档列表
    """
    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    results = knowledge_collection.query(
        query_embeddings=[query_vector],
        n_results=top_k
    )
    return {
        "documents": results["documents"][0] if results["documents"] else [],
        "metadatas": results["metadatas"][0] if results["metadatas"] else [],
        "distances": results["distances"][0] if results["distances"] else []
    }
# 删除文档
def delete_document(doc_id: str):
    """
    从向量库删除文档
    :param doc_id: 文档ID
    """
    try:
        knowledge_collection.delete(ids=[str(doc_id)])
    except Exception as e:
        print(f"删除向量文档失败: {e}")
