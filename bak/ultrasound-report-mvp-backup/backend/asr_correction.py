"""ASR 后处理纠错引擎 — 4层级联纠正

第1层: 混淆词典直接替换 (401条 wrong→correct)
第2层: 数值标准化 (单位/小数/数字格式)
第3层: 模式修正 (结构/标点)
第4层: 幻觉清洗 (ASR流式重复/无意义串)
"""

import re


def apply_unit_conversions(text: str) -> str:
    """
    应用单位转换规则 (从 knowledge/unit_conversion.json 加载)
    
    规则中的 \\x01 表示捕获组1的占位符。
    对于 type="multiply" 的规则，使用 factor 进行数值乘法。
    """
    try:
        from knowledge.loader import get_kb
        unit_rules = get_kb().unit_rules
    except Exception:
        unit_rules = {}
    
    if not unit_rules:
        # 回退到硬编码规则
        text = re.sub(r"(\d+(?:\.\d+)?)\s*公分", r"\1cm", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*公厘", r"\1mm", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:豪|毫)米", r"\1mm", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:离|厘)米", r"\1cm", text)
        text = re.sub(r"(\d+)毫米", r"\1mm", text)
        text = re.sub(r"(\d+)厘米", r"\1cm", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*公斤", lambda m: str(int(float(m.group(1))*1000))+'克', text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:kg|千克)", lambda m: str(int(float(m.group(1))*1000))+'克', text, flags=re.IGNORECASE)
        text = text.replace('平面', '平段')
        return text
    
    # 按规则类型处理
    for rule_id, rule in unit_rules.items():
        pattern = rule.get("pattern", "")
        replace = rule.get("replace", "")
        rule_type = rule.get("type", "")
        factor = rule.get("factor", 1)
        
        if not pattern:
            continue
        
        # 处理 \x01 占位符 (替换为正则反向引用 \1)
        replace = replace.replace('\x01', r'\1')
        
        if rule_type == "multiply":
            # 数值乘法规则 (如 公斤→克): 提取 \x01 后的单位后缀 (去掉数字和运算符)
            suffix = re.sub(r'^[\d\.\*\+x]+', '', replace.split('\\1')[-1]) if '\\1' in replace else ''
            def _multiply_replace(m, f=factor, s=suffix):
                try:
                    val = float(m.group(1))
                    result = val * f
                    return str(int(result)) + s
                except (ValueError, IndexError):
                    return m.group(0)
            text = re.sub(pattern, _multiply_replace, text)
        else:
            # 普通替换规则
            text = re.sub(pattern, replace, text)
    
    return text

# ========== 混淆词典 ==========
CONFUSION_DICT = {
    "肝脏":["肝藏","肝张","肝章","干脏","甘藏"],
    "胆囊":["胆郎","胆狼","胆朗","单囊","胆廊"],
    "胆总管":["胆肿冠","胆总关"],
    "胰腺":["一线","胰限","遗限","一现"],
    "胰头":["一头","遗头","以头","姨头"],
    "脾脏":["皮脏","脾张","皮张"],
    "肾脏":["慎脏","肾张","甚脏"],
    "肾皮质":["慎皮质","肾皮脂","甚皮质"],
    "膀胱":["旁光","膀光","旁观"],
    "前列腺":["前裂线","前列线","千列线"],
    "子宫":["子工","子公","自宫","紫宫"],
    "卵巢":["卵朝","栾巢","卵潮","乱巢"],
    "输卵管":["输暖管","书卵管","舒卵管"],
    "盆腔":["盆墙","盆强","喷墙"],
    "宫腔":["工腔","公腔","弓腔"],
    "甲状腺":["甲状县","甲装线","假状线"],
    "乳腺":["如县","乳线","汝县"],
    "淋巴结":["林巴结","淋疤节","林八节"],
    "阑尾":["拦尾","蓝尾","览尾"],
    "腹腔":["富强","复强","腹强"],
    "胸腔":["胸墙","凶腔"],
    "囊肿":["囊种","囊重","囊中","郎肿","囊肿"],
    "结石":["节食","接石","结时","节时"],
    "息肉":["吸肉","西肉","洗肉"],
    "钙化":["概化","改化","钙话","盖化"],
    "积液":["及夜","急夜","几夜","积夜"],
    "腹水":["富水","复水","浮水"],
    "占位":["战位","沾位","展位","占未"],
    "肿瘤":["种留","中留","仲瘤"],
    "结节":["接节","洁洁","节节","结杰","节结"],
    "血管瘤":["血关留","写管留","血管留"],
    "脂肪肝":["脂房干","之房甘","枝房肝"],
    "肝硬化":["干硬化","甘硬化","杆硬化"],
    "肝囊肿":["肝郎肿","干囊肿","甘囊肿"],
    "胆囊壁":["胆郎壁","胆囊必","胆狼壁","胆囊逼"],
    "胆囊炎":["胆郎炎","胆狼言","胆囊言"],
    "胆结石":["胆节食","胆结石"],
    "肝内胆管":["肝内胆关","甘内胆管"],
    "肾结石":["慎结石","肾节食","深结石"],
    "肾积水":["肾及水","慎急水","深积水","肾集水"],
    "肾盂":["肾雨","慎盂","甚盂","肾鱼"],
    "输尿管":["书尿管","输尿关","书尿关"],
    "前列腺增生":["前裂线增生","前列线增声"],
    "子宫肌瘤":["子工基留","自宫肌瘤","子宫及留","子公肌留"],
    "子宫内膜":["子工内膜","自宫内模"],
    "卵巢囊肿":["卵朝囊种","乱巢囊重","栾巢囊肿"],
    "多囊卵巢":["多囊卵朝","多郎卵巢"],
    "子宫腺肌症":["子工线急症","子宫线肌症"],
    "盆腔积液":["盆墙积液","喷强及夜"],
    "异位妊娠":["一位妊娠","已位妊娠","以为妊娠"],
    "中孕":["中运","中韵","中蕴"],
    "早孕":["早运","早韵"],
    "晚孕":["晚运","晚韵"],
    "妊娠":["认身","任深","人神","人身"],
    "孕期":["运期","韵期","云期"],
    "中孕期":["中运期","中韵期"],
    "早孕期":["早运期","早韵期"],
    "四维":["思维","四位","四点维","是维","四为"],
    "排畸":["排机","排击","牌机","排鸡"],
    "彩超":["采超","彩抄","才超","菜超"],
    "B超":["必超","笔超","碧超"],
    "产科":["产可","产颗","禅科"],
    "妇科":["妇颗","复科","富科"],
    "胎儿":["台儿","胎而","泰儿"],
    "胎盘":["胎潘","太盘","台盘"],
    "脐带":["期待","奇带","其带","脐戴"],
    "羊水":["洋水","杨水","阳水","洋随"],
    "羊水指数":["洋水指数","杨水止数","阳水指书"],
    "双顶径":["双顶经","双定径","伤顶径"],
    "头围":["头为","头未","投围"],
    "腹围":["父围","富围","副围"],
    "股骨长":["股骨常","古骨长","鼓骨长"],
    "肱骨长":["红骨长","工骨常","公骨长"],
    "胎心":["台心","太心","态心"],
    "胎心率":["台心率","太心率","态心率"],
    "绕颈":["扰颈","绕经","绕紧","扰经","扰紧"],
    "未见绕颈":["未见扰颈","未见绕经","未见扰经","未见绕紧"],
    "头位":["投喂","头卫","头未"],
    "臀位":["屯位","豚位"],
    "横位":["恒位","衡位"],
    "前壁":["钱壁","前必","千壁"],
    "后壁":["后必","厚壁","候壁"],
    "左壁":["左必","佐壁"],
    "右壁":["右必","又壁"],
    "血栓":["血拴","写栓","雪栓"],
    "狭窄":["狭载","峡窄","侠窄"],
    "扩张":["扩长","阔张","括张"],
    "反流":["返流","反留"],
    "血栓形成":["血拴形成","写栓行程","雪栓形成"],
    "心律失常":["心率失常","心理失常"],
    "无回声":["无回生","吴回声","五回声"],
    "低回声":["低回生","底回声","狄回声"],
    "高回声":["高回生","高会生"],
    "强回声":["强回生","墙回声","强会生"],
    "混合回声":["混合回生","魂和会生"],
    "回声均匀":["回声军云","回生均匀","会声均匀"],
    "回声不均匀":["回声不均","回生不均","回声部均"],
    "回声增强":["回声增墙","回声争强"],
    "边界清晰":["边境清晰","边接清洗","边界清希"],
    "边界模糊":["边接模糊","边境模狐","边界磨糊"],
    "形态规则":["形态归则","形太规则"],
    "形态不规则":["形态不归则","形太不规则"],
    "后方声影":["后方呻吟","后方身影","后方申影"],
    "后方增强":["后方增墙","后方争强"],
    "后方衰减":["后方摔减","后方衰简"],
    "声影":["呻吟","身影","申影","深影"],
    "透声好":["头声好","透生好"],
    "透声差":["头声差","透生查"],
    "血流信号":["血留信号","写流信号","血流信好"],
    "丰富血流":["丰富血留","风富血流"],
    "包膜完整":["包模完整","薄模完整"],
    "毫米":["好米","豪米","颢米"],
    "厘米":["离米","礼米","理米"],
    "公分":["工分","公份"],
    "前后径":["前后经","前后精"],
    "未见异常":["未见已常","未见异长"],
    "未见明显异常":["未见名显异常","未见明天异常"],
    "大小正常":["大小正长","大小政常"],
    "毛糙":["毛操","毛草","毛曹"],
    "光滑":["光华","光花","广滑"],
    "增厚":["增后","曾厚","增侯"],
    "变厚":["变后","便厚"],
    "分离":["分立","芬离","分理"],
    "回声":["回生","会声"],
    "清晰":["清希","青晰","轻晰"],
    "粗糙":["粗操","初糙"],
    "弥漫":["迷漫","米漫","迷慢"],
    "增大":["增大","蒸大","曾大","增大"],
    "减小":["减小","减少"],
    "畸形":["机型","畸型"],
    "畸形儿":["机型二","畸形而"],
    "单活胎":["单火台","担活胎","单活台"],
    "U形":["优形","U型"],
    "W形":["大不了形","W型"],
    "绕颈一圈":["扰颈一圈","绕经一圈","扰经一圈"],
    "绕颈两周":["扰颈两周","绕经两周"],
    # ASR空格展开
    "RI":["R I","R  I","A I"],
    "PI":["P I","P  I","T I","T  I"],
    "S/D":["S D","S  D","S/D"],
    # 单位转换标记（数值后跟kg/公斤时触发L2）
}

# 构建快速查表: wrong → correct
CONFUSION_MAP = {}
for correct, wrongs in CONFUSION_DICT.items():
    for w in wrongs:
        if w not in CONFUSION_MAP or len(correct) <= len(CONFUSION_MAP.get(w, "")):
            CONFUSION_MAP[w] = correct

# 幻觉词语列表
HALLUCINATION = [
    "建板郎","见板郎","见板囊","建板囊",
    "相三三","香三三","象三三",
    "做做腹部彩超","采做腹部彩超","座座腹部彩超",
    "做做腹部","采做腹部","座座腹部",
    "所建建板","所建见板",
    "压缩到","压缩","压到",
    "做做","左左","采做",
]



def correct_ASR_text(text: str) -> str:
    """4层级联纠正 (v2: L1+L1.5并行, 纯数值跳过L3/L4)"""
    corrected, _ = correct_ASR_text_with_stats(text)
    return corrected


def correct_ASR_text_with_stats(text: str) -> tuple:
    """4层级联纠正 + 逐层编辑统计

    Returns:
        (corrected_text, stats_dict)
        stats_dict: {"edits": int, "l1": int, "l15": int, "l2": int, "l3": int, "l4": int, "rate": float}
    """
    if not text or not text.strip():
        return text, {"edits": 0, "l1": 0, "l15": 0, "l2": 0, "l3": 0, "l4": 0, "rate": 0.0}

    text = text.strip()
    stats = {"l1": 0, "l15": 0, "l2": 0, "l3": 0, "l4": 0}

    # L1 + L1.5: 混淆词典 + 中文数字转换 (串行)
    from cn_num import cn_to_arabic

    def _l1_correct(t):
        """L1: 混淆词典替换 (统计替换次数)"""
        count = 0
        for wrong in sorted(CONFUSION_MAP.keys(), key=len, reverse=True):
            if wrong in t:
                n = t.count(wrong)
                count += n
                t = t.replace(wrong, CONFUSION_MAP[wrong])
        stats["l1"] = count
        return t

    def _l15_correct(t):
        """L1.5: 中文数字转阿拉伯 (统计转换次数)"""
        import cn_num as _cn
        before = t
        result = _cn.cn_to_arabic(t)
        # 统计: 每次中文数字序列被替换为阿拉伯数字算 1 次编辑
        if result != before:
            import re as _re
            stats["l15"] = len(_re.findall(r'[零一二三四五六七八九十百千万亿]+', before))
        return result

    text = _l1_correct(text)
    text = _l15_correct(text)

    # L2: 数值标准化 (统计每次正则命中)
    def _l2_count_sub(pattern, repl, t, flags=0):
        n = len(re.findall(pattern, t, flags))
        stats["l2"] += n
        return re.sub(pattern, repl, t, flags=flags)

    text = _l2_count_sub(
        r'[零一二三四五六七八九]点[零一二三四五六七八九]',
        lambda m: m.group().replace('点', '.').translate(str.maketrans({'零': '0', '一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9'})),
        text)
    text = _l2_count_sub(r"(\d+)点(\d+)", r"\1.\2", text)
    text = _l2_count_sub(r"零点(\d)", r"0.\1", text)
    # L2.5: 单位转换
    before_unit = text
    text = apply_unit_conversions(text)
    if text != before_unit:
        stats["l2"] += 1
    text = _l2_count_sub(r"(\d)\s*[xX\*乘]\s*(\d)", r"\1×\2", text)
    text = _l2_count_sub(r"(\d+)\s*[到至\-~为]\s*(\d+)", r"\1-\2", text)

    # P2-4: 纯数值短路
    digit_ratio = sum(1 for c in text if c in '0123456789.mmcx×- ') / max(len(text), 1)
    if digit_ratio < 0.8:
        # L3: 模式修正
        def _l3_count_sub(pattern, repl, t, flags=0):
            n = len(re.findall(pattern, t, flags))
            stats["l3"] += n
            return re.sub(pattern, repl, t, flags=flags)

        text = _l3_count_sub(r"TI\s*[-–]\s*RADS", "TI-RADS", text, re.IGNORECASE)
        text = _l3_count_sub(r"[Ss]\s*[/／]\s*[Dd]\s*[：:＝=]?\s*(\d)", r"S/D \1", text)
        text = _l3_count_sub(r"RI\s*[Ii1l]\s*[：:＝=]?\s*(\d)", r"RI \1", text)
        text = _l3_count_sub(r"TI\s*[：:＝=]?\s*(\d)", r"TI \1", text)
        text = _l3_count_sub(r"PI\s*[：:＝=]?\s*(\d)", r"PI \1", text)
        text = _l3_count_sub(r"Vma[x×X]\s*[：:＝=]?\s*(\d)", r"Vmax \1", text)
        text = _l3_count_sub(r"(\d+)\s*[次ci]?\s*[/／]\s*分", r"\1次/分", text)
        text = _l3_count_sub(r"[一1]级", "I级", text)
        text = _l3_count_sub(r"[二2]级", "II级", text)
        text = _l3_count_sub(r"[三3]级", "III级", text)
        text = _l3_count_sub(r"(\d)[豪毫][米迷]", r"\1mm", text)
        text = _l3_count_sub(r"([。，、])\1+", r"\1", text)
        text = _l3_count_sub(r"(?<!\d)心(\d{2,3})(?!\d)", r"胎心\1", text)

        # L4: 幻觉清洗
        for hw in HALLUCINATION:
            if hw in text:
                n = text.count(hw)
                stats["l4"] += n
                text = text.replace(hw, "")
        before_l4_tail = text
        text = re.sub(r"腹部\s*彩\s*超", "腹部彩超", text)
        text = re.sub(r"腹部B超", "腹部超声", text)
        if text != before_l4_tail:
            stats["l4"] += 1

    # 收尾
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"([。，、；：])\s*", r"\1", text)

    total_edits = stats["l1"] + stats["l15"] + stats["l2"] + stats["l3"] + stats["l4"]
    stats["edits"] = total_edits
    stats["rate"] = total_edits / max(len(text), 1)

    return text.strip(), stats
