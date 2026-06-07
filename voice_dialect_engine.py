#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方言处理引擎 - 三合一：数据增强+拼音模糊匹配+自学习
纯Python，零依赖
"""
import re, json, random, os
from collections import defaultdict

PINYIN_DICT = {
    "结石":"jie2 shi2","囊肿":"nang2 zhong3","结节":"jie2 jie2",
    "回声":"hui2 sheng1","肾脏":"shen4 zang4","团块":"tuan2 kuai4",
    "边界":"bian1 jie4","形态":"xing2 tai4","血流":"xue4 liu2",
    "分级":"fen1 ji2","光滑":"guang1 hua2","均匀":"jun1 yun2",
    "增强":"zeng1 qiang2","衰减":"shuai1 jian3","正常":"zheng4 chang2",
    "清晰":"qing1 xi1","规则":"gui1 ze2","肝脏":"gan1 zang4",
    "胆囊":"dan3 nang2","甲状腺":"jia3 zhuang4 xian4","前列腺":"qian2 lie4 xian4",
}

ACCENT_MAP = {
    "zh":"z","z":"zh","ch":"c","c":"ch","sh":"s","s":"sh",
    "n":"l","l":"n","r":"z",
    "in":"ing","ing":"in","en":"eng","eng":"en",
}

DIALECT_NOUNS = {
    "结石":["石头","石子"],"囊肿":["水泡泡","水包"],"结节":["包包","疙瘩","坨坨"],
    "肾脏":["腰子"],"回声":["回音"],"团块":["坨坨"],
    "未见明显":["没得","莫得","没看到"],"边界清晰":["边界清","边界好"],
    "形态规则":["形态好","规整"],"颈部":["头头"],
}

FILLERS = ["嗯","让我看看","我想想","看一哈","等一下"]
PATIENT_TALK = ["放松点哈","不要紧张","忍一下","深呼吸","痛不痛"]


def accent_variants(word):
    """生成方言拼音变体"""
    py = PINYIN_DICT.get(word, word)
    variants = {py}
    for s, a in ACCENT_MAP.items():
        alt = py.replace(s, a)
        if alt != py:
            variants.add(alt)
    return variants


class DialectEngine:
    def __init__(self):
        self.noun_map = {}
        for std, dials in DIALECT_NOUNS.items():
            for d in dials:
                self.noun_map[d] = std
        self.learned = {}
        self.log = []

    # ------ 数据增强 ------
    def gen_variants(self, text, count=5):
        out = []
        for _ in range(count):
            t = text
            for std, dials in DIALECT_NOUNS.items():
                if std in t and random.random() < 0.35:
                    t = t.replace(std, random.choice(dials), 1)
            if random.random() < 0.25:
                t = random.choice(FILLERS) + "，" + t
            if random.random() < 0.1:
                t = t + "。" + random.choice(PATIENT_TALK)
            out.append(t)
        return out

    # ------ 方言标准化 ------
    def normalize(self, text):
        t = text
        # L1: 精确词映射
        for dial, std in {**self.noun_map, **self.learned}.items():
            t = t.replace(dial, std)
        # L1b: 中文数字
        dm = {"零":"0","一":"1","二":"2","三":"3","四":"4","五":"5","六":"6","七":"7","八":"8","九":"9","十":"10"}
        t = re.sub(r'点([一二三四五六七八九])', lambda m: '.' + dm[m.group(1)], t)
        t = re.sub(r'零([一二三四五六七八九])', lambda m: '0.' + dm[m.group(1)], t)
        for cn, num in dm.items():
            t = re.sub(cn + r'点([0-9])', num + r'.', t)
        # L2: 拼音模糊匹配 (通过读音识别方言词汇)
        for word, py in PINYIN_DICT.items():
            base = re.sub(r'[0-9]', '', py)
            for var in accent_variants(word):
                var_base = re.sub(r'[0-9]', '', var)
                if var_base in t and word not in t:
                    t = t.replace(var_base, word)
        return t

    # ------ 自学习 ------
    def learn(self, raw, corrected):
        new = {}
        for rw in raw.split("，"):
            found = False
            for cw in corrected.split("，"):
                if len(rw) >= 2 and len(cw) >= 2 and rw != cw and rw not in self.noun_map and rw not in self.learned:
                    new[rw] = cw
                    found = True
                if found:
                    break
        if new:
            self.learned.update(new)
            self.log.append({"raw":raw, "corrected":corrected, "learned":new})
        return new

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"learned":self.learned, "log":self.log[-100:]}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    eng = DialectEngine()

    print("=== 演示1: 数据增强 ===")
    tpl = "肝脏形态规则，大小正常，表面光滑，实质回声分布均匀，肝内管系尚清。"
    for i, v in enumerate(eng.gen_variants(tpl, 8), 1):
        tags = []
        if any(f in v for f in FILLERS): tags.append("填充")
        if any(d in v for d in eng.noun_map): tags.append("方言")
        if any(p in v for p in PATIENT_TALK): tags.append("患者")
        t = " | ".join(tags) if tags else "标准"
        print(f"  [{i}] {v} [{t}]")

    print("\n=== 演示2: 方言标准化 ===")
    cases = [
        "右乳外上点八乘零点五低回声，边界清，无血流，二类",
        "胆囊头头有个一点二的石头，壁不厚",
        "甲状腺右叶有个零点四的水泡泡，边界清，二类",
        "左乳内上有个一点二的包包，边界欠清，四a",
        "腰子左叶有个一点二的无回声，边界清",
        "右乳外上点八点五低回声，不对不对，零点九乘零点六",
        "胆囊大小正常，腔内见一点二的石头，后方伴声影",
    ]
    for c in cases:
        n = eng.normalize(c)
        ok = "数字" if re.search(r'[0-9]', n) else "FAIL"
        print(f"  IN:  {c}")
        print(f"  OUT: {n} [{ok}]")
        print()

    print("=== 演示3: 自学习 ===")
    eng.learn("腰子左叶有个水泡泡", "左肾囊肿")
    print(f"  学到: {eng.learned}")
    eng.learn("胆囊头头有石头", "胆囊颈部结石")
    print(f"  又学到: {eng.learned}")
    # 再次遇到
    n = eng.normalize("右肾有个水泡泡")
    print('  再次说"右肾有个水泡泡" -> ' + n)

    print("\n=== 统计 ===")
    print(f"  种子方言词: {sum(len(v) for v in DIALECT_NOUNS.values())}个")
    print(f"  拼音词典: {len(PINYIN_DICT)}条")
    print(f"  拼音变体(含方言口音): {sum(len(accent_variants(w)) for w in PINYIN_DICT)}个")
    print(f"  自学习: 每次医生确认自动更新")
    print(f"\n  Python文件本身可以直接 import 使用")
    print(f"  也可以作为独立模块嵌入语音管线")

    eng.save("E:/claude/dialect_learned.json")
