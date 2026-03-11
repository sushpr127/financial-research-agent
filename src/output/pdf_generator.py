import os
import re
import io
from datetime import date
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle, Image,
    KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable

NAVY    = colors.HexColor("#0D1B2A")
COBALT  = colors.HexColor("#2563EB")
SKY     = colors.HexColor("#DBEAFE")
GOLD    = colors.HexColor("#D4AF37")
CHARCOAL= colors.HexColor("#1F2937")
SLATE   = colors.HexColor("#6B7280")
LIGHT   = colors.HexColor("#F9FAFB")
WHITE   = colors.white
GREEN   = colors.HexColor("#065F46")
GREEN_BG= colors.HexColor("#D1FAE5")
RED     = colors.HexColor("#991B1B")
RED_BG  = colors.HexColor("#FEE2E2")
DIVIDER = colors.HexColor("#E5E7EB")


def _fmt_number(val):
    """
    FIX 1: Round bare floats (P/E ratios, multiples) to 2 dp.
    Leave values that already carry units (%, $, B, T, M, x) untouched.
    """
    if val is None or val == "" or val == 0:
        return "N/A"
    sv = str(val)
    if any(c in sv for c in ('%', '$', 'B', 'T', 'M', 'x')):
        return sv
    try:
        return f"{float(sv.replace(',', '')):.2f}"
    except Exception:
        return sv


class CoverPage(Flowable):
    def __init__(self, ticker, company_name, report_date,
                 recommendation, current_price, target_price, num_analysts="—"):
        super().__init__()
        self.ticker        = ticker
        self.company_name  = company_name
        self.report_date   = report_date
        self.recommendation= recommendation
        self.current_price = current_price
        self.target_price  = target_price
        self.num_analysts  = num_analysts
        self.width, self.height = letter

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        c.setFillColor(colors.white)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#F0F4F8"))
        c.rect(0, 0, W, H * 0.45, fill=1, stroke=0)
        c.setFillColor(COBALT)
        c.rect(0, H - 7, W, 7, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#DDE3EA"))
        for x in range(30, int(W), 22):
            for y in range(int(H * 0.45) + 10, int(H) - 10, 22):
                c.circle(x, y, 0.8, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#E8ECF0"))
        c.setFont("Helvetica-Bold", 160)
        c.drawCentredString(W / 2, H * 0.52, self.ticker)

        c.setFillColor(COBALT)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(0.6 * inch, H - 0.48 * inch,
                     "EQUITY RESEARCH  ·  INVESTMENT MEMORANDUM")
        c.setFillColor(SLATE)
        c.drawRightString(W - 0.6 * inch, H - 0.48 * inch, self.report_date)

        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.5)
        c.line(0.6 * inch, H - 0.58 * inch, W - 0.6 * inch, H - 0.58 * inch)

        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(0.6 * inch, H - 1.35 * inch, self.company_name)

        pill_x = 0.6 * inch
        pill_y = H - 1.82 * inch
        c.setFillColor(COBALT)
        c.roundRect(pill_x, pill_y, 0.95 * inch, 0.30 * inch, 5, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(pill_x + 0.475 * inch, pill_y + 0.09 * inch, self.ticker)

        date_pill_x = pill_x + 1.05 * inch
        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.roundRect(date_pill_x, pill_y, 1.8 * inch, 0.30 * inch, 5, fill=1, stroke=0)
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 9)
        c.drawCentredString(date_pill_x + 0.9 * inch, pill_y + 0.09 * inch,
                            f"Report Date: {self.report_date}")

        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(1)
        c.line(0.6 * inch, H * 0.46 + 6, W - 0.6 * inch, H * 0.46 + 6)

        PAD   = 0.55 * inch
        PNL_X = PAD
        PNL_W = W - 2 * PAD
        PNL_H = 1.55 * inch
        PNL_Y = H * 0.45 - PNL_H - 0.15 * inch

        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.roundRect(PNL_X + 3, PNL_Y - 3, PNL_W, PNL_H, 10, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.roundRect(PNL_X, PNL_Y, PNL_W, PNL_H, 10, fill=1, stroke=0)
        c.setStrokeColor(COBALT)
        c.setLineWidth(2.5)
        c.line(PNL_X + 10, PNL_Y + PNL_H, PNL_X + PNL_W - 10, PNL_Y + PNL_H)

        col_xs = [PNL_X + PNL_W * 0.17, PNL_X + PNL_W * 0.42,
                  PNL_X + PNL_W * 0.67, PNL_X + PNL_W * 0.88]
        label_y = PNL_Y + PNL_H - 0.30 * inch
        value_y = PNL_Y + PNL_H - 0.82 * inch
        sub_y   = PNL_Y + PNL_H - 1.12 * inch

        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(1)
        for div_x in [PNL_X + PNL_W * 0.295,
                      PNL_X + PNL_W * 0.545,
                      PNL_X + PNL_W * 0.775]:
            c.line(div_x, PNL_Y + 0.15 * inch, div_x, PNL_Y + PNL_H - 0.1 * inch)

        rec = str(self.recommendation).upper()
        rec_val_color = (colors.HexColor("#16A34A") if "BUY"  in rec else
                         colors.HexColor("#DC2626") if "SELL" in rec else
                         colors.HexColor("#D97706"))

        # FIX 2: Dynamic font size so STRONG_BUY never gets clipped
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(col_xs[0], label_y, "RECOMMENDATION")
        c.setFillColor(rec_val_color)
        rec_font = 14 if len(rec) > 8 else (18 if len(rec) > 6 else 24)
        c.setFont("Helvetica-Bold", rec_font)
        c.drawCentredString(col_xs[0], value_y, rec)

        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(col_xs[1], label_y, "CURRENT PRICE")
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(col_xs[1], value_y, f"${self.current_price}")

        try: 
            cp_f   = float(str(self.current_price).replace(',', ''))
            tp_f   = float(str(self.target_price).replace(',', ''))
            upside = ((tp_f - cp_f) / cp_f) * 100
            upside_str   = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"
            upside_color = (colors.HexColor("#16A34A") if upside >= 0
                            else colors.HexColor("#DC2626"))
        except Exception:
            upside_str   = "N/A"
            upside_color = NAVY

        # FIX 3: Price target always 2 decimal places
        try:
            tp_disp = f"${float(str(self.target_price).replace(',', '')):.2f}"
        except Exception:
            tp_disp = f"${self.target_price}"

        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(col_xs[2], label_y, "PRICE TARGET")
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(col_xs[2], value_y, tp_disp)
        c.setFillColor(upside_color)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(col_xs[2], sub_y, upside_str + " upside")

        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(col_xs[3], label_y, "ANALYST COVERAGE")
        c.setFillColor(COBALT)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(col_xs[3], value_y, str(self.num_analysts))
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 8)
        c.drawCentredString(col_xs[3], sub_y, "analysts")

        c.setFillColor(colors.HexColor("#94A3B8"))
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(W / 2, 0.52 * inch,
            "Generated by Financial Research Agent  ·  "
            "For informational purposes only  ·  Not investment advice")
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.5)
        c.line(0.6 * inch, 0.67 * inch, W - 0.6 * inch, 0.67 * inch)


class SectionLabel(Flowable):
    def __init__(self, text, width=6.8 * inch):
        super().__init__()
        self.text  = text
        self.width = width
        self.height= 0.38 * inch

    def draw(self):
        c = self.canv
        c.setFillColor(SKY)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(COBALT)
        c.rect(0, 0, 4, self.height, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(12, 0.12 * inch, self.text.upper())


def _metric_card(label, value, sub=None, highlight=False):
    items = [
        Paragraph(f'<font size="8" color="#6B7280">{label}</font>',
            ParagraphStyle("ml", fontName="Helvetica", fontSize=8,
                textColor=SLATE, leading=10)),
        Paragraph(f'<b><font size="14" color="#0D1B2A">{value}</font></b>',
            ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=14,
                textColor=NAVY, leading=17)),
    ]
    if sub:
        items.append(Paragraph(f'<font size="7.5" color="#6B7280">{sub}</font>',
            ParagraphStyle("ms", fontName="Helvetica", fontSize=7.5,
                textColor=SLATE, leading=9)))
    return items


def _make_gauge_chart(score):
    fig, ax = plt.subplots(figsize=(3.2, 1.8), subplot_kw=dict(aspect="equal"))
    fig.patch.set_facecolor('#F9FAFB')
    ax.set_facecolor('#F9FAFB')
    score  = max(0, min(10, score))
    theta  = np.linspace(np.pi, 0, 100)
    ax.plot(np.cos(theta), np.sin(theta), linewidth=14,
            color='#E5E7EB', solid_capstyle='round')
    if score > 0:
        color  = '#22C55E' if score <= 3 else ('#F59E0B' if score <= 6 else '#EF4444')
        theta2 = np.linspace(np.pi, np.pi - (score / 10.0) * np.pi, 100)
        ax.plot(np.cos(theta2), np.sin(theta2), linewidth=14,
                color=color, solid_capstyle='round')
    level = "LOW" if score <= 3 else ("MEDIUM" if score <= 6 else "HIGH")
    ax.text(0, -0.05, f"{score}/10", ha='center', va='center',
            fontsize=20, fontweight='bold', color='#0D1B2A')
    ax.text(0, -0.38, level, ha='center', va='center', fontsize=9,
            fontweight='bold',
            color='#22C55E' if score <= 3 else ('#F59E0B' if score <= 6 else '#EF4444'))
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-0.6, 1.2); ax.axis('off')
    plt.tight_layout(pad=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#F9FAFB')
    plt.close(fig); buf.seek(0)
    return buf


def _make_metrics_bar_chart(fin):
    metrics = {}
    for k, lbl in [("gross_margin", "Gross Margin"),
                   ("operating_margin", "Operating Margin"),
                   ("net_margin", "Net Margin")]:
        v = fin.get(k)
        if v and v != "N/A":
            try:
                metrics[lbl] = float(str(v).replace('%', '').replace(',', ''))
            except Exception:
                pass
    if not metrics:
        return None
    fig, ax = plt.subplots(figsize=(4.5, 1.8))
    fig.patch.set_facecolor('#F9FAFB'); ax.set_facecolor('#F9FAFB')
    labels, values = list(metrics.keys()), list(metrics.values())
    bars = ax.barh(labels, values,
                   color=['#2563EB', '#1B4F8A', '#0D1B2A'][:len(labels)],
                   height=0.5, edgecolor='none')
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', ha='left', fontsize=8.5,
                fontweight='bold', color='#1F2937')
    ax.set_xlim(0, max(values) * 1.25)
    for sp in ['top', 'right', 'left']:
        ax.spines[sp].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.tick_params(axis='y', labelsize=8, labelcolor='#6B7280')
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#F9FAFB')
    plt.close(fig); buf.seek(0)
    return buf


def _make_growth_chart(fin):
    vals = {}
    for lbl, k in [("Revenue Growth", "revenue_growth"),
                   ("Earnings Growth", "earnings_growth")]:
        v = fin.get(k)
        if v and v != "N/A":
            try:
                vals[lbl] = float(str(v).replace('%', '').replace(',', ''))
            except Exception:
                pass
    if not vals:
        return None
    fig, ax = plt.subplots(figsize=(3.0, 1.8))
    fig.patch.set_facecolor('#F9FAFB'); ax.set_facecolor('#F9FAFB')
    labels, values = list(vals.keys()), list(vals.values())
    bars = ax.bar(labels, values,
                  color=['#22C55E' if v >= 0 else '#EF4444' for v in values],
                  width=0.45, edgecolor='none')
    for bar, val in zip(bars, values):
        ypos = val + 0.3 if val >= 0 else val - 1.5
        ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                f'{val:+.1f}%', ha='center',
                va='bottom' if val >= 0 else 'top',
                fontsize=8.5, fontweight='bold', color='#1F2937')
    ax.axhline(0, color='#D1D5DB', linewidth=0.8)
    for sp in ['top', 'right', 'left']:
        ax.spines[sp].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=True)
    ax.tick_params(axis='x', labelsize=7.5, labelcolor='#6B7280')
    ax.tick_params(axis='y', labelleft=False)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#F9FAFB')
    plt.close(fig); buf.seek(0)
    return buf


def _styles():
    return {
        "kicker":  ParagraphStyle("kicker", fontName="Helvetica", fontSize=8,
                       textColor=COBALT, spaceAfter=2, letterSpacing=1),
        "h1":      ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18,
                       textColor=NAVY, spaceAfter=4, leading=22),
        "body":    ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                       textColor=CHARCOAL, leading=15, spaceAfter=5,
                       alignment=TA_JUSTIFY),
        "bullet":  ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                       textColor=CHARCOAL, leading=14, spaceAfter=3,
                       leftIndent=14),
        "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=7.5,
                       textColor=SLATE, spaceAfter=2, alignment=TA_CENTER),
        "th":      ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8.5,
                       textColor=WHITE),
        "disc":    ParagraphStyle("disc", fontName="Helvetica", fontSize=7,
                       textColor=SLATE, leading=10, alignment=TA_JUSTIFY),
    }


def _parse_memo(memo_text):
    section_map = {
        "executive summary":    "exec",
        "financial highlights": "financials",
        "recent developments":  "developments",
        "risk factors":         "risks",
        "valuation":            "valuation",
    }
    sections = {v: [] for v in section_map.values()}
    current  = None
    for line in memo_text.split("\n"):
        s  = line.strip()
        hm = re.match(r'^#{1,3}\s+(.+)', s)
        if hm:
            htxt    = hm.group(1).lower()
            current = next((v for k, v in section_map.items() if k in htxt), None)
        elif current and s:
            sections[current].append(s)
    return {k: "\n".join(v) for k, v in sections.items()}


def _flowables(text, S):
    """
    Convert section text to ReportLab flowables.
    FIX 4: Strips leading stray asterisk Gemini artifact (* **Bold:** text)
    FIX 5: Removes double numbering (1. 1. Text → 1. Text)
    """
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            out.append(Spacer(1, 3))
            continue

        # Convert **bold** to ReportLab tags
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)

        # Strip leading stray asterisk: "* <b>Revenue:</b> ..." → "<b>Revenue:</b> ..."
        s = re.sub(r'^\*\s+', '', s)

        if re.match(r'^[\*\-]\s+', s):
            text_content = re.sub(r'^[\*\-]\s+', '', s)
            out.append(Paragraph(f"<bullet>&bull;</bullet> {text_content}", S["bullet"]))

        elif re.match(r'^\d+\.\s+', s):
            # Fix double numbering: "1. 1. Text" or "1. 2. Text" → "1. Text"
            s = re.sub(r'^(\d+)\.\s+\d+\.\s+', r'\1. ', s)
            num          = re.match(r'^(\d+)\.', s).group(1)
            text_content = re.sub(r'^\d+\.\s+', '', s)
            out.append(Paragraph(f"<bullet>{num}.</bullet> {text_content}", S["bullet"]))

        else:
            out.append(Paragraph(s, S["body"]))

    return out


def _header_footer(canvas, doc):
    canvas.saveState()
    W, H = letter
    canvas.setStrokeColor(COBALT); canvas.setLineWidth(1.5)
    canvas.line(0.6 * inch, H - 0.45 * inch, W - 0.6 * inch, H - 0.45 * inch)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(SLATE)
    canvas.drawString(0.6 * inch, H - 0.38 * inch,
                      "EQUITY RESEARCH  ·  INVESTMENT MEMORANDUM")
    canvas.drawRightString(W - 0.6 * inch, H - 0.38 * inch, doc.ticker_label)
    canvas.setStrokeColor(DIVIDER); canvas.setLineWidth(0.5)
    canvas.line(0.6 * inch, 0.5 * inch, W - 0.6 * inch, 0.5 * inch)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(SLATE)
    canvas.drawCentredString(W / 2, 0.34 * inch, f"Page {doc.page}")
    canvas.drawString(0.6 * inch, 0.34 * inch, doc.report_date_label)
    canvas.drawRightString(W - 0.6 * inch, 0.34 * inch, "CONFIDENTIAL")
    canvas.restoreState()


def generate_pdf(memo_text, ticker, company_name,
                 financial_data=None, risk_assessment=None,
                 output_dir="outputs") -> str:

    os.makedirs(output_dir, exist_ok=True)
    today    = date.today().strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"{ticker.upper()}_memo_{today}.pdf")

    doc = SimpleDocTemplate(filepath, pagesize=letter,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.75 * inch,  bottomMargin=0.75 * inch)
    doc.ticker_label      = f"{company_name}  ({ticker.upper()})"
    doc.report_date_label = f"Report Date: {today}"

    S        = _styles()
    fin      = financial_data or {}
    sections = _parse_memo(memo_text)
    story    = []

    rec = str(fin.get("analyst_recommendation", "N/A"))
    cp = f"{float(fin.get('current_price', 0)):.2f}" if fin.get('current_price') != 'N/A' else 'N/A'
    tp  = str(fin.get("target_price",           "N/A"))

    # ── PAGE 1 — COVER ────────────────────────────────────────────────────────
    cover = CoverPage(
        ticker=ticker.upper(), company_name=company_name,
        report_date=today, recommendation=rec,
        current_price=cp, target_price=tp,
        num_analysts=str(fin.get("number_of_analysts", "—")))
    cover.width, cover.height = letter
    story.append(cover)
    story.append(PageBreak())

    # ── PAGE 2 — OVERVIEW + METRICS ───────────────────────────────────────────
    def safe(key):
        v = fin.get(key, "N/A")
        if v is None or v == "" or v == 0:
            return "N/A"
        # Hide negative EV/EBITDA — occurs when cash > debt (e.g. Berkshire)
        # Mathematically valid but confusing in a report
        if key == "ev_ebitda":
            sv = str(v)
            if sv.startswith("-"):
                return "N/A"
        formatted = _fmt_number(v)
        # Hide Price/Book that rounds to 0.00 — bad Yahoo Finance data
        if key == "price_to_book" and formatted == "0.00":
            return "N/A"
        return formatted

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("INVESTMENT OVERVIEW", S["kicker"]))
    story.append(Paragraph(f"{company_name} ({ticker.upper()})", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COBALT, spaceAfter=10))

    def card_row(cards):
        cols = []
        for card in cards:
            cell = Table([[p] for p in card], colWidths=[2.0 * inch])
            cell.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("PADDING",    (0, 0), (-1, -1), 7),
                ("LINEABOVE",  (0, 0), (-1, 0),  2, COBALT),
            ]))
            cols.append(cell)
        tbl = Table([cols], colWidths=[2.15 * inch] * 3)
        tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tbl

    story.append(card_row([
        _metric_card("Market Cap",    safe("market_cap"),  "Total capitalisation", True),
        _metric_card("Revenue (TTM)", safe("revenue_ttm"), "Trailing 12 months"),
        _metric_card("Net Income",    safe("net_income"),  "Trailing 12 months",   True),
    ]))
    story.append(Spacer(1, 4))
    story.append(card_row([
        _metric_card("P/E Ratio",   safe("pe_ratio"),   "Price / Earnings"),
        _metric_card("Forward P/E", safe("forward_pe"), "Next 12 months", True),
        _metric_card("EV/EBITDA",   safe("ev_ebitda"),  "Enterprise value multiple"),
    ]))
    story.append(Spacer(1, 4))
    story.append(card_row([
        _metric_card("Gross Margin",     safe("gross_margin"), "% of revenue", True),
        _metric_card("Net Margin",       safe("net_margin"),   "% of revenue"),
        _metric_card("Return on Equity", safe("roe"),          "Shareholder return", True),
    ]))
    story.append(Spacer(1, 10))

    story.append(SectionLabel("Executive Summary"))
    story.append(Spacer(1, 6))
    if sections.get("exec"):
        story.extend(_flowables(sections["exec"], S))

    story.append(Spacer(1, 8))

    rec_color_hex = ("#065F46" if "buy"  in rec.lower() else
                     "#991B1B" if "sell" in rec.lower() else "#92400E")
    rec_bg_hex    = ("#D1FAE5" if "buy"  in rec.lower() else
                     "#FEE2E2" if "sell" in rec.lower() else "#FEF3C7")

    # FIX 3 applied to consensus table price target
    try:
        tp_fmt = f"${float(str(tp).replace(',', '')):.2f}"
    except Exception:
        tp_fmt = f"${tp}"

    consensus = [
        [Paragraph('<font color="#6B7280" size="8">ANALYST CONSENSUS</font>', S["caption"]),
         Paragraph('<font color="#6B7280" size="8">NO. OF ANALYSTS</font>',   S["caption"]),
         Paragraph('<font color="#6B7280" size="8">PRICE TARGET</font>',      S["caption"]),
         Paragraph('<font color="#6B7280" size="8">CURRENT PRICE</font>',     S["caption"])],
        [Paragraph(f'<b><font color="{rec_color_hex}" size="14">{rec.upper()}</font></b>', S["body"]),
         Paragraph(f'<b><font size="14">{fin.get("number_of_analysts", "N/A")}</font></b>', S["body"]),
         Paragraph(f'<b><font size="14">{tp_fmt}</font></b>', S["body"]),
         Paragraph(f'<b><font size="14">${cp}</font></b>',    S["body"])],
    ]
    ctbl = Table(consensus, colWidths=[1.65 * inch] * 4)
    ctbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BACKGROUND", (0, 0), (0, -1),  colors.HexColor(rec_bg_hex)),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",    (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.5, DIVIDER),
        ("LINEABOVE",  (0, 0), (-1, 0),  1.5, COBALT),
    ]))
    story.append(ctbl)
    story.append(PageBreak())

    # ── PAGE 3 — FINANCIALS ───────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("FINANCIAL ANALYSIS", S["kicker"]))
    story.append(Paragraph("Key Financial Metrics & Performance", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COBALT, spaceAfter=10))

    mb = _make_metrics_bar_chart(fin)
    gb = _make_growth_chart(fin)
    if mb and gb:
        chart_tbl = Table([[
            Table([[Paragraph("MARGIN ANALYSIS", S["kicker"])],
                   [Image(mb, width=3.5 * inch, height=1.6 * inch)]],
                  colWidths=[3.6 * inch]),
            Table([[Paragraph("YoY GROWTH", S["kicker"])],
                   [Image(gb, width=2.5 * inch, height=1.6 * inch)]],
                  colWidths=[2.8 * inch]),
        ]], colWidths=[3.7 * inch, 2.9 * inch])
        chart_tbl.setStyle(TableStyle([
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("PADDING",    (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.5, DIVIDER),
        ]))
        story.append(chart_tbl)
        story.append(Spacer(1, 10))

    story.append(SectionLabel("Comprehensive Financial Data"))
    story.append(Spacer(1, 6))

    fin_pairs = [
        ("Revenue (TTM)",       safe("revenue_ttm")),
        ("Gross Profit",        safe("gross_profit")),
        ("Net Income",          safe("net_income")),
        ("EBITDA",              safe("ebitda")),
        ("Gross Margin",        safe("gross_margin")),
        ("Operating Margin",    safe("operating_margin")),
        ("Net Margin",          safe("net_margin")),
        ("Return on Equity",    safe("roe")),
        ("P/E Ratio",           safe("pe_ratio")),
        ("Forward P/E",         safe("forward_pe")),
        ("EV/EBITDA",           safe("ev_ebitda")),
        ("Price/Book",          safe("price_to_book")),
        ("Revenue Growth YoY",  safe("revenue_growth")),
        ("Earnings Growth YoY", safe("earnings_growth")),
        ("Total Debt",          safe("total_debt")),
        ("Cash & Equivalents",  safe("cash")),
        ("Debt/Equity",         safe("debt_to_equity")),
        ("Current Ratio",       safe("current_ratio")),
    ]

    fin_rows = [[Paragraph("METRIC", S["th"]), Paragraph("VALUE", S["th"]),
                 Paragraph("METRIC", S["th"]), Paragraph("VALUE", S["th"])]]
    lbl_s = ParagraphStyle("fl", fontName="Helvetica-Bold", fontSize=8.5, textColor=NAVY)
    val_s = ParagraphStyle("fv", fontName="Helvetica",      fontSize=8.5, textColor=CHARCOAL)

    for i in range(0, len(fin_pairs), 2):
        ll, lv = fin_pairs[i]
        rl, rv = fin_pairs[i + 1] if i + 1 < len(fin_pairs) else ("", "")
        fin_rows.append([Paragraph(ll, lbl_s), Paragraph(lv, val_s),
                         Paragraph(rl, lbl_s), Paragraph(rv, val_s)])

    fin_tbl = Table(fin_rows, colWidths=[1.8 * inch, 1.5 * inch, 1.8 * inch, 1.5 * inch])
    fin_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT, WHITE]),
        ("PADDING",       (0, 0), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0.3, DIVIDER),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.5, GOLD),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(fin_tbl)
    story.append(Spacer(1, 10))
    story.append(SectionLabel("Management Commentary"))
    story.append(Spacer(1, 6))
    if sections.get("financials"):
        story.extend(_flowables(sections["financials"], S))
    story.append(PageBreak())

    # ── PAGE 4 — RISK ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("RISK & MARKET INTELLIGENCE", S["kicker"]))
    story.append(Paragraph("Risk Assessment & Recent Developments", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COBALT, spaceAfter=10))

    score, level = 5, "MEDIUM"
    if risk_assessment:
        sm = re.search(r'RISK SCORE[:\s]+(\d+)/10', risk_assessment, re.IGNORECASE)
        if sm:
            score = int(sm.group(1))
        # Derive level from score number so gauge and label always match.
        # Never parse from Gemini text — it sometimes writes LOW for score 4
        # causing "4/10 MEDIUM" on gauge but "LOW" in the label below it.
        level = ("VERY HIGH" if score >= 9 else
                 "HIGH"      if score >= 7 else
                 "LOW"       if score <= 3 else
                 "MEDIUM")
    flags      = fin.get("analyst_flags", []) or []
    flags_text = "\n".join([f"• {f}" for f in flags]) if flags else "• No critical flags detected"

    risk_row = Table([[
        Table([
            [Paragraph("RISK SCORE", S["kicker"])],
            [Image(_make_gauge_chart(score), width=2.5 * inch, height=1.5 * inch)],
            [Paragraph(f"Overall Risk Level: <b>{level}</b>",
                ParagraphStyle("rl", fontName="Helvetica", fontSize=8.5,
                    textColor=CHARCOAL, leading=12))],
        ], colWidths=[2.8 * inch]),
        Table([
            [Paragraph("ANALYST FLAGS", S["kicker"])],
            [Paragraph(flags_text,
                ParagraphStyle("fl2", fontName="Helvetica", fontSize=8.5,
                    textColor=CHARCOAL, leading=14, leftIndent=4))],
        ], colWidths=[3.5 * inch]),
    ]], colWidths=[2.9 * inch, 3.7 * inch])
    risk_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(risk_row)
    story.append(Spacer(1, 10))

    story.append(SectionLabel("Risk Factors"))
    story.append(Spacer(1, 6))
    if sections.get("risks"):
        story.extend(_flowables(sections["risks"], S))
    story.append(Spacer(1, 10))

    story.append(SectionLabel("Recent Developments & News"))
    story.append(Spacer(1, 6))
    if sections.get("developments"):
        story.extend(_flowables(sections["developments"], S))
    story.append(PageBreak())

    # ── PAGE 5 — VALUATION ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("VALUATION & RECOMMENDATION", S["kicker"]))
    story.append(Paragraph("Investment Thesis & Price Target Analysis", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COBALT, spaceAfter=10))

    try:
        upside    = ((float(tp) - float(cp)) / float(cp)) * 100
        up_str    = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"
        up_hex    = "#065F46" if upside >= 0 else "#991B1B"
        up_bg_hex = "#D1FAE5" if upside >= 0 else "#FEE2E2"
    except Exception:
        up_str    = "N/A"
        up_hex    = "#065F46"
        up_bg_hex = "#D1FAE5"

    # FIX 3: Price target 2dp on page 5
    try:
        tp_p5 = f"${float(str(tp).replace(',', '')):.2f}"
    except Exception:
        tp_p5 = f"${tp}"

    # FIX 2: STRONG_BUY never clipped on page 5
    rec_font_p5 = "14" if len(rec) > 8 else ("16" if len(rec) > 6 else "18")

    up_tbl = Table([[
        Table([[Paragraph('<font color="#6B7280" size="8">CURRENT PRICE</font>', S["caption"])],
               [Paragraph(f'<b><font size="18">${cp}</font></b>', S["body"])]],
              colWidths=[1.8 * inch]),
        Table([[Paragraph('<font color="#6B7280" size="8">PRICE TARGET</font>', S["caption"])],
               [Paragraph(f'<b><font size="18">{tp_p5}</font></b>', S["body"])]],
              colWidths=[1.8 * inch]),
        Table([[Paragraph('<font color="#6B7280" size="8">POTENTIAL UPSIDE</font>', S["caption"])],
               [Paragraph(f'<b><font size="22" color="{up_hex}">{up_str}</font></b>', S["body"])]],
              colWidths=[1.8 * inch]),
        Table([[Paragraph('<font color="#6B7280" size="8">RECOMMENDATION</font>', S["caption"])],
               [Paragraph(f'<b><font size="{rec_font_p5}" color="{up_hex}">{rec.upper()}</font></b>',
                          S["body"])]],
              colWidths=[1.8 * inch]),
    ]], colWidths=[1.65 * inch] * 4)
    up_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BACKGROUND", (2, 0), (3, 0),   colors.HexColor(up_bg_hex)),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",    (0, 0), (-1, -1), 10),
        ("GRID",       (0, 0), (-1, -1), 0.5, DIVIDER),
        ("LINEABOVE",  (0, 0), (-1, 0),  2.5, colors.HexColor(up_hex)),
    ]))
    story.append(up_tbl)
    story.append(Spacer(1, 12))

    story.append(SectionLabel("Valuation Analysis"))
    story.append(Spacer(1, 6))
    if sections.get("valuation"):
        story.extend(_flowables(sections["valuation"], S))
    story.append(Spacer(1, 12))

    exec_lines = [l.strip() for l in sections.get("exec", "").split("\n")
                  if l.strip()][:4]
    if exec_lines:
        story.append(SectionLabel("Investment Thesis Summary"))
        story.append(Spacer(1, 6))
        thesis_rows = [[Paragraph("KEY INVESTMENT POINTS", S["kicker"])]]
        for item in exec_lines:
            item = re.sub(r'\*\*(.+?)\*\*', r'\1', item)
            item = re.sub(r'^\*\s+', '', item)  # FIX 4
            thesis_rows.append([Paragraph(f"<bullet>&bull;</bullet> {item}",
                ParagraphStyle("ti", fontName="Helvetica", fontSize=9,
                    textColor=CHARCOAL, leading=14, leftIndent=10))])
        tt = Table(thesis_rows, colWidths=[6.3 * inch])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SKY),
            ("BACKGROUND", (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0),  WHITE),
            ("PADDING",    (0, 0), (-1, -1), 9),
            ("LINEBEFORE", (0, 0), (0, -1),  3, GOLD),
        ]))
        story.append(tt)
        story.append(Spacer(1, 12))

    if risk_assessment:
        story.append(SectionLabel("Full Risk Assessment"))
        story.append(Spacer(1, 6))
        for line in risk_assessment.strip().split("\n"):
            l = line.strip()
            if not l:
                story.append(Spacer(1, 3))
                continue
            story.append(Paragraph(re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', l), S["body"]))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDER, spaceAfter=6))
    story.append(Paragraph(
        "<b>IMPORTANT DISCLAIMER:</b> This investment memorandum has been generated by an "
        "AI-powered Financial Research Agent for educational and informational purposes only. "
        "It does not constitute investment advice, a solicitation, or an offer to buy or sell "
        "any securities. Past performance is not indicative of future results. All financial "
        "data is sourced from public filings, market data providers, and news sources. "
        "Always conduct your own due diligence and consult a qualified financial advisor "
        "before making investment decisions.", S["disc"]))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    from reportlab.platypus.doctemplate import PageTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.platypus import NextPageTemplate

    W, H = letter
    doc.addPageTemplates([
        PageTemplate(
            id='Cover',
            frames=[Frame(0, 0, W, H,
                          leftPadding=0, bottomPadding=0,
                          rightPadding=0, topPadding=0, id='cover')],
            onPage=lambda c, d: None),
        PageTemplate(
            id='Content',
            frames=[Frame(doc.leftMargin, doc.bottomMargin,
                          W - doc.leftMargin - doc.rightMargin,
                          H - doc.topMargin  - doc.bottomMargin, id='normal')],
            onPage=_header_footer),
    ])
    story.insert(1, NextPageTemplate('Content'))
    doc.build(story)
    print(f"   📄 PDF saved: {filepath}")
    return filepath


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    sample_memo = """
## Executive Summary
Apple Inc. (AAPL) is the world's most valuable company, designing and selling premium
consumer electronics, software, and digital services. TTM revenue of $435.62B with a
net margin of 27.04%. BUY rating supported by strong brand loyalty and AI integration.

## Financial Highlights
* **Revenue (TTM):** $435.62B
* **Gross Margin:** 47.33%
* **Operating Margin:** 35.37%
* **Net Margin:** 27.04%
* **Revenue Growth YoY:** 15.70%
* **Earnings Growth YoY:** 18.30%

## Recent Developments
Apple beat Q4 FY2025 EPS by $0.08. iPhone 16 demand strong. $110B buyback announced.

## Risk Factors
1. **Liquidity Risk:** Current ratio of 0.974.
2. **China Concentration:** ~18% of revenue exposed to US-China tensions.
3. **Regulatory:** EU App Store investigations ongoing.

## Valuation & Recommendation
P/E 33.02x, forward P/E 28.07x. Price target $295.44 implies 13.27% upside. BUY.
"""
    path = generate_pdf(
        memo_text=sample_memo,
        ticker="AAPL",
        company_name="Apple Inc.",
        financial_data={
            "market_cap": "$3.84T", "revenue_ttm": "$435.62B",
            "net_income": "$117.85B", "gross_profit": "$206.20B",
            "ebitda": "$137.35B", "gross_margin": "47.33%",
            "operating_margin": "35.37%", "net_margin": "27.04%",
            "roe": "152.02%", "pe_ratio": 33.02, "forward_pe": 28.07,
            "ev_ebitda": "24.8x", "price_to_book": "52.1x",
            "revenue_growth": "15.70%", "earnings_growth": "18.30%",
            "total_debt": "$104.59B", "cash": "$65.17B",
            "debt_to_equity": "102.63%", "current_ratio": 0.974,
            "analyst_recommendation": "buy", "number_of_analysts": 41,
            "target_price": 295.44, "current_price": 260.83,
            "analyst_flags": ["LIQUIDITY_RISK: Current ratio below 1.0 (0.974)"]
        },
        risk_assessment=(
            "OVERALL RISK LEVEL: MEDIUM\n"
            "TOP RISKS:\n- China revenue concentration\n"
            "- EU regulatory pressure\nRISK SCORE 5/10"
        ),
        output_dir="outputs"
    )
    print(f"✅ PDF generated: {path}")