"""快速测试解析逻辑"""
import re


def parse_csv_line(line):
    cols = []
    current = ''
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            current += ch
        elif ch == ',' and not in_quotes:
            cols.append(current)
            current = ''
        else:
            current += ch
    cols.append(current)
    return cols


def test_parse():
    filepath = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        header = f.readline()
        print(f"Header: {header[:200]}")

        # 试试解析前几行
        report_count = 0
        for i in range(50):
            line = f.readline()
            cols = parse_csv_line(line)
            col0 = cols[0].strip('" ') if cols else ''
            study_id_match = re.match(r'^\d{15,}$', col0)

            if study_id_match:
                report_count += 1
                print(f"\n--- 报告 #{report_count} (行{i+2}) ---")
                print(f"  ID: {col0}")
                if len(cols) > 7:
                    see = cols[7][:100].strip('" ')
                    print(f"  StudySee: {see[:80]}...")
                if len(cols) > 8:
                    hint = cols[8][:100].strip('" ')
                    print(f"  StudyHint: {hint[:80]}...")
                if len(cols) > 4:
                    doctor = cols[4].strip('" ')
                    print(f"  Doctor: {doctor}")


def test_hint_match():
    """测试提示匹配是否有效"""
    print("\n\n=== 测试匹配 ===")
    hint = "二尖瓣口轻度返流。三尖瓣口轻度返流。"
    tpl_hints = [
        "二尖瓣口轻度返流。",
        "三尖瓣口轻度返流。",
        "心内结构未见明显异常声像",
        "肝、胆、脾、胰、双肾、输尿管未见明显异常声像。",
    ]
    for t in tpl_hints:
        t_clean = re.sub(r'\s+', '', t)
        h_clean = re.sub(r'\s+', '', hint)
        match = t_clean in h_clean
        print(f"  '{t[:20]}' in hint? {match}")


if __name__ == '__main__':
    test_parse()
    test_hint_match()
