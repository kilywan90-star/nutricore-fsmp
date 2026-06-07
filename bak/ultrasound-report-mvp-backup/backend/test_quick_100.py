"""快速100条回归测试 — 增量写入CSV, 用于对比修复效果"""
import random, requests, json, re, csv, time, os
from datetime import datetime

API_URL = "http://127.0.0.1:9999/api/structure"
TOTAL = 100
TIMEOUT = 120
CSV_FILE = "test_results_100.csv"

EXAM_ORGANS = {
    "腹部超声": ["肝脏","胆囊","胆总管","胰腺","脾脏","双肾","左肾","右肾"],
    "甲状腺超声": ["甲状腺左叶","甲状腺右叶","甲状腺峡部","双侧甲状腺"],
    "乳腺超声": ["左侧乳腺","右侧乳腺","双侧乳腺","右乳外上象限","左乳内上象限"],
    "前列腺超声": ["前列腺","精囊腺","膀胱"],
    "妇产超声": ["子宫","宫腔","左侧卵巢","右侧卵巢","双侧附件区","盆腔"],
    "血管超声": ["左侧颈总动脉","右侧颈总动脉","右侧椎动脉","双侧颈动脉"],
    "心脏超声": ["左心房","左心室","右心房","右心室","室间隔","二尖瓣"],
}
NORMAL_FINDINGS = {
    "腹部超声": ["形态规则，大小正常，实质回声均匀","包膜光滑，表面平整","内未见明显异常回声","管系显示清晰，走行正常","CDFI未见明显异常血流信号"],
    "甲状腺超声": ["形态规则，大小正常","实质回声均匀，分布正常","内未见明显结节及占位回声","CDFI血流分布未见明显异常"],
    "乳腺超声": ["层次清楚，边界光滑","内部回声分布均匀","未见明显结节及异常回声","CDFI未见明显异常血流信号","腋窝未见明显肿大淋巴结"],
    "前列腺超声": ["形态规则，大小正常","包膜完整，实质回声均匀","内未见明显包块回声","CDFI未见异常血流信号"],
    "妇产超声": ["形态规则，大小正常","肌层回声均匀","未见明显异常回声","盆腔未见积液"],
    "血管超声": ["走行正常，内径正常","内膜光滑，内中膜不厚","管腔未见明显狭窄","CDFI血流充盈良好，速度正常"],
    "心脏超声": ["各腔室大小正常","室壁运动协调","瓣膜形态及活动正常","未见明显占位"],
}
ABNORMAL_FINDINGS = {
    "腹部超声": [
        ("肝囊肿","见一无回声区，大小约{d1}×{d2}cm，边界清晰，后方回声增强"),
        ("脂肪肝","体积增大，实质回声增强增粗，分布不均匀"),
        ("胆囊结石","内见一强回声团，大小约{d1}cm，后方伴声影，随体位移动"),
        ("肾囊肿","见一无回声区，大小约{d1}×{d2}cm，壁薄，内透声好"),
        ("肝血管瘤","见一高回声团，大小约{d1}×{d2}cm，边界清晰，内部回声均匀"),
        ("胆总管扩张","胆总管扩张约{d1}cm，管壁增厚毛糙，内见一强回声团约{d2}cm"),
    ],
    "甲状腺超声": [
        ("甲状腺结节","见一低回声结节，约{d1}×{d2}cm，边界清晰，内未见明显钙化"),
        ("甲状腺多发结节","见多个低回声结节，左侧最大约{d1}×{d2}cm，右侧最大约{d3}×{d4}cm"),
        ("弥漫性甲状腺病","弥漫性增大，实质回声减低，分布不均匀，CDFI血流信号丰富"),
    ],
    "乳腺超声": [
        ("乳腺结节","见一低回声区，大小约{d1}×{d2}cm，边界模糊"),
        ("乳腺结节血流","见一低回声区，大小约{d1}×{d2}cm，边界不清，内可见血流信号"),
        ("乳腺囊肿","见一无回声区，约{d1}×{d2}cm，壁薄，内透声好"),
    ],
    "前列腺超声": [
        ("前列腺增大","体积增大，约{d1}×{d2}cm，实质回声不均匀"),
        ("前列腺钙化","实质内见数个强回声点，较大者约{d1}cm"),
        ("精囊腺增大","精囊腺增大，左右径约{d1}cm，前后径约{d2}cm，壁增厚毛糙"),
    ],
    "妇产超声": [
        ("卵巢囊肿","卵巢见一无回声区，大小约{d1}×{d2}cm，壁薄光滑"),
        ("盆腔积液","盆腔见液性暗区，深约{d1}cm"),
        ("早孕","宫腔内见一孕囊，大小约{d1}×{d2}cm，可见卵黄囊及胚芽，可见原始心管搏动"),
    ],
    "血管超声": [
        ("颈动脉斑块","内中膜厚约{d1}mm，分叉处见一低回声斑块约{d2}×{d3}cm"),
        ("颈动脉IMT增厚","内中膜厚约{d1}mm，管壁毛糙，未见明显斑块"),
        ("锁骨下动脉狭窄","起始处见一混合回声斑块，约{d1}×{d2}cm，管腔狭窄约{d3}%"),
    ],
    "心脏超声": [
        ("瓣膜反流","二尖瓣见少量反流信号，反流面积约{d1}平方厘米"),
        ("左室壁增厚","室间隔厚约{d1}mm，左室后壁厚约{d2}mm"),
    ],
}

def gen_dim(lo=0.3, hi=6.0):
    return str(round(random.uniform(lo, hi), 1))

def gen_meas():
    return {"d1":gen_dim(0.3,3.0),"d2":gen_dim(0.2,2.5),"d3":gen_dim(0.5,8.0),"d4":gen_dim(0.3,4.0),"d5":gen_dim(0.2,3.0)}

def gen_case():
    exam = random.choice(list(EXAM_ORGANS.keys()))
    organs = EXAM_ORGANS[exam]
    abnormals = ABNORMAL_FINDINGS.get(exam, [])
    normals = NORMAL_FINDINGS.get(exam, [])
    is_abn = random.random() < 0.7
    parts = []
    if is_abn and abnormals:
        organ = random.choice(organs)
        name, tpl = random.choice(abnormals)
        parts.append(f"{organ}{tpl.format(**gen_meas())}")
        if random.random() < 0.3 and normals:
            parts.append(random.choice(normals))
    else:
        sel = random.sample(organs, min(random.randint(2,3), len(organs)))
        for o in sel:
            parts.append(f"{o}{random.choice(normals)}")
    text = "".join(parts)
    meaningful = re.sub(r'[\s\W]', '', text)
    if len(meaningful) < 20 and normals:
        text += random.choice(normals)
    return {"text": text, "exam_type": exam}

def strip_html(h):
    return re.sub(r'<[^>]+>', '', h or "")

HEADERS = ["序号","检查类型","输入文本","输入字数","处理方式","意图模板","模板原始内容","最终输出","诊断提示","警告信息","推理说明","状态","错误信息"]

def run():
    start = datetime.now()
    print(f"=" * 60)
    print(f"快速回归测试: {TOTAL}条")
    print(f"开始: {start.strftime('%H:%M:%S')}")
    print(f"=" * 60)

    # 增量写入: 每10条flush一次
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()

        for i in range(1, TOTAL + 1):
            case = gen_case()
            row = {"序号":i, "检查类型":case["exam_type"], "输入文本":case["text"], "输入字数":len(case["text"])}
            try:
                resp = requests.post(API_URL, json=case, timeout=TIMEOUT)
                if resp.status_code == 200:
                    d = resp.json()
                    rpt = d.get("report", {})
                    ef = d.get("sources", {}).get("EF_combined", {}) or {}
                    tpl_name = ef.get("template_name", d.get("template_used", ""))
                    row.update({
                        "处理方式": d.get("method",""),
                        "意图模板": tpl_name or rpt.get("_template_matched",""),
                        "模板原始内容": strip_html(ef.get("filled",""))[:500],
                        "最终输出": strip_html(rpt.get("study_see",""))[:800],
                        "诊断提示": "; ".join([h.get("diagnosis","") for h in rpt.get("study_hint",[])[:5]]),
                        "警告信息": "; ".join(d.get("warnings",[])),
                        "推理说明": (d.get("reasoning","") or "")[:300],
                        "状态": "OK", "错误信息": "",
                    })
                elif resp.status_code == 400:
                    row.update({"处理方式":"L0拦截","意图模板":"","模板原始内容":"","最终输出":"","诊断提示":"","警告信息":"","推理说明":"","状态":"BLOCKED","错误信息":resp.json().get("detail","")})
                else:
                    row.update({"处理方式":"","意图模板":"","模板原始内容":"","最终输出":"","诊断提示":"","警告信息":"","推理说明":"","状态":f"HTTP_{resp.status_code}","错误信息":resp.text[:200]})
            except Exception as e:
                row.update({"处理方式":"","意图模板":"","模板原始内容":"","最终输出":"","诊断提示":"","警告信息":"","推理说明":"","状态":"ERROR","错误信息":str(e)[:200]})

            writer.writerow({k: row.get(k,"") for k in HEADERS})
            if i % 10 == 0:
                f.flush()
                elapsed = (datetime.now() - start).total_seconds()
                rate = i / elapsed if elapsed > 0 else 0
                eta = (TOTAL - i) / rate if rate > 0 else 0
                print(f"[{i}/{TOTAL}] {rate:.1f}条/秒 | 剩余{eta:.0f}秒")

    dur = (datetime.now() - start).total_seconds()
    print(f"\n完成! 耗时{dur:.0f}秒 ({dur/60:.1f}分钟)")
    print(f"结果: {CSV_FILE}")

if __name__ == "__main__":
    run()
