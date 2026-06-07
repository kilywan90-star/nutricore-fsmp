"""阿里云百炼集成测试"""
import requests
import urllib3
urllib3.disable_warnings()

BASE = "https://localhost:8700"

print("=" * 60)
print("阿里云百炼模型集成测试")
print("=" * 60)

# 测试1: 健康检查
print("\n[1] 健康检查...")
r = requests.get(f"{BASE}/api/health", verify=False)
print(f"    状态: {r.status_code} - {r.json()}")

# 测试2: 获取模板
print("\n[2] 获取模板列表...")
r = requests.get(f"{BASE}/api/templates", verify=False)
templates = r.json()
print(f"    共{len(templates)}个模板:")
for k, v in templates.items():
    print(f"      - {v['name']}")

# 测试3: 简单腹部超声结构化
print("\n[3] 测试腹部超声结构化...")
text1 = "肝脏大小正常形态正常包膜光滑实质回声均匀肝内血管走行清晰门静脉不宽胆囊大小正常壁不厚腔内透声好胰腺大小正常形态正常实质回声均匀脾脏不大双肾大小正常形态正常皮质髓质分界清楚集合系统未见分离"
r = requests.post(f"{BASE}/api/structure", json={"text": text1, "exam_type": "腹部超声"}, verify=False, timeout=60)
print(f"    状态: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"    方法: {data['method']}")
    print(f"    模板: {data['template_used']}")
    print(f"    置信度: {data['confidence']}")
    report = data['report']
    # 清理HTML标签显示
    import re
    see_text = re.sub(r'<[^>]+>', '', report['study_see'])[:100]
    print(f"    报告片段: {see_text}...")
    print(f"    诊断建议: {len(report['study_hint'])}条")

# 测试4: 带病灶的描述
print("\n[4] 测试异常发现结构化...")
text2 = "肝脏右叶可见一个强回声团大小约15mm乘12mm后方伴声影边界清晰肝脏其余部分实质回声均匀胆囊大小正常壁稍厚约4mm腔内未见明显异常脾脏厚度正常双肾集合系统轻度分离左肾约8mm右肾约6mm"
r = requests.post(f"{BASE}/api/structure", json={"text": text2, "exam_type": "腹部超声"}, verify=False, timeout=60)
print(f"    状态: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"    方法: {data['method']}")
    print(f"    模板: {data['template_used']}")
    report = data['report']
    import re
    see_text = re.sub(r'<[^>]+>', '', report['study_see'])[:150]
    print(f"    报告片段: {see_text}...")
    hints = report['study_hint']
    print(f"    诊断建议: {len(hints)}条")
    for h in hints[:3]:
        if isinstance(h, dict):
            print(f"      - {h.get('diagnosis', '')}")

# 测试5: 妇产超声
print("\n[5] 测试妇产超声结构化...")
text3 = "子宫前位大小约80mm乘70mm乘60mm形态饱满肌层回声均匀宫腔内可见孕囊大小约25mm乘18mm形态规则囊内可见卵黄囊及胎芽胎芽长约8mm可见原始心管搏动双侧附件区未见明显异常回声"
r = requests.post(f"{BASE}/api/structure", json={"text": text3, "exam_type": "妇产超声"}, verify=False, timeout=60)
print(f"    状态: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"    方法: {data['method']}")
    print(f"    模板: {data['template_used']}")
    report = data['report']
    import re
    see_text = re.sub(r'<[^>]+>', '', report['study_see'])[:150]
    print(f"    报告片段: {see_text}...")

print("\n" + "=" * 60)
print("✅ 所有测试完成!")
print("=" * 60)
