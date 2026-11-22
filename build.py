"""Build mess_menu.com outputs from menu.json.

Usage: python3 build.py menu.json index.html out.pdf
 - Rewrites the MENU and FETCHED lines in index.html from menu.json
 - Writes a one-page landscape A4 PDF of the week (days in date order)
"""
import json, re, sys
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from xml.sax.saxutils import escape

NONVEG = re.compile(r"chicken|egg curry|mutton|fish", re.I)
SPECIAL = re.compile(r"paneer|ice cream|halwa|barfi|sheera|churma|hot choco|chicken|naan|gulab jamun|shahi tukda|tofu", re.I)
MEALS = ["Breakfast", "Lunch", "Dinner"]

ACCENT = colors.HexColor("#d9480f")
INK = colors.HexColor("#1d1a16")
MUTED = colors.HexColor("#6f665a")
LINE = colors.HexColor("#e4dccd")
CREAM = colors.HexColor("#fbf6ec")
RED = colors.HexColor("#c92a2a")


def patch_html(menu, html_path):
    html = open(html_path, encoding="utf-8").read()
    days_js = json.dumps(menu["days"], ensure_ascii=False, indent=1)
    html, n1 = re.subn(r"const MENU = \[.*?\];\nconst ORDER",
                       lambda m: "const MENU = " + days_js + ";\nconst ORDER", html, flags=re.S)
    html, n2 = re.subn(r'const FETCHED = ".*?";', lambda m: f'const FETCHED = "{menu["fetched"]}";', html)
    if n1 != 1 or n2 != 1:
        sys.exit("Could not find MENU/FETCHED in index.html")
    open(html_path, "w", encoding="utf-8").write(html)


def build_pdf(menu, pdf_path):
    days = sorted(menu["days"], key=lambda d: d["date"])
    d0 = date.fromisoformat(days[0]["date"]); d1 = date.fromisoformat(days[-1]["date"])
    span = f"{d0.day} {d0:%b} – {d1.day} {d1:%b %Y}"

    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, textColor=INK, leading=24)
    sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, textColor=MUTED, leading=12)
    head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white, leading=11, alignment=1)
    rowlab = ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=10, textColor=ACCENT, leading=12)
    cell = ParagraphStyle("c", fontName="Helvetica", fontSize=8.3, textColor=INK, leading=10.2)
    foot = ParagraphStyle("f", fontName="Helvetica", fontSize=7, textColor=MUTED, leading=9)

    def cell_para(meal):
        lines = [f'<font color="#6f665a"><b>{escape(meal["time"])}</b></font>']
        for it in meal["items"]:
            t = escape(it)
            if SPECIAL.search(it): t = f"<b>{t}</b>"
            dot = '<font color="#c92a2a">&#8226;</font>' if NONVEG.search(it) else '<font color="#d9480f">&#183;</font>'
            lines.append(f"{dot} {t}")
        return Paragraph("<br/>".join(lines), cell)

    data = [[""] + [Paragraph(f'{d["day"]}<br/><font size="8">{date.fromisoformat(d["date"]).day} '
                              f'{date.fromisoformat(d["date"]):%b}</font>', head) for d in days]]
    for m in MEALS:
        data.append([Paragraph(m, rowlab)] + [cell_para(d["meals"][m]) for d in days])

    page_w, page_h = landscape(A4)
    margin = 22
    label_w = 58
    col_w = (page_w - 2 * margin - label_w) / 7
    t = Table(data, colWidths=[label_w] + [col_w] * 7, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (-1, 0), ACCENT),
        ("BACKGROUND", (0, 1), (0, -1), CREAM),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, CREAM]),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), leftMargin=margin, rightMargin=margin,
                            topMargin=18, bottomMargin=14, title=f"Mess menu {span}", author="mess_menu.com")
    story = [
        Paragraph('mess_menu<font color="#d9480f">.com</font>', title),
        Paragraph(f"Weekly mess menu · BITS Pilani, Pilani campus · {span}", sub),
        Spacer(1, 8), t, Spacer(1, 6),
        Paragraph('<font color="#c92a2a">&#8226;</font> non-veg &nbsp;&nbsp; <b>bold</b> = special &nbsp;&nbsp; '
                  f'Source: ssms-pilani.in (SSMS), fetched {escape(menu["fetched"])}. Unofficial; check the official site for last-minute changes.', foot),
    ]
    doc.build(story)


if __name__ == "__main__":
    src, html_path, pdf_path = sys.argv[1:4]
    menu = json.load(open(src, encoding="utf-8"))
    assert len(menu["days"]) == 7, "expected 7 days"
    patch_html(menu, html_path)
    build_pdf(menu, pdf_path)
    print("ok", pdf_path)
