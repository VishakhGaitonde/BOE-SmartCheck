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
    doc = SimpleDocTemplate(str(filepath), pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=18)
    heading = styles["Heading2"]
    normal = styles["Normal"]
    small = ParagraphStyle("S", parent=styles["Normal"], fontSize=8, leading=10)

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
    t = Table(summary_data, colWidths=[220, 220])
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
                elements.append(Paragraph(f"- {issue}", small))
        elements.append(Spacer(1, 12))

    elements.append(PageBreak())
    elements.append(Paragraph("Question-wise Results", heading))

    table_data = [["No.", "Question", "Marks", "AI Status", "CO/Bloom", "BOE Decision"]]
    for q in questions:
        v = verifications_by_qid.get(q.id)
        cb = co_bloom_by_qid.get(q.id)
        d = decisions_by_qid.get(q.id)
        table_data.append([
            q.question_number,
            Paragraph(q.question_text[:150], small),
            str(q.marks or "-"),
            v.ai_status if v else "-",
            f"{cb.bloom_level}/{cb.co_alignment}" if cb else "-",
            d.decision if d else "PENDING",
        ])

    qtable = Table(table_data, colWidths=[30, 220, 35, 75, 75, 65], repeatRows=1)
    qtable.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(qtable)

    if duplication_pairs:
        elements.append(PageBreak())
        elements.append(Paragraph("Duplicate Question Pairs", heading))
        qnum_by_id = {q.id: q.question_number for q in questions}
        dup_data = [["Q A", "Q B", "Similarity", "Status"]]
        for d in duplication_pairs:
            dup_data.append([qnum_by_id.get(d.question_id_a, "-"), qnum_by_id.get(d.question_id_b, "-"), f"{d.similarity:.2f}", d.status])
        dtable = Table(dup_data, colWidths=[80, 80, 80, 150])
        dtable.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        elements.append(dtable)

    doc.build(elements)
    return str(filepath)