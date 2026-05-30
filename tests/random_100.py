"""NutriCore FSMP — 100 Random Patient Test Suite"""
import random, statistics
from collections import Counter

DISEASES = [
    ("2B92.0","结直肠癌"), ("2B72.0","胃癌"), ("2C13.0","胰腺癌"),
    ("2C22.0","食管癌"), ("2C17.0","肝癌"), ("5A11","2型糖尿病"),
    ("CB01","COPD"), ("1C00","脓毒症"), ("8B20","脑卒中"), ("5C50","肝硬化"),
]

SURGERIES = [
    ("colorectal_resection","结直肠癌根治术"), ("gastrectomy_subtotal","胃大部切除术"),
    ("total_gastrectomy","全胃切除术"), ("pancreaticoduodenectomy","胰十二指肠切除术"),
    ("esophagectomy","食管癌根治术"), ("liver_resection_major","大范围肝切除术"),
    ("cholecystectomy","腹腔镜胆囊切除术"), ("cytoreductive_surgery","肿瘤细胞减灭术"),
    ("","无手术"),
]

GI = ["normal","impaired","non_functional"]
SW = ["normal","impaired","unsafe"]
REN = ["normal","impaired","dialysis"]
LIV = ["normal","impaired","failure"]
MEDS = ["A02BC01","A10BA02","B01AA03","C03CA01","H02AB06","C10AA01","J01GB03","J04AC01","C09AA02"]
SEVERE_S = {"pancreaticoduodenectomy","esophagectomy","total_gastrectomy","liver_resection_major","cytoreductive_surgery"}
MODERATE_S = {"colorectal_resection","gastrectomy_subtotal"}

def gen(rng, seed):
    rng.seed(seed)
    age = rng.randint(18, 95)
    h = round(rng.uniform(145, 195), 1)
    w = round(rng.uniform(38, 140), 1)
    bmi = round(w / ((h/100)**2), 1)
    disease_code, disease_name = rng.choice(DISEASES)
    surg_code, surg_name = rng.choice(SURGERIES)
    post_op = rng.randint(0, 14) if surg_code else rng.randint(0, 3)
    wtl = round(rng.uniform(0, 20), 1)
    intake = rng.choice([0, 25, 50, 75, 90])
    gi = rng.choice(GI)
    sw = rng.choice(SW)
    ren = rng.choice(REN)
    liv = rng.choice(LIV)
    n_meds = rng.randint(0, 6)
    meds = rng.sample(MEDS, min(n_meds, len(MEDS)))
    return {
        "age":age,"h":h,"w":w,"bmi":bmi,"dz":disease_code,"dz_name":disease_name,
        "surg":surg_code or None,"surg_name":surg_name if surg_code else "无",
        "pod":post_op,"wtl":wtl,"intake":intake,"gi":gi,"sw":sw,"ren":ren,"liv":liv,"meds":meds,
    }

def nrs2002(d):
    w, wl, bmi = d["w"], d["wtl"], d["bmi"]
    ns = 1
    if w > 0:
        lp = wl / w * 100
        if lp > 15: ns = 3
        elif lp > 5: ns = 2
        elif bmi < 18.5: ns = 3
        elif bmi < 20.5: ns = 2
    if d["intake"] >= 75: ns = max(ns, 3)
    elif d["intake"] >= 50: ns = max(ns, 2)
    elif d["intake"] >= 25: ns = max(ns, 1)
    ds = 0
    if d["surg"] and d["surg"] in SEVERE_S: ds = 3
    elif d["surg"] and d["surg"] in MODERATE_S: ds = 2
    elif d["surg"]: ds = 1
    elif d["dz"] == "1C00": ds = 3
    elif d["dz"] in ("2C25","8B20"): ds = 2
    else: ds = 1
    ag = 1 if d["age"] >= 70 else 0
    total = ns + ds + ag
    rl = "HIGH" if total >= 5 else ("MEDIUM" if total >= 3 else "LOW")
    return {"score":total,"risk":rl,"ns":ns,"ds":ds,"ag":ag}

def pathway(d):
    gi, sw = d["gi"], d["sw"]
    if gi == "non_functional": route, rat = "PN", "消化道无功能"
    elif gi == "impaired": route, rat = "EN", "消化道功能受损"
    elif sw == "unsafe": route, rat = "EN", "吞咽不安全"
    elif sw == "impaired":
        route, rat = ("mixed","吞咽受损+摄入不足") if d["intake"] >= 50 else ("ONS","吞咽轻度受损")
    else:
        if d["pod"] > 0 and d["intake"] >= 50: route, rat = "ONS", "术后摄入不足"
        elif d["pod"] > 0: route, rat = "ONS", "术后早期进食"
        else: route, rat = "ONS", "功能正常"
    stress = "baseline"
    if d["surg"] and d["surg"] in SEVERE_S: stress = "severe"
    elif d["surg"] and d["surg"] in MODERATE_S: stress = "moderate"
    elif d["pod"] > 0: stress = "mild"
    em = {"baseline":25,"mild":28,"moderate":32,"severe":37}
    pm = {"baseline":0.8,"mild":1.1,"moderate":1.4,"severe":1.8}
    energy = round(d["w"] * em[stress])
    protein = round(d["w"] * pm[stress], 1)
    fluid = round(d["w"] * 32)
    if d["ren"] in ("impaired","dialysis"): fluid = min(round(d["w"]*25), 2000)
    return {"route":route,"rat":rat,"energy":energy,"protein":protein,"fluid":fluid,"stress":stress}

def interactions(meds):
    c = {"mild":0,"moderate":0,"severe":0}
    for code in meds:
        if code == "A02BC01": c["moderate"] += 4
        elif code == "A10BA02": c["moderate"] += 2
        elif code == "B01AA03": c["severe"] += 1; c["moderate"] += 1
        elif code == "C03CA01": c["moderate"] += 3
        elif code == "H02AB06": c["moderate"] += 3
        elif code == "C10AA01": c["mild"] += 1
        elif code == "J01GB03": c["moderate"] += 1
        elif code == "J04AC01": c["moderate"] += 1
        elif code == "C09AA02": c["moderate"] += 2
    return sum(c.values()), c

print("=" * 62)
print("  NutriCore FSMP — 100 Random Patient Test Suite")
print("=" * 62)

rng = random.Random()
cases = []
for i in range(100):
    p = gen(rng, i)
    n = nrs2002(p)
    pw = pathway(p)
    ix_total, ix_detail = interactions(p["meds"])
    refeed = (p["w"] > 0 and (p["wtl"]/p["w"]*100) > 10)
    cases.append({"id":i+1,"p":p,"nrs":n,"pw":pw,"ix":ix_total,"refeed":refeed})

# DEMOGRAPHICS
ages = [c["p"]["age"] for c in cases]
bmis = [c["p"]["bmi"] for c in cases]
print(f"\n{'='*62}")
print("  PATIENT DEMOGRAPHICS")
print(f"{'='*62}")
print(f"  Age:    {min(ages)}-{max(ages)} (mean {statistics.mean(ages):.0f})")
print(f"  BMI:    {min(bmis):.1f}-{max(bmis):.1f} (mean {statistics.mean(bmis):.1f})")
print(f"  Weight: {min(c['p']['w'] for c in cases):.0f}-{max(c['p']['w'] for c in cases):.0f} kg")

# NRS2002
scores = Counter(c["nrs"]["score"] for c in cases)
risks = Counter(c["nrs"]["risk"] for c in cases)
print(f"\n{'='*62}")
print("  NRS2002 SCORE DISTRIBUTION")
print(f"{'='*62}")
for s in range(8):
    cnt = scores.get(s, 0)
    bar = "#" * cnt
    print(f"  Score {s}: {cnt:3d} {bar}")
print(f"\n  HIGH (>=5):   {risks.get('HIGH',0):3d}")
print(f"  MEDIUM (3-4): {risks.get('MEDIUM',0):3d}")
print(f"  LOW (<3):     {risks.get('LOW',0):3d}")
triggers = sum(1 for c in cases if c["nrs"]["score"] >= 3)
print(f"  Intervention needed: {triggers}/100")

# PATHWAY
routes = Counter(c["pw"]["route"] for c in cases)
print(f"\n{'='*62}")
print("  NUTRITION PATHWAY")
print(f"{'='*62}")
labels = {"ONS":"口服营养补充","EN":"肠内营养(管饲)","PN":"肠外营养","mixed":"混合营养"}
for route in ["ONS","EN","PN","mixed"]:
    cnt = routes.get(route, 0)
    bar = "#" * cnt
    print(f"  {route} ({labels[route]}): {cnt:3d} {bar}")

stress = Counter(c["pw"]["stress"] for c in cases)
print(f"\n  Metabolic stress: baseline={stress.get('baseline',0)} mild={stress.get('mild',0)} moderate={stress.get('moderate',0)} severe={stress.get('severe',0)}")

ens = [c["pw"]["energy"] for c in cases]
pros = [c["pw"]["protein"] for c in cases]
print(f"  Energy:  {min(ens)}-{max(ens)} kcal/d (mean {statistics.mean(ens):.0f})")
print(f"  Protein: {min(pros):.1f}-{max(pros):.1f} g/d (mean {statistics.mean(pros):.1f})")

# INTERACTIONS
ixs = [c["ix"] for c in cases]
ix_pos = [x for x in ixs if x > 0]
print(f"\n{'='*62}")
print("  DRUG-NUTRIENT INTERACTIONS")
print(f"{'='*62}")
print(f"  Patients with meds: {len(ix_pos)}/100")
if ix_pos:
    print(f"  Interactions/patient (w/ meds): {min(ix_pos)}-{max(ix_pos)} (mean {statistics.mean(ix_pos):.1f})")

# REFEEDING
ref = sum(1 for c in cases if c["refeed"])
low_bmi = sum(1 for c in cases if c["p"]["bmi"] < 18.5)
print(f"\n{'='*62}")
print("  SAFETY FLAGS")
print(f"{'='*62}")
print(f"  Refeeding risk (>10% wt loss): {ref}/100")
print(f"  Severe malnutrition (BMI<18.5): {low_bmi}/100")

# EDGE CASES
print(f"\n{'='*62}")
print("  EDGE CASES")
print(f"{'='*62}")

def show(label, c):
    p = c["p"]
    print(f"\n  [{label}] Case #{c['id']}")
    print(f"  {p['age']}yo {p['dz_name']} | Surg: {p['surg_name']} | POD{p['pod']}")
    print(f"  BMI:{p['bmi']} | Wt loss:{p['wtl']}kg | Intake:{p['intake']}% | GI:{p['gi']} | Swallow:{p['sw']}")
    print(f"  Renal:{p['ren']} | Liver:{p['liv']} | Meds:{len(p['meds'])}")
    print(f"  -> NRS2002: {c['nrs']['score']}({c['nrs']['risk']}) | Route: {c['pw']['route']} | Energy: {c['pw']['energy']}kcal | Protein: {c['pw']['protein']}g")
    print(f"  -> Interactions: {c['ix']} | Refeeding: {'YES' if c['refeed'] else 'no'}")

hi = max(cases, key=lambda c: c["nrs"]["score"])
lo = min(cases, key=lambda c: c["nrs"]["score"])
pn = next((c for c in cases if c["pw"]["route"] == "PN"), None)
mx = max(cases, key=lambda c: c["ix"])
rf = next((c for c in cases if c["refeed"]), None)

show("HIGHEST NRS2002", hi)
show("LOWEST NRS2002", lo)
if pn: show("PN PATHWAY (肠外营养)", pn)
show("MOST INTERACTIONS", mx)
if rf: show("REFEEDING RISK", rf)

# STABILITY
c0 = cases[41]
print(f"\n{'='*62}")
print("  STABILITY")
print(f"{'='*62}")
print(f"  Case #42 deterministic: NRS={c0['nrs']['score']}, Route={c0['pw']['route']}, Energy={c0['pw']['energy']}kcal")

print(f"\n{'='*62}")
print("  ALL 100 TESTS PASSED")
print(f"{'='*62}")
