"""
MCP Server — Thavorn Palm Beach Resort F&B SOP
เปิดคู่มือมาตรฐานการปฏิบัติงานแผนกอาหารและเครื่องดื่มให้ Claude เรียกใช้ได้

เนื้อหาทั้งหมดอยู่ในโฟลเดอร์ data/ เป็นไฟล์ Markdown ธรรมดา
พนักงานที่ไม่เขียนโค้ดสามารถแก้ไขเนื้อหาได้โดยตรง ไม่ต้องแตะไฟล์นี้
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from mcp.server.mcpserver import MCPServer

DATA_DIR = Path(__file__).parent / "data"

# ป้ายหมวดหมู่ของแต่ละไฟล์ ใช้แสดงผลและใช้กรองใน list_sops
CATEGORY_LABELS = {
    "outlets-and-conduct": "จุดบริการและมาตรฐานพนักงาน",
    "service-standards": "มาตรฐานการบริการหลัก",
    "outlet-operations": "การปฏิบัติงานเฉพาะจุดบริการ",
    "food-safety": "ความปลอดภัยด้านอาหาร",
    "incidents-and-compliance": "กฎหมาย ข้อร้องเรียน และเหตุฉุกเฉิน",
    "management": "การบริหารจัดการ",
}

# คำพ้องความหมายที่พนักงานใช้จริงหน้างาน แต่ไม่ปรากฏในตัวเนื้อหา
# ช่วยให้ search_sop เจอแม้ผู้ใช้พิมพ์คำพูดติดปากแทนศัพท์ในคู่มือ
SYNONYMS = {
    "SOP-FB-001": ["เปิดร้าน", "เตรียมร้าน", "มิสอองปลาส", "opening", "brief", "บรีฟ"],
    "SOP-FB-002": ["ต้อนรับ", "รับแขก", "พาไปนั่ง", "โฮสเตส", "greeting", "seating", "คิว"],
    "SOP-FB-003": ["ลำดับการเสิร์ฟ", "เสิร์ฟ", "รอนาน", "ช้า", "กี่นาที", "sequence", "เสิร์ฟทางไหน", "รออาหาร", "อาหารช้า", "ยังไม่มา"],
    "SOP-FB-004": ["รับออร์เดอร์", "จดออร์เดอร์", "สั่งอาหาร", "upsell", "ขายเพิ่ม", "POS"],
    "SOP-FB-005": ["เก็บเงิน", "ปิดบิล", "บิล", "รูดบัตร", "ลงห้อง", "void", "ยกเลิกบิล"],
    "SOP-FB-006": ["บุฟเฟต์", "อาหารเช้า", "breakfast", "ไลน์อาหาร", "เติมอาหาร"],
    "SOP-FB-007": ["รูมเซอร์วิส", "room service", "ส่งอาหารห้อง", "เก็บถาด", "in room dining"],
    "SOP-FB-008": ["ริมสระ", "พูลบาร์", "ชายหาด", "เตียงอาบแดด", "pool bar", "แก้วแตก"],
    "SOP-FB-009": ["บาร์", "ค็อกเทล", "ไวน์", "ชงเครื่องดื่ม", "สต็อกเหล้า", "jigger", "อุณหภูมิไวน์"],
    "SOP-FB-010": ["สุขอนามัย", "ล้างมือ", "อุณหภูมิ", "เขียง", "ปนเปื้อน", "HACCP", "อาหารเป็นพิษ"],
    "SOP-FB-011": ["แพ้อาหาร", "allergy", "ภูมิแพ้", "ฮาลาล", "มังสวิรัติ", "วีแกน", "กลูเตน", "เมนูเด็ก", "แพ้", "ถั่ว", "กุ้ง", "นม"],
    "SOP-FB-012": ["เหล้า", "เบียร์", "แอลกอฮอล์", "เมา", "อายุ", "บัตรประชาชน", "ห้ามขาย", "เยาว์", "ไม่ถึง 20", "ต่ำกว่า 20"],
    "SOP-FB-013": ["ร้องเรียน", "คอมเพลน", "แขกด่า", "แขกโกรธ", "LEARN", "ขอโทษ", "ชดเชย", "รีวิว", "บ่น", "ไม่พอใจ", "ตำหนิ", "ขอเปลี่ยน"],
    "SOP-FB-014": ["จัดเลี้ยง", "งานแต่ง", "banquet", "BEO", "อีเวนต์", "ประชุม", "ฝนตก"],
    "SOP-FB-015": ["สต็อก", "ต้นทุน", "เบิกของ", "รับของ", "ของเสีย", "food cost", "inventory"],
    "SOP-FB-016": ["ปิดร้าน", "closing", "ปิดกะ", "ส่งกะ", "logbook", "นับเงิน", "ส่งเวร", "ปิดยอด"],
    "SOP-FB-017": ["ฉุกเฉิน", "ไฟไหม้", "สำลัก", "อุบัติเหตุ", "ไฟดับ", "เบอร์โทร", "ความปลอดภัย"],
    "SOP-FB-018": ["อบรม", "เทรน", "พนักงานใหม่", "ประเมิน", "training", "ทดลองงาน"],
    "SOP-FB-019": ["KPI", "ตัวชี้วัด", "เป้า", "คะแนน"],
}

# กฎที่อยู่เหนือความรวดเร็วในการบริการและความพึงพอใจของแขก
# แยกออกมาจากตัวเนื้อหาเพราะต้องเรียกดูได้ทันทีโดยไม่ต้องค้นหา
CRITICAL_RULES = [
    {
        "rule": "ห้ามจำหน่ายเครื่องดื่มแอลกอฮอล์แก่ผู้มีอายุต่ำกว่า 20 ปีบริบูรณ์",
        "why": "เป็นความผิดตามกฎหมายและกระทบใบอนุญาตของโรงแรม การที่ผู้ปกครองอนุญาตไม่ใช่ข้อยกเว้น",
        "action": "ตรวจบัตรประชาชนหรือหนังสือเดินทางเมื่อแขกดูอายุน้อยกว่า 25 ปี",
        "ref": "SOP-FB-012",
    },
    {
        "rule": "ห้ามเดาส่วนผสมเมื่อแขกแจ้งว่าแพ้อาหาร",
        "why": "การปนเปื้อนระดับร่องรอยทำให้แขกเสียชีวิตได้ การเขี่ยออกหรือล้างน้ำไม่ถือว่าปลอดสารก่อภูมิแพ้",
        "action": "ถามเชฟก่อนตอบแขกทุกครั้ง แจ้งครัวทั้งใน POS และด้วยวาจา ปรุงใหม่ทั้งจาน",
        "ref": "SOP-FB-011",
    },
    {
        "rule": "อาหารที่อยู่ในเขตอันตราย 5-60°C เกิน 2 ชั่วโมงต้องทิ้ง",
        "why": "เชื้อโรคเพิ่มจำนวนถึงระดับก่อโรคแล้ว การอุ่นซ้ำไม่ทำลายสารพิษที่เชื้อสร้างไว้",
        "action": "ทิ้งทันที ห้ามนำกลับมาใช้ซ้ำเพื่อประหยัดต้นทุน บันทึกลงแบบฟอร์ม F-06",
        "ref": "SOP-FB-010",
    },
]

# จุดที่คู่มือยังไม่สมบูรณ์ ต้องเตือนผู้ใช้ก่อนนำไปใช้จริง
VERIFY_BEFORE_USE = [
    {
        "topic": "เวลาห้ามจำหน่ายแอลกอฮอล์",
        "issue": "กฎเรื่องเวลา วันสำคัญทางศาสนา และข้อยกเว้นสำหรับโรงแรมที่จดทะเบียน มีการแก้ไขเป็นระยะ "
                 "คู่มือจึงระบุแต่หลักการ ห้ามอ้างช่วงเวลาเป็นข้อเท็จจริง",
        "who": "ฝ่ายกฎหมายหรือผู้จัดการทั่วไป ยืนยันกับสำนักงานสาธารณสุขจังหวัดภูเก็ต แล้วทำเป็นภาคผนวก ก.",
    },
    {
        "topic": "ตัวเลขต้นทุนและ KPI",
        "issue": "Food Cost 33% และ Beverage Cost 25% เป็นค่ามาตรฐานอุตสาหกรรมที่ตั้งไว้ก่อน "
                 "ยังไม่ใช่เป้าที่ฝ่ายบริหารอนุมัติ",
        "who": "F&B Manager และฝ่ายบัญชี ปรับตามงบประมาณจริง",
    },
    {
        "topic": "เบอร์ติดต่อภายในและเวลาทำการ",
        "issue": "เบอร์ภายในยังไม่ได้กรอก และเวลาทำการอ้างจากเว็บไซต์สาธารณะ อาจต่างจากที่ใช้จริง",
        "who": "ผู้จัดการแต่ละจุดบริการ",
    },
    {
        "topic": "ชื่อจุดบริการ",
        "issue": "Ciao Pizza and Grill เปลี่ยนเป็น FLARE Flame & Flavour และ Ciao Wine Bar เป็น "
                 "FLARE Wine Bar & Store แล้ว แต่ชื่อเก่ายังปรากฏในหลายช่องทาง",
        "who": "ฝ่ายการตลาด ยืนยันชื่อทางการที่ใช้ภายใน",
    },
]


# ---------------------------------------------------------------------------
# การอ่านและแยกส่วนเนื้อหา
# ---------------------------------------------------------------------------

class Section:
    """หนึ่งหัวข้อในคู่มือ อาจเป็น SOP ที่มีรหัส หรือหัวข้อทั่วไปที่ไม่มีรหัส"""

    def __init__(self, code: str | None, title: str, body: str, source: str):
        self.code = code
        self.title = title
        self.body = body
        self.source = source

    @property
    def category(self) -> str:
        return CATEGORY_LABELS.get(self.source, self.source)

    @property
    def keywords(self) -> list[str]:
        return SYNONYMS.get(self.code or "", [])

    def summary(self, limit: int = 160) -> str:
        """บรรทัดแรกที่เป็นเนื้อความจริง ใช้แสดงในรายการ"""
        for line in self.body.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "|", "```", "-", "*")):
                continue
            clean = re.sub(r"\*\*|`", "", line)
            return clean[:limit] + ("…" if len(clean) > limit else "")
        return ""

    def to_dict(self, include_body: bool = False) -> dict:
        data = {
            "code": self.code,
            "title": self.title,
            "category": self.category,
            "summary": self.summary(),
        }
        if include_body:
            data["content"] = self.body
        return data


def _load_sections() -> list[Section]:
    """แยกไฟล์ Markdown ในโฟลเดอร์ data/ ออกเป็นหัวข้อระดับ ## แต่ละหัวข้อ"""
    sections: list[Section] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        source = path.stem
        # ตัดหัวเรื่องระดับ # ของไฟล์ทิ้ง แล้วแยกตาม ## แต่ละอัน
        parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        for part in parts:
            heading, _, body = part.partition("\n")
            heading = heading.strip()
            match = re.match(r"(SOP-FB-\d{3})\s*(.*)", heading)
            if match:
                code, title = match.group(1), match.group(2).strip()
            else:
                code, title = None, heading
            sections.append(Section(code, title, body.strip(), source))
    return sections


SECTIONS = _load_sections()
BY_CODE = {s.code: s for s in SECTIONS if s.code}


def _normalize(code: str) -> str:
    """รับได้ทั้ง SOP-FB-003, FB-003, 003 และ 3 เพราะพนักงานพิมพ์ไม่เหมือนกัน"""
    digits = re.findall(r"\d+", code)
    if not digits:
        return code.strip().upper()
    return f"SOP-FB-{int(digits[-1]):03d}"


def _find_subsection(section: Section, needle: str) -> str | None:
    """ดึงหัวข้อย่อยระดับ ### ที่ชื่อมีคำว่า needle ออกมา"""
    parts = re.split(r"^### ", section.body, flags=re.MULTILINE)
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        if needle in heading:
            return f"### {heading.strip()}\n\n{body.strip()}"
    return None


# ---------------------------------------------------------------------------
# ตารางอ้างอิงที่ถูกเรียกดูบ่อยจนควรมีทางลัด
# ---------------------------------------------------------------------------

TABLE_SOURCES: dict[str, tuple[str, str | None, str]] = {
    # key: (รหัส SOP หรือชื่อหัวข้อ, คำในหัวข้อย่อย, คำอธิบาย)
    "temperatures": ("SOP-FB-010", "การควบคุมอุณหภูมิ", "อุณหภูมิปลอดภัยของอาหารและตู้เย็น"),
    "service_timing": ("SOP-FB-003", None, "เวลามาตรฐานแต่ละขั้นตอนของการบริการ"),
    "wine_service": ("SOP-FB-009", "การบริการไวน์", "ปริมาณการรินและอุณหภูมิเสิร์ฟไวน์"),
    "outlets": ("จุดบริการทั้งหมด", None, "รายชื่อจุดบริการและเวลาทำการ"),
    "forms": ("แบบฟอร์มและใบตรวจสอบ", None, "ทะเบียนแบบฟอร์ม F-01 ถึง F-15"),
    "kpi": ("SOP-FB-019", None, "ตัวชี้วัดผลการดำเนินงานและเป้าหมาย"),
    "emergency_contacts": ("SOP-FB-017", "เบอร์ติดต่อฉุกเฉิน", "เบอร์ติดต่อกรณีฉุกเฉิน"),
    "complaint_handling": ("SOP-FB-013", None, "ขั้นตอน LEARN สำหรับจัดการข้อร้องเรียน"),
}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = MCPServer(
    name="thavorn-fb-sop",
    title="Thavorn Palm Beach Resort — F&B SOP",
    version="1.0.0",
    instructions=(
        "คู่มือมาตรฐานการปฏิบัติงานแผนกอาหารและเครื่องดื่มของ Thavorn Palm Beach Resort "
        "เมื่อผู้ใช้ถามเรื่องการบริการ ห้องอาหาร บาร์ อาหารเช้า room service จัดเลี้ยง "
        "ความปลอดภัยด้านอาหาร การแพ้อาหาร แอลกอฮอล์ ข้อร้องเรียน สต็อก หรือการอบรมพนักงาน "
        "ให้เรียก search_sop ก่อนตอบเสมอ อย่าตอบจากความรู้ทั่วไปเรื่องโรงแรม "
        "เพราะมาตรฐานของแต่ละโรงแรมต่างกันและพนักงานต้องได้คำตอบที่ตรงกับที่หัวหน้างานจะตรวจจริง "
        "ระบุรหัส SOP ที่อ้างอิงท้ายคำตอบทุกครั้ง และตอบเป็นภาษาไทยเป็นค่าเริ่มต้น"
    ),
)


@mcp.tool()
def list_sops(category: str = "") -> str:
    """แสดงรายการหัวข้อทั้งหมดในคู่มือ SOP พร้อมรหัสและคำอธิบายย่อ

    ใช้เมื่อผู้ใช้อยากเห็นภาพรวมว่าคู่มือครอบคลุมอะไรบ้าง หรือเมื่อต้องการหารหัส SOP
    ที่ถูกต้องก่อนเรียก get_sop

    Args:
        category: กรองตามหมวด เช่น "ความปลอดภัย" "บริการ" "จัดการ" เว้นว่างเพื่อดูทั้งหมด
    """
    items = SECTIONS
    if category.strip():
        needle = category.strip().lower()
        items = [s for s in SECTIONS if needle in s.category.lower() or needle in s.title.lower()]
        if not items:
            available = sorted({s.category for s in SECTIONS})
            return json.dumps(
                {"error": f"ไม่พบหมวด '{category}'", "available_categories": available},
                ensure_ascii=False, indent=2,
            )

    grouped: dict[str, list[dict]] = {}
    for s in items:
        grouped.setdefault(s.category, []).append(s.to_dict())

    return json.dumps({"total": len(items), "sections": grouped}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_sop(code: str) -> str:
    """ดึงเนื้อหาเต็มของ SOP หนึ่งหัวข้อตามรหัส

    ใช้เมื่อทราบรหัสแล้ว หรือหลังจาก search_sop ชี้มาที่หัวข้อใดหัวข้อหนึ่ง
    รับได้ทั้งรูปแบบ SOP-FB-003, FB-003, 003 และ 3

    Args:
        code: รหัส SOP เช่น "SOP-FB-011" หรือ "11"
    """
    key = _normalize(code)
    section = BY_CODE.get(key)
    if section is None:
        # ถ้าไม่ใช่รหัส ลองหาจากชื่อหัวข้อแทน เผื่อผู้ใช้พิมพ์ชื่อมา
        for s in SECTIONS:
            if code.strip() and code.strip() in s.title:
                section = s
                break
    if section is None:
        return json.dumps(
            {
                "error": f"ไม่พบ SOP รหัส '{code}'",
                "hint": "เรียก list_sops เพื่อดูรหัสทั้งหมด หรือ search_sop เพื่อค้นด้วยคำค้น",
                "available_codes": sorted(BY_CODE),
            },
            ensure_ascii=False, indent=2,
        )

    payload = section.to_dict(include_body=True)
    # เตือนเรื่องที่ต้องยืนยันก่อนใช้ ถ้า SOP นั้นแตะประเด็นที่ยังไม่สมบูรณ์
    if section.code in {"SOP-FB-012", "SOP-FB-015", "SOP-FB-017", "SOP-FB-019"}:
        payload["verify_before_use"] = [
            v for v in VERIFY_BEFORE_USE
            if (section.code == "SOP-FB-012" and "แอลกอฮอล์" in v["topic"])
            or (section.code in {"SOP-FB-015", "SOP-FB-019"} and "ต้นทุน" in v["topic"])
            or (section.code == "SOP-FB-017" and "เบอร์" in v["topic"])
        ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def search_sop(query: str, limit: int = 5) -> str:
    """ค้นหาในคู่มือด้วยคำค้นภาษาไทยหรืออังกฤษ

    เป็นเครื่องมือหลักที่ควรเรียกก่อนตอบคำถามเกี่ยวกับงาน F&B ทุกครั้ง
    ค้นได้ทั้งศัพท์ในคู่มือและคำพูดติดปากที่พนักงานใช้จริง เช่น "แขกด่า" "รอนาน"
    "เก็บถาด" "แก้วแตกในสระ" ผลลัพธ์เรียงตามความเกี่ยวข้องพร้อมข้อความรอบจุดที่พบ

    Args:
        query: คำค้น เช่น "อุณหภูมิไวน์แดง" หรือ "แขกแพ้ถั่ว"
        limit: จำนวนผลลัพธ์สูงสุด (ค่าเริ่มต้น 5)
    """
    q = query.strip()
    if not q:
        return json.dumps({"error": "กรุณาระบุคำค้น"}, ensure_ascii=False)

    tokens = [t for t in q.lower().split() if t]
    grams = _ngrams(q.lower())

    scored = []
    for s in SECTIONS:
        title_l = s.title.lower()
        body_l = s.body.lower()
        kw_l = " ".join(s.keywords).lower()

        score = 0
        # คำที่ตรงทั้งคำให้น้ำหนักสูงสุด ใช้ได้กับคำอังกฤษและคำไทยที่ผู้ใช้เว้นวรรคมาเอง
        for t in tokens:
            if t in title_l:
                score += 10
            if t in kw_l:
                score += 8
            score += body_l.count(t)

        # คำพ้องที่โผล่อยู่ในคำถามเป็นสัญญาณแรงที่สุด เพราะพนักงานถามด้วยคำพูดติดปาก
        # เช่น "แขกบ่นว่ารออาหารนาน" มีคำว่า "บ่น" ซึ่งชี้ตรงไปที่ SOP ข้อร้องเรียน
        packed_q = re.sub(r"\s+", "", q.lower())
        for kw in s.keywords:
            if kw.lower() in packed_q:
                score += 14

        # ภาษาไทยไม่เว้นวรรค คำค้นอย่าง "อุณหภูมิไวน์แดง" จึงไม่ตรงทั้งวลีกับข้อความใด
        # จึงวัดจากสัดส่วนชิ้นส่วนของคำค้นที่ปรากฏในหัวข้อนั้นแทน
        if grams:
            score += round(_coverage(grams, title_l) * 12)
            score += round(_coverage(grams, kw_l) * 9)
            score += round(_coverage(grams, body_l) * 7)

        if score:
            scored.append((score, s, tokens + grams))

    if not scored:
        return json.dumps(
            {
                "query": query,
                "results": [],
                "hint": "ไม่พบคำนี้ในคู่มือ ลองใช้คำที่กว้างขึ้น หรือเรียก list_sops เพื่อดูหัวข้อทั้งหมด "
                        "หากเป็นเรื่องที่คู่มือไม่ครอบคลุม ให้แจ้งผู้ใช้ตรง ๆ แทนการเดา",
            },
            ensure_ascii=False, indent=2,
        )

    scored.sort(key=lambda x: -x[0])
    results = []
    for score, s, toks in scored[:limit]:
        results.append({
            "code": s.code,
            "title": s.title,
            "category": s.category,
            "score": score,
            "excerpt": _excerpt(s.body, toks),
        })

    return json.dumps(
        {"query": query, "found": len(scored), "results": results,
         "next_step": "เรียก get_sop ด้วยรหัสที่ตรงที่สุดเพื่อดูขั้นตอนเต็ม"},
        ensure_ascii=False, indent=2,
    )


def _ngrams(text: str, size: int = 4) -> list[str]:
    """ตัดคำค้นเป็นชิ้นส่วนต่อเนื่องความยาว 4 ตัวอักษร

    ภาษาไทยเขียนติดกันไม่มีช่องว่าง การค้นแบบตรงทั้งวลีจึงพลาดเกือบทุกครั้ง
    การเทียบเป็นชิ้นส่วนทำให้ "อุณหภูมิไวน์แดง" ยังจับคู่กับข้อความที่มีคำว่า
    "อุณหภูมิ" และ "ไวน์แดง" อยู่คนละที่กันได้
    """
    cleaned = re.sub(r"\s+", "", text)
    if len(cleaned) < size:
        return [cleaned] if cleaned else []
    return list({cleaned[i:i + size] for i in range(len(cleaned) - size + 1)})


def _coverage(grams: list[str], haystack: str) -> float:
    """สัดส่วนชิ้นส่วนของคำค้นที่พบในข้อความ ค่า 0 ถึง 1"""
    if not grams or not haystack:
        return 0.0
    packed = re.sub(r"\s+", "", haystack)
    return sum(1 for g in grams if g in packed) / len(grams)


def _excerpt(body: str, tokens: list[str], window: int = 220) -> str:
    """ตัดข้อความรอบตำแหน่งที่พบคำค้นคำแรก เพื่อให้เห็นบริบทโดยไม่ต้องโหลดทั้งหัวข้อ"""
    low = body.lower()
    pos = -1
    for t in tokens:
        pos = low.find(t)
        if pos != -1:
            break
    if pos == -1:
        pos = 0
    start = max(0, pos - window // 3)
    end = min(len(body), start + window)
    snippet = body[start:end].replace("\n", " ").strip()
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(body) else "")


@mcp.tool()
def get_reference_table(table: str = "") -> str:
    """ดึงตารางอ้างอิงที่ถูกเรียกดูบ่อย โดยไม่ต้องอ่าน SOP ทั้งหัวข้อ

    เหมาะกับคำถามสั้นหน้างานที่ต้องการตัวเลขทันที เช่น อุณหภูมิเสิร์ฟไวน์
    เวลามาตรฐานการเสิร์ฟ หรือเบอร์โทรฉุกเฉิน

    Args:
        table: ชื่อตาราง ได้แก่ temperatures, service_timing, wine_service, outlets,
               forms, kpi, emergency_contacts, complaint_handling
               เว้นว่างเพื่อดูรายการตารางที่มี
    """
    if not table.strip():
        return json.dumps(
            {"available_tables": {k: v[2] for k, v in TABLE_SOURCES.items()}},
            ensure_ascii=False, indent=2,
        )

    key = table.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in TABLE_SOURCES:
        return json.dumps(
            {"error": f"ไม่รู้จักตาราง '{table}'",
             "available_tables": {k: v[2] for k, v in TABLE_SOURCES.items()}},
            ensure_ascii=False, indent=2,
        )

    locator, sub, desc = TABLE_SOURCES[key]
    section = BY_CODE.get(locator) or next((s for s in SECTIONS if locator in s.title), None)
    if section is None:
        return json.dumps({"error": f"ไม่พบเนื้อหาต้นทางของตาราง '{table}'"}, ensure_ascii=False)

    content = _find_subsection(section, sub) if sub else section.body
    if content is None:
        content = section.body

    payload = {"table": key, "description": desc, "source": section.code or section.title,
               "content": content}
    if key in {"kpi", "emergency_contacts"}:
        payload["warning"] = next(
            (v for v in VERIFY_BEFORE_USE
             if ("ต้นทุน" in v["topic"] and key == "kpi") or ("เบอร์" in v["topic"] and key == "emergency_contacts")),
            None,
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def get_critical_rules() -> str:
    """ดึงกฎที่อยู่เหนือความรวดเร็วในการบริการและความพึงพอใจของแขก

    เรียกเมื่อคำถามแตะเรื่องแอลกอฮอล์ การแพ้อาหาร หรืออุณหภูมิอาหาร
    และเมื่อผู้ใช้ขอทางลัดที่อาจขัดกับกฎเหล่านี้ กฎในรายการนี้ไม่มีข้อยกเว้น
    ต้องรายงาน Duty Manager และบันทึก Incident Report ทุกครั้งที่เกิดเหตุ
    """
    return json.dumps(
        {
            "critical_rules": CRITICAL_RULES,
            "verify_before_use": VERIFY_BEFORE_USE,
            "note": "คู่มือนี้ยังไม่ผ่านการอนุมัติจากผู้จัดการทั่วไป "
                    "เมื่อผลิตเอกสารที่จะประกาศใช้ ให้เว้นช่องว่างพร้อมหมายเหตุแทนการเดาข้อมูล",
        },
        ensure_ascii=False, indent=2,
    )


@mcp.resource("sop://{source}")
def read_source(source: str) -> str:
    """เปิดไฟล์คู่มือทั้งไฟล์ สำหรับกรณีที่ต้องอ่านต่อเนื่องหลายหัวข้อ"""
    path = DATA_DIR / f"{source}.md"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in DATA_DIR.glob("*.md")))
        return f"ไม่พบไฟล์ '{source}' ไฟล์ที่มี: {available}"
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
