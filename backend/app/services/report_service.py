"""PDF report generation (ReportLab)."""

from __future__ import annotations

import io
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(title: str, sections: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>{title}</b>", styles["Title"]), Spacer(1, 0.25 * inch)]

    for heading, body in sections.items():
        story.append(Paragraph(f"<b>{heading}</b>", styles["Heading2"]))
        if isinstance(body, (list, tuple)):
            for line in body:
                story.append(Paragraph(str(line), styles["BodyText"]))
        elif isinstance(body, dict):
            data = [[str(k), str(v)] for k, v in body.items()]
            t = Table(data, colWidths=[2.2 * inch, 3.5 * inch])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ]
                )
            )
            story.append(t)
        else:
            story.append(Paragraph(str(body), styles["BodyText"]))
        story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    return buf.getvalue()
