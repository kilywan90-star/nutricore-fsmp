"""随机生成1000条超声报告测试用例并调用ABCDEF流水线

用法:
    cd backend
    python test_random_1000.py

输出:
    test_results_1000.csv  — 完整测试结果，可用Excel打开评价
    test_progress.log      — 实时进度日志
"""

import random
import requests
import json
import re
import csv
import time
import os
from datetime import datetime

# ============================================================
# 配置
# ============================================================
API_URL = os.environ.get("TEST_API_URL", "http://127.0.0.1:9999/api/structure")
TOTAL_CASES = 1000
TIMEOUT = 120  # 每条超时秒数
OUTPUT_CSV = "test_results_1000.csv"
PROGRESS_LOG = "test_progress.log"

# ============================================================
# 随机报告生成器 — 组件库
# ============================================================

# 检查类型 → 器官/部位
EXAM_ORGANS = {
    "腹部超声": ["肝脏", "胆囊", "胆总管", "胰腺", "脾脏", "双肾", "左肾", "右肾"],
    "甲状腺超声": ["甲状腺左叶", "甲状腺右叶", "甲状腺峡部", "双侧甲状腺"],
    "乳腺超声": ["左侧乳腺", "右侧乳腺", "双侧乳腺", "右乳外上象限", "左乳内上象限", "右乳内下象限"],
    "前列腺超声": ["前列腺", "精囊腺", "膀胱"],
    "妇产超声": ["子宫", "宫腔", "左侧卵巢", "右侧卵巢", "双侧附件区", "盆腔"],
    "血管超声": ["左侧颈总动脉", "右侧颈总动脉", "左侧颈内动脉", "右侧椎动脉", "双侧颈动脉"],
    "心脏超声": ["左心房", "左心室", "右心房", "右心室", "室间隔", "二尖瓣", "主动脉瓣"],
}

# 正常描述片段
NORMAL_FINDINGS = {
    "腹部超声": [
        "形态规则，大小正常，实质回声均匀",
        "包膜光滑，表面平整",
        "内未见明显异常回声",
        "管系显示清晰，走行正常",
        "CDFI未见明显异常血流信号",
    ],
    "甲状腺超声": [
        "形态规则，大小正常",
        "实质回声均匀，分布正常",
        "内未见明显结节及占位回声",
        "CDFI血流分布未见明显异常",
    ],
    "乳腺超声": [
        "层次清楚，边界光滑",
        "内部回声分布均匀",
        "未见明显结节及异常回声",
        "CDFI未见明显异常血流信号",
        "腋窝未见明显肿大淋巴结",
    ],
    "前列腺超声": [
        "形态规则，大小正常",
        "包膜完整，实质回声均匀",
        "内未见明显包块回声",
        "CDFI未见异常血流信号",
    ],
    "妇产超声": [
        "形态规则，大小正常",
        "肌层回声均匀",
        "未见明显异常回声",
        "盆腔未见积液",
    ],
    "血管超声": [
        "走行正常，内径正常",
        "内膜光滑，内中膜不厚",
        "管腔未见明显狭窄",
        "CDFI血流充盈良好，速度正常",
    ],
    "心脏超声": [
        "各腔室大小正常",
        "室壁运动协调",
        "瓣膜形态及活动正常",
        "未见明显占位",
    ],
}

# 异常发现片段 (带数值)
ABNORMAL_FINDINGS = {
    "腹部超声": [
        ("肝囊肿", "见一无回声区，大小约{d1}×{d2}cm，边界清晰，后方回声增强"),
        ("脂肪肝", "体积增大，实质回声增强增粗，分布不均匀，后方回声衰减"),
        ("胆囊结石", "内见一强回声团，大小约{d1}cm，后方伴声影，随体位移动"),
        ("胆囊息肉", "壁上见一附壁高回声团，约{d1}cm，后方无声影，不随体位移动"),
        ("肾结石", "集合系统分离约{d1}cm，内见一强回声团约{d2}cm，后方伴声影"),
        ("肾囊肿", "见一无回声区，大小约{d1}×{d2}cm，壁薄，内透声好"),
        ("脾大", "增大，厚约{d1}cm，肋下约{d2}cm，实质回声均匀"),
        ("胰腺囊肿", "见一囊性暗区，大小约{d1}×{d2}cm，边界清晰，内透声可"),
        ("肝血管瘤", "见一高回声团，大小约{d1}×{d2}cm，边界清晰，内部回声均匀"),
        ("胆总管扩张", "胆总管扩张约{d1}cm，管壁增厚毛糙，内见一强回声团约{d2}cm"),
        ("子宫肌瘤", "增大，约{d1}×{d2}×{d3}cm，肌壁间见低回声团，约{d4}×{d5}cm"),
        ("子宫内膜增厚", "内膜增厚约{d1}cm，回声不均匀，内见小囊性暗区"),
    ],
    "甲状腺超声": [
        ("甲状腺结节", "见一低回声结节，约{d1}×{d2}cm，边界清晰，内未见明显钙化"),
        ("甲状腺结节钙化", "见一低回声结节，约{d1}×{d2}cm，形态不规则，内见点状强回声"),
        ("甲状腺多发结节", "见多个低回声结节，左侧最大约{d1}×{d2}cm，右侧最大约{d3}×{d4}cm"),
        ("弥漫性甲状腺病", "弥漫性增大，实质回声减低，分布不均匀，呈网格样改变，CDFI血流信号丰富"),
        ("甲状腺囊肿", "见一无回声区，大小约{d1}×{d2}cm，壁薄光滑，内透声好"),
    ],
    "乳腺超声": [
        ("乳腺增生", "腺体增厚，回声不均匀"),
        ("乳腺结节", "见一低回声区，大小约{d1}×{d2}cm，边界模糊"),
        ("乳腺结节血流", "见一低回声区，大小约{d1}×{d2}cm，边界不清，内可见血流信号"),
        ("乳腺囊肿", "见一无回声区，约{d1}×{d2}cm，壁薄，内透声好"),
        ("导管扩张", "局部导管扩张约{d1}cm，内见低回声充填"),
    ],
    "前列腺超声": [
        ("前列腺增大", "体积增大，约{d1}×{d2}cm，实质回声不均匀"),
        ("前列腺钙化", "实质内见数个强回声点，较大者约{d1}cm，后方伴声影"),
        ("前列腺增大并钙化", "体积增大，约{d1}×{d2}cm，实质回声不均匀，内见散在强回声点，考虑钙化灶"),
        ("精囊腺增大", "精囊腺增大，左右径约{d1}cm，前后径约{d2}cm，壁增厚毛糙"),
    ],
    "妇产超声": [
        ("卵巢囊肿", "卵巢见一无回声区，大小约{d1}×{d2}cm，壁薄光滑，内透声好"),
        ("盆腔积液", "盆腔见液性暗区，深约{d1}cm"),
        ("早孕", "宫腔内见一孕囊，大小约{d1}×{d2}cm，可见卵黄囊及胚芽，可见原始心管搏动"),
        ("子宫内膜增厚", "内膜增厚约{d1}cm，回声不均匀"),
    ],
    "血管超声": [
        ("颈动脉斑块", "内中膜厚约{d1}mm，分叉处见一低回声斑块约{d2}×{d3}cm，管腔未见明显狭窄"),
        ("颈动脉IMT增厚", "内中膜厚约{d1}mm，管壁毛糙，未见明显斑块"),
        ("锁骨下动脉狭窄", "起始处见一混合回声斑块，约{d1}×{d2}cm，管腔狭窄约{d3}%"),
    ],
    "心脏超声": [
        ("瓣膜反流", "二尖瓣见少量反流信号，反流面积约{d1}平方厘米"),
        ("左室壁增厚", "室间隔厚约{d1}mm，左室后壁厚约{d2}mm"),
    ],
}

# 连接词
CONNECTORS = ["，", "，", "，", "；", "。"]

# 修饰词
MODIFIERS = ["约", "约", "大约", ""]  # "约"出现频率更高


def gen_dimension(lo=0.3, hi=6.0):
    """生成随机尺寸"""
    v = round(random.uniform(lo, hi), 1)
    return str(v)


def gen_measurement():
    """生成随机测量值"""
    d1 = gen_dimension(0.3, 3.0)
    d2 = gen_dimension(0.2, 2.5)
    d3 = gen_dimension(0.5, 8.0)
    d4 = gen_dimension(0.3, 4.0)
    d5 = gen_dimension(0.2, 3.0)
    return {"d1": d1, "d2": d2, "d3": d3, "d4": d4, "d5": d5}


def pick_random(lst):
    return random.choice(lst)


def generate_case():
    """生成一条随机测试用例"""
    exam_type = random.choice(list(EXAM_ORGANS.keys()))
    organs = EXAM_ORGANS[exam_type]
    abnormals = ABNORMAL_FINDINGS.get(exam_type, [])
    normals = NORMAL_FINDINGS.get(exam_type, [])

    # 70% 概率生成异常报告, 30% 正常报告
    is_abnormal = random.random() < 0.7

    parts = []

    if is_abnormal and abnormals:
        # 选一个器官 + 一个异常发现
        organ = pick_random(organs)
        disease_name, finding_tpl = pick_random(abnormals)
        dims = gen_measurement()
        finding = finding_tpl.format(**dims)
        parts.append(f"{organ}{finding}")

        # 30% 概率再加一个正常描述
        if random.random() < 0.3 and normals:
            parts.append(pick_random(normals))
    else:
        # 正常报告: 选2-3个器官的正常描述
        selected_organs = random.sample(organs, min(random.randint(2, 3), len(organs)))
        for organ in selected_organs:
            normal = pick_random(normals)
            parts.append(f"{organ}{normal}")

    text = "".join(parts)

    # 确保至少20个有效字符
    meaningful = re.sub(r'[\s\W]', '', text)
    if len(meaningful) < 20:
        # 补充内容
        if normals:
            text += pick_random(normals)

    return {"text": text, "exam_type": exam_type}


def strip_html(html):
    """去除HTML标签"""
    return re.sub(r'<[^>]+>', '', html or "")


def run_test():
    """执行测试"""
    start_time = datetime.now()
    results = []
    success_count = 0
    error_count = 0
    blocked_count = 0

    # CSV 列头
    headers = [
        "序号", "检查类型", "输入文本", "输入字数",
        "处理方式", "意图模板", "模板原始内容",
        "最终输出", "诊断提示", "警告信息", "推理说明",
        "状态", "错误信息"
    ]

    print(f"=" * 70)
    print(f"超声报告ABCDEF流水线随机测试")
    print(f"总数: {TOTAL_CASES} 条")
    print(f"API: {API_URL}")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 70)

    with open(PROGRESS_LOG, "w", encoding="utf-8") as log_f:
        for i in range(1, TOTAL_CASES + 1):
            case = generate_case()
            row = {
                "序号": i,
                "检查类型": case["exam_type"],
                "输入文本": case["text"],
                "输入字数": len(case["text"]),
            }

            try:
                resp = requests.post(API_URL, json=case, timeout=TIMEOUT)
                if resp.status_code == 400:
                    # L0 拦截
                    detail = resp.json().get("detail", "")
                    row.update({
                        "处理方式": "L0拦截",
                        "意图模板": "", "模板原始内容": "",
                        "最终输出": "", "诊断提示": "",
                        "警告信息": "", "推理说明": "",
                        "状态": "BLOCKED",
                        "错误信息": detail,
                    })
                    blocked_count += 1
                elif resp.status_code == 200:
                    d = resp.json()
                    rpt = d.get("report", {})
                    sources = d.get("sources", {})
                    ef_info = sources.get("EF_combined", {}) or {}

                    # 模板原始内容
                    tpl_name = ef_info.get("template_name", d.get("template_used", ""))
                    tpl_filled_raw = ef_info.get("filled", "")

                    # C路模板内容 (规则引擎)
                    c_info = sources.get("C_regex", {}) or {}

                    row.update({
                        "处理方式": d.get("method", ""),
                        "意图模板": tpl_name or rpt.get("_template_matched", ""),
                        "模板原始内容": strip_html(tpl_filled_raw)[:500],
                        "最终输出": strip_html(rpt.get("study_see", ""))[:800],
                        "诊断提示": "; ".join([
                            h.get("diagnosis", "")
                            for h in rpt.get("study_hint", [])[:5]
                        ]),
                        "警告信息": "; ".join(d.get("warnings", [])),
                        "推理说明": (d.get("reasoning", "") or "")[:300],
                        "状态": "OK",
                        "错误信息": "",
                    })
                    success_count += 1
                else:
                    row.update({
                        "处理方式": "", "意图模板": "", "模板原始内容": "",
                        "最终输出": "", "诊断提示": "",
                        "警告信息": "", "推理说明": "",
                        "状态": f"HTTP_{resp.status_code}",
                        "错误信息": resp.text[:200],
                    })
                    error_count += 1

            except requests.exceptions.Timeout:
                row.update({
                    "处理方式": "", "意图模板": "", "模板原始内容": "",
                    "最终输出": "", "诊断提示": "",
                    "警告信息": "", "推理说明": "",
                    "状态": "TIMEOUT",
                    "错误信息": f"超时({TIMEOUT}s)",
                })
                error_count += 1
            except Exception as e:
                row.update({
                    "处理方式": "", "意图模板": "", "模板原始内容": "",
                    "最终输出": "", "诊断提示": "",
                    "警告信息": "", "推理说明": "",
                    "状态": "ERROR",
                    "错误信息": str(e)[:200],
                })
                error_count += 1

            results.append(row)

            # 进度输出
            if i % 10 == 0 or i == 1:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = i / elapsed if elapsed > 0 else 0
                eta = (TOTAL_CASES - i) / rate if rate > 0 else 0
                progress = f"[{i}/{TOTAL_CASES}] 成功:{success_count} 拦截:{blocked_count} 错误:{error_count} | {rate:.1f}条/秒 | 预计剩余:{eta:.0f}秒"
                print(progress)
                log_f.write(f"{datetime.now().strftime('%H:%M:%S')} {progress}\n")
                log_f.flush()

            # 请求间隔，避免压垮服务
            time.sleep(0.3)

    # 写入CSV
    print(f"\n写入CSV: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in headers})

    # 统计
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n{'=' * 70}")
    print(f"测试完成!")
    print(f"总耗时: {duration:.1f}秒 ({duration/60:.1f}分钟)")
    print(f"成功: {success_count} | L0拦截: {blocked_count} | 错误: {error_count}")
    print(f"结果文件: {OUTPUT_CSV}")
    print(f"进度日志: {PROGRESS_LOG}")
    print(f"{'=' * 70}")

    # 生成简要统计
    status_counts = {}
    method_counts = {}
    for r in results:
        s = r.get("状态", "UNKNOWN")
        m = r.get("处理方式", "N/A")
        status_counts[s] = status_counts.get(s, 0) + 1
        method_counts[m] = method_counts.get(m, 0) + 1

    print(f"\n状态分布:")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    print(f"\n处理方式分布:")
    for m, c in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")


if __name__ == "__main__":
    run_test()
