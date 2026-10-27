import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_report(paper, questions, verifications_by_qid, co_bloom_by_qid, decisions_by_qid, validation, summary, duplication_pairs) -> str:
    filepath = OUTPUT_DIR / f"paper_{paper.id}_report.pdf"
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=18)
    heading = styles["Heading2"]
    normal = styles["Normal"]
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=7.5, leading=9.5, wordWrap="CJK")
    header_style = ParagraphStyle("Header", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.black, fontName="Helvetica-Bold")

    elements.append(Paragraph("Smart BOE — Question Paper Verification Report", title_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>Paper:</b> {paper.paper_name}", normal))
    elements.append(Paragraph(f"<b>Course:</b> {paper.course or '-'}", normal))
    elements.append(Paragraph(f"<b>Pattern:</b> {paper.pattern} marks ({paper.structure_type})", normal))
    elements.append(Paragraph(f"<b>Date:</b> {paper.uploaded_at.strftime('%d-%m-%Y') if paper.uploaded_at else '-'}", normal))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Summary", heading))
    summary_data = [
        ["Total Questions", str(len(questions))],
        ["Supported", str(summary["supported_count"])],
        ["Requires Review", str(summary["review_count"])],
        ["Potentially Unrelated", str(summary["unrelated_count"])],
        ["CO Aligned", str(summary["aligned_count"])],
        ["CO Potential Mismatch", str(summary["mismatch_count"])],
        ["Likely Duplicate Pairs", str(summary["likely_duplicate_count"])],
        ["Possible Duplicate Pairs", str(summary["possible_duplicate_count"])],
        ["Marks Valid", "Yes" if summary["marks_valid"] else "No"],
        ["Overall AI Recommendation", summary["overall_status"]],
    ]
    t = Table(summary_data, colWidths=[90 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    if summary["reasons"]:
        elements.append(Paragraph("Reasons for Review", heading))
        for r in summary["reasons"]:
            elements.append(Paragraph(f"- {r}", normal))
        elements.append(Spacer(1, 12))

    if validation:
        elements.append(Paragraph("Marks Validation", heading))
        elements.append(Paragraph(f"Expected: {validation.expected_total_marks} | Calculated: {validation.calculated_total_marks}", normal))
        if validation.issues_json:
            for issue in json.loads(validation.issues_json):
                elements.append(Paragraph(f"- {issue}", cell_style))
        elements.append(Spacer(1, 12))

    elements.append(PageBreak())
    elements.append(Paragraph("Question-wise Results", heading))
    elements.append(Spacer(1, 6))

    # Column widths sized to fit A4 portrait printable width (~180mm here)
    col_widths = [12 * mm, 70 * mm, 14 * mm, 28 * mm, 28 * mm, 28 * mm]

    table_data = [[
        Paragraph("No.", header_style),
        Paragraph("Question", header_style),
        Paragraph("Marks", header_style),
        Paragraph("AI Status", header_style),
        Paragraph("CO/Bloom", header_style),
        Paragraph("BOE Decision", header_style),
    ]]

    for q in questions:
        v = verifications_by_qid.get(q.id)
        cb = co_bloom_by_qid.get(q.id)
        d = decisions_by_qid.get(q.id)
        table_data.append([
            Paragraph(str(q.question_number), cell_style),
            Paragraph(q.question_text[:220], cell_style),
            Paragraph(str(q.marks or "-"), cell_style),
            Paragraph((v.ai_status if v else "-").replace("_", " "), cell_style),
            Paragraph(f"{cb.bloom_level}<br/>{cb.co_alignment.replace('_', ' ')}" if cb else "-", cell_style),
            Paragraph((d.decision if d else "PENDING"), cell_style),
        ])

    qtable = Table(table_data, colWidths=col_widths, repeatRows=1)
    qtable.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(qtable)

    if duplication_pairs:
        elements.append(PageBreak())
        elements.append(Paragraph("Duplicate Question Pairs", heading))
        qnum_by_id = {q.id: q.question_number for q in questions}
        dup_data = [[
            Paragraph("Q A", header_style),
            Paragraph("Q B", header_style),
            Paragraph("Similarity", header_style),
            Paragraph("Status", header_style),
        ]]
        for d in duplication_pairs:
            dup_data.append([
                Paragraph(str(qnum_by_id.get(d.question_id_a, "-")), cell_style),
                Paragraph(str(qnum_by_id.get(d.question_id_b, "-")), cell_style),
                Paragraph(f"{d.similarity:.2f}", cell_style),
                Paragraph(d.status.replace("_", " "), cell_style),
            ])
        dtable = Table(dup_data, colWidths=[30 * mm, 30 * mm, 30 * mm, 70 * mm])
        dtable.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(dtable)

    doc.build(elements)
    return str(filepath)