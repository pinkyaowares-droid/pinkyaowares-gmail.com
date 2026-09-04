"""
ทดสอบว่า MCP server ทำงานถูกต้อง ก่อนนำไปต่อกับ Claude Desktop

วิธีรัน:  python test_server.py
ถ้าขึ้น ALL PASSED แปลว่าพร้อมใช้งาน ถ้าไม่ผ่านจะบอกว่าข้อไหนพัง
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str(Path(__file__).parent / "server.py")

# คำถามที่พนักงานถามจริงหน้างาน กับรหัส SOP ที่ควรได้อันดับ 1
SEARCH_CASES = [
    ("แขกบ่นว่ารออาหารนาน", {"SOP-FB-003", "SOP-FB-013"}),
    ("แขกแพ้ถั่ว", {"SOP-FB-011"}),
    ("เด็ก17ขอเบียร์", {"SOP-FB-012"}),
    ("อุณหภูมิไวน์แดง", {"SOP-FB-009"}),
    ("แก้วแตกในสระ", {"SOP-FB-008"}),
    ("เก็บถาดรูมเซอร์วิส", {"SOP-FB-007"}),
    ("จัดงานแต่งริมหาดฝนตก", {"SOP-FB-014"}),
    ("food cost", {"SOP-FB-015"}),
]

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"\nเชื่อมต่อ: {init.server_info.name} v{init.server_info.version}\n")

            print("[1] ตรวจว่า tool ครบ")
            tools = {t.name for t in (await session.list_tools()).tools}
            expected = {"list_sops", "get_sop", "search_sop",
                        "get_reference_table", "get_critical_rules"}
            check("tools ครบ 5 ตัว", expected <= tools, f"ขาด {expected - tools}")

            print("\n[2] ตรวจว่าอ่านคู่มือครบ 19 SOP")
            data = json.loads((await session.call_tool("list_sops", {})).content[0].text)
            codes = {s["code"] for group in data["sections"].values() for s in group if s["code"]}
            check("พบ SOP ครบ 19 หัวข้อ", len(codes) == 19, f"พบ {len(codes)}")

            print("\n[3] ตรวจการค้นหาภาษาไทย")
            for query, want in SEARCH_CASES:
                res = json.loads(
                    (await session.call_tool("search_sop", {"query": query, "limit": 1})).content[0].text
                )
                top = res.get("results", [{}])[0].get("code") if res.get("results") else None
                check(f'"{query}" -> {top}', top in want, f"คาดว่า {want}")

            print("\n[4] ตรวจการดึง SOP ด้วยรหัสหลายรูปแบบ")
            for variant in ["SOP-FB-011", "FB-011", "011", "11"]:
                res = json.loads((await session.call_tool("get_sop", {"code": variant})).content[0].text)
                check(f'get_sop("{variant}")', res.get("code") == "SOP-FB-011", res.get("error", ""))

            print("\n[5] ตรวจตารางอ้างอิง")
            # wine_service เป็นรายการข้อ ไม่ใช่ตาราง จึงตรวจด้วยคำที่ต้องปรากฏแทน
            table_markers = {
                "temperatures": "60",
                "wine_service": "อุณหภูมิเสิร์ฟ",
                "emergency_contacts": "1669",
                "forms": "F-15",
                "kpi": "รายเดือน",
            }
            for table, marker in table_markers.items():
                res = json.loads(
                    (await session.call_tool("get_reference_table", {"table": table})).content[0].text
                )
                check(f'ตาราง "{table}"', marker in res.get("content", ""), res.get("error", ""))

            print("\n[6] ตรวจว่าไม่พบแล้วต้องไม่มั่ว")
            res = json.loads(
                (await session.call_tool("search_sop", {"query": "ซูชิโอมากาเสะ"})).content[0].text
            )
            check("คำที่ไม่มีในคู่มือต้องคืน hint ให้แจ้งผู้ใช้ตรง ๆ",
                  not res.get("results") and "เดา" in res.get("hint", ""))

            res = json.loads((await session.call_tool("get_sop", {"code": "SOP-FB-999"})).content[0].text)
            check("รหัสที่ไม่มีต้องคืน error ไม่ใช่เนื้อหามั่ว", "error" in res)

            print("\n[7] ตรวจกฎสำคัญและคำเตือนก่อนใช้จริง")
            res = json.loads((await session.call_tool("get_critical_rules", {})).content[0].text)
            check("มีกฎห้ามพลาด 3 ข้อ", len(res.get("critical_rules", [])) == 3)
            check("มีคำเตือนเรื่องกฎหมายแอลกอฮอล์",
                  any("แอลกอฮอล์" in v["topic"] for v in res.get("verify_before_use", [])))

    print()
    if failures:
        print(f"FAILED {len(failures)} ข้อ: {', '.join(failures)}")
        return 1
    print("ALL PASSED — พร้อมต่อกับ Claude Desktop")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
