#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超声ASR语音识别评测数据集生成器
产出: 100条混合样本 + 5×3000条专项样本 = 15100条
格式: 序号|ASR语音错写文本|归属模板|标准答案结构化字段
"""

import random
import json
import os
import re

random.seed(42)

OUTPUT_DIR = r"e:\claude\docs\ultrasound_asr_testset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# ASR 同音/错字 映射表
# ============================================================
HOMOPHONE_MAP = {
    '双顶径': '双丁径', '股骨长': '古骨长', '股骨': '古骨',
    '动脉': '冻麦', '静脉': '净麦', '内中膜': '内中末',
    '反流': '反留', '肾盂': '肾余', '瓣膜': '办膜',
    '瓣': '办', '腔': '仓', '室': '时',
    '径': '经', '厚': '后', '流': '留', '宽': '款',
    'EF': '益福', 'AFI': '阿菲指数',
}

FILLER_WORDS = ['那个', '嗯', '这个', '然后', '就是', '就是说', '呃', '啊', '对吧', '好']

# ============================================================
# 测量值生成器
# ============================================================
def rand_val(lo, hi, decimals=1):
    v = random.uniform(lo, hi)
    return round(v, decimals)

def fmt_mm(v):
    if isinstance(v, float) and v == int(v):
        return f"{int(v)}mm"
    return f"{v}mm"

def fmt_cm(v):
    return f"{v}cm"

def fmt_pct(v):
    return f"{v}%"

def fmt_cms(v):
    return f"{v}cm/s"

def fmt_mms(v):
    return f"{v}mm/s"

# ============================================================
# ASR 噪声注入器
# ============================================================
def inject_asr_noise(text, error_level=0.15):
    """
    error_level: 0.0~1.0, 控制错误密度
    错误类型:
    1. 同音替换 (40%)
    2. 缺字 (20%)
    3. 口语冗余插入 (25%)
    4. 语序局部颠倒 (10%)
    5. 多字/重复字 (5%)
    """
    words = list(text)  # 按字符处理

    # 1. 同音替换 — 对特定词汇做替换
    for correct, wrong in HOMOPHONE_MAP.items():
        if correct in text and random.random() < error_level * 1.5:
            text = text.replace(correct, wrong, 1)  # 每次只替换一处

    # 2. 缺字 (随机删除非关键字符)
    chars = list(text)
    i = 0
    while i < len(chars):
        if random.random() < error_level * 0.3 and chars[i] not in '0123456789.%':
            if i > 0 and random.random() < 0.5:
                del chars[i]
                continue
        i += 1
    text = ''.join(chars)

    # 3. 口语冗余 — 随机插入填充词
    if random.random() < error_level * 2:
        filler = random.choice(FILLER_WORDS)
        pos = random.randint(0, len(text))
        text = text[:pos] + filler + text[pos:]

    # 4. 局部颠倒
    if random.random() < error_level * 0.5 and len(text) > 6:
        i = random.randint(0, len(text) - 4)
        j = i + 2
        text = text[:i] + text[j] + text[i] + text[j+1:]

    # 5. 重复字
    if random.random() < error_level * 0.2 and len(text) > 2:
        i = random.randint(0, len(text) - 1)
        text = text[:i] + text[i] + text[i] + text[i+1:]

    return text


# ============================================================
# A: 中孕期胎儿系统大排畸 (20-24周)
# ============================================================
def gen_fetal_anomaly():
    """生成一条大排畸记录, 返回 (asr_text, structured_answer)"""
    ga_week = random.randint(20, 24)
    ga_day = random.randint(0, 6)
    ga = f"{ga_week}周{ga_day}天" if ga_day > 0 else f"{ga_week}周"

    # 测量值 (GA-dependent ranges)
    week_factor = (ga_week - 20) / 4.0  # 0~1
    bpd = rand_val(46 + week_factor * 12, 50 + week_factor * 12)
    hc = rand_val(170 + week_factor * 40, 180 + week_factor * 40)
    ac = rand_val(150 + week_factor * 40, 160 + week_factor * 40)
    fl = rand_val(33 + week_factor * 11, 36 + week_factor * 11)
    hl = rand_val(31 + week_factor * 10, 34 + week_factor * 10)
    tcd = rand_val(19 + week_factor * 5, 22 + week_factor * 5)  # 小脑横径
    lv = rand_val(4, 8)  # 侧脑室宽度
    afi = rand_val(80, 180)
    afv_max = rand_val(30, 70)

    # 胎盘
    placenta_pos = random.choice(['前壁', '后壁', '宫底', '右侧壁', '左侧壁'])
    placenta_grade = random.choice(['0级', 'I级', 'I级', '0-I级'])
    placenta_thick = rand_val(25, 40)

    # 胎心
    hr = random.randint(120, 160)

    # 结构是否可见
    structures_visible = [
        '颅骨光环完整', '大脑镰居中', '透明隔腔可见', '小脑形态正常',
        '侧脑室未见增宽', '眼眶可见', '鼻骨可见', '上唇连续',
        '脊柱排列整齐', '四腔心可见', '胃泡可见', '双肾可见',
        '膀胱可见', '脐带血管数3条', '四肢长骨可见', '双手可见', '双足可见'
    ]

    # 偶尔有异常发现
    findings = []
    if random.random() < 0.12:
        findings.append(random.choice([
            f'左心室强回声光点, 直径{rand_val(1.5, 3.0)}mm',
            f'肾盂分离, 左侧{rand_val(5, 8)}mm, 右侧{rand_val(4, 7)}mm',
            f'侧脑室后角宽{rand_val(8, 12)}mm, 临界增宽',
            f'脉络丛囊肿, {rand_val(3, 6)}mm',
            f'肠管回声增强, 范围约{rand_val(15, 25)}mm',
            '单脐动脉',
            '脐带绕颈1周',
            f'胎盘内见{rand_val(15, 25)}mm×{rand_val(10, 20)}mm无回声区',
        ]))

    # 构建标准答案
    answer_parts = [
        f"GA={ga}", f"BPD={bpd}mm", f"HC={hc}mm", f"AC={ac}mm",
        f"FL={fl}mm", f"HL={hl}mm", f"TCD={tcd}mm", f"LV={lv}mm",
        f"AFI={afi}mm", f"AFVmax={afv_max}mm",
        f"胎盘={placenta_pos},{placenta_grade},{placenta_thick}mm",
        f"胎心={hr}bpm",
    ]
    if findings:
        answer_parts.append(f"异常={';'.join(findings)}")
    else:
        answer_parts.append("异常=无")
    answer_parts.append(f"结构={';'.join(random.sample(structures_visible, 8))}")

    structured = '|'.join(answer_parts)

    # 构建自然语言描述
    desc = (
        f"孕{ga}, 胎儿双顶径{bpd}mm, 头围{hc}mm, 腹围{ac}mm, "
        f"股骨长{fl}mm, 肱骨长{hl}mm, 小脑横径{tcd}mm, "
        f"侧脑室宽{lv}mm, 羊水指数{afi}mm, 最大羊水深度{afv_max}mm, "
        f"胎盘位于{placenta_pos}, 成熟度{placenta_grade}, 厚{placenta_thick}mm, "
        f"胎心{hr}次每分。"
    )
    if findings:
        desc += ' ' + '; '.join(findings) + '。'
    desc += ' ' + '。'.join(random.sample(structures_visible, 6)) + '。'

    return desc, structured


# ============================================================
# B: 胎儿专项心脏彩超
# ============================================================
def gen_fetal_echo():
    ga_week = random.randint(22, 28)
    ga_day = random.randint(0, 6)
    ga = f"{ga_week}周{ga_day}天" if ga_day > 0 else f"{ga_week}周"
    hr = random.randint(120, 160)
    ctr = rand_val(0.28, 0.35, 2)  # 心/胸比

    # 各瓣口血流
    mv_e = rand_val(20, 40)
    mv_a = rand_val(30, 50)
    tv_e = rand_val(20, 40)
    tv_a = rand_val(30, 50)
    av_vel = rand_val(60, 100)
    pv_vel = rand_val(50, 90)
    dao_vel = rand_val(70, 120)

    # 结构
    normal_findings = [
        '四腔心可见, 心轴正常', '左右心室大小对称',
        '室间隔完整', '房间隔见卵圆孔, 瓣膜活动好',
        '二尖瓣形态正常', '三尖瓣形态正常',
        '主动脉骑跨未见异常', '肺动脉与主动脉比例正常',
        '主动脉弓完整', '动脉导管开放',
        '上下腔静脉引流入右心房', '肺静脉引流入左心房',
        '心包未见积液',
    ]

    abnormal = []
    if random.random() < 0.1:
        abnormal.append(random.choice([
            f'室间隔缺损, {rand_val(1.5, 3.5)}mm',
            f'三尖瓣反流, 轻度, 流速{rand_val(180, 250)}cm/s',
            f'肺动脉瓣狭窄, 流速{rand_val(200, 350)}cm/s',
            '永存左上腔静脉',
            f'右心室流出道流速偏快, {rand_val(120, 180)}cm/s',
        ]))

    answer_parts = [
        f"GA={ga}", f"HR={hr}bpm", f"CTR={ctr}",
        f"MV_E={mv_e}cm/s", f"MV_A={mv_a}cm/s",
        f"TV_E={tv_e}cm/s", f"TV_A={tv_a}cm/s",
        f"AV={av_vel}cm/s", f"PV={pv_vel}cm/s", f"DAO={dao_vel}cm/s",
    ]
    if abnormal:
        answer_parts.append(f"异常={';'.join(abnormal)}")
    else:
        answer_parts.append("异常=无")
    answer_parts.append(f"结构={';'.join(random.sample(normal_findings, 6))}")

    structured = '|'.join(answer_parts)

    desc = (
        f"孕{ga}, 胎心{hr}次每分, 心胸面积比{ctr}, "
        f"二尖瓣血流E峰{mv_e}cm/s, A峰{mv_a}cm/s, "
        f"三尖瓣血流E峰{tv_e}cm/s, A峰{tv_a}cm/s, "
        f"主动脉瓣上流速{av_vel}cm/s, 肺动脉瓣上流速{pv_vel}cm/s, "
        f"降主动脉流速{dao_vel}cm/s。"
    )
    if abnormal:
        desc += ' ' + '; '.join(abnormal) + '。'
    desc += ' ' + '。'.join(random.sample(normal_findings, 5)) + '。'

    return desc, structured


# ============================================================
# C: 成人全套经胸心超
# ============================================================
def gen_adult_echo():
    male = random.random() < 0.5
    age = random.randint(25, 78)

    # 测量值
    lvedd = rand_val(42, 56) if male else rand_val(38, 50)
    lvesd = rand_val(24, 38)
    ivs = rand_val(7, 11)
    lvpw = rand_val(7, 11)
    la = rand_val(28, 38)
    ao = rand_val(26, 36)
    rv = rand_val(18, 28)
    ra = rand_val(30, 42)
    ef = rand_val(55, 72)
    fs = rand_val(28, 40)
    ea = rand_val(0.8, 2.0, 2)

    # 瓣膜流速
    mv_e_vel = rand_val(60, 100)
    av_vel = rand_val(100, 170)
    pv_vel = rand_val(60, 100)
    tv_vel = rand_val(40, 70)

    # 常见异常
    abnormal = []
    if random.random() < 0.25:
        abnormal.append(random.choice([
            f'二尖瓣反流, 轻度, 反流面积{rand_val(2, 4, 1)}cm²',
            f'主动脉瓣反流, 轻度, 压差半降时间{rand_val(400, 600)}ms',
            f'三尖瓣反流, 轻度, 估测肺动脉收缩压{rand_val(28, 38)}mmHg',
            f'室间隔基底部增厚, {rand_val(12, 14)}mm',
            '左心室舒张功能减退, E/A<1',
            f'升主动脉增宽, 内径{rand_val(38, 42)}mm',
            '心包少量积液',
            f'左心房增大, 前后径{rand_val(40, 45)}mm',
        ]))

    answer_parts = [
        f"性别={'男' if male else '女'}", f"年龄={age}",
        f"LVEDD={lvedd}mm", f"LVESD={lvesd}mm",
        f"IVS={ivs}mm", f"LVPW={lvpw}mm",
        f"LA={la}mm", f"AO={ao}mm", f"RV={rv}mm", f"RA={ra}mm",
        f"EF={ef}%", f"FS={fs}%", f"E/A={ea}",
        f"MV_E={mv_e_vel}cm/s", f"AV={av_vel}cm/s",
        f"PV={pv_vel}cm/s", f"TV={tv_vel}cm/s",
    ]
    if abnormal:
        answer_parts.append(f"异常={';'.join(abnormal)}")
    else:
        answer_parts.append("异常=无")

    structured = '|'.join(answer_parts)

    gender_str = '男' if male else '女'
    desc = (
        f"{gender_str}性, {age}岁, 左心室舒张末期内径{lvedd}mm, "
        f"左心室收缩末期内径{lvesd}mm, 室间隔厚度{ivs}mm, "
        f"左室后壁厚度{lvpw}mm, 左心房前后径{la}mm, "
        f"主动脉根部内径{ao}mm, 右心室前后径{rv}mm, "
        f"右心房左右径{ra}mm, 射血分数EF{ef}%, "
        f"缩短分数FS{fs}%, 二尖瓣E/A比值{ea}。"
    )
    desc += (
        f" 二尖瓣血流E峰流速{mv_e_vel}cm/s, "
        f"主动脉瓣前向流速{av_vel}cm/s, "
        f"肺动脉瓣前向流速{pv_vel}cm/s, "
        f"三尖瓣反流流速{tv_vel}cm/s。"
    )
    if abnormal:
        desc += ' ' + '; '.join(abnormal) + '。'

    return desc, structured


# ============================================================
# D: 颈 + 双上下肢动静脉全套
# ============================================================
def gen_vascular():
    age = random.randint(40, 75)
    male = random.random() < 0.5

    # 颈动脉
    cca_right_imt = rand_val(0.5, 1.1, 2)
    cca_left_imt = rand_val(0.5, 1.1, 2)
    cca_right_d = rand_val(5.5, 7.5, 1)
    cca_left_d = rand_val(5.5, 7.5, 1)
    ica_psv_r = rand_val(50, 90)
    ica_edv_r = rand_val(15, 30)
    ica_ri_r = rand_val(0.55, 0.75, 2)
    ica_psv_l = rand_val(50, 90)
    ica_edv_l = rand_val(15, 30)
    ica_ri_l = rand_val(0.55, 0.75, 2)
    va_d_r = rand_val(2.5, 3.8, 1)
    va_d_l = rand_val(2.5, 3.8, 1)

    # 下肢动脉
    cfa_psv = rand_val(80, 120)
    pop_psv = rand_val(50, 80)
    pta_psv = rand_val(40, 65)
    dpa_psv = rand_val(35, 60)

    abnormal = []
    if random.random() < 0.3:
        abnormal.append(random.choice([
            f'右侧颈总动脉分叉处斑块, {rand_val(8, 15, 1)}mm×{rand_val(1.5, 3.0, 1)}mm, 混合回声',
            f'左侧颈内动脉起始部斑块, {rand_val(6, 12, 1)}mm, 低回声',
            f'右侧颈总动脉IMT增厚, {rand_val(1.1, 1.5, 2)}mm',
            f'双侧颈动脉粥样硬化并斑块形成',
            f'右侧椎动脉管径纤细, {rand_val(1.8, 2.3, 1)}mm',
            f'左侧锁骨下动脉起始处斑块, 狭窄率{rand_val(30, 50)}%',
            f'右侧股浅动脉斑块, {rand_val(10, 18, 1)}mm',
            f'左侧下肢动脉粥样硬化, 多发斑块',
            f'右侧胫前动脉流速减低, PSV{rand_val(25, 35)}cm/s',
            f'双侧股总静脉瓣膜功能不全, 反流时间{rand_val(1.0, 2.5, 2)}s',
        ]))

    answer_parts = [
        f"年龄={age}", f"性别={'男' if male else '女'}",
        f"CCA_R_IMT={cca_right_imt}mm", f"CCA_L_IMT={cca_left_imt}mm",
        f"CCA_R_D={cca_right_d}mm", f"CCA_L_D={cca_left_d}mm",
        f"ICA_R_PSV={ica_psv_r}cm/s", f"ICA_R_EDV={ica_edv_r}cm/s", f"ICA_R_RI={ica_ri_r}",
        f"ICA_L_PSV={ica_psv_l}cm/s", f"ICA_L_EDV={ica_edv_l}cm/s", f"ICA_L_RI={ica_ri_l}",
        f"VA_R_D={va_d_r}mm", f"VA_L_D={va_d_l}mm",
        f"CFA_PSV={cfa_psv}cm/s", f"POP_PSV={pop_psv}cm/s",
        f"PTA_PSV={pta_psv}cm/s", f"DPA_PSV={dpa_psv}cm/s",
    ]
    if abnormal:
        answer_parts.append(f"异常={';'.join(abnormal)}")
    else:
        answer_parts.append("异常=无")

    structured = '|'.join(answer_parts)

    gender_str = '男' if male else '女'
    desc = (
        f"{gender_str}性, {age}岁, "
        f"右侧颈总动脉内中膜厚度{cca_right_imt}mm, 管径{cca_right_d}mm, "
        f"左侧颈总动脉内中膜厚度{cca_left_imt}mm, 管径{cca_left_d}mm, "
        f"右侧颈内动脉PSV{ica_psv_r}cm/s, EDV{ica_edv_r}cm/s, RI{ica_ri_r}, "
        f"左侧颈内动脉PSV{ica_psv_l}cm/s, EDV{ica_edv_l}cm/s, RI{ica_ri_l}, "
        f"右侧椎动脉内径{va_d_r}mm, 左侧椎动脉内径{va_d_l}mm。"
    )
    desc += (
        f" 双侧股总动脉PSV{cfa_psv}cm/s, 腘动脉PSV{pop_psv}cm/s, "
        f"胫后动脉PSV{pta_psv}cm/s, 足背动脉PSV{dpa_psv}cm/s。"
    )
    if abnormal:
        desc += ' ' + '; '.join(abnormal) + '。'

    return desc, structured


# ============================================================
# E: 全腹 + 腹膜后 + 腹腔血管彩超
# ============================================================
def gen_abdomen():
    age = random.randint(30, 70)
    male = random.random() < 0.5

    # 肝脏
    liver_rl = rand_val(110, 140)  # 右叶斜径
    liver_thick = rand_val(80, 110)
    liver_echo = random.choice(['均匀', '均匀', '均匀', '稍增粗'])

    # 胆囊
    gb_long = rand_val(55, 80)
    gb_wide = rand_val(22, 35)
    gb_wall = rand_val(2, 3, 1)

    # 胰腺
    panc_head = rand_val(18, 25)
    panc_body = rand_val(10, 18)
    panc_tail = rand_val(10, 20)

    # 脾
    spleen_thick = rand_val(28, 38)
    spleen_long = rand_val(85, 110)

    # 双肾
    rk_long = rand_val(95, 115)
    rk_wide = rand_val(45, 58)
    rk_thick = rand_val(38, 48)
    lk_long = rand_val(95, 115)
    lk_wide = rand_val(45, 58)
    lk_thick = rand_val(38, 48)

    # 血管
    pv_d = rand_val(9, 12, 1)
    sma_psv = rand_val(100, 160)
    sma_ri = rand_val(0.75, 0.90, 2)
    ao_d = rand_val(16, 22)
    ivc_d = rand_val(14, 20)

    abnormal = []
    if random.random() < 0.35:
        abnormal.append(random.choice([
            f'脂肪肝, {random.choice(["轻度", "中度"])}',
            f'肝囊肿, 右叶, {rand_val(8, 25)}mm×{rand_val(6, 20)}mm, 无回声',
            f'胆囊息肉, {rand_val(3, 8)}mm, 不移动',
            f'胆囊结石, {rand_val(4, 12)}mm, 强回声伴声影',
            f'右肾囊肿, {rand_val(10, 30)}mm, 无回声',
            f'左肾结石, {rand_val(3, 7)}mm, 强回声',
            f'脾大, 厚{rand_val(42, 50)}mm',
            f'门静脉增宽, 内径{rand_val(13, 15)}mm',
            f'腹主动脉粥样硬化, 斑块{rand_val(8, 15)}mm',
            f'肾动脉狭窄, PSV{rand_val(200, 350)}cm/s',
            f'前列腺增生, {rand_val(35, 50)}mm×{rand_val(30, 42)}mm×{rand_val(28, 38)}mm',
            f'子宫肌瘤, {rand_val(20, 45)}mm×{rand_val(15, 35)}mm, 低回声',
        ]))

    answer_parts = [
        f"年龄={age}", f"性别={'男' if male else '女'}",
        f"肝右叶斜径={liver_rl}mm", f"肝厚={liver_thick}mm", f"肝回声={liver_echo}",
        f"胆囊={gb_long}mm×{gb_wide}mm", f"胆囊壁={gb_wall}mm",
        f"胰头={panc_head}mm", f"胰体={panc_body}mm", f"胰尾={panc_tail}mm",
        f"脾厚={spleen_thick}mm", f"脾长={spleen_long}mm",
        f"右肾={rk_long}mm×{rk_wide}mm×{rk_thick}mm",
        f"左肾={lk_long}mm×{lk_wide}mm×{lk_thick}mm",
        f"门静脉={pv_d}mm", f"SMA_PSV={sma_psv}cm/s", f"SMA_RI={sma_ri}",
        f"腹主动脉={ao_d}mm", f"下腔静脉={ivc_d}mm",
    ]
    if abnormal:
        answer_parts.append(f"异常={';'.join(abnormal)}")
    else:
        answer_parts.append("异常=无")

    structured = '|'.join(answer_parts)

    gender_str = '男' if male else '女'
    desc = (
        f"{gender_str}性, {age}岁, "
        f"肝脏右叶斜径{liver_rl}mm, 肝实质回声{liver_echo}, "
        f"胆囊大小{gb_long}mm×{gb_wide}mm, 壁厚{gb_wall}mm, "
        f"胰腺头{int(panc_head)}mm体{int(panc_body)}mm尾{int(panc_tail)}mm, "
        f"脾厚{spleen_thick}mm长径{spleen_long}mm, "
        f"右肾{rk_long}mm×{rk_wide}mm×{rk_thick}mm, "
        f"左肾{lk_long}mm×{lk_wide}mm×{lk_thick}mm。"
    )
    desc += (
        f" 门静脉主干内径{int(pv_d)}mm, "
        f"肠系膜上动脉PSV{int(sma_psv)}cm/s, RI{round(sma_ri, 2)}, "
        f"腹主动脉内径{int(ao_d)}mm, 下腔静脉内径{int(ivc_d)}mm。"
    )
    if abnormal:
        desc += ' ' + '; '.join(abnormal) + '。'

    return desc, structured


# ============================================================
# 生成器注册表
# ============================================================
GENERATORS = {
    'A': ('中孕期胎儿系统大排畸', gen_fetal_anomaly),
    'B': ('胎儿专项心脏彩超', gen_fetal_echo),
    'C': ('成人全套经胸心超', gen_adult_echo),
    'D': ('颈+双上下肢动静脉全套', gen_vascular),
    'E': ('全腹+腹膜后+腹腔血管彩超', gen_abdomen),
}

# ============================================================
# 输出函数
# ============================================================
def write_dataset(filename, records):
    """records: list of (idx, asr_text, template, structured_answer)"""
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("序号|ASR语音错写文本|归属模板|标准答案结构化字段\n")
        for idx, asr_text, template, structured in records:
            # Escape pipe in text
            asr_text = asr_text.replace('|', '/')
            structured = structured.replace('|', '/')
            f.write(f"{idx}|{asr_text}|{template}|{structured}\n")
    print(f"  -> {path} ({len(records)} 条)")

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("超声ASR评测数据集生成器")
    print("=" * 60)

    # ---- 第1轮: 100条混合样本 ----
    print("\n[1/6] 生成 100 条混合随机样本...")
    mixed_records = []
    templates_cycle = ['A', 'B', 'C', 'D', 'E'] * 20  # 100条, 每类20条
    random.shuffle(templates_cycle)

    for idx in range(1, 101):
        t = templates_cycle[idx - 1]
        t_name, gen_func = GENERATORS[t]
        clean_desc, structured = gen_func()
        # 应用不同级别的ASR噪声
        error_level = random.uniform(0.08, 0.30)
        asr_text = inject_asr_noise(clean_desc, error_level)
        mixed_records.append((idx, asr_text, t, structured))

    write_dataset("01_mixed_100.csv", mixed_records)

    # ---- 第2轮: 5×3000条专项样本 ----
    for t_code in ['A', 'B', 'C', 'D', 'E']:
        t_name, gen_func = GENERATORS[t_code]
        filename = f"02_template_{t_code}_3000.csv"
        print(f"\n[{['A','B','C','D','E'].index(t_code)+2}/6] 生成 {t_name} 3000条...")

        records = []
        for idx in range(1, 3001):
            clean_desc, structured = gen_func()
            # 多样化噪声水平
            if idx % 5 == 0:
                error_level = random.uniform(0.02, 0.08)  # 较干净
            elif idx % 5 == 1:
                error_level = random.uniform(0.25, 0.40)  # 高噪声
            else:
                error_level = random.uniform(0.10, 0.25)  # 中等
            asr_text = inject_asr_noise(clean_desc, error_level)
            records.append((idx, asr_text, t_code, structured))

        write_dataset(filename, records)

    print("\n" + "=" * 60)
    print("全部生成完成! 文件列表:")
    for f in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, f)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {f} ({size_kb:.1f} KB)")
    print("=" * 60)


if __name__ == '__main__':
    main()
