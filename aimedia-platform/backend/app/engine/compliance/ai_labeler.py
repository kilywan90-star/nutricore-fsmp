"""
AI 内容标识器 —— GB 45438-2025 强制执行。

两类标识:
  显式标识: 用户可感知 — 文本标注、图片水印、视频首帧、音频提示音
  隐式标识: 元数据写入 — 生成属性、服务商编码、内容编号
"""

import hashlib
import json
import time


class AILabeler:
    """AI 生成内容标识注入"""

    PROVIDER_CODE = "AIMEDIA-001"

    def label_text(self, text: str) -> str:
        """文本: 起始+末尾添加标识"""
        prefix = "【AI生成内容】"
        suffix = "\n\n———\n本文由AI辅助生成，经人工审核后发布。"
        return f"{prefix}\n{text}{suffix}"

    def label_image_metadata(self, metadata: dict) -> dict:
        """图片: 元数据写入"""
        labeled = dict(metadata)
        labeled["AIGenerated"] = True
        labeled["AISource"] = self.PROVIDER_CODE
        labeled["AIContentID"] = self._gen_content_id(metadata.get("filename", ""))
        return labeled

    def label_video_overlay(self, duration_seconds: float) -> dict:
        """视频: 返回首帧叠加配置（需前端/转码端执行）"""
        return {
            "overlay_text": "AI生成内容",
            "position": "top-right",
            "duration_seconds": max(2.0, duration_seconds * 0.1),
            "font_size": "5%",
        }

    def label_audio(self, audio_config: dict) -> dict:
        """音频: 摩斯码节奏 + 语音提示"""
        return {
            "morse_pattern": "····",  # H = AI (短长长长短)
            "voice_prompt": "以下内容由AI生成",
            "position": "beginning",
        }

    def inject_hidden_label(self, file_bytes: bytes, content_type: str) -> bytes:
        """隐式标识: 写入文件元数据"""
        meta = json.dumps({
            "AIGenerated": True,
            "Provider": self.PROVIDER_CODE,
            "ContentType": content_type,
            "Timestamp": int(time.time()),
            "Version": "GB45438-2025",
        })
        # PNG/JPEG/Mp4 等不同格式需不同的元数据注入方式，此处返回标记信息
        return file_bytes, meta

    def _gen_content_id(self, seed: str) -> str:
        return hashlib.sha256(f"{seed}{time.time()}".encode()).hexdigest()[:16]
