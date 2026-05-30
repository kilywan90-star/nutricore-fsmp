"""Tests for HL7 v2 message parser — ADT, ORU, ORM."""

import pytest
from src.adapters.hl7_parser import HL7Parser


# ---------------------------------------------------------------------------
# Test 1: ADT^A01 admission message
# ---------------------------------------------------------------------------

def test_adt_a01_parsing():
    """Parse a standard ADT^A01 admit message with pipe-and-hat encoding."""
    # Build PV1 with exactly 44 fields (PV1-44 = Admit Date/Time)
    pv1_fields = [""] * 45
    pv1_fields[0] = "PV1"
    pv1_fields[1] = "1"
    pv1_fields[2] = "I"
    pv1_fields[3] = "3E^301^1^^General Hospital"
    pv1_fields[7] = "0045^李^医生"
    pv1_fields[44] = "20260530080000"
    pv1 = "|".join(pv1_fields)

    message = (
        "MSH|^~\\&|HIS|General Hospital|EHR|DigitalDoctor|20260530080000||ADT^A01|MSG0001|P|2.5\r"
        "EVN|A01|20260530080000\r"
        "PID|1||12345^^^MRN||张^三||19800115|M|||北京市朝阳区\r"
        + pv1
    )

    result = HL7Parser.parse_adt(message)
    assert result["patient_id"] == "12345"
    assert result["name"] == "张三"
    assert result["gender"] == "male"
    assert result["birth_year"] == 1980
    assert result["birth_date"] == "19800115"
    assert result["admission_date"] == "20260530080000"
    assert result["attending_doctor"] == "李医生"


# ---------------------------------------------------------------------------
# Test 2: ADT^A08 patient update
# ---------------------------------------------------------------------------

def test_adt_a08_parsing():
    """Parse an ADT^A08 update message."""
    message = (
        "MSH|^~\\&|HIS|General Hospital|EHR|DigitalDoctor|20260530140000||ADT^A08|MSG0002|P|2.5\r"
        "EVN|A08|20260530140000\r"
        "PID|1||67890^^^MRN||王^秀英||19650722|F|||上海市浦东新区\r"
        "PV1|1|O|2W^202^1^^General Hospital||||0012^赵^医生|||||||||||A||||||||||||||||||20260530140000"
    )

    result = HL7Parser.parse_adt(message)
    assert result["patient_id"] == "67890"
    assert result["name"] == "王秀英"
    assert result["gender"] == "female"
    assert result["birth_year"] == 1965
    assert result["birth_date"] == "19650722"
    assert result["attending_doctor"] == "赵医生"


# ---------------------------------------------------------------------------
# Test 3: ORU^R01 lab result with glucose
# ---------------------------------------------------------------------------

def test_oru_r01_glucose_result():
    """Parse an ORU^R01 lab result containing a glucose observation."""
    message = (
        "MSH|^~\\&|LIS|General Hospital Lab|EHR|DigitalDoctor|20260530090000||ORU^R01|MSG0003|P|2.5\r"
        "PID|1||12345^^^MRN||张^三||19800115|M\r"
        "OBR|1||LAB001|2345-7^Glucose^LOINC|||20260530084500\r"
        "OBX|1|NM|2345-7^Glucose||8.5|mmol/L|3.9-6.1|H|||F|||20260530084500"
    )

    result = HL7Parser.parse_oru(message)
    assert result["patient_id"] == "12345"
    assert result["order_number"] == "LAB001"

    observations = result["observations"]
    assert len(observations) == 1
    obs = observations[0]
    assert obs["test_code"] == "2345-7"
    assert obs["test_name"] == "Glucose"
    assert obs["result_value"] == 8.5
    assert obs["unit"] == "mmol/L"
    assert obs["reference_range"] == "3.9-6.1"
    assert obs["abnormal_flag"] == "H"
    assert obs["result_date"] == "20260530084500"


# ---------------------------------------------------------------------------
# Test 4: ORM^O01 medication order
# ---------------------------------------------------------------------------

def test_orm_o01_medication_order():
    """Parse an ORM^O01 medication order message."""
    message = (
        "MSH|^~\\&|CPOE|General Hospital|Pharmacy|DigitalDoctor|20260530100000||ORM^O01|MSG0004|P|2.5\r"
        "PID|1||12345^^^MRN||张^三||19800115|M\r"
        "ORC|NW|ORD001|||E||||20260530100000|||0045^李^医生\r"
        "RXO|0043-0488-10^二甲双胍^RxNorm|500||mg||bid|餐后口服|口服"
    )

    result = HL7Parser.parse_orm(message)
    assert result["patient_id"] == "12345"

    orders = result["medication_orders"]
    assert len(orders) == 1
    order = orders[0]
    assert order["order_number"] == "ORD001"
    assert order["drug_code"] == "0043-0488-10"
    assert order["drug_name"] == "二甲双胍"
    assert "500" in order["dose"]
    assert order["route"] == "口服"
    assert order["ordering_doctor"] == "李医生"


# ---------------------------------------------------------------------------
# Test 5: Message type detection
# ---------------------------------------------------------------------------

def test_detect_message_type():
    """detect_message_type should correctly identify all supported HL7 types."""

    adt_msg = (
        "MSH|^~\\&|HIS|Hospital|EHR|DD|20260530080000||ADT^A01|MSG01|P|2.5\r"
        "EVN|A01|20260530080000\r"
        "PID|1||12345^^^MRN"
    )
    assert HL7Parser.detect_message_type(adt_msg) == "ADT^A01"

    oru_msg = (
        "MSH|^~\\&|LIS|Lab|EHR|DD|20260530080000||ORU^R01|MSG02|P|2.5\r"
        "PID|1||12345"
    )
    assert HL7Parser.detect_message_type(oru_msg) == "ORU^R01"

    orm_msg = (
        "MSH|^~\\&|CPOE|Hospital|Pharm|DD|20260530080000||ORM^O01|MSG03|P|2.5\r"
        "PID|1||12345"
    )
    assert HL7Parser.detect_message_type(orm_msg) == "ORM^O01"

    assert HL7Parser.detect_message_type("garbage data") == "UNKNOWN"
    assert HL7Parser.detect_message_type("") == "UNKNOWN"
