"""Portable PDF assessment exports with identity, source and interpretation preserved."""
from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def assessment_pdf(listing: dict, result: dict, quoted: float, listed: float) -> bytes:
    """Build a printable report without persisting private quotes on the server."""
    output = BytesIO()
    styles = getSampleStyleSheet()
    items = [Paragraph("Price Truth - historical price assessment", styles["Title"]),
             Paragraph(escape(str(listing["name"])), styles["BodyText"]), Spacer(1, 12)]
    rows = [
        ["Field", "Value"], ["Listing identity", listing["key"]],
        ["Platform", listing["platform"]], ["Observation date", str(listing.get("observed_at") or "Unknown")],
        ["User reference / selling quote (INR)", f"{listed:.2f} / {quoted:.2f}"],
        ["Advertised discount", f"{result['claimed_discount_pct']:.2f}%"],
        ["Historical model estimate (INR)", f"{result['estimate']:.2f}"],
        ["Calibrated model range (INR)", f"{result['lower']:.2f} - {result['upper']:.2f}"],
        ["Assessment", result["status"].replace("_", " ")],
        ["Subcategory fitting support", str(result["support"])],
        ["Listing seen during model fitting", str(result["seen_in_training"])],
    ]
    cells = [[Paragraph(escape(str(v)), styles["BodyText"]) for v in row] for row in rows]
    table = Table(cells, colWidths=[230, 270])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                              ("GRID", (0, 0), (-1, -1), .3, colors.lightgrey),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    items.extend([table, Spacer(1, 15), Paragraph(
        "This is historical price regression, not a fraud verdict or current fair-price guarantee. "
        "The interval targets 90% coverage on comparable data; it is not a genuineness probability. "
        "Listed reference price influences the estimate. SHAP explains model computation, not causation.", styles["BodyText"])])
    items.append(Paragraph("Generated " + datetime.now(UTC).isoformat(), styles["BodyText"]))
    SimpleDocTemplate(output, leftMargin=48, rightMargin=48).build(items)
    return output.getvalue()
