#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超声ASR测试用例自动生成脚本（极限严苛版）
1. 5大模板：A大排畸 / B胎儿心超 / C成人心超 / D全身血管 / E全腹彩超
2. 支持：同音错字、缺字段、口语噪声、乱序、数字畸变、跨模板混杂、临界值、矛盾反例、全阴、重症多病灶
3. 单模板可配置base_cnt=3000基础样本+extra_cnt=500极端用例，自动输出CSV评测文件，附带标注标签
4. 每条输出：编号,原始ASR文本,标准模板标签,扰动标签列表,标准答案JSON
"""

import random
import csv
import json

# ====================== 配置区 ======================
CFG = {
    "base_per_temp": 3000,
    "extra_per_temp": 500,
    "output_csv": "ultrasound_asr_testset_v2.csv",
    "seed": 42,
}

TEMP_MAP = {
    "A": "中孕期大排畸",
    "B": "胎儿专项心超",
    "C": "成人全套心超",
    "D": "颈下肢全套血管",
    "E": "全腹+腹膜后彩超"
}

# 同音替换词典（ASR识别错误源）
TYPO_DICT = {
    "径": ["经"], "厚": ["后"], "腔": ["仓"], "瓣": ["办"], "宽": ["款"],
    "动脉": ["冻麦"], "静脉": ["净麦"], "双顶径": ["双丁径", "双丁"],
    "股骨": ["古骨"], "肾盂": ["肾余"], "EF": ["益福", "伊夫"],
    "AFI": ["阿菲指数", "阿菲"], "PSV": ["匹斯维"], "RI": ["阿瑞"],
    "反流": ["反留"], "二尖瓣": ["二尖办"], "三尖瓣": ["三尖办"],
    "主动脉瓣": ["主冻麦办"], "肺动脉": ["肺冻麦"],
}

# 口语噪声插入池
NOISE_WORDS = [
    "患者体位偏斜反复测量两次", "探头微凉", "下一位病人准备",
    "大概测出来", "目测数值", "肉眼观察结果", "机器轻微抖动",
    "差不多这个数值", "不需要额外记录", "床边加急检查",
    "那个", "嗯", "就是说", "然后", "对吧",
]

# 各模板标准字段库
FIELD_LIB = {
    "A": {
        "num_fields": ["BPD", "HC", "AC", "FL", "HL", "侧脑室宽度", "后颅窝池", "AFI", "胎盘厚度", "NF"],
        "norm_range": {"BPD":(45,85),"HC":(180,290),"AC":(160,260),"FL":(32,55),"侧脑室宽度":(3,12),"后颅窝池":(2,8),"AFI":(70,220),"胎盘厚度":(20,45),"NF":(1,6),"HL":(30,55)},
        "disease": ["脉络丛囊肿", "单脐动脉可疑", "胃泡未显示", "NF增厚", "羊水偏少", "胎盘增厚", "左心室强回声光点", "肾盂分离", "肠管回声增强", "侧脑室临界增宽"],
        "structure": ["颅骨光环完整","大脑镰居中","透明隔腔可见","小脑形态正常","眼眶可见","鼻骨可见","上唇连续","脊柱排列整齐","四腔心可见","胃泡可见","双肾可见","膀胱可见","脐带血管数3条","四肢长骨可见"],
        "conflict": [("单脐动脉", "脐血管2动1静")],
        "templates": [
            "孕{ga}周{ga_d}天, 胎儿双顶径{bpd}mm, 头围{hc}mm, 腹围{ac}mm, 股骨长{fl}mm, 肱骨长{hl}mm, 侧脑室宽{lv}mm, 后颅窝池{pf}mm, AFI{afi}mm, 最大羊水深度{afv}mm, 胎盘位于{plac_pos}, 成熟度{plac_grade}, 厚{plac_thick}mm, 胎心{hr}次每分。{structs}。{abnorm}",
        ]
    },
    "B": {
        "num_fields": ["MV_E", "MV_A", "TV_E", "TV_A", "AV_VEL", "PV_VEL", "DAO_VEL", "CTR"],
        "norm_range": {"MV_E":(20,45),"MV_A":(25,55),"TV_E":(20,45),"TV_A":(25,55),"AV_VEL":(60,120),"PV_VEL":(50,100),"DAO_VEL":(70,140),"CTR":(0.25,0.40)},
        "disease": ["主动脉骑跨", "肺动脉狭窄", "三尖瓣下移", "卵圆孔早闭", "室间隔缺损", "永存左上腔静脉"],
        "structure": ["四腔心可见心轴正常","左右心室大小对称","室间隔完整","房间隔见卵圆孔瓣膜活动好","二尖瓣形态正常","三尖瓣形态正常","主动脉骑跨未见异常","肺动脉与主动脉比例正常","主动脉弓完整","动脉导管开放","上下腔静脉引流入右心房","肺静脉引流入左心房","心包未见积液"],
        "conflict": [("室间隔完整", "室缺3.2mm")],
        "templates": [
            "孕{ga}周{ga_d}天, 胎心{hr}次每分, 心胸面积比{ctr}, 二尖瓣血流E峰{mv_e}cm/s, A峰{mv_a}cm/s, 三尖瓣血流E峰{tv_e}cm/s, A峰{tv_a}cm/s, 主动脉瓣上流速{av}cm/s, 肺动脉瓣上流速{pv}cm/s, 降主动脉流速{dao}cm/s。{structs}。{abnorm}",
        ]
    },
    "C": {
        "num_fields": ["LVEDD","LVESD","IVS","LVPW","LA","AO","RV","RA","EF","FS","E_A","MV_E","AV_VEL","PV_VEL","TV_VEL"],
        "norm_range": {"LVEDD":(38,56),"LVESD":(22,38),"IVS":(7,12),"LVPW":(7,12),"LA":(28,42),"AO":(24,38),"RV":(18,30),"RA":(30,45),"EF":(50,75),"FS":(28,42),"E_A":(0.8,2.5),"MV_E":(60,120),"AV_VEL":(80,180),"PV_VEL":(60,110),"TV_VEL":(30,80)},
        "disease": ["二尖瓣少量反流", "主动脉中量反流", "心包积液", "右室肥厚", "室间隔基底部增厚", "左心房增大", "升主动脉增宽", "左心室舒张功能减退", "左心室收缩功能减低"],
        "conflict": [("EF62%心功能正常", "左心室收缩功能减低")],
        "templates": [
            "{gender}性, {age}岁, 左心室舒张末期内径{lvedd}mm, 左心室收缩末期内径{lvesd}mm, 室间隔厚度{ivs}mm, 左室后壁厚度{lvpw}mm, 左房前后径{la}mm, 主动脉根部内径{ao}mm, 右室前后径{rv}mm, 右房左右径{ra}mm, EF{ef}%, FS{fs}%, 二尖瓣E/A比值{ea}。二尖瓣E峰{mv_e}cm/s, 主动脉瓣前向流速{av}cm/s, 肺动脉瓣前向流速{pv}cm/s, 三尖瓣反流流速{tv}cm/s。{abnorm}",
        ]
    },
    "D": {
        "num_fields": ["CCA_R_IMT","CCA_L_IMT","CCA_R_D","CCA_L_D","ICA_R_PSV","ICA_L_PSV","ICA_R_EDV","ICA_L_EDV","VA_R_D","VA_L_D","CFA_PSV","POP_PSV","PTA_PSV","DPA_PSV"],
        "norm_range": {"CCA_R_IMT":(0.5,1.2),"CCA_L_IMT":(0.5,1.2),"CCA_R_D":(5,8),"CCA_L_D":(5,8),"ICA_R_PSV":(45,95),"ICA_L_PSV":(45,95),"ICA_R_EDV":(12,32),"ICA_L_EDV":(12,32),"VA_R_D":(2.0,4.0),"VA_L_D":(2.0,4.0),"CFA_PSV":(70,130),"POP_PSV":(45,85),"PTA_PSV":(35,70),"DPA_PSV":(30,65)},
        "disease": ["颈总动脉斑块", "颈内动脉起始部斑块", "下肢动脉粥样硬化", "胫前动脉流速减低", "股总静脉瓣膜功能不全"],
        "conflict": [("管腔通畅", "局部闭塞")],
        "templates": [
            "{gender}性, {age}岁, 右颈总动脉IMT{cca_ri}mm, 管径{cca_rd}mm, 左颈总动脉IMT{cca_li}mm, 管径{cca_ld}mm, 右颈内动脉PSV{ica_rp}cm/s, EDV{ica_re}cm/s, RI{ica_rri}, 左颈内动脉PSV{ica_lp}cm/s, EDV{ica_le}cm/s, RI{ica_lri}, 右椎动脉内径{va_rd}mm, 左椎动脉内径{va_ld}mm。股总动脉PSV{cfa}cm/s, 腘动脉PSV{pop}cm/s, 胫后动脉PSV{pta}cm/s, 足背动脉PSV{dpa}cm/s。{abnorm}",
        ]
    },
    "E": {
        "num_fields": ["肝右叶斜径","肝厚","胆囊长","胆囊宽","胆囊壁","胰头","胰体","胰尾","脾厚","脾长","右肾长","右肾宽","左肾长","左肾宽","门静脉","SMA_PSV","腹主动脉","下腔静脉"],
        "norm_range": {"肝右叶斜径":(100,145),"肝厚":(80,115),"胆囊长":(55,85),"胆囊宽":(22,38),"胆囊壁":(1.5,3.5),"胰头":(15,28),"胰体":(8,18),"胰尾":(8,22),"脾厚":(25,42),"脾长":(80,115),"右肾长":(90,120),"右肾宽":(40,60),"左肾长":(90,120),"左肾宽":(40,60),"门静脉":(8,13),"SMA_PSV":(90,170),"腹主动脉":(14,24),"下腔静脉":(12,22)},
        "disease": ["脂肪肝", "肝囊肿", "胆囊结石", "胆囊息肉", "右肾囊肿", "左肾结石", "脾大", "门静脉增宽", "腹主动脉粥样硬化", "肾动脉狭窄", "前列腺增生", "子宫肌瘤", "腹水"],
        "conflict": [("左肾可见", "左肾缺如")],
        "templates": [
            "{gender}性, {age}岁, 肝右叶斜径{liver_rl}mm, 肝厚{liver_th}mm, 回声{liver_echo}, 胆囊{gb_l}mm×{gb_w}mm, 壁厚{gb_wall}mm, 胰头{pan_h}mm体{pan_b}mm尾{pan_t}mm, 脾厚{spl_th}mm长径{spl_l}mm, 右肾{rk_l}mm×{rk_w}mm, 左肾{lk_l}mm×{lk_w}mm。门静脉{portal}mm, SMA_PSV{sma}cm/s, 腹主动脉{ao}mm, 下腔静脉{ivc}mm。{abnorm}",
        ]
    }
}

DISTURB_TYPE = [
    "干净原文", "同音错字", "缺数值缺单位", "插入口语噪声", "语序打乱",
    "数字点位错误", "跨模板字段混杂", "临界边界值", "逻辑矛盾", "全阴性无异常", "多病灶重症"
]


# ====================== 工具函数 ======================
def typo_replace(s: str) -> str:
    """随机同音错字替换"""
    for src, dst_list in TYPO_DICT.items():
        if src in s and random.random() < 0.35:
            s = s.replace(src, random.choice(dst_list))
    return s

def insert_noise(s: str) -> str:
    """随机插入口语干扰"""
    if random.random() < 0.3:
        noise = random.choice(NOISE_WORDS)
        pos = random.randint(0, len(s))
        s = s[:pos] + noise + s[pos:]
    return s

def num_disturb(val: float, low: float, high: float) -> tuple:
    """数字畸变：小数点错位、临界偏移"""
    dist_tag = ""
    r = random.random()
    if r < 0.1:
        # 临界值
        val = high * 1.02 if random.random() > 0.5 else low * 0.98
        dist_tag = "临界边界值"
    elif r < 0.2:
        # 小数点错位
        val = val * 10 if random.random() > 0.5 else val / 10
        dist_tag = "数字小数点错位"
    elif r < 0.25:
        # 缺失小数 (24.5 → 24)
        val = round(val)
        dist_tag = "缺失小数"
    return round(val, 2), dist_tag

def shuffle_words(word_list: list) -> list:
    random.shuffle(word_list)
    return word_list

def gen_full_normal(temp_code: str) -> tuple:
    """全阴性正常报告 — 保留足够关键词以维持模板识别"""
    base = {
        "A": "胎儿各生长指标正常，颅脑、脊柱、内脏、胎盘羊水未见异常",
        "B": "胎儿心脏房室连接正常，各办膜无反留，大血管发育正常",
        "C": "心仓大小正常、室壁厚度正常、心功能各项测值均在正常范围",
        "D": "颈总动脉管径正常，未见斑块及办膜反流",
        "E": "肝脏大小正常，肝胆胰脾肾形态正常，管道无扩张无积液"
    }
    txt = base[temp_code]
    txt = typo_replace(txt)
    return txt, "全阴性无异常"

def gen_multi_disease(temp_code: str) -> tuple:
    """多病灶重症（≥4处异常）"""
    dis_list = FIELD_LIB[temp_code]["disease"]
    pick_dis = random.sample(dis_list, min(len(dis_list), 4))
    text = "；".join(pick_dis)
    return text, "多病灶重症"

def gen_conflict_item(temp_code: str) -> tuple:
    """生成医学矛盾语句"""
    conf_pairs = FIELD_LIB[temp_code]["conflict"][0]
    text = f"{conf_pairs[0]}，{conf_pairs[1]}"
    return text, "逻辑矛盾"


def generate_patient_context(temp_code: str):
    """生成患者基本信息"""
    if temp_code in ('A', 'B'):
        ga = random.randint(20, 28)
        gd = random.randint(0, 6)
        return {"ga": ga, "ga_d": gd, "hr": random.randint(120, 160), "age": None, "gender": None}
    else:
        gender = random.choice(["男", "女"])
        if temp_code == 'D':
            age = random.randint(35, 75)
        elif temp_code == 'C':
            age = random.randint(25, 78)
        else:
            age = random.randint(30, 70)
        return {"ga": None, "ga_d": None, "hr": None, "age": age, "gender": gender}

def build_normal_case(temp_code: str, ctx: dict) -> tuple:
    """构建一条正常病例(无异常发现)"""
    lib = FIELD_LIB[temp_code]
    nr = lib["norm_range"]

    measurements = {}
    for fd in lib["num_fields"]:
        for k, vr in nr.items():
            if k.replace("_","").upper() in fd.replace("_","").upper() or k in fd:
                val = round(random.uniform(vr[0], vr[1]), 2)
                val, _ = num_disturb(val, vr[0], vr[1])
                measurements[fd] = val
                break
        if fd not in measurements:
            measurements[fd] = round(random.uniform(5, 30), 1)

    # 构建模板文本
    tmpl = lib["templates"][0]
    tmpl_vars = {}

    if temp_code == 'A':
        tmpl_vars = {
            "ga": ctx["ga"], "ga_d": ctx["ga_d"],
            "bpd": measurements.get("BPD", random.randint(45,85)),
            "hc": measurements.get("HC", random.randint(180,290)),
            "ac": measurements.get("AC", random.randint(160,260)),
            "fl": measurements.get("FL", random.randint(32,55)),
            "hl": measurements.get("HL", random.randint(30,55)),
            "lv": measurements.get("侧脑室宽度", random.randint(3,10)),
            "pf": measurements.get("后颅窝池", random.randint(2,7)),
            "afi": measurements.get("AFI", random.randint(70,200)),
            "afv": random.randint(30,70),
            "plac_pos": random.choice(["前壁","后壁","宫底","右侧壁","左侧壁"]),
            "plac_grade": random.choice(["0级","I级","I级","0-I级"]),
            "plac_thick": random.randint(25,40),
            "hr": ctx["hr"],
            "structs": "。".join(random.sample(lib["structure"], 6)),
            "abnorm": "",
        }
    elif temp_code == 'B':
        tmpl_vars = {
            "ga": ctx["ga"], "ga_d": ctx["ga_d"],
            "hr": ctx["hr"],
            "ctr": round(random.uniform(0.28, 0.38), 2),
            "mv_e": measurements.get("MV_E", random.randint(22,42)),
            "mv_a": measurements.get("MV_A", random.randint(28,52)),
            "tv_e": measurements.get("TV_E", random.randint(22,42)),
            "tv_a": measurements.get("TV_A", random.randint(28,52)),
            "av": measurements.get("AV_VEL", random.randint(65,115)),
            "pv": measurements.get("PV_VEL", random.randint(55,95)),
            "dao": measurements.get("DAO_VEL", random.randint(75,135)),
            "structs": "。".join(random.sample(lib["structure"], 5)),
            "abnorm": "",
        }
    elif temp_code == 'C':
        tmpl_vars = {
            "gender": ctx["gender"],
            "age": ctx["age"],
            "lvedd": measurements.get("LVEDD", random.randint(40,54)),
            "lvesd": measurements.get("LVESD", random.randint(24,36)),
            "ivs": measurements.get("IVS", random.randint(7,11)),
            "lvpw": measurements.get("LVPW", random.randint(7,11)),
            "la": measurements.get("LA", random.randint(28,38)),
            "ao": measurements.get("AO", random.randint(26,36)),
            "rv": measurements.get("RV", random.randint(18,28)),
            "ra": measurements.get("RA", random.randint(30,42)),
            "ef": measurements.get("EF", random.randint(55,72)),
            "fs": measurements.get("FS", random.randint(28,40)),
            "ea": round(random.uniform(0.9, 2.0), 2),
            "mv_e": measurements.get("MV_E", random.randint(65,110)),
            "av": measurements.get("AV_VEL", random.randint(90,170)),
            "pv": measurements.get("PV_VEL", random.randint(65,105)),
            "tv": measurements.get("TV_VEL", random.randint(35,70)),
            "abnorm": "",
        }
    elif temp_code == 'D':
        ica_psv_r = measurements.get("ICA_R_PSV", random.randint(50,90))
        ica_edv_r = measurements.get("ICA_R_EDV", random.randint(15,28))
        ica_psv_l = measurements.get("ICA_L_PSV", random.randint(50,90))
        ica_edv_l = measurements.get("ICA_L_EDV", random.randint(15,28))
        tmpl_vars = {
            "gender": ctx["gender"],
            "age": ctx["age"],
            "cca_ri": measurements.get("CCA_R_IMT", round(random.uniform(0.5,1.1),2)),
            "cca_rd": round(random.uniform(5.5,7.5),1),
            "cca_li": measurements.get("CCA_L_IMT", round(random.uniform(0.5,1.1),2)),
            "cca_ld": round(random.uniform(5.5,7.5),1),
            "ica_rp": ica_psv_r,
            "ica_re": ica_edv_r,
            "ica_rri": round(1 - ica_edv_r/ica_psv_r, 2) if ica_psv_r > 0 else 0.65,
            "ica_lp": ica_psv_l,
            "ica_le": ica_edv_l,
            "ica_lri": round(1 - ica_edv_l/ica_psv_l, 2) if ica_psv_l > 0 else 0.65,
            "va_rd": round(random.uniform(2.5,3.8),1),
            "va_ld": round(random.uniform(2.5,3.8),1),
            "cfa": measurements.get("CFA_PSV", random.randint(80,120)),
            "pop": measurements.get("POP_PSV", random.randint(50,80)),
            "pta": measurements.get("PTA_PSV", random.randint(40,65)),
            "dpa": measurements.get("DPA_PSV", random.randint(35,60)),
            "abnorm": "",
        }
    elif temp_code == 'E':
        liver_echo = random.choice(["均匀","均匀","均匀","稍增粗"])
        tmpl_vars = {
            "gender": ctx["gender"],
            "age": ctx["age"],
            "liver_rl": measurements.get("肝右叶斜径", random.randint(105,140)),
            "liver_th": measurements.get("肝厚", random.randint(80,112)),
            "liver_echo": liver_echo,
            "gb_l": measurements.get("胆囊长", random.randint(56,78)),
            "gb_w": measurements.get("胆囊宽", random.randint(23,33)),
            "gb_wall": round(random.uniform(1.8,3.2),1),
            "pan_h": int(measurements.get("胰头", random.randint(18,26))),
            "pan_b": int(measurements.get("胰体", random.randint(10,17))),
            "pan_t": int(measurements.get("胰尾", random.randint(10,20))),
            "spl_th": measurements.get("脾厚", random.randint(28,39)),
            "spl_l": measurements.get("脾长", random.randint(82,110)),
            "rk_l": measurements.get("右肾长", random.randint(95,116)),
            "rk_w": measurements.get("右肾宽", random.randint(44,56)),
            "lk_l": measurements.get("左肾长", random.randint(95,116)),
            "lk_w": measurements.get("左肾宽", random.randint(44,56)),
            "portal": round(random.uniform(9,12.5),1),
            "sma": measurements.get("SMA_PSV", random.randint(95,165)),
            "ao": random.randint(15,23),
            "ivc": random.randint(12,21),
            "abnorm": "",
        }

    text = tmpl.format(**tmpl_vars)

    # Build answer JSON — collect ALL numeric tmpl_vars as measurements
    ans = {"template": TEMP_MAP[temp_code], "measurements": {}, "abnormality": "无"}

    # Map template variable names to standard field names with units
    if temp_code == 'A':
        var_map = {
            "bpd": ("BPD", "mm"), "hc": ("HC", "mm"), "ac": ("AC", "mm"),
            "fl": ("FL", "mm"), "hl": ("HL", "mm"), "lv": ("侧脑室宽度", "mm"),
            "pf": ("后颅窝池", "mm"), "afi": ("AFI", "mm"), "afv": ("羊水深度", "mm"),
            "plac_thick": ("胎盘厚度", "mm"), "hr": ("胎心", "bpm"),
        }
    elif temp_code == 'B':
        var_map = {
            "ctr": ("CTR", ""), "mv_e": ("MV_E", "cm/s"), "mv_a": ("MV_A", "cm/s"),
            "tv_e": ("TV_E", "cm/s"), "tv_a": ("TV_A", "cm/s"),
            "av": ("AV_VEL", "cm/s"), "pv": ("PV_VEL", "cm/s"),
            "dao": ("DAO_VEL", "cm/s"), "hr": ("HR", "bpm"),
        }
    elif temp_code == 'C':
        var_map = {
            "lvedd": ("LVEDD", "mm"), "lvesd": ("LVESD", "mm"),
            "ivs": ("IVS", "mm"), "lvpw": ("LVPW", "mm"),
            "la": ("LA", "mm"), "ao": ("AO", "mm"),
            "rv": ("RV", "mm"), "ra": ("RA", "mm"),
            "ef": ("EF", "%"), "fs": ("FS", "%"), "ea": ("E/A", ""),
            "mv_e": ("MV_E", "cm/s"), "av": ("AV_VEL", "cm/s"),
            "pv": ("PV_VEL", "cm/s"), "tv": ("TV_VEL", "cm/s"),
        }
    elif temp_code == 'D':
        var_map = {
            "cca_ri": ("CCA_R_IMT", "mm"), "cca_li": ("CCA_L_IMT", "mm"),
            "cca_rd": ("CCA_R_D", "mm"), "cca_ld": ("CCA_L_D", "mm"),
            "ica_rp": ("ICA_R_PSV", "cm/s"), "ica_re": ("ICA_R_EDV", "cm/s"),
            "ica_rri": ("ICA_R_RI", ""),
            "ica_lp": ("ICA_L_PSV", "cm/s"), "ica_le": ("ICA_L_EDV", "cm/s"),
            "ica_lri": ("ICA_L_RI", ""),
            "va_rd": ("VA_R_D", "mm"), "va_ld": ("VA_L_D", "mm"),
            "cfa": ("CFA_PSV", "cm/s"), "pop": ("POP_PSV", "cm/s"),
            "pta": ("PTA_PSV", "cm/s"), "dpa": ("DPA_PSV", "cm/s"),
        }
    elif temp_code == 'E':
        var_map = {
            "liver_rl": ("肝右叶斜径", "mm"), "liver_th": ("肝厚", "mm"),
            "gb_l": ("胆囊长", "mm"), "gb_w": ("胆囊宽", "mm"),
            "gb_wall": ("胆囊壁", "mm"),
            "pan_h": ("胰头", "mm"), "pan_b": ("胰体", "mm"), "pan_t": ("胰尾", "mm"),
            "spl_th": ("脾厚", "mm"), "spl_l": ("脾长", "mm"),
            "rk_l": ("右肾长", "mm"), "rk_w": ("右肾宽", "mm"),
            "lk_l": ("左肾长", "mm"), "lk_w": ("左肾宽", "mm"),
            "portal": ("门静脉", "mm"), "sma": ("SMA_PSV", "cm/s"),
            "ao": ("腹主动脉", "mm"), "ivc": ("下腔静脉", "mm"),
        }

    for var_key, (field_name, unit) in var_map.items():
        if var_key in tmpl_vars:
            val = tmpl_vars[var_key]
            if isinstance(val, (int, float)):
                ans["measurements"][field_name] = f"{val}{unit}"

    return text, ans


def build_single_case(temp_code: str, is_extra: bool = False) -> tuple:
    """生成单条样本：返回(原始文本, 扰动标签列表, 标准答案JSON)"""
    lib = FIELD_LIB[temp_code]
    ctx = generate_patient_context(temp_code)
    disturb_tags = []

    # 极端用例分支
    if is_extra:
        r = random.random()
        if r < 0.2:
            raw_txt, tag = gen_full_normal(temp_code)
            disturb_tags.append(tag)
            ans = {"template": TEMP_MAP[temp_code], "measurements": {}, "abnormality": "无"}
            raw_txt = insert_noise(raw_txt)
            return raw_txt, disturb_tags, ans
        elif r < 0.4:
            disease_txt, tag = gen_multi_disease(temp_code)
            disturb_tags.append(tag)
            # Build normal case first, then replace abnorm with disease
            raw_txt, ans = build_normal_case(temp_code, ctx)
            raw_txt = raw_txt.replace("。", f"。{disease_txt}。", 1)
            ans["abnormality"] = disease_txt.replace("；", ";")
            raw_txt = insert_noise(raw_txt)
            return raw_txt, disturb_tags, ans
        elif r < 0.6:
            conflict_txt, tag = gen_conflict_item(temp_code)
            disturb_tags.append(tag)
            raw_txt, ans = build_normal_case(temp_code, ctx)
            raw_txt = raw_txt.replace("。", f"。{conflict_txt}。", 1)
            ans["abnormality"] = conflict_txt
            raw_txt = insert_noise(raw_txt)
            return raw_txt, disturb_tags, ans
        else:
            # 多扰动叠加：临界值+噪声+错字
            disturb_tags.extend(["临界边界值", "同音错字", "插入口语噪声"])
            raw_txt, ans = build_normal_case(temp_code, ctx)
            disturb_tags.append("多扰动叠加")
    else:
        raw_txt, ans = build_normal_case(temp_code, ctx)

    # --- 统一施加扰动 ---
    # 语序打乱(部分记录)
    if random.random() < 0.15:
        parts = raw_txt.split("。")
        random.shuffle(parts)
        raw_txt = "。".join(parts)
        disturb_tags.append("语序打乱")

    # 同音错字
    before_typo = raw_txt
    raw_txt = typo_replace(raw_txt)
    if raw_txt != before_typo:
        disturb_tags.append("同音错字")

    # 口语噪声
    before_noise = raw_txt
    raw_txt = insert_noise(raw_txt)
    if raw_txt != before_noise:
        disturb_tags.append("插入口语噪声")

    # 缺单位(随机删除一个单位)
    if random.random() < 0.12:
        raw_txt = re.sub(r'(mm|cm/s|cm|%|bpm)(?=\s*[,;，；。])', '', raw_txt, count=1)
        disturb_tags.append("缺数值缺单位")

    # 跨模板混杂
    if random.random() < 0.08:
        other_temp = random.choice([k for k in TEMP_MAP if k != temp_code])
        other_fd = random.choice(FIELD_LIB[other_temp]["num_fields"])
        raw_txt += f"，{other_fd}{random.randint(10,50)}mm"
        disturb_tags.append("跨模板字段混杂")

    if not disturb_tags:
        disturb_tags.append("干净原文")

    return raw_txt, disturb_tags, ans


# ====================== 批量生成&导出CSV ======================
def run_generate():
    random.seed(CFG["seed"])
    all_rows = []
    case_id = 1

    for temp_code in TEMP_MAP:
        print(f"生成 {TEMP_MAP[temp_code]} [{temp_code}]: 基础{CFG['base_per_temp']} + 极端{CFG['extra_per_temp']}...")
        # 基础样本
        for _ in range(CFG["base_per_temp"]):
            txt, tags, ans = build_single_case(temp_code, is_extra=False)
            all_rows.append([case_id, txt, temp_code, ",".join(tags), json.dumps(ans, ensure_ascii=False)])
            case_id += 1
        # 极端用例
        for _ in range(CFG["extra_per_temp"]):
            txt, tags, ans = build_single_case(temp_code, is_extra=True)
            all_rows.append([case_id, txt, temp_code, ",".join(tags), json.dumps(ans, ensure_ascii=False)])
            case_id += 1

    # 写入CSV
    output_path = CFG["output_csv"]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["样本ID", "ASR原始文本", "标准模板(A/B/C/D/E)", "扰动标签", "标准答案JSON"])
        writer.writerows(all_rows)

    # 统计
    from collections import Counter
    tag_counter = Counter()
    template_counter = Counter()
    for row in all_rows:
        for t in row[3].split(","):
            tag_counter[t.strip()] += 1
        template_counter[row[2]] += 1

    print(f"\n生成完毕! 总样本: {len(all_rows)} 输出: {output_path}")
    print(f"明细: 5模板×{CFG['base_per_temp']}=15000 + 极端5×{CFG['extra_per_temp']}=2500 = 17500")
    print(f"\n模板分布:")
    for t in "ABCDE":
        print(f"  {t}({TEMP_MAP[t]}): {template_counter[t]}")
    print(f"\n扰动标签分布(Top 10):")
    for tag, cnt in tag_counter.most_common(10):
        print(f"  {tag}: {cnt}")
    print(f"\n各模板异常率:")
    for t in "ABCDE":
        abnorm_count = sum(1 for row in all_rows if row[2] == t and '"abnormality":"无"' not in row[4])
        t_total = sum(1 for row in all_rows if row[2] == t)
        rate = abnorm_count / t_total * 100 if t_total else 0
        print(f"  {t}: {abnorm_count}/{t_total} = {rate:.1f}%")


if __name__ == "__main__":
    import re
    run_generate()
