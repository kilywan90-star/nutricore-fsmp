"""FHIR R4 test data — realistic Chinese patient and observation samples.

Provides sample Patient, Observation, and Bundle resources for testing
FHIR import/export without a real FHIR server.
"""

from datetime import date, datetime


def load_sample_patients() -> list[dict]:
    """Return 10 FHIR R4 Patient resources with realistic Chinese patient data."""
    return [
        {
            "resourceType": "Patient",
            "id": "fh-pat-0001",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "BJ-20240001"}],
            "name": [{"use": "official", "family": "李", "given": ["建国"]}],
            "gender": "male",
            "birthDate": "1965-03-15",
            "address": [{"city": "北京市", "district": "朝阳区"}],
            "telecom": [{"system": "phone", "value": "13800138001"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2018-05-20"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 7.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0002",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "SH-20240002"}],
            "name": [{"use": "official", "family": "王", "given": ["秀英"]}],
            "gender": "female",
            "birthDate": "1958-07-22",
            "address": [{"city": "上海市", "district": "浦东新区"}],
            "telecom": [{"system": "phone", "value": "13900139002"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2015-11-03"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 7.5},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0003",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "GZ-20240003"}],
            "name": [{"use": "official", "family": "张", "given": ["伟强"]}],
            "gender": "male",
            "birthDate": "1972-01-08",
            "address": [{"city": "广州市", "district": "天河区"}],
            "telecom": [{"system": "phone", "value": "13700137003"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2020-02-14"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 6.5},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0004",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "SZ-20240004"}],
            "name": [{"use": "official", "family": "刘", "given": ["芳梅"]}],
            "gender": "female",
            "birthDate": "1968-09-30",
            "address": [{"city": "深圳市", "district": "南山区"}],
            "telecom": [{"system": "phone", "value": "13600136004"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2010-08-10"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 7.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0005",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "CD-20240005"}],
            "name": [{"use": "official", "family": "陈", "given": ["志远"]}],
            "gender": "male",
            "birthDate": "1980-12-25",
            "address": [{"city": "成都市", "district": "武侯区"}],
            "telecom": [{"system": "phone", "value": "13500135005"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2023-01-15"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 7.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0006",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "WH-20240006"}],
            "name": [{"use": "official", "family": "杨", "given": ["雪梅"]}],
            "gender": "female",
            "birthDate": "1963-05-18",
            "address": [{"city": "武汉市", "district": "洪山区"}],
            "telecom": [{"system": "phone", "value": "13400134006"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2008-04-22"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 8.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0007",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "NJ-20240007"}],
            "name": [{"use": "official", "family": "赵", "given": ["鹏飞"]}],
            "gender": "male",
            "birthDate": "1955-11-02",
            "address": [{"city": "南京市", "district": "鼓楼区"}],
            "telecom": [{"system": "phone", "value": "13300133007"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2005-06-30"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 8.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0008",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "HZ-20240008"}],
            "name": [{"use": "official", "family": "黄", "given": ["婉婷"]}],
            "gender": "female",
            "birthDate": "1975-06-14",
            "address": [{"city": "杭州市", "district": "西湖区"}],
            "telecom": [{"system": "phone", "value": "13200132008"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2019-09-01"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 6.5},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0009",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "TJ-20240009"}],
            "name": [{"use": "official", "family": "周", "given": ["建国"]}],
            "gender": "male",
            "birthDate": "1960-02-28",
            "address": [{"city": "天津市", "district": "和平区"}],
            "telecom": [{"system": "phone", "value": "13100131009"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2012-03-15"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 7.0},
            ],
        },
        {
            "resourceType": "Patient",
            "id": "fh-pat-0010",
            "identifier": [{"system": "urn:oid:2.16.156.10011.1.1", "value": "CQ-20240010"}],
            "name": [{"use": "official", "family": "吴", "given": ["雅文"]}],
            "gender": "female",
            "birthDate": "1985-10-10",
            "address": [{"city": "重庆市", "district": "渝中区"}],
            "telecom": [{"system": "phone", "value": "13000130010"}],
            "extension": [
                {"url": "http://example.org/fhir/StructureDefinition/diabetes-type", "valueString": "2型糖尿病"},
                {"url": "http://example.org/fhir/StructureDefinition/diagnosis-date", "valueDate": "2021-07-20"},
                {"url": "http://example.org/fhir/StructureDefinition/hba1c-target", "valueDecimal": 6.5},
            ],
        },
    ]


def load_sample_observations() -> list[dict]:
    """Return 50 FHIR R4 Observation resources for glucose, HbA1c, lipids, renal.

    Distributed across 10 patients with realistic values.
    """
    today = date.today().isoformat()
    observations: list[dict] = []

    # ── Glucose observations (20) ────────────────────────────────────────────
    glucose_data = [
        ("fh-pat-0001", 5.8, f"{today}T06:30:00Z", "fasting"),
        ("fh-pat-0001", 8.5, f"{today}T10:30:00Z", "postprandial"),
        ("fh-pat-0002", 9.2, f"{today}T07:00:00Z", "fasting"),
        ("fh-pat-0002", 12.1, f"{today}T11:00:00Z", "postprandial"),
        ("fh-pat-0003", 5.2, f"{today}T06:45:00Z", "fasting"),
        ("fh-pat-0003", 7.0, f"{today}T10:15:00Z", "postprandial"),
        ("fh-pat-0004", 7.8, f"{today}T07:15:00Z", "fasting"),
        ("fh-pat-0004", 10.3, f"{today}T11:30:00Z", "postprandial"),
        ("fh-pat-0005", 8.9, f"{today}T06:50:00Z", "fasting"),
        ("fh-pat-0005", 13.2, f"{today}T10:45:00Z", "postprandial"),
        ("fh-pat-0006", 11.0, f"{today}T07:10:00Z", "fasting"),
        ("fh-pat-0006", 15.5, f"{today}T11:15:00Z", "postprandial"),
        ("fh-pat-0007", 6.3, f"{today}T06:30:00Z", "fasting"),
        ("fh-pat-0007", 9.0, f"{today}T10:00:00Z", "postprandial"),
        ("fh-pat-0008", 4.8, f"{today}T07:00:00Z", "fasting"),
        ("fh-pat-0008", 6.5, f"{today}T10:30:00Z", "postprandial"),
        ("fh-pat-0009", 5.5, f"{today}T06:40:00Z", "fasting"),
        ("fh-pat-0009", 7.8, f"{today}T10:20:00Z", "postprandial"),
        ("fh-pat-0010", 6.1, f"{today}T07:05:00Z", "fasting"),
        ("fh-pat-0010", 8.0, f"{today}T10:35:00Z", "postprandial"),
    ]

    for i, (pat_id, value, dt, measure_type) in enumerate(glucose_data):
        observations.append({
            "resourceType": "Observation",
            "id": f"fh-obs-glc-{i:04d}",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "2345-7", "display": "Glucose [Moles/volume] in Blood"},
                    {"text": "血糖" if measure_type == "fasting" else "餐后血糖"},
                ],
                "text": "空腹血糖" if measure_type == "fasting" else "餐后2h血糖",
            },
            "subject": {"reference": f"Patient/{pat_id}"},
            "effectiveDateTime": dt,
            "valueQuantity": {"value": value, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
            "referenceRange": [
                {"low": {"value": 3.9, "unit": "mmol/L"}, "high": {"value": 6.1, "unit": "mmol/L"}}
            ] if measure_type == "fasting" else [
                {"low": {"value": 3.9, "unit": "mmol/L"}, "high": {"value": 7.8, "unit": "mmol/L"}}
            ],
            "interpretation": [{"coding": [{"code": "H", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"}]}] if value > 7.0 else [],
        })

    # ── HbA1c observations (10) ──────────────────────────────────────────────
    hba1c_data = [
        ("fh-pat-0001", 6.8, today),
        ("fh-pat-0002", 9.5, today),
        ("fh-pat-0003", 5.7, today),
        ("fh-pat-0004", 7.2, today),
        ("fh-pat-0005", 8.9, today),
        ("fh-pat-0006", 10.5, today),
        ("fh-pat-0007", 6.9, today),
        ("fh-pat-0008", 5.6, today),
        ("fh-pat-0009", 6.2, today),
        ("fh-pat-0010", 6.5, today),
    ]

    for i, (pat_id, value, dt) in enumerate(hba1c_data):
        observations.append({
            "resourceType": "Observation",
            "id": f"fh-obs-a1c-{i:04d}",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
                    {"text": "糖化血红蛋白"},
                ],
                "text": "糖化血红蛋白(HbA1c)",
            },
            "subject": {"reference": f"Patient/{pat_id}"},
            "effectiveDateTime": f"{dt}T08:00:00Z",
            "valueQuantity": {"value": value, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"},
            "referenceRange": [
                {"low": {"value": 4.0, "unit": "%"}, "high": {"value": 6.0, "unit": "%"}}
            ],
            "interpretation": [{"coding": [{"code": "H", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"}]}] if value > 6.0 else [],
        })

    # ── Lipid panel observations (10) ────────────────────────────────────────
    lipid_data = [
        # pat_id, tc, ldl, hdl, tg, date
        ("fh-pat-0001", 5.2, 3.2, 1.1, 1.8),
        ("fh-pat-0002", 6.5, 4.5, 0.9, 3.2),
        ("fh-pat-0004", 5.8, 3.8, 1.0, 2.5),
        ("fh-pat-0006", 7.0, 5.0, 0.8, 4.0),
        ("fh-pat-0008", 4.8, 2.6, 1.4, 1.2),
    ]

    obs_idx = len(observations)
    for i, (pat_id, tc, ldl, hdl, tg) in enumerate(lipid_data):
        lipid_items = [
            ("2093-3", "Cholesterol", "总胆固醇(TC)", tc),
            ("13457-7", "LDL Cholesterol", "低密度脂蛋白(LDL-C)", ldl),
            ("2085-9", "HDL Cholesterol", "高密度脂蛋白(HDL-C)", hdl),
            ("2571-8", "Triglyceride", "甘油三酯(TG)", tg),
        ]
        for j, (loinc, loinc_display, text, value) in enumerate(lipid_items):
            observations.append({
                "resourceType": "Observation",
                "id": f"fh-obs-lip-{i * 4 + j:04d}",
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": loinc, "display": f"{loinc_display} [Moles/volume] in Blood"}],
                    "text": text,
                },
                "subject": {"reference": f"Patient/{pat_id}"},
                "effectiveDateTime": f"{today}T08:00:00Z",
                "valueQuantity": {"value": value, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
            })

    # ── Renal function observations (10) ─────────────────────────────────────
    renal_data = [
        # pat_id, creatinine, bun, egfr, uacr
        ("fh-pat-0001", 88, 5.2, 92, 15),
        ("fh-pat-0002", 150, 8.5, 48, 120),
        ("fh-pat-0004", 95, 6.0, 78, 45),
        ("fh-pat-0006", 180, 10.2, 35, 250),
        ("fh-pat-0007", 102, 6.5, 72, 30),
    ]

    for i, (pat_id, cr, bun, egfr, uacr) in enumerate(renal_data):
        renal_items = [
            ("2160-0", "肌酐(Cr)", "umol/L", cr),
            ("3094-0", "尿素(BUN)", "mmol/L", bun),
            ("62238-1", "eGFR", "mL/min/1.73m2", egfr),
            ("9318-7", "尿微量白蛋白/肌酐比(UACR)", "mg/g", uacr),
        ]
        for j, (loinc, text, unit, value) in enumerate(renal_items):
            observations.append({
                "resourceType": "Observation",
                "id": f"fh-obs-ren-{i * 4 + j:04d}",
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": loinc}],
                    "text": text,
                },
                "subject": {"reference": f"Patient/{pat_id}"},
                "effectiveDateTime": f"{today}T08:30:00Z",
                "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit},
            })

    return observations


def load_sample_bundle() -> dict:
    """Return a complete FHIR Bundle with patients + observations for bulk import testing."""
    patients = load_sample_patients()
    observations = load_sample_observations()

    entries: list[dict] = []

    for p in patients:
        pid = p["id"]
        entries.append({
            "fullUrl": f"urn:uuid:{pid}",
            "resource": p,
            "request": {"method": "PUT", "url": f"Patient/{pid}"},
        })

    for obs in observations:
        oid = obs["id"]
        entries.append({
            "fullUrl": f"urn:uuid:{oid}",
            "resource": obs,
            "request": {"method": "PUT", "url": f"Observation/{oid}"},
        })

    return {
        "resourceType": "Bundle",
        "id": "sample-demo-bundle-001",
        "type": "transaction",
        "total": len(entries),
        "entry": entries,
    }
