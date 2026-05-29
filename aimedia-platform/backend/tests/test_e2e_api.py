"""端到端 API 测试: 登录 → 创建 → 提交 → 三审 → 合规检测"""

import httpx
import asyncio

BASE = "http://localhost:8000/api"


async def login(client, username, password):
    r = await client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    data = r.json()
    return data["access_token"], {"Authorization": f"Bearer {data['access_token']}"}


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        # 1. Login as doctor (author)
        token, headers = await login(client, "doctor_zhang", "doctor123")
        user = (await client.get("/content")).json()  # just verify auth works
        print("1. Login OK (doctor_zhang)")

        # 2. Create content
        r = await client.post("/content", json={
            "title": "高血压的早期预防与日常管理",
            "content_type": "article",
            "body": {"text": "高血压是一种常见的慢性疾病。建议每日食盐摄入量不超过6克，保持规律运动，定期监测血压。如有不适请及时就医，遵医嘱用药。"},
            "medical_tags": ["心血管", "高血压"],
            "source_references": ["中国高血压防治指南2024"],
            "ai_generated": False,
        }, headers=headers)
        assert r.status_code == 201, f"Create failed: {r.text}"
        content = r.json()
        content_id = content["id"]
        assert content["status"] == "draft"
        print(f"2. Create OK: status={content['status']}")

        # 3. Submit for review
        r = await client.post(f"/content/{content_id}/submit", headers=headers)
        assert r.status_code == 200, f"Submit failed: {r.text}"
        assert r.json()["status"] == "pending_1st"
        print("3. Submit OK: draft → pending_1st")

        # 4. Compliance check
        r = await client.post(f"/content/{content_id}/compliance-check", headers=headers)
        assert r.status_code == 200
        report = r.json()
        assert report["overall_verdict"] == "pass"
        print(f"4. Compliance Check: {report['overall_verdict']}")

        # 5. 一审 (editor)
        _, h1 = await login(client, "editor_wang", "editor123")
        r = await client.post("/review/submit", json={
            "content_id": content_id, "action": "approve",
            "comment": "一审通过，语言文字准确", "review_level": 1,
        }, headers=h1)
        assert r.status_code == 200, f"Review1 failed: {r.text}"
        assert r.json()["new_status"] == "pending_2nd"
        print("5. 一审 OK: pending_1st → pending_2nd")

        # 6. 二审 (dept_head)
        _, h2 = await login(client, "dept_head_li", "head123")
        r = await client.post("/review/submit", json={
            "content_id": content_id, "action": "approve",
            "comment": "二审通过，专业内容审核无误", "review_level": 2,
        }, headers=h2)
        assert r.status_code == 200, f"Review2 failed: {r.text}"
        assert r.json()["new_status"] == "pending_3rd"
        print("6. 二审 OK: pending_2nd → pending_3rd")

        # 7. 三审 (director)
        _, h3 = await login(client, "director_chen", "director123")
        r = await client.post("/review/submit", json={
            "content_id": content_id, "action": "approve",
            "comment": "三审通过，同意发布", "review_level": 3,
        }, headers=h3)
        assert r.status_code == 200, f"Review3 failed: {r.text}"
        assert r.json()["new_status"] == "approved"
        print("7. 三审 OK: pending_3rd → approved")

        # 8. Verify final status
        r = await client.get(f"/content/{content_id}", headers=headers)
        assert r.json()["status"] == "approved"
        print(f"8. Final status: {r.json()['status']}")

        # 9. Review records (3 records)
        r = await client.get(f"/review/records/{content_id}", headers=headers)
        records = r.json()["records"]
        assert len(records) == 3
        print(f"9. Review records: {len(records)} records")

        # 10. Rejection test
        r = await client.post("/content", json={
            "title": "测试内容-待驳回",
            "content_type": "article",
            "body": {"text": "测试"},
            "medical_tags": ["测试"],
            "source_references": [],
            "ai_generated": False,
        }, headers=headers)
        c2_id = r.json()["id"]

        # Submit
        await client.post(f"/content/{c2_id}/submit", headers=headers)

        # 一审通过
        await client.post("/review/submit", json={
            "content_id": c2_id, "action": "approve",
            "comment": "通过", "review_level": 1,
        }, headers=h1)

        # 二审驳回
        r = await client.post("/review/submit", json={
            "content_id": c2_id, "action": "reject",
            "comment": "二审驳回，内容需修改", "review_level": 2,
        }, headers=h2)
        assert r.json()["new_status"] == "draft"
        print("10. Rejection test OK: back to draft")

        # 11. Ad compliance block test
        r = await client.post("/content", json={
            "title": "我院冠心病特效治疗方案",
            "content_type": "article",
            "body": {"text": "我院拥有全国最先进的治疗方案，100%治愈冠心病，永不复发。请拨打咨询电话预约挂号。"},
            "medical_tags": ["心血管"],
            "source_references": [],
            "ai_generated": False,
        }, headers=headers)
        c3_id = r.json()["id"]

        r = await client.post(f"/content/{c3_id}/compliance-check", headers=headers)
        report = r.json()
        assert report["overall_verdict"] == "block"
        violations = report["rule_findings"]
        assert len(violations) > 0
        print(f"11. Ad compliance block: {len(violations)} violations")
        for v in violations:
            print(f"    [{v['severity']}] {v['rule_id']}: {v['message']}")

        print("\n=== ALL 11 E2E TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
