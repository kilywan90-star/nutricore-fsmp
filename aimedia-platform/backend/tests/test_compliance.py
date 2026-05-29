"""Compliance engine unit tests."""

import pytest
from app.engine.compliance.ad_detector import AdDetector
from app.engine.compliance.privacy_masker import PrivacyMasker


class TestAdDetector:
    def setup_method(self):
        self.detector = AdDetector()

    def test_guarantee_words_blocked(self):
        findings = self.detector.detect(
            "使用本方案可100%治愈糖尿病，确保永不复发"
        )
        assert len(findings) > 0
        assert any(f.rule_id == "AD001" for f in findings)

    def test_superlative_blocked(self):
        findings = self.detector.detect(
            "我院拥有全国最先进的CT设备，排名第一"
        )
        assert any(f.rule_id == "AD002" for f in findings)

    def test_case_promotion_blocked(self):
        findings = self.detector.detect(
            "真实案例：张先生在我院就诊后康复效果显著"
        )
        assert any(f.rule_id == "AD005" for f in findings)

    def test_normal_knowledge_passes(self):
        findings = self.detector.detect(
            "高血压患者应注意低盐饮食，每日食盐摄入量不超过6克"
        )
        assert len(findings) == 0


class TestPrivacyMasker:
    def setup_method(self):
        self.masker = PrivacyMasker()

    def test_id_card_detected(self):
        findings = self.masker.detect("ID: 320102199001011234, registered at hospital")
        assert any(f.rule_id == "PRV001" for f in findings)

    def test_phone_detected(self):
        findings = self.masker.detect("Contact: 13812345678")
        assert any(f.rule_id == "PRV002" for f in findings)

    def test_normal_text_passes(self):
        findings = self.masker.detect(
            "Patients should measure blood pressure twice a week and record it in a health diary."
        )
        assert len(findings) == 0

    def test_mask_phone(self):
        masked = self.masker.mask("Phone: 13812345678, call me")
        assert "138****5678" in masked

    def test_mask_id_card(self):
        masked = self.masker.mask("ID: 320102199001011234")
        assert "****" in masked
