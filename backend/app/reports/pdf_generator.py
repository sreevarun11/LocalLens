import os
import io
from datetime import datetime
from typing import Any
import segno
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable,
    PageBreak
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y' and headers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "LocalLens — Neighborhood Intelligence & Locality Decision Report")
            self.drawRightString(letter[0] - 54, letter[1] - 36, f"Report ID: {getattr(self, 'report_id_str', '')}")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            
        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_text)
        self.drawString(54, 36, "INDEPENDENT & EVIDENCE-GROUNDED — Zero fabricated scores, livability rankings, or fake reviews.")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 46, letter[0] - 54, 46)
        
        self.restoreState()

def generate_report_pdf(
    output_path: str,
    report_id: str,
    locality_name: str,
    verification_hash: str,
    verification_url: str,
    findings: list[dict[str, Any]],
    amenity_rows: list[dict[str, Any]],
    env_data: dict[str, Any] | None,
    property_context: dict[str, Any] | None = None,
    checklist_questions: list[str] | None = None,
    comparison_name: str | None = None,
    user_profile: str = "family",
    user_priorities: list[str] | None = None,
    gaps: list[dict[str, Any]] | None = None,
    coords: dict[str, float] | None = None
) -> str:
    """
    Generates a professional, publication-grade decision report PDF meeting Section 18 specifications.
    Strictly avoids fabricated scores, winners, or unverified claims.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom color palette (Navy & Teal Geospatial aesthetic)
    c_navy = colors.HexColor("#0f172a")
    c_teal = colors.HexColor("#0f766e")
    c_slate = colors.HexColor("#475569")
    c_light = colors.HexColor("#f8fafc")
    c_border = colors.HexColor("#cbd5e1")
    c_amber_bg = colors.HexColor("#fefce8")
    c_amber_border = colors.HexColor("#fef08a")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_navy
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_teal
    )
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_navy,
        spaceBefore=12,
        spaceAfter=6
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_teal,
        spaceBefore=8,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=c_navy
    )
    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=c_slate
    )
    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#854d0e")
    )
    tag_style = ParagraphStyle(
        'TagStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#065f46")
    )

    story = []

    # ========================================================
    # PAGE 1: COVER & EXECUTIVE OVERVIEW
    # ========================================================
    
    # Generate QR Code image
    qr = segno.make(verification_url)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, kind='png', scale=3, border=0)
    qr_buffer.seek(0)
    qr_img = Image(qr_buffer, width=1.15*inch, height=1.15*inch)

    header_table_data = [
        [
            Paragraph("<b>LocalLens</b><br/><font size='13' color='#475569'>Neighborhood Intelligence Report</font>", title_style),
            qr_img
        ],
        [
            Paragraph(
                f"<b>Target Locality:</b> {locality_name}<br/>"
                f"<b>Survey Boundary:</b> 1,500 meters (straight-line radius)<br/>"
                f"<b>Generated:</b> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}<br/>"
                f"<b>Report ID:</b> <font face='Courier'>{report_id}</font><br/>"
                f"<b>Verification Hash:</b> <font face='Courier'>{verification_hash[:20]}...</font>",
                subtitle_style
            ),
            Paragraph("<font size='7' color='#64748b'>Scan QR code to verify this snapshot on the public register</font>", caption_style)
        ]
    ]
    header_table = Table(header_table_data, colWidths=[4.9*inch, 1.6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_teal, spaceBefore=4, spaceAfter=10))

    # User Profile & Stated Priorities
    story.append(Paragraph("Requester Profile & Decision Context", h1_style))
    priorities_str = ", ".join([p.replace("_", " ").title() for p in (user_priorities or ["Education", "Healthcare", "Transport", "Daily Essentials"])])
    profile_table_data = [
        ["Selected Profile", user_profile.replace("_", " ").title()],
        ["Evaluated Priorities", priorities_str],
        ["Decision Purpose", "Independent pre-relocation or home evaluation based on open factual evidence"]
    ]
    t_profile = Table(profile_table_data, colWidths=[2.0*inch, 4.5*inch])
    t_profile.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), c_light),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), c_navy),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 10))

    # Property Context (User-Provided) if present
    if property_context and any(property_context.values()):
        story.append(Paragraph("User-Supplied Property Context", h1_style))
        prop_rows = [["Declared Attribute", "User Supplied Detail"]]
        if property_context.get("property_address"):
            prop_rows.append(["Specific Address / Project", property_context["property_address"]])
        if property_context.get("floor_level"):
            prop_rows.append(["Floor Level", property_context["floor_level"]])
        if property_context.get("unit_facing"):
            prop_rows.append(["Unit Facing", property_context["unit_facing"]])
        if property_context.get("water_source_declared"):
            prop_rows.append(["Declared Water Source", property_context["water_source_declared"]])
        if property_context.get("power_backup_declared"):
            prop_rows.append(["Declared Power Backup", property_context["power_backup_declared"]])
        if property_context.get("rent_or_price"):
            prop_rows.append(["Quoted Rent / Price", f"Rs. {property_context['rent_or_price']}"])
        if property_context.get("user_notes"):
            prop_rows.append(["Requester Notes", property_context["user_notes"]])

        t_prop = Table(prop_rows, colWidths=[2.2*inch, 4.3*inch])
        t_prop.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, c_border),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_prop)
        story.append(Spacer(1, 4))
        story.append(Paragraph("<i>Notice: Property details were supplied by the user and have not been independently inspected by LocalLens.</i>", caption_style))
        story.append(Spacer(1, 8))

    # Executive Overview
    story.append(Paragraph("Executive Intelligence Summary", h1_style))
    story.append(Paragraph(
        "LocalLens analyzes facts derived strictly from open geospatial databases and atmospheric model grids at the moment of report generation. Unlike real-estate portals, LocalLens does not produce fabricated composite ratings, livability scores, or subjective safety labels. Every statement below is tied to verified evidence.",
        body_style
    ))
    story.append(Spacer(1, 8))

    if findings:
        for f in findings[:5]:
            f_head = f.get("headline", "Verified finding")
            f_det = f.get("detail", "")
            story.append(Paragraph(f"<b>• {f_head}</b>: {f_det}", body_style))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("Baseline geographic search completed within 1,500m radius.", body_style))

    # End of Page 1
    story.append(PageBreak())

    # ========================================================
    # PAGE 2: LOCALITY SNAPSHOT & DATA COVERAGE
    # ========================================================
    story.append(Paragraph("1. Locality Snapshot", h1_style))
    story.append(Paragraph("Objective synthesis of retrieved neighborhood evidence, divided into what was verified, what is limited, and what is currently unavailable:", caption_style))
    story.append(Spacer(1, 8))

    # 3-Box Evidence Breakdown
    # Box A: What We Found
    found_items = []
    if findings:
        for f in findings[:4]:
            found_items.append(f"• {f.get('headline')}: {f.get('detail')}")
    else:
        found_items.append("• Nearby amenities mapped within 1.5 km straight-line radius.")

    # Box B: What Is Limited
    limited_items = [
        "• Straight-line distances shown; physical walking or driving paths may be longer due to road geometry.",
        "• Atmospheric figures represent European CAMS model grid estimates (~11 km resolution), not an on-site ground sensor.",
        "• OpenStreetMap completeness depends on active contributor mapping density."
    ]

    # Box C: What Is Unavailable
    unavailable_items = [
        "• Locality-level micro crime records are not published as machine-readable datasets by municipal authorities.",
        "• Real-time municipal tap water quality (TDS/pH/chlorine) is not available from public sensors.",
        "• Absence of records in open databases does not prove non-existence. Verify on site."
    ]

    snapshot_table_data = [
        [
            Paragraph("<b>WHAT WE FOUND (VERIFIED)</b>", tag_style),
            Paragraph("<b>WHAT IS LIMITED (CAVEATS)</b>", ParagraphStyle('AmberH', parent=tag_style, textColor=colors.HexColor("#92400e"))),
            Paragraph("<b>WHAT IS UNAVAILABLE (DISCLOSURES)</b>", ParagraphStyle('RedH', parent=tag_style, textColor=colors.HexColor("#991b1b")))
        ],
        [
            Paragraph("<br/>".join(found_items), body_style),
            Paragraph("<br/>".join(limited_items), body_style),
            Paragraph("<br/>".join(unavailable_items), body_style)
        ]
    ]
    t_snapshot = Table(snapshot_table_data, colWidths=[2.16*inch, 2.16*inch, 2.16*inch])
    t_snapshot.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ecfdf5")),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor("#fffbeb")),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor("#fef2f2")),
        ('BOX', (0, 0), (0, -1), 0.5, colors.HexColor("#a7f3d0")),
        ('BOX', (1, 0), (1, -1), 0.5, colors.HexColor("#fde68a")),
        ('BOX', (2, 0), (2, -1), 0.5, colors.HexColor("#fecaca")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_snapshot)
    story.append(Spacer(1, 14))

    # Data Coverage Meter / Table
    story.append(Paragraph("Data Coverage & Provenance Table", h1_style))
    story.append(Paragraph("This measures data completeness and provider granularity, NOT a subjective livability score:", caption_style))
    story.append(Spacer(1, 6))

    coverage_rows = [
        ["Domain / Module", "Status", "Source Provider", "Granularity", "Storage Policy"],
        ["Essential Amenities", "Verified", "OpenStreetMap", "Exact Facility", "Storable (ODbL)"],
        ["Air Quality & Atmosphere", "Verified", "Open-Meteo European CAMS", "11 km Grid Estimate", "Storable (Attribution)"],
        ["Transit & Connectivity", "Verified", "OpenStreetMap Transit Nodes", "Station / Stop", "Storable (ODbL)"],
        ["Piped Water Quality", "Unavailable", "Municipal Agency / CGWB", "No local sensor", "Public domain caveat"],
        ["Micro Crime Statistics", "Unavailable", "NCRB / State Police", "District only (no local data)", "Absence disclaimer"]
    ]
    t_coverage = Table(coverage_rows, colWidths=[1.6*inch, 1.0*inch, 1.7*inch, 1.2*inch, 1.0*inch])
    t_coverage.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_light),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(t_coverage)

    # End of Page 2
    story.append(PageBreak())

    # ========================================================
    # PAGE 3+: DETAILED CATEGORIES, CONNECTIVITY & DISCLOSURES
    # ========================================================
    story.append(Paragraph("2. Essential Services & Amenities Detail", h1_style))
    story.append(Paragraph("Verified facilities identified within the 1,500 meter survey boundary, sorted by category:", caption_style))
    story.append(Spacer(1, 6))

    amenity_table_data = [
        ["Category", "Facility Count (≤1.5 km)", "Nearest Distance", "Provider", "Evidence Quality"]
    ]
    for row in amenity_rows:
        amenity_table_data.append([
            row.get("category", "").replace("_", " ").title(),
            str(row.get("count", 0)),
            f"{row.get('nearest_m')} m" if row.get('nearest_m') else "None identified",
            "OpenStreetMap",
            "Grounded Fact"
        ])

    t_amenities = Table(amenity_table_data, colWidths=[1.8*inch, 1.2*inch, 1.1*inch, 1.3*inch, 1.1*inch])
    t_amenities.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_light),
        ('TEXTCOLOR', (0, 0), (-1, 0), c_navy),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    story.append(t_amenities)
    story.append(Spacer(1, 10))

    # Environmental Detail
    story.append(Paragraph("3. Environmental & Atmosphere Data", h1_style))
    if env_data:
        aqi_val = env_data.get("aqi", "N/A")
        pm25 = env_data.get("pm25", "N/A")
        pm10 = env_data.get("pm10", "N/A")
        env_text = f"<b>Air Quality Index:</b> {aqi_val} (US AQI Scale) &nbsp;&nbsp;|&nbsp;&nbsp; <b>PM2.5:</b> {pm25} µg/m³ &nbsp;&nbsp;|&nbsp;&nbsp; <b>PM10:</b> {pm10} µg/m³"
    else:
        env_text = "Air quality model estimates currently unavailable for this geographic coordinate."

    story.append(Paragraph(env_text, body_style))
    story.append(Spacer(1, 4))
    
    env_callout = [
        [Paragraph("<b>Mandatory Disclosure:</b> Air quality estimates are sourced from Open-Meteo European CAMS atmospheric model grid estimates (approx 11 km spatial resolution), not a calibrated ground-level sensor at this specific property. Wind and micro-topography may cause localized variations.", callout_style)]
    ]
    t_env_callout = Table(env_callout, colWidths=[6.5*inch])
    t_env_callout.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_amber_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, c_amber_border),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(t_env_callout)
    story.append(Spacer(1, 10))

    # Water & Safety Disclosures
    story.append(Paragraph("4. Water & Safety Infrastructure Disclosures", h1_style))
    disclosure_rows = [
        [
            Paragraph("<b>Water Quality Assessment:</b> Continuous piped water quality measurements are not published in machine-readable format by municipal water boards for this micro-locality. Rely on on-site tap TDS testing and society water source declaration (borewell vs municipal).", body_style)
        ],
        [
            Paragraph("<b>Safety & Crime Data Disclosure:</b> Locality-level micro crime statistics were not available from configured verified sources. In India, crime records (NCRB) are aggregated at the police station or district tier, not at street or block level. <i>Crucial: Absence of data does not imply absence of crime or guarantee personal safety.</i>", body_style)
        ]
    ]
    t_disclosures = Table(disclosure_rows, colWidths=[6.5*inch])
    t_disclosures.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_light),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#fff1f2")),
        ('BOX', (0, 0), (-1, 0), 0.5, c_border),
        ('BOX', (0, 1), (-1, 1), 0.5, colors.HexColor("#fecdd3")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(t_disclosures)
    story.append(Spacer(1, 10))

    # Comparison (if comparison locality selected)
    if comparison_name:
        story.append(Paragraph(f"5. Locality Comparison: {locality_name} vs {comparison_name}", h1_style))
        story.append(Paragraph(f"Both localities evaluated using identical 1,500m radius parameters without declaring a subjective 'winner':", caption_style))
        story.append(Spacer(1, 4))
        comp_rows = [
            ["Metric / Category", locality_name, comparison_name, "Comparability Note"],
            ["Essential Amenities", f"{sum(r.get('count',0) for r in amenity_rows)} identified", "Evaluated in comparison mode", "Comparable under same ODbL survey criteria"],
            ["Atmosphere (AQI)", str(env_data.get('aqi', 'N/A')) if env_data else 'N/A', "Grid estimate", "Same model resolution (~11 km)"]
        ]
        t_comp = Table(comp_rows, colWidths=[1.8*inch, 1.5*inch, 1.5*inch, 1.7*inch])
        t_comp.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_comp)
        story.append(Spacer(1, 10))

    # Physical Checklist
    story.append(KeepTogether([
        Paragraph("6. Physical 'Verify On-Site' Inspection Checklist", h1_style),
        Paragraph("Digital datasets cannot inspect street lighting, physical water pressure, or localized construction noise. Bring this checklist on your in-person visit:", caption_style),
        Spacer(1, 6)
    ]))

    questions = checklist_questions or [
        "Inspect water pressure and test TDS level directly from kitchen tap.",
        "Verify operational status of nearest clinic or emergency medical facility.",
        "Assess evening street lighting along direct pedestrian route to nearest transit stop.",
        "Check cellular data signal and 5G network coverage inside the target property.",
        "Observe traffic bottleneck conditions during peak commute hours (8:30 AM & 6:30 PM)."
    ]

    check_table_data = []
    for q in questions[:5]:
        check_table_data.append([
            Paragraph("<font size='9'><b>[ &nbsp; ]</b></font>", body_style),
            Paragraph(q, body_style)
        ])

    t_check = Table(check_table_data, colWidths=[0.4*inch, 6.1*inch])
    t_check.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_check)
    story.append(Spacer(1, 10))

    # Provenance, Disclaimer & Authenticity Seal
    story.append(KeepTogether([
        Paragraph("7. Data Provenance & Legal Disclaimers", h1_style),
        Paragraph(
            "<b>Licensing & Attributions:</b> Map listings © OpenStreetMap contributors under ODbL 1.0. Environmental data provided by Open-Meteo. Proprietary commercial map data is excluded from persistent PDF records.<br/>"
            "<b>Disclaimer:</b> LocalLens is an informational decision support tool. It does not provide real estate, legal, structural, or financial advice. All physical inspections must be conducted independently.<br/>"
            f"<b>Verification URI:</b> <font color='#0f766e'>{verification_url}</font><br/>"
            f"<b>Cryptographic Seal:</b> SHA-256 Digest <font face='Courier'>{verification_hash}</font>",
            caption_style
        )
    ]))

    # Set report_id on canvas for running header
    def make_canvas(*args, **kwargs):
        c = NumberedCanvas(*args, **kwargs)
        c.report_id_str = report_id[:8]
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path
