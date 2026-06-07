"""v4 fix verification - 100 random tests (incremental write)"""
import random, requests, json, re, csv, sys
import urllib3
urllib3.disable_warnings()

API_URL = "https://localhost:8700/api/structure"
TOTAL = 100
TIMEOUT = 120
CSV_PATH = r"e:\qoder\ultrasound-report-mvp\backend\test_results_100_v4.csv"

def strip_html(h):
    return re.sub(r'<[^>]+>', '', h or '').strip()

EXAM_TYPES = ["腹部超声", "甲状腺超声", "乳腺超声", "前列腺超声", "妇产超声", "血管超声", "心脏超声"]

TEMPLATES = {
    "腹部超声": {
        "normal": ["肝脏大小形态正常，表面光滑，实质回声均匀，肝内未见明显异常。胆囊大小形态正常，壁薄光滑。胆总管不扩张。胰腺大小正常。脾脏正常。双肾大小正常，集合系统未见分离。"],
        "abnormal": [
            "肝脏大小正常，实质回声均匀，肝内可见一低回声结节，约{v1}x{v2}cm，边界清晰。胆囊壁毛糙，壁厚约{v3}mm。胆总管内径约{v4}mm。胰腺稍大，厚约{v5}cm。脾脏不大。双肾正常。",
            "肝脏增大，实质回声增粗增强。胆囊约{v1}x{v2}cm，壁不毛糙，内见强回声灶约{v3}cm伴声影。胰腺正常。脾脏正常。双肾正常。",
        ],
    },
    "甲状腺超声": {
        "normal": ["甲状腺双侧叶大小正常，实质回声均匀，未见结节。CDFI:血流正常。"],
        "abnormal": ["甲状腺右叶见一低回声结节，约{v1}x{v2}cm，边界清，形态规则。左叶正常。峡部不厚。CDFI:结节内未见血流。"],
    },
    "乳腺超声": {
        "normal": ["双侧乳腺层次清晰，回声均匀，未见结节。"],
        "abnormal": ["右乳外上象限见一低回声结节，约{v1}x{v2}cm，边界清。左乳未见异常。"],
    },
    "前列腺超声": {
        "normal": ["前列腺约3.0x2.0cm，回声均匀。精囊腺正常。膀胱正常。"],
        "abnormal": ["前列腺增大，约{v1}x{v2}cm，回声不均，内见钙化灶。残余尿约{v3}ml。"],
    },
    "妇产超声": {
        "normal": ["子宫大小正常，肌层回声均匀，宫腔线居中。双卵巢正常。盆腔无积液。"],
        "abnormal": [
            "子宫增大，肌层回声不均，见低回声结节约{v1}x{v2}cm。盆腔积液深约{v3}cm。",
            "子宫前位增大，宫腔内见孕囊约{v1}x{v2}cm，可见胚芽及原始心管搏动。",
        ],
    },
    "血管超声": {
        "normal": ["双侧颈动脉内中膜光滑，厚约0.5mm，管腔通畅，未见斑块。CDFI:血流正常。"],
        "abnormal": ["颈动脉内中膜增厚约{v1}mm，分叉处见斑块约{v2}x{v3}mm。CDFI:未见明显狭窄。"],
    },
    "心脏超声": {
        "normal": ["各房室大小正常，室间隔约8mm，搏动好。各瓣膜正常。主动脉不宽。心包无积液。"],
        "abnormal": ["左房约{v1}mm增大。室间隔增厚约{v2}mm。二尖瓣少量反流。主动脉不宽。"],
    },
}

def fill_vals(t):
    return re.sub(r'\{v\d+\}', lambda m: str(round(random.uniform(0.3, 4.5), 1)), t)

def generate():
    exam = random.choice(EXAM_TYPES)
    tpls = TEMPLATES.get(exam, {})
    pool = tpls.get("abnormal", []) if random.random() < 0.7 else tpls.get("normal", [])
    if not pool:
        pool = tpls.get("normal", ["未见明显异常。"])
    return {"exam_type": exam, "text": fill_vals(random.choice(pool))}

HEADERS = ["序号","检查类型","输入文本","输入字数","处理方式","意图模板",
           "模板原始内容","最终输出","诊断提示","警告信息","推理说明","状态","错误信息"]

print(f"v4 test start API={API_URL}", flush=True)

with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=HEADERS)
    w.writeheader()
    ok = err = 0
    for i in range(1, TOTAL + 1):
        case = generate()
        row = {"序号": i, "检查类型": case["exam_type"],
               "输入文本": case["text"], "输入字数": len(case["text"])}
        try:
            resp = requests.post(API_URL, json=case, timeout=TIMEOUT, verify=False)
            if resp.status_code == 200:
                d = resp.json()
                rpt = d.get("report", {})
                src = d.get("sources", {})
                ef = src.get("EF_combined", {}) or {}
                row.update({
                    "处理方式": d.get("method", ""),
                    "意图模板": ef.get("template_name", d.get("template_used", rpt.get("_template_matched", ""))),
                    "模板原始内容": "",
                    "最终输出": rpt.get("study_see", "")[:800],
                    "诊断提示": "; ".join([h.get("diagnosis","") for h in rpt.get("study_hint",[])[:5] if isinstance(h,dict)]),
                    "警告信息": "; ".join(d.get("warnings", [])),
                    "推理说明": (d.get("reasoning","") or "")[:300],
                    "状态": "OK", "错误信息": "",
                })
                ok += 1
            elif resp.status_code == 400:
                row.update({"处理方式":"L0","意图模板":"","模板原始内容":"","最终输出":"",
                    "诊断提示":"","警告信息":"","推理说明":"","状态":"BLOCK","错误信息":resp.json().get("detail","")})
                ok += 1
            else:
                row.update({"处理方式":"","意图模板":"","模板原始内容":"","最终输出":"",
                    "诊断提示":"","警告信息":"","推理说明":"","状态":"ERR","错误信息":str(resp.status_code)})
                err += 1
        except Exception as e:
            row.update({"处理方式":"","意图模板":"","模板原始内容":"","最终输出":"",
                "诊断提示":"","警告信息":"","推理说明":"","状态":"ERR","错误信息":str(e)[:200]})
            err += 1
        w.writerow({k: row.get(k, "") for k in HEADERS})
        f.flush()
        if i % 10 == 0 or i == TOTAL:
            print(f"  [{i}/{TOTAL}] ok={ok} err={err}", flush=True)

print(f"Done! ok={ok} err={err}", flush=True)
print(f"CSV: {CSV_PATH}", flush=True)
