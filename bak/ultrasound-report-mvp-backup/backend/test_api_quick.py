"""快速API测试 - 验证阿里云百炼集成"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json

BASE_URL = "https://localhost:8700"

# 忽略SSL警告(自签名证书)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_health():
    """测试健康检查"""
    print("=" * 60)
    print("1. 测试健康检查...")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", verify=False, timeout=5)
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {resp.json()}")
        print("   ✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False

def test_transcribe():
    """测试语音转写(需要音频文件)"""
    print("\n" + "=" * 60)
    print("2. 测试语音转写...")
    print("   ⚠️  需要音频文件,跳过此测试")
    print("   提示: 请在前端页面点击录音按钮进行测试")
    return True

def test_structure():
    """测试结构化报告生成"""
    print("\n" + "=" * 60)
    print("3. 测试结构化报告生成...")

    # 模拟超声口述文本
    test_text = """
    患者张三,男性,45岁。腹部超声检查显示:
    肝脏大小正常,实质回声均匀,肝内可见一个强回声团,大小约15mm×12mm,后方伴声影。
    胆囊大小形态正常,壁不厚,腔内未见明显异常回声。
    脾脏厚度正常,实质回声均匀。
    双肾大小形态正常,皮质髓质分界清楚,集合系统未见分离。
    胰腺大小形态正常,实质回声均匀,主胰管不扩张。
    """

    payload = {
        "text": test_text,
        "exam_type": "腹部超声",
        "patient_id": None
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/api/structure",
            json=payload,
            verify=False,
            timeout=30
        )
        print(f"   状态码: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ 结构化成功")
            print(f"   方法: {data.get('method', 'unknown')}")
            print(f"   模板: {data.get('template_used', 'unknown')}")
            print(f"   置信度: {data.get('confidence', 0)}")

            report = data.get('report', {})
            study_see = report.get('study_see', '')
            study_hint = report.get('study_hint', [])

            print(f"\n   生成的报告片段:")
            print(f"   {'-' * 60}")
            # 提取纯文本显示
            import re
            clean_text = re.sub(r'<[^>]+>', '', study_see)[:300]
            print(f"   {clean_text}")
            print(f"   {'-' * 60}")

            print(f"\n   诊断建议数量: {len(study_hint)}")
            if study_hint:
                for i, hint in enumerate(study_hint[:3], 1):
                    if isinstance(hint, dict):
                        print(f"   {i}. {hint.get('diagnosis', hint.get('text', ''))}")
                    else:
                        print(f"   {i}. {hint}")

            return True
        else:
            print(f"   ❌ 失败: {resp.text}")
            return False
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False

def test_templates():
    """测试模板列表"""
    print("\n" + "=" * 60)
    print("4. 测试模板列表...")
    try:
        resp = requests.get(f"{BASE_URL}/api/templates", verify=False, timeout=5)
        print(f"   状态码: {resp.status_code}")

        if resp.status_code == 200:
            templates = resp.json()
            print(f"   ✅ 获取到 {len(templates)} 个模板:")
            for key, info in templates.items():
                print(f"      - {info['name']}: {', '.join(info['organs'])}")
            return True
        else:
            print(f"   ❌ 失败: {resp.text}")
            return False
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("  超声报告系统 API 测试")
    print("  使用阿里云百炼模型 (qwen-plus)")
    print("=" * 60)

    results = []
    results.append(("健康检查", test_health()))
    results.append(("模板列表", test_templates()))
    results.append(("结构化报告", test_structure()))

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过! 系统运行正常!")
    else:
        print("\n⚠️  部分测试失败,请检查配置和日志")

if __name__ == "__main__":
    main()
