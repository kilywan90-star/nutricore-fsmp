from src.security.deidentifier import deidentify_clinical_text, mask_phi


def test_mask_phone_number():
    text = "患者电话13812345678请联系"
    result = mask_phi(text)
    assert "13812345678" not in result
    assert "***" in result


def test_mask_id_card():
    text = "身份证号110101199001011234"
    result = mask_phi(text)
    assert "110101199001011234" not in result


def test_mask_name():
    text = "患者张三，男，50岁"
    result = mask_phi(text)
    assert "张三" not in result


def test_deidentify_preserves_clinical_info():
    text = "患者张三，空腹血糖7.8mmol/L，HbA1c 7.2%，建议调整二甲双胍用量"
    result = deidentify_clinical_text(text)
    assert "7.8mmol/L" in result
    assert "7.2%" in result
    assert "二甲双胍" in result
    assert "张三" not in result


def test_deidentify_handles_empty():
    assert deidentify_clinical_text("") == ""
    assert deidentify_clinical_text(None) == ""
