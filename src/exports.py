from io import BytesIO
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def dataframe_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

def excel_bytes(dataframes):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in dataframes.items():
            df.to_excel(writer, index=False, sheet_name=name[:31] or "Sheet")
    return bio.getvalue()

def trip_pdf(trip, itinerary, expenses, packing, documents):
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Travel Planner — Trip Summary", styles["Title"]))
    story.append(Paragraph(
        f"<b>{trip['name']}</b> · {trip['destination']}<br/>"
        f"{trip['start_date']} → {trip['end_date']} · {trip['travelers']} traveler(s)<br/>"
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["BodyText"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Itinerary", styles["Heading2"]))
    rows = [["Date","Time","Activity","Category","Cost"]]
    for _, r in itinerary.iterrows():
        rows.append([str(r["day_date"]), f"{r['start_time']}–{r['end_time']}", str(r["title"]), str(r["category"]), f"{r['cost']:,.2f}"])
    if len(rows) == 1:
        rows.append(["—","—","No itinerary items","—","—"])
    t = Table(rows, repeatRows=1, colWidths=[65,75,180,80,65])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172033")),
                           ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                           ("GRID",(0,0),(-1,-1),0.3,colors.grey),
                           ("FONTSIZE",(0,0),(-1,-1),8),
                           ("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(t)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Expenses", styles["Heading2"]))
    total = float(expenses["amount"].sum()) if not expenses.empty else 0
    story.append(Paragraph(f"Recorded expenses: {trip['currency']} {total:,.2f}", styles["BodyText"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Packing Checklist", styles["Heading2"]))
    packed = int(packing["packed"].sum()) if not packing.empty else 0
    count = len(packing)
    story.append(Paragraph(f"{packed} of {count} items packed.", styles["BodyText"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Documents", styles["Heading2"]))
    ready = int((documents["status"] == "Ready").sum()) if not documents.empty else 0
    story.append(Paragraph(f"{ready} of {len(documents)} documents ready.", styles["BodyText"]))
    doc.build(story)
    return bio.getvalue()
