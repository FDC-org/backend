import io
import os
import base64
import datetime
import subprocess
import tempfile
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas as rl_canvas

# ==================== UTILITIES ====================

class BarcodeFlowable(Flowable):
    """Pure ReportLab barcode - works on Windows & Linux without external tools."""
    def __init__(self, value, total_width=190*mm, bar_height=14*mm):
        Flowable.__init__(self)
        self.value = str(value)
        self.width = total_width
        self.height = bar_height

    def draw(self):
        # Using Code128 which is standard forAWB/Manifests
        barcode = code128.Code128(
            self.value,
            barWidth=1.1,
            barHeight=self.height,
            humanReadable=False
        )
        # Center the barcode in the allocated width
        x_offset = (self.width - barcode.width) / 2
        barcode.drawOn(self.canv, x_offset, 0)


class RotatedText(Flowable):
    """Rotates a paragraph of text by 90 degrees."""
    def __init__(self, text, style):
        Flowable.__init__(self)
        self.text = text
        self.style = style
        self.p = Paragraph(self.text, self.style)
        self.p.wrap(72*mm, 10*mm)
        self.width = self.p.height
        self.height = self.p.width

    def draw(self):
        self.canv.saveState()
        self.canv.translate(self.width, 0)
        self.canv.rotate(90)
        self.p.drawOn(self.canv, 0, 0)
        self.canv.restoreState()


def generate_error_pdf(error_message):
    """
    Generate a simple PDF containing only the error message
    Used when proper generation fails so the user gets a readable file
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        elements = []
        elements.append(Paragraph("PDF Generation Error", styles['Heading1']))
        elements.append(Spacer(1, 10))
        
        # Sanitize error message to prevent ReportLab markup errors
        safe_message = str(error_message).replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe_message, styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.read()
    except:
        return None


def generate_drs_pdf(drs_data):
    """
    Generate DRS PDF using ReportLab
    
    Args:
        drs_data: Dictionary containing DRS information
    
    Returns:
        PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           topMargin=10*mm, bottomMargin=10*mm,
                           leftMargin=10*mm, rightMargin=10*mm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#2e7d32'),
        alignment=TA_LEFT,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_LEFT,
        spaceAfter=4
    )

    drs_label_style = ParagraphStyle(
        'DRSLabel',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=0,
        spaceBefore=2,
    )
    
    # Left cell: brand + tagline + branch info
    brand_block = [
        Paragraph('<b><font color="#2e7d32">FDC Couriers and Cargo</font></b>', title_style),
        Paragraph('Fast, Reliable, Trusted Delivery Services', subtitle_style),
        Paragraph(
            f'<b>{drs_data["branch_name"]}</b><br/>{drs_data["branch_address"]}',
            styles['Normal']
        ),
    ]

    # Right cell: barcode + DRS number, both centered
    drs_barcode_img = BarcodeFlowable(drs_data['drs_number'], total_width=72*mm, bar_height=14*mm)
    drs_num_para = Paragraph(
        f'<b>{drs_data["drs_number"]}</b>',
        drs_label_style
    )

    barcode_inner = Table(
        [[drs_barcode_img], [drs_num_para]],
        colWidths=[80*mm]
    )
    barcode_inner.setStyle(TableStyle([
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Single-row header: brand (left) | barcode+number (right, centered)
    header_table = Table([[brand_block, barcode_inner]], colWidths=[105*mm, 85*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (1, 0), (1,  0), 'CENTER'),
        ('LEFTPADDING',  (0, 0), (0, 0), 4*mm),
        ('RIGHTPADDING', (1, 0), (1, 0), 4*mm),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2e7d32')),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))
    
    # DRS Details Bar
    details_data = [[
        Paragraph(f'<b>Date:</b> {drs_data["date"]}', styles['Normal']),
        Paragraph(f'<b>Area:</b> {drs_data["area"]}', styles['Normal']),
        Paragraph(f'<b>Delivery Boy:</b> {drs_data["delivery_boy"]}', styles['Normal'])
    ]]
    
    details_table = Table(details_data, colWidths=[63*mm, 63*mm, 64*mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 5*mm))
    
    # AWB Table
    awb_table_data = [['#', 'Center', 'Doc No', 'Party Name', 'Pcs', 'Wt', 'Signature']]
    
    for idx, item in enumerate(drs_data.get('awb_items', []), 1):
        # Center column with STD and remarks
        center_text = f"{item['center']}<br/><font size=8>STD: {item['doc_type']}</font>"
        # Add Time
        if item.get('time'):
             center_text += f"<br/><font size=8>Time: {item['time']}</font>"
        
        if item.get('remarks'):
            center_text += f"<br/><font size=8><i>Remarks: {item['remarks']}</i></font>"
        center_cell = Paragraph(center_text, styles['Normal'])
        
        
        # Doc No with barcode
        awb_barcode_img = BarcodeFlowable(item['awb_number'], total_width=40*mm, bar_height=10*mm)
        doc_cell = [Paragraph(item['awb_number'], styles['Normal']), awb_barcode_img]
        
        # Party details
        party_text = f"<b>{item['party_name']}</b><br/><font size=8>{item['party_phone']}</font>"
        party_cell = Paragraph(party_text, styles['Normal'])

        pcs_cell = Paragraph(str(item.get('pieces', '')), styles['Normal'])
        wt_cell  = Paragraph(str(item.get('weight', '')), styles['Normal'])
        
        awb_table_data.append([
            str(idx),
            center_cell,
            doc_cell,
            party_cell,
            pcs_cell,
            wt_cell,
            ''
        ])

    awb_table = Table(awb_table_data, colWidths=[8*mm, 32*mm, 48*mm, 38*mm, 12*mm, 14*mm, 38*mm])
    awb_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        
        # All cells
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(awb_table)
    elements.append(Spacer(1, 10*mm))
    
    # Signature Section
    sig_data = [[
        Paragraph('<br/><br/><br/>_____________________<br/>Delivery Boy Signature', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER)),
        Paragraph('<br/><br/><br/>_____________________<br/>Branch Manager Signature', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER)),
        Paragraph('<br/><br/><br/>_____________________<br/>Date & Stamp', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER))
    ]]
    
    sig_table = Table(sig_data, colWidths=[63*mm, 63*mm, 64*mm])
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def get_drs_data(drs_number):
    """
    Gather all necessary data for DRS PDF generation
    
    Args:
        drs_number: DRS Number
        
    Returns:
        drs_data dictionary or None if DRS not found
    """
    try:
        from ..models import DRS, BranchDetails, BookingDetails, DrsDetails, DeliveryBoyDetalis, Locations, UserDetails
        import datetime
        
        drs = DRS.objects.filter(drsno=drs_number).first()
        if not drs:
            return None
            
        # Get delivery boy name
        try:
            delivery_boy_name = DeliveryBoyDetalis.objects.get(boy_code=drs.boycode).name
        except:
            delivery_boy_name = drs.boycode
            
        # Get location name
        try:
            location_name = Locations.objects.get(location_code=drs.location).location
        except:
            location_name = drs.location
            
        # Get branch details
        branch_code = drs.code
        branch_name = ""
        branch_address = ""
        
        if BranchDetails.objects.filter(branch_code=branch_code).exists():
            branch_details = BranchDetails.objects.get(branch_code=branch_code)
            branch_name = branch_details.branchname
            branch_address = f"{branch_details.address}, {branch_details.location}"
        else:
            # Try to get from UserDetails if BranchDetails not found
            try:
                user_details = UserDetails.objects.filter(code=branch_code).first()
                if user_details:
                    branch_name = user_details.code_name
            except:
                pass

        # Get AWB items
        awb_items = []
        drs_details = DrsDetails.objects.filter(drsno=drs_number)
        
        for item in drs_details:
            awb = item.awbno
            booking = BookingDetails.objects.filter(awbno=awb).first()
            
            if booking:
                booking_time = booking.date.strftime('%I:%M %p') if booking.date else ''
                awb_items.append({
                    'center': booking.destination_code or branch_name,
                    'doc_type': booking.doc_type or 'NON-DOX',
                    'awb_number': awb,
                    'party_name': booking.recievername or '',
                    'party_phone': booking.recieverphonenumber or '',
                    'time': booking_time,
                    'pieces': booking.pcs or 0,
                    'weight': float(booking.wt) if booking.wt else 0.0,
                    'remarks': booking.contents or ''
                })
            else:
                awb_items.append({
                    'center': branch_name,
                    'doc_type': 'NON-DOX',
                    'awb_number': awb,
                    'party_name': '',
                    'party_phone': '',
                    'time': '',
                    'pieces': 0,
                    'weight': 0.0,
                    'remarks': ''
                })
        
        return {
            'drs_number': drs.drsno,
            'branch_name': branch_name,
            'branch_address': branch_address,
            'date': drs.date.strftime('%d/%m/%Y %H:%M:%S') if drs.date else "",
            'area': location_name,
            'delivery_boy': delivery_boy_name,
            'awb_items': awb_items
        }
    except Exception as e:
        print(f"Error gathering DRS data: {e}")
        return None


# ==================== MANIFEST PDF GENERATION ====================

def generate_manifest_pdf(manifest_data):
    """
    Generate Manifest PDF using ReportLab
    
    Args:
        manifest_data: Dictionary containing Manifest information
            {
                'manifest_number': str,
                'date': str,
                'origin': str,
                'origin_address': str,
                'destination': str,
                'destination_address': str,
                'vehicle_number': str (optional),
                'awb_list': [str, str, ...]  # List of AWB numbers
            }
    
    Returns:
        PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           topMargin=10*mm, bottomMargin=10*mm,
                           leftMargin=10*mm, rightMargin=10*mm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2e7d32'),
        alignment=TA_LEFT,
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=10
    )

    barcode_label_style = ParagraphStyle(
        'BarcodeLabel',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=0,
        spaceBefore=2,
    )

    # Left cell: brand name + tagline + origin
    brand_block = [
        Paragraph('<b><font color="#2e7d32">FDC Couriers and Cargo</font></b>', title_style),
        Paragraph('Fast, Reliable, Trusted Delivery Services', subtitle_style),
        Paragraph(
            f'<b>Origin:</b> {manifest_data["origin"]}<br/>{manifest_data.get("origin_address", "")}',
            styles['Normal']
        ),
    ]

    # Right cell: barcode + number, both centered
    manifest_barcode_img = BarcodeFlowable(
        manifest_data['manifest_number'], total_width=75*mm, bar_height=14*mm
    )
    manifest_num_para = Paragraph(
        f'<b>{manifest_data["manifest_number"]}</b>',
        barcode_label_style
    )

    barcode_inner = Table(
        [[manifest_barcode_img], [manifest_num_para]],
        colWidths=[80*mm]
    )
    barcode_inner.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Single-row header: brand (left) | barcode+number (right, centered)
    header_table = Table([[brand_block, barcode_inner]], colWidths=[105*mm, 85*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 4*mm),
        ('RIGHTPADDING', (1, 0), (1, 0), 4*mm),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2e7d32')),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))
    
    # Manifest Details Bar
    vehicle_text = manifest_data.get('vehicle_number', 'N/A')
    details_data = [[
        Paragraph(f'<b>Date:</b> {manifest_data["date"]}', styles['Normal']),
        Paragraph(f'<b>Destination:</b> {manifest_data["destination"]}', styles['Normal']),
        Paragraph(f'<b>Vehicle:</b> {vehicle_text}', styles['Normal'])
    ]]
    
    details_table = Table(details_data, colWidths=[63*mm, 63*mm, 64*mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 5*mm))
    
    
    # AWB Table with Sender, Receiver, Destination, Pieces and Weight
    awb_table_data = [['#', 'AWB No', 'Sender', 'Receiver', 'Dest', 'Pcs', 'Wt']]
    
    for idx, awb_item in enumerate(manifest_data.get('awb_list', []), 1):
        awb_number = awb_item['awb_number']
        pcs = awb_item.get('pcs', 0)
        wt = awb_item.get('wt', 0.0)
        sender = awb_item.get('sender', '')
        receiver = awb_item.get('receiver', '')
        destination = awb_item.get('destination', '')
        
        # Truncate if too long
        if len(sender) > 15:
            sender = sender[:13] + '..'
        if len(receiver) > 15:
            receiver = receiver[:13] + '..'
            
        awb_table_data.append([
            str(idx),
            Paragraph(awb_number, styles['Normal']),
            Paragraph(sender, styles['Normal']),
            Paragraph(receiver, styles['Normal']),
            Paragraph(destination, styles['Normal']),
            str(pcs),
            f"{wt:.2f}"
        ])
    
    # Adjusted column widths for new layout
    awb_table = Table(awb_table_data, colWidths=[10*mm, 35*mm, 45*mm, 45*mm, 20*mm, 15*mm, 20*mm])
    awb_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9), # Slightly smaller font for header
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (4, 0), (5, -1), 'CENTER'),  # Center align Pcs and Wt columns
        
        # All cells
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(awb_table)
    elements.append(Spacer(1, 5*mm))
    
    # Summary with Totals
    total_awbs = len(manifest_data.get('awb_list', []))
    total_pcs = manifest_data.get('total_pcs', 0)
    total_wt = manifest_data.get('total_wt', 0.0)
    
    summary_data = [[
        Paragraph(f'<b>Total AWBs:</b> {total_awbs}', styles['Normal']),
        Paragraph(f'<b>Total Pieces:</b> {total_pcs}', styles['Normal']),
        Paragraph(f'<b>Total Weight:</b> {total_wt:.2f} kg', styles['Normal'])
    ]]
    summary_table = Table(summary_data, colWidths=[63*mm, 63*mm, 64*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10*mm))
    
    # Signature Section
    sig_data = [[
        Paragraph('<br/><br/><br/>_____________________<br/>Prepared By', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER)),
        Paragraph('<br/><br/><br/>_____________________<br/>Verified By', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER)),
        Paragraph('<br/><br/><br/>_____________________<br/>Date & Stamp', 
                 ParagraphStyle('Sig', parent=styles['Normal'], alignment=TA_CENTER))
    ]]
    
    sig_table = Table(sig_data, colWidths=[63*mm, 63*mm, 64*mm])
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def get_manifest_data(manifest_number):
    """
    Gather all necessary data for Manifest PDF generation
    
    Args:
        manifest_number: Manifest Number
        
    Returns:
        manifest_data dictionary or None if Manifest not found
    """
    try:
        from ..models import ManifestDetails, OutscanModel, BranchDetails, HubDetails, UserDetails
        
        manifest = ManifestDetails.objects.filter(manifestnumber=manifest_number).first()
        if not manifest:
            return None
        
        # Get origin details
        origin_code = manifest.inscaned_branch_code
        origin_name = origin_code
        origin_address = ""
        
        # Try BranchDetails first
        if BranchDetails.objects.filter(branch_code=origin_code).exists():
            branch = BranchDetails.objects.get(branch_code=origin_code)
            origin_name = branch.branchname
            origin_address = f"{branch.address}, {branch.location}"
        else:
            # Try UserDetails
            try:
                user = UserDetails.objects.filter(code=origin_code).first()
                if user:
                    origin_name = user.code_name
            except:
                pass
        
        # Get destination details
        dest_code = manifest.tohub_branch_code
        dest_name = dest_code
        dest_address = ""
        
        # Try HubDetails first
        if HubDetails.objects.filter(hub_code=dest_code).exists():
            hub = HubDetails.objects.get(hub_code=dest_code)
            dest_name = hub.hubname
            dest_address = f"{hub.address}, {hub.location}"
        elif BranchDetails.objects.filter(branch_code=dest_code).exists():
            branch = BranchDetails.objects.get(branch_code=dest_code)
            dest_name = branch.branchname
            dest_address = f"{branch.address}, {branch.location}"
        
        
        # Get vehicle number with better error handling
        vehicle_number = "N/A"
        try:
            if manifest.vehicle_number:
                vehicle_number = manifest.vehicle_number.vehiclenumber
        except Exception as e:
            # If vehicle_number field exists but can't be accessed
            vehicle_number = "N/A"
        
        
        # Get AWB list with pieces and weight
        awb_list = []
        total_pcs = 0
        total_wt = 0.0
        
        outscans = OutscanModel.objects.filter(manifestnumber=manifest)
        for outscan in outscans:
            awb_no = outscan.awbno
            pcs = 0
            wt = 0.0
            sender = ""
            receiver = ""
            destination = ""
            
            # Try to get booking details for pieces and weight
            try:
                from ..models import BookingDetails
                booking = BookingDetails.objects.filter(awbno=awb_no).first()
                if booking:
                    pcs = booking.pcs or 0
                    wt = float(booking.wt) if booking.wt else 0.0
                    sender = booking.sendername or ""
                    receiver = booking.recievername or ""
                    # Resolve destination name from code
                    dest_code = booking.destination_code
                    destination = dest_code or ""
                    
                    if dest_code:
                        # Try to resolve destination name
                        if HubDetails.objects.filter(hub_code=dest_code).exists():
                            destination = HubDetails.objects.get(hub_code=dest_code).hubname
                        elif BranchDetails.objects.filter(branch_code=dest_code).exists():
                            destination = BranchDetails.objects.get(branch_code=dest_code).branchname
                        # Fallback to UserDetails if needed
                        elif UserDetails.objects.filter(code=dest_code).exists():
                             destination = UserDetails.objects.get(code=dest_code).code_name 
            except:
                pass
            
            awb_list.append({
                'awb_number': awb_no,
                'pcs': pcs,
                'wt': wt,
                'sender': sender,
                'receiver': receiver,
                'destination': destination
            })
            
            total_pcs += pcs
            total_wt += wt
        
        return {
            'manifest_number': manifest.manifestnumber,
            'date': manifest.date.strftime('%d/%m/%Y %H:%M:%S') if manifest.date else "",
            'origin': origin_name,
            'origin_address': origin_address,
            'destination': dest_name,
            'destination_address': dest_address,
            'vehicle_number': vehicle_number,
            'awb_list': awb_list,
            'total_pcs': total_pcs,
            'total_wt': total_wt
        }
    except Exception as e:
        print(f"Error gathering Manifest data: {e}")
        return None


# ==================== HELPERS ====================

def style(size=8, bold=False, align=TA_LEFT, leading=None, color=colors.black):
    return ParagraphStyle('_',
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,
        leading=leading or (size * 1.3),
        alignment=align,
        textColor=color,
    )

def P(text, size=8, bold=False, align=TA_LEFT, leading=None, color=colors.black):
    return Paragraph(text, style(size, bold, align, leading, color))

BLUE  = colors.HexColor('#1a6fa8')
WHITE = colors.white
LGREY = colors.Color(0.91, 0.91, 0.91)


def style(size=8, bold=False, align=TA_LEFT, leading=None, color=colors.black):
    return ParagraphStyle('_',
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,
        leading=leading or (size * 1.3),
        alignment=align,
        textColor=color,
    )


def P(text, size=8, bold=False, align=TA_LEFT, leading=None):
    return Paragraph(text, style(size, bold, align, leading))


BLUE  = colors.HexColor('#1a6fa8')
WHITE = colors.white
LGREY = colors.Color(0.91, 0.91, 0.91)

def BOX(extra=None):
    s = [
        ('BOX',           (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2),
    ]
    if extra:
        s.extend(extra)
    return s


# def generate_booking_pdf(booking_data):
#     buffer = BytesIO()

#     # A4 portrait: usable = 210-8-8 = 194mm wide, 297-3-3 = 291mm tall
#     # 3 slips + 2 gaps of 1mm = 289mm → each slip ~96mm tall
#     W  = 194 * mm
#     SH = 95  * mm   # slip height

#     doc = SimpleDocTemplate(
#         buffer, pagesize=A4,
#         topMargin=3*mm, bottomMargin=3*mm,
#         leftMargin=8*mm, rightMargin=8*mm,
#     )

#     awb   = booking_data.get('awb_number', '')
#     org   = booking_data.get('origin_name', '').upper()
#     dst   = booking_data.get('destination_name', '').upper()
#     sn    = booking_data.get('sender_name', '')
#     sa    = booking_data.get('sender_address', '')
#     sp    = booking_data.get('sender_phone', '')
#     rn    = booking_data.get('receiver_name', '')
#     ra    = booking_data.get('receiver_address', '')
#     rp    = booking_data.get('receiver_phone', '')
#     dt    = booking_data.get('date', '')
#     tm    = booking_data.get('time', '')
#     pcs   = str(booking_data.get('pieces', ''))
#     wt    = str(booking_data.get('weight', ''))
#     cont  = str(booking_data.get('contents', ''))
#     amt   = str(booking_data.get('amount', ''))
#     bookingbranch = booking_data.get('booked_branch_address', '')

#     # ── Panel widths ──────────────────────────────────────────────────────────
#     # Image: left ~58% right ~42%
#     LP = 112 * mm
#     RP = W - LP   # 82mm

#     def make_slip(copy_label):

#         # ════════════════════════════════════════════════════════════════════
#         # LEFT PANEL
#         # ════════════════════════════════════════════════════════════════════

#         # ── L1: Branding row ─────────────────────────────────────────────────
#         # [icon 12mm | FDC COURIER & CARGO large]
#         brand = Table([[
#             P('✈', 14, bold=True, align=TA_CENTER),
#             Paragraph(
#                 '<b><font size=11>FDC COURIER &amp; CARGO</font></b><br/>'
#                 '<font size=7>(LOCAL &amp; DOMESTIC CARGO SERVICES)</font><br/>'
#                 f'<font size=8>Booked Branch: <b>{bookingbranch}</b></font>',
#                 style(8, leading=13, align=TA_LEFT)
#             ),
           
#         ]], colWidths=[12*mm, LP-12*mm], rowHeights=[18*mm])
#         brand.setStyle(TableStyle([
#             ('BOX',          (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',   (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1), 1),
#             ('LEFTPADDING',  (0,0),(-1,-1), 2),
#         ]))

#         # ── L2: CONSIGNOR label ──────────────────────────────────────────────
#         consignor_label = Table([[
#             P('CONSIGNOR', 9, bold=True, align=TA_CENTER),
#         ]], colWidths=[LP], rowHeights=[6*mm])
#         consignor_label.setStyle(TableStyle([
#             ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
#             ('LEFTPADDING', (0,0),(-1,-1), 2),
#             ('TOPPADDING',  (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── L3: Consignor address (tall blank writing area) ──────────────────
#         consignor_info = Table([[
#             Paragraph(
#                 f'<b>{sn}</b><br/>{sa}' if sn else '',
#                 style(11, leading=9.5, align=TA_CENTER)
#             ),
#         ]], colWidths=[LP], rowHeights=[15*mm])
#         consignor_info.setStyle(TableStyle([
#             ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'TOP'),
#             ('TOPPADDING',  (0,0),(-1,-1), 3),
#             ('LEFTPADDING', (0,0),(-1,-1), 3),
#         ]))
#         # booked_branch_label = Table([[
#         #     P('BOOKED BRANCH', 9, bold=True, align=TA_LEFT),
#         # ]], colWidths=[LP], rowHeights=[6*mm])
#         # booked_branch_label.setStyle(TableStyle([
#         #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#         #     ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
#         #     ('LEFTPADDING', (0,0),(-1,-1), 2),
#         #     ('TOPPADDING',  (0,0),(-1,-1), 1),
#         #     ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         # ]))
#         # booked_branch_info = Table([[
#         #     Paragraph(
#         #         f'<b>{bookingbranch}</b>' if bookingbranch else '',
#         #         style(7, leading=9.5, align=TA_LEFT)
#         #     ),
#         # ]], colWidths=[LP], rowHeights=[5*mm])
#         # booked_branch_info.setStyle(TableStyle([
#         #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#         #     ('VALIGN', (0,0),(-1,-1), 'TOP'),
#         #     ('TOPPADDING',  (0,0),(-1,-1), 1),
#         #     ('LEFTPADDING', (0,0),(-1,-1), 3),
#         # ]))

#         # ── L4: Barcode ──────────────────────────────────────────────────────
#         bc = Table([
#             [BarcodeFlowable(awb, total_width=LP, bar_height=11*mm)],
#             [P(f'* {awb} *', 14, bold=True, align=TA_CENTER)],
#         ], colWidths=[LP], rowHeights=[12*mm, 5*mm])
#         bc.setStyle(TableStyle([
#             ('BOX',      (0,0),(-1,-1), 0.5, colors.black),
#             ('LINEABOVE',(0,1),(0,1),   0.5, colors.black),
#             ('ALIGN',    (0,0),(-1,-1), 'CENTER'),
#             ('VALIGN',   (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',   (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1), 1),
#         ]))

#         # ── L5: Footer ───────────────────────────────────────────────────────
#         # Matches image exactly:
#         # [small warrant text] | Date | Time | Amount Rs. |        |
#         #                      |      |      | GST        |        |
#         #                      | Recd By     | Total Rs.  |        |
#         #                      | FDC         | CASH | CREDIT       |
#         # [Sender Signature]
#         warrant = Paragraph(' ', style(4.5, leading=6))
#         sig = Paragraph('Sender Signature', style(5, align=TA_CENTER))

#         # col widths must sum to LP=112mm
#         # [warrant+sig=24mm | date=18 | time=18 | amt=22 | cash=15 | credit=15]
#         fc = [24*mm, 18*mm, 18*mm, 22*mm, 15*mm, 15*mm]

#         footer = Table([
#             # row0: warrant | Date(hdr) | Time(hdr) | Amount Rs(hdr) | blank | blank
#             [warrant,
#              P('Date',       6, bold=True, align=TA_CENTER),
#              P('Time',       6, bold=True, align=TA_CENTER),
#              P('Amount Rs.', 6, bold=True, align=TA_CENTER),
#              P('', 6), P('', 6)],
#             # row1: '' | date val | time val | blank | blank | blank
#             ['',
#              P(dt, 7, align=TA_CENTER),
#              P(tm, 7, align=TA_CENTER),
#              P('', 7), P('', 7), P('', 7)],
#             # row2: '' | '' | '' | GST(hdr) | blank | blank
#             ['', '', '',
#              P('GST', 6, bold=True, align=TA_CENTER),
#              P('', 6), P('', 6)],
#             # row3: '' | Recd By(hdr, span2) | Total Rs(hdr) | blank | blank
#             ['',
#              P('Recd By', 6, bold=True, align=TA_CENTER),
#              P('', 6),
#              P('Total Rs.', 6, bold=True, align=TA_CENTER),
#              P('', 6), P('', 6)],
#             # row4: sig | FDC(span2) | CASH | CREDIT | blank
#             [sig,
#              P('FDC', 7, bold=True, align=TA_CENTER),
#              P('', 6),
#              P('CASH',   7, bold=True, align=TA_CENTER),
#              P('CREDIT', 7, bold=True, align=TA_CENTER),
#              P('', 6)],
#         ], colWidths=fc, rowHeights=[5*mm, 4*mm, 4*mm, 4*mm, 5*mm])

#         footer.setStyle(TableStyle([
#             ('BOX',          (0,0),(-1,-1), 0.5, colors.black),
#             # vertical dividers between main columns
#             ('LINEAFTER',    (0,0),(0,-1),  0.5, colors.black),
#             ('LINEAFTER',    (1,0),(2,-1),  0.5, colors.black),  # after time col
#             ('LINEAFTER',    (3,0),(3,-1),  0.5, colors.black),
#             ('LINEAFTER',    (4,0),(4,-1),  0.5, colors.black),
#             # horizontal line below header row
#             ('LINEBELOW',    (1,0),(5,0),   0.5, colors.black),
#             ('LINEBELOW',    (1,2),(5,2),   0.5, colors.black),
#             ('LINEBELOW',    (1,3),(5,3),   0.5, colors.black),
#             # spans
#             ('SPAN', (0,0),(0,4)),   # warrant text full height
#             ('SPAN', (1,1),(1,2)),   # date value spans rows 1-2
#             ('SPAN', (2,1),(2,2)),   # time value spans rows 1-2
#             ('SPAN', (1,3),(2,3)),   # Recd By header spans cols 1-2
#             ('SPAN', (1,4),(2,4)),   # FDC value spans cols 1-2
#             # backgrounds
#             ('BACKGROUND',   (1,0),(3,0),   LGREY),
#             ('BACKGROUND',   (1,3),(2,3),   LGREY),
#             ('BACKGROUND',   (3,2),(3,2),   LGREY),
#             ('BACKGROUND',   (3,3),(3,3),   LGREY),
#             # alignment
#             ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
#             ('VALIGN',       (0,0),(0,0),   'TOP'),
#             ('ALIGN',        (0,0),(-1,-1), 'CENTER'),
#             ('TOPPADDING',   (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1), 1),
#             ('LEFTPADDING',  (0,0),(-1,-1), 1),
#             ('RIGHTPADDING', (0,0),(-1,-1), 1),
#         ]))

#         left = Table([
#             [brand],
#             [consignor_label],
#             [consignor_info],
#             # [booked_branch_label],
#             # [booked_branch_info],
#             [bc],
#             [footer],
#         ], colWidths=[LP])
#         left.setStyle(TableStyle([
#             ('TOPPADDING',   (0,0),(-1,-1), 0),
#             ('BOTTOMPADDING',(0,0),(-1,-1), 0),
#             ('LEFTPADDING',  (0,0),(-1,-1), 0),
#             ('RIGHTPADDING', (0,0),(-1,-1), 0),
#         ]))

#         # ════════════════════════════════════════════════════════════════════
#         # RIGHT PANEL
#         # ════════════════════════════════════════════════════════════════════

#         # ── R1: CARGO CONSIGNMENT NOTE header (grey bg) ──────────────────────
#         r_title = Table([[
#             P(copy_label, 7, bold=True, align=TA_CENTER),
#         ]], colWidths=[RP], rowHeights=[5*mm])
#         r_title.setStyle(TableStyle([
#             ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
#             ('BACKGROUND', (0,0),(-1,-1), LGREY),
#             ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING', (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R2: SURFACE BOOKING | ORIGIN | DESTN (grey bg header) ───────────
#         # col widths inside RP=82mm: [42 | 22 | 18]
#         r_hdr = Table([[
#             P('', 7, bold=True, align=TA_CENTER),
#             P('ORIGIN',          7, bold=True, align=TA_CENTER),
#             P('DESTN',           7, bold=True, align=TA_CENTER),
#         ]], colWidths=[10*mm, 36*mm, 36*mm], rowHeights=[5*mm])
#         r_hdr.setStyle(TableStyle([
#             ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
#             ('LINEAFTER', (0,0),(1,-1),  0.5, colors.black),
#             ('BACKGROUND',(0,0),(-1,-1), LGREY),
#             ('VALIGN',    (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',(0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R3: blank | ORIGIN city large | DESTN city ──────────────────────
#         r_cities = Table([[
#             P('Surface', 4),
#             P(f'<b>{org}</b>', 10, align=TA_CENTER),
#             P(f'<b>{dst}</b>', 10, align=TA_CENTER),
#         ]], colWidths=[10*mm, 36*mm, 36*mm], rowHeights=[8*mm])
#         r_cities.setStyle(TableStyle([
#             ('BOX',      (0,0),(-1,-1), 0.5, colors.black),
#             ('LINEAFTER',(0,0),(1,-1),  0.5, colors.black),
#             ('VALIGN',   (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',(0,0),(-1,-1),1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R4: CONSIGNEE label ──────────────────────────────────────────────
#         r_conslabel = Table([[
#             P('CONSIGNEE', 9 , bold=True, align=TA_CENTER),
#         ]], colWidths=[RP], rowHeights=[6*mm])
#         r_conslabel.setStyle(TableStyle([
#             ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
#             ('LEFTPADDING',(0,0),(-1,-1), 2),
#             ('TOPPADDING', (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R5: Consignee address blank writing area ─────────────────────────
#         r_consinfo = Table([[
#             Paragraph(
#                 f'<b>{rn}</b><br/>{ra}' if rn else '',
#                 style(11, leading=9.5, align=TA_CENTER)
#             ),
#         ]], colWidths=[RP], rowHeights=[24*mm])
#         r_consinfo.setStyle(TableStyle([
#             ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'TOP'),
#             ('TOPPADDING', (0,0),(-1,-1), 3),
#             ('LEFTPADDING',(0,0),(-1,-1), 3),
#         ]))

#         # ── R6: Phone | Pincode ──────────────────────────────────────────────
#         r_phone = Table([[
#             P(f'Phone :{rp}',   7, align=TA_LEFT),
#             P(f'Pincode :', 7, align=TA_LEFT),
#         ]], colWidths=[RP*0.55, RP*0.45], rowHeights=[5*mm])
#         r_phone.setStyle(TableStyle([
#             # ('LINEBEFORE',  (0,0),(0,-1),  0, colors.black),
#             # ('LINEAFTER',   (-1,0),(-1,-1),0, colors.black),
#             # ('LINEBELOW',   (0,-1),(-1,-1),0, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
#             ('LEFTPADDING',(0,0),(-1,-1), 3),
#             ('TOPPADDING', (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R7: Terms text (small italic) ────────────────────────────────────
#         # r_terms = Table([[
#         #     Paragraph(
#         #         '',
#         #         style(4.5, leading=6, align=TA_LEFT)
#         #     ),
#         # ]], colWidths=[RP], rowHeights=[9*mm])
#         # r_terms.setStyle(TableStyle([
#         #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#         #     ('VALIGN', (0,0),(-1,-1), 'TOP'),
#         #     ('TOPPADDING', (0,0),(-1,-1), 2),
#         #     ('LEFTPADDING',(0,0),(-1,-1), 2),
#         # ]))

#         # ── R8: Declared Value | Contents | No Pieces | Weight (grey header) ─
#         cw8 = [RP*0.27, RP*0.27, RP*0.23, RP*0.23]
#         r_sumhdr = Table([[
#             P('Declared Value', 6, bold=True, align=TA_CENTER),
#             P('Contents',       6, bold=True, align=TA_CENTER),
#             P('No Pieces',      6, bold=True, align=TA_CENTER),
#             P('Weight',         6, bold=True, align=TA_CENTER),
#         ]], colWidths=cw8, rowHeights=[5*mm])
#         r_sumhdr.setStyle(TableStyle([
#             ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
#             ('INNERGRID',  (0,0),(-1,-1), 0.5, colors.black),
#             ('BACKGROUND', (0,0),(-1,-1), LGREY),
#             ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING', (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R9: Summary values ───────────────────────────────────────────────
#         r_sumval = Table([[
#             P(amt,  7, align=TA_CENTER),
#             P(cont, 7, align=TA_CENTER),
#             P(pcs,  7, align=TA_CENTER),
#             P(f'{wt} kg', 7, align=TA_CENTER),
#         ]], colWidths=cw8, rowHeights=[6*mm])
#         r_sumval.setStyle(TableStyle([
#             ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
#             ('INNERGRID', (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN',    (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',(0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R10: Self Cheques prohibited (grey) ──────────────────────────────
#         r_prohib = Table([[
#             P('Self Cheques, Jewellery, Cell Phones & Cash is Strictly Prohibited',
#               6, bold=True, align=TA_CENTER),
#         ]], colWidths=[RP], rowHeights=[5*mm])
#         r_prohib.setStyle(TableStyle([
#             ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
#             ('BACKGROUND', (0,0),(-1,-1), LGREY),
#             ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING', (0,0),(-1,-1), 1),
#             ('BOTTOMPADDING',(0,0),(-1,-1),1),
#         ]))

#         # ── R11: THANKS FOR UTILISING OUR SERVICES ───────────────────────────
#         r_thanks = Table([[
#             P('Signature', 6, bold=True, align=TA_CENTER),
#         ]], colWidths=[RP], rowHeights=[5*mm])
#         r_thanks.setStyle(TableStyle([
#             ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
#             ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
#             ('TOPPADDING',(0,0),(-1,-1),1),
#     elements = []
#     for i, label in enumerate(['SHIPPER COPY', 'POD COPY', 'OFFICE COPY']):
#         elements.append(make_slip(label))
#         if i < 2:
#             elements.append(Spacer(1, 10*mm))

#     doc.build(elements)
#     buffer.seek(0)
#     return buffer.read()


def get_booking_data(awb_number):
    try:
        from ..models import BookingDetails, BranchDetails, HubDetails, UserDetails
        import datetime

        booking = BookingDetails.objects.filter(awbno=awb_number).first()
        if not booking:
            return None

        origin_code = booking.booked_code
        origin_name = origin_code
        if BranchDetails.objects.filter(branch_code=origin_code).exists():
            origin_name = BranchDetails.objects.get(branch_code=origin_code).branchname
        elif UserDetails.objects.filter(code=origin_code).exists():
            origin_name = UserDetails.objects.get(code=origin_code).code_name

        dest_code = booking.destination_code
        dest_name = dest_code
        if HubDetails.objects.filter(hub_code=dest_code).exists():
            dest_name = HubDetails.objects.get(hub_code=dest_code).hubname
        elif BranchDetails.objects.filter(branch_code=dest_code).exists():
            dest_name = BranchDetails.objects.get(branch_code=dest_code).branchname
        elif UserDetails.objects.filter(code=dest_code).exists():
            dest_name = UserDetails.objects.get(code=dest_code).code_name
        
        branch_name_address = ""
        branch_phone = ""
        if HubDetails.objects.filter(hub_code=origin_code).exists():
            h = HubDetails.objects.get(hub_code=origin_code)
            branch_name_address = h.address
            branch_phone = h.phone_number
        elif BranchDetails.objects.filter(branch_code=origin_code).exists():
            b = BranchDetails.objects.get(branch_code=origin_code)
            branch_name_address = b.address
            branch_phone = b.phone_number

        return {
            'awb_number':       booking.awbno,
            'date':             booking.date.strftime('%d-%m-%Y') if booking.date else datetime.datetime.now().strftime('%d-%m-%Y'),
            'time':             datetime.datetime.now().strftime('%I:%M %p'),
            'origin_name':      origin_name,
            'destination_name': dest_name,
            'sender_name':      booking.sendername,
            'sender_address':   booking.senderaddress,
            'sender_phone':     booking.senderphonenumber,
            'receiver_name':    booking.recievername,
            'receiver_address': booking.recieveraddress,
            'receiver_phone':   booking.recieverphonenumber,
            'pieces':           booking.pcs,
            'weight':           booking.wt,
            'contents':         booking.contents,
            'amount':           str(booking.total) if getattr(booking, 'total', None) is not None else '0.00',
            'courier_charges':  str(booking.courier_charges) if getattr(booking, 'courier_charges', None) is not None else '0.00',
            'gst':              str(booking.gst) if getattr(booking, 'gst', None) is not None else '0.00',
            'packing_charges':  str(booking.packing_charges) if getattr(booking, 'packing_charges', None) is not None else '0.00',
            'freight_charges':  str(booking.freight_charges) if getattr(booking, 'freight_charges', None) is not None else '0.00',
            'others':           str(booking.others) if getattr(booking, 'others', None) is not None else '0.00',
            'total':            str(booking.total) if getattr(booking, 'total', None) is not None else '0.00',
            'booked_branch_address': branch_name_address,
            'booked_branch_phone': branch_phone,
            'mode':             booking.mode or 'ROAD',
            'reference_no':     booking.refernce_no or '',
            'eway_bill_no':     getattr(booking, 'eway_bill_no', ''),
            'invoice_no':       getattr(booking, 'invoice_no', ''),
            'invoice_date':     booking.invoice_date.strftime('%d-%m-%Y') if getattr(booking, 'invoice_date', None) else '',
            'invoice_amount':   str(booking.invoice_amount) if getattr(booking, 'invoice_amount', None) is not None else '',
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


from io import BytesIO
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.barcode import code128

def generate_booking_pdf(input1):
    input3 = BytesIO()

    # A4 portrait usable width: 210mm - 8mm - 8mm = 194mm
    W  = 194 * mm
    CP = 6 * mm
    LP = (W - CP) / 2.0  
    RP = (W - CP) / 2.0  

    # Brand color matching the physical copy
    FDC_GREEN = colors.HexColor("#008A4A")

    doc = SimpleDocTemplate(
        input3, pagesize=A4,
        topMargin=5*mm, bottomMargin=5*mm,
        leftMargin=8*mm, rightMargin=8*mm,
    )

    # Core data mapping
    input2 = input1.get('awb_number', '')  # AWB & Barcode
    org  = input1.get('origin_name', '').upper()
    dst  = input1.get('destination_name', '').upper()
    sn   = input1.get('sender_name', '')
    sa   = input1.get('sender_address', '')
    sp   = input1.get('sender_phone', '')
    rn   = input1.get('receiver_name', '')
    ra   = input1.get('receiver_address', '')
    rp   = input1.get('receiver_phone', '')
    dt   = input1.get('date', '')
    tm   = input1.get('time', '')
    pcs  = str(input1.get('pieces', ''))
    wt   = str(input1.get('weight', ''))
    cont = str(input1.get('contents', ''))
    amt  = str(input1.get('amount', ''))
    courier_charges = str(input1.get('courier_charges', '0.00'))
    gst = str(input1.get('gst', '0.00'))
    packing_charges = str(input1.get('packing_charges', '0.00'))
    freight_charges = str(input1.get('freight_charges', '0.00'))
    others = str(input1.get('others', '0.00'))
    total = str(input1.get('total', '0.00'))
    bookingbranch = input1.get('booked_branch_address', '')
    bookingphone = input1.get('booked_branch_phone', '')
    eway_bill = input1.get('eway_bill_no', '')
    invoice_amount = input1.get('invoice_amount', '')

    # Typography helpers
    def style(size, leading=None, align=TA_LEFT, color=FDC_GREEN):
        if leading is None:
            leading = size * 1.2
        return ParagraphStyle(name=f's_{size}_{align}', fontSize=size, leading=leading, alignment=align, textColor=color)

    def P(text, size, bold=False, align=TA_LEFT, color=FDC_GREEN):
        if bold:
            text = f"<b>{text}</b>"
        return Paragraph(text, style(size, align=align, color=color))

    def make_slip(copy_label):

        # ════════════════════════════════════════════════════════════════════
        # LEFT PANEL
        # ════════════════════════════════════════════════════════════════════

        # ── L1: Branding row ────────────────────────────────────────────────
        brand = Table([[
            P('✈', 16, bold=True, align=TA_CENTER),
            Paragraph(
                '<b><font size=12 color="#008A4A">FDC COURIER &amp; CARGO</font></b><br/>'
                '<font size=7 color="#008A4A">(LOCAL &amp; DOMESTIC CARGO SERVICES)</font><br/>',
                style(8, leading=10, align=TA_LEFT)
            ),
        ]], colWidths=[12*mm, LP-12*mm], rowHeights=[15*mm])
        brand.setStyle(TableStyle([
            ('LINEAFTER',    (0,0),(0,0), 0.5, FDC_GREEN),
            ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
            ('LEFTPADDING',  (0,0),(-1,-1), 2),
            ('RIGHTPADDING', (0,0),(-1,-1), 2),
        ]))

        # ── L2: CONSIGNOR label ─────────────────────────────────────────────
        consignor_label = Table([[
            P('CONSIGNOR', 9, bold=True, align=TA_CENTER),
        ]], colWidths=[LP], rowHeights=[5*mm])
        consignor_label.setStyle(TableStyle([
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
        ]))

        # ── L3: Consignor address ───────────────────────────────────────────
        consignor_info = Table([[
            Paragraph(
                f'<b><font color="black">{sn}</font></b><br/><font color="black">{sa}</font><br/><font color="black">Phone: {sp}</font>' if sn else '',
                style(9, leading=11, align=TA_CENTER)
            ),
        ]], colWidths=[LP], rowHeights=[16*mm])
        consignor_info.setStyle(TableStyle([
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
            ('TOPPADDING', (0,0),(-1,-1), 2),
            ('BOTTOMPADDING', (0,0),(-1,-1), 2),
            ('LEFTPADDING', (0,0),(-1,-1), 4),
            ('RIGHTPADDING', (0,0),(-1,-1), 4),
        ]))

        # ── L4: Barcode (Dynamic via ReportLab) ─────────────────────────────
        bc_flowable = code128.Code128(input2, barWidth=1.2, barHeight=9*mm) if input2 else P('NO AWB', 10)
        bc = Table([
            [bc_flowable],
            [P(f'* {input2} *', 11, bold=True, align=TA_CENTER, color=colors.black)],
        ], colWidths=[LP], rowHeights=[12*mm, 5*mm])
        bc.setStyle(TableStyle([
            ('ALIGN',    (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',   (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
        ]))

        # ── L5: Footer ──────────────────────────────────────────────────────
        # Col widths summing to LP (94mm) without the empty leftmost signature column
        fc = [23*mm, 14*mm, 23*mm, 17*mm, 17*mm] 

        footer = Table([
            [P('Date', 6, bold=True, align=TA_CENTER), P('Time', 6, bold=True, align=TA_CENTER), P('Amount Rs.', 6, bold=True, align=TA_CENTER), P(courier_charges, 6, align=TA_CENTER, color=colors.black), P('', 6)],
            [P(dt, 6, align=TA_CENTER, color=colors.black), P(tm, 6, align=TA_CENTER, color=colors.black), P('GST', 6, bold=True, align=TA_CENTER), P(gst, 6, align=TA_CENTER, color=colors.black), P('', 7)],
            [P('Recd By', 6, bold=True, align=TA_CENTER), '', P('Total Rs.', 6, bold=True, align=TA_CENTER), P(total, 6, align=TA_CENTER, color=colors.black), P('', 6)],
            [P('FDC', 7, bold=True, align=TA_CENTER), '', P('PAY MODE', 7, bold=True, align=TA_CENTER), P('[  ] CASH', 6.5, bold=True, align=TA_CENTER), P('[  ] CREDIT', 6.5, bold=True, align=TA_CENTER)],
        ], colWidths=fc, rowHeights=[4.75*mm, 4.75*mm, 4.75*mm, 4.75*mm])
        
        footer.setStyle(TableStyle([
            ('LINEAFTER',    (0,0),(0,-1),  0.5, FDC_GREEN),
            ('LINEAFTER',    (1,0),(1,-1),  0.5, FDC_GREEN),
            ('LINEAFTER',    (2,0),(2,-1),  0.5, FDC_GREEN),
            ('LINEAFTER',    (3,0),(3,-1),  0.5, FDC_GREEN),
            ('LINEBELOW',    (0,0),(4,2),   0.5, FDC_GREEN),
            ('SPAN', (0,2),(1,2)),
            ('SPAN', (0,3),(1,3)),
            ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
            ('ALIGN',        (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
            ('LEFTPADDING',  (0,0),(-1,-1), 1),
            ('RIGHTPADDING', (0,0),(-1,-1), 1),
        ]))

        left = Table([[brand], [consignor_label], [consignor_info], [bc], [footer]], colWidths=[LP], rowHeights=[15*mm, 5*mm, 16*mm, 17*mm, 19*mm])
        left.setStyle(TableStyle([
            ('LINEBELOW', (0,0),(-1,-2), 0.5, FDC_GREEN),
            ('TOPPADDING', (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
            ('LEFTPADDING', (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))


        # ════════════════════════════════════════════════════════════════════
        # RIGHT PANEL
        # ════════════════════════════════════════════════════════════════════

        # Row 0: Booking Header & Cities (15mm total)
        r_hdr_cities = Table([
            [
                P('BOOKED BRANCH', 6, bold=True, align=TA_CENTER),
                P('ORIGIN', 7, bold=True, align=TA_CENTER),
                P('DESTN', 7, bold=True, align=TA_CENTER)
            ],
            [
                Paragraph(f"{bookingbranch}<br/>Phone: {bookingphone}" if bookingphone else bookingbranch, style(5, leading=6, align=TA_CENTER, color=colors.black)),
                P(f'<b>{org}</b>', 10, align=TA_CENTER, color=colors.black),
                P(f'<b>{dst}</b>', 10, align=TA_CENTER, color=colors.black)
            ]
        ], colWidths=[RP*0.28, RP*0.36, RP*0.36], rowHeights=[5*mm, 10*mm])
        r_hdr_cities.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 0.5, FDC_GREEN),
            ('INNERGRID', (0,0), (-1,-1), 0.5, FDC_GREEN),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ]))

        # Row 1: Consignee Label (5mm)
        r_conslabel = Table([[P('CONSIGNEE', 9, bold=True, align=TA_CENTER)]], colWidths=[RP], rowHeights=[5*mm])
        r_conslabel.setStyle(TableStyle([
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING', (0,0),(-1,-1), 1),
        ]))

        # Row 2: Consignee Address, Phone, Pincode Info (16mm)
        r_consinfo = Table([[
            Paragraph(f'<b><font color="black">{rn}</font></b><br/><font color="black">{ra}</font><br/><font color="black">Phone: {rp} | Pincode: </font>' if rn else '', style(9, leading=11, align=TA_CENTER))
        ]], colWidths=[RP], rowHeights=[16*mm])
        r_consinfo.setStyle(TableStyle([
            ('VALIGN', (0,0),(-1,-1), 'TOP'), 
            ('TOPPADDING', (0,0),(-1,-1), 2),
            ('BOTTOMPADDING', (0,0),(-1,-1), 2),
            ('LEFTPADDING', (0,0),(-1,-1), 4),
            ('RIGHTPADDING', (0,0),(-1,-1), 4),
        ]))

        # Row 3: Summary Details (17mm total)
        # cw8 column widths: Declared Value decreased to 18%, Contents increased to 36%
        cw8 = [RP*0.18, RP*0.36, RP*0.23, RP*0.23]
        declared_val = invoice_amount if eway_bill else ""
        r_sum = Table([
            [
                P('Declared Value', 6, bold=True, align=TA_CENTER),
                P('Contents', 6, bold=True, align=TA_CENTER),
                P('No Pieces', 6, bold=True, align=TA_CENTER),
                P('Weight', 6, bold=True, align=TA_CENTER)
            ],
            [
                P(declared_val, 8, align=TA_CENTER, color=colors.black),
                P(cont, 8, align=TA_CENTER, color=colors.black),
                P(pcs, 8, align=TA_CENTER, color=colors.black),
                P(f'{wt} kg' if wt else '', 8, align=TA_CENTER, color=colors.black)
            ]
        ], colWidths=cw8, rowHeights=[7*mm, 10*mm])
        r_sum.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 0.5, FDC_GREEN),
            ('INNERGRID', (0,0), (-1,-1), 0.5, FDC_GREEN),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ]))

        # Row 4: Prohibited Warning & Signatures (19mm total)
        # Warning text size decreased to size=5, added consignment status, aligned signature to bottom and borders to left
        r_prohib_thanks = Table([
            [P('Self Cheques, Jewellery, Cell Phones & Cash is Strictly Prohibited', 5, bold=True, align=TA_CENTER)],
            [P('CONSIGNMENT RECEIVED IN GOOD CONDITION', 6, bold=True, align=TA_CENTER)],
            [P('Signature', 6, bold=True, align=TA_CENTER)]
        ], colWidths=[RP], rowHeights=[4.75*mm, 7.25*mm, 7.0*mm])
        r_prohib_thanks.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (0,0), 0.5, FDC_GREEN),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('VALIGN', (0,2), (0,2), 'BOTTOM'),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,2), (0,2), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ]))

        right = Table([
            [r_hdr_cities], [r_conslabel], [r_consinfo], [r_sum], [r_prohib_thanks]
        ], colWidths=[RP], rowHeights=[15*mm, 5*mm, 16*mm, 17*mm, 19*mm])
        right.setStyle(TableStyle([
            ('LINEBELOW', (0,0),(-1,-2), 0.5, FDC_GREEN),
            ('TOPPADDING', (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
            ('LEFTPADDING', (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))

        # ── Combine Left and Right ──────────────────────────────────────────
        # ── Combine Left, Right and Copy Label ──────────────────────────────
        lbl_style = ParagraphStyle(
            name=f'lbl_{copy_label.replace(" ", "_")}',
            fontSize=5.5,
            leading=7,
            alignment=TA_CENTER,
            textColor=FDC_GREEN,
            fontName='Helvetica-Bold'
        )
        vertical_label = RotatedText(copy_label, lbl_style)

        slip = Table([[left, right, vertical_label]], colWidths=[LP, RP, CP])
        slip.setStyle(TableStyle([
            ('BOX', (0,0),(-1,-1), 1.5, FDC_GREEN),
            ('INNERGRID', (0,0),(-1,-1), 1.0, FDC_GREEN),
            ('VALIGN', (0,0),(1,0), 'TOP'),
            ('VALIGN', (2,0),(2,0), 'MIDDLE'),
            ('ALIGN', (2,0),(2,0), 'CENTER'),
            ('TOPPADDING', (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
            ('LEFTPADDING', (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))
        return slip

    # Build 3 vertical copies with spacers
    elements = []
    for i, label in enumerate(['SHIPPER COPY', 'POD COPY', 'OFFICE COPY']):
        elements.append(make_slip(label))
        if i < 2:
            elements.append(Spacer(1, 4*mm))

    doc.build(elements)
    input3.seek(0)
    return input3.read()


def generate_cargo_booking_pdf(input1):
    from reportlab.platypus import PageBreak
    input3 = BytesIO()

    # A4 portrait usable width: 210mm - 8mm - 8mm = 194mm
    # A4 portrait usable height: 297mm - 6mm - 6mm = 285mm
    # We fit 2 copies in a single page: each is 128mm tall, with a 9mm Spacer in between them.
    # Page layout columns:
    # Column 0: Left vertical margin text -> 6*mm
    # Column 1: Main Form Table -> 182*mm
    # Column 2: Right vertical margin text -> 6*mm
    # Total width = 194*mm
    
    doc = SimpleDocTemplate(
        input3, pagesize=A4,
        topMargin=6*mm, bottomMargin=6*mm,
        leftMargin=8*mm, rightMargin=8*mm,
    )

    # Core data mapping
    awb_code = input1.get('awb_number', '')  # AWB & Barcode
    org  = input1.get('origin_name', '').upper()
    dst  = input1.get('destination_name', '').upper()
    sn   = input1.get('sender_name', '')
    sa   = input1.get('sender_address', '')
    sp   = input1.get('sender_phone', '')
    rn   = input1.get('receiver_name', '')
    ra   = input1.get('receiver_address', '')
    rp   = input1.get('receiver_phone', '')
    dt   = input1.get('date', '')
    tm   = input1.get('time', '')
    pcs  = str(input1.get('pieces', ''))
    wt   = str(input1.get('weight', ''))
    cont = str(input1.get('contents', ''))
    amt  = str(input1.get('amount', ''))
    courier_charges = str(input1.get('courier_charges', '0.00'))
    gst = str(input1.get('gst', '0.00'))
    packing_charges = str(input1.get('packing_charges', '0.00'))
    freight_charges = str(input1.get('freight_charges', '0.00'))
    others = str(input1.get('others', '0.00'))
    total = str(input1.get('total', '0.00'))
    bookingbranch = input1.get('booked_branch_address', '')
    bookingphone = input1.get('booked_branch_phone', '')
    eway_bill = input1.get('eway_bill_no', '')
    inv_no = input1.get('invoice_no', '')
    inv_date = input1.get('invoice_date', '')
    inv_amt = input1.get('invoice_amount', '')
    mode = input1.get('mode', 'ROAD')
    ref_no = input1.get('reference_no', '')

    # Brand color matching the physical copy (green or HexColor("#008A4A"))
    FDC_GREEN = colors.HexColor("#008A4A")

    # Typography helpers
    def style(size, leading=None, align=TA_LEFT, color=FDC_GREEN, bold=False):
        if leading is None:
            leading = size * 1.2
        return ParagraphStyle(
            name=f'c_{size}_{align}_{bold}_{color.hexval()}',
            fontSize=size,
            leading=leading,
            alignment=align,
            textColor=color,
            fontName='Helvetica-Bold' if bold else 'Helvetica'
        )

    def P(text, size, bold=False, align=TA_LEFT, color=FDC_GREEN, leading=None):
        return Paragraph(text, style(size, leading=leading, align=align, color=color, bold=bold))

    # Construct the form_table layout (width 182mm)
    # ── 1. Header (15mm height)
    pay_trans = Table([
        [P('Payment Mode', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN), P('Transport Mode', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P('CREDIT', 8, bold=True, align=TA_CENTER, color=colors.black), P(mode.upper(), 8, bold=True, align=TA_CENTER, color=colors.black)]
    ], colWidths=[22.5*mm, 22.5*mm], rowHeights=[6*mm, 9*mm])
    pay_trans.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))

    middle_header = Table([
        [P('FDC COURIER & CARGO', 12, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P('(LOCAL & DOMESTIC CARGO SERVICES)', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)]
    ], colWidths=[67*mm], rowHeights=[8*mm, 7*mm])
    middle_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    barcode_flowable = code128.Code128(awb_code, barWidth=1.0, barHeight=6*mm) if awb_code else P('NO AWB', 10)
    
    barcode_box = Table([
        [P(awb_code, 9.5, bold=True, align=TA_CENTER, color=colors.black)],
        [barcode_flowable],
        [P(f'SHIPPING DATE : {dt}', 5.5, bold=True, align=TA_RIGHT, color=colors.black)]
    ], colWidths=[70*mm], rowHeights=[5*mm, 6.5*mm, 3.5*mm])
    barcode_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    header_row = Table([
        [pay_trans, middle_header, barcode_box]
    ], colWidths=[45*mm, 67*mm, 70*mm], rowHeights=[15*mm])
    header_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # ── 2. Origin/Destination (7mm height)
    origin_dest_row = Table([
        [
            P('ORIGIN', 6.5, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P(org, 8, bold=True, align=TA_CENTER, color=colors.black),
            P('DESTINATION', 6.5, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P(dst, 8, bold=True, align=TA_CENTER, color=colors.black)
        ]
    ], colWidths=[18*mm, 73*mm, 25*mm, 66*mm], rowHeights=[7*mm])
    origin_dest_row.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('BACKGROUND', (2,0), (2,0), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # ── 3. Addresses block (21mm height)
    bookingphone_str = f" | Phone: {bookingphone}" if bookingphone else ""
    booked_branch_text = f"<b><font color='{FDC_GREEN.hexval()}'>BOOKED BRANCH:</font> {org}</b><br/>{bookingbranch}{bookingphone_str}"
    sender_text = f"<b><font color='{FDC_GREEN.hexval()}'>SENDER:</font> {sn}</b><br/>{sa}<br/>Phone: {sp}"
    ship_to_text = f"<b><font color='{FDC_GREEN.hexval()}'>SHIP TO:</font> {rn}</b><br/>{ra}<br/>Phone: {rp}"

    address_row = Table([
        [
            Paragraph(booked_branch_text, style(6.5, leading=8.5, color=colors.black)),
            Paragraph(sender_text, style(6.5, leading=8.5, color=colors.black)),
            Paragraph(ship_to_text, style(6.5, leading=8.5, color=colors.black))
        ]
    ], colWidths=[60*mm, 61*mm, 61*mm], rowHeights=[21*mm])
    address_row.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))

    # ── 4. Main Grid (52mm height total)
    # Left part (Columns 1, 2, 3) -> 110mm wide
    left_headers = Table([
        [
            P('METHOD OF PACKING', 6, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P('DESCRIPTION (SAID TO CONTAIN)', 6, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P('VOLUME (CMS \ Inches)', 6, bold=True, align=TA_CENTER, color=FDC_GREEN)
        ]
    ], colWidths=[30*mm, 45*mm, 35*mm], rowHeights=[7*mm])
    left_headers.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    left_vals = Table([
        [
            P('', 7), 
            P(cont, 7.5, align=TA_CENTER, color=colors.black), 
            P('', 7)
        ]
    ], colWidths=[30*mm, 45*mm, 35*mm], rowHeights=[13*mm])
    left_vals.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    left_mid_headers = Table([
        [
            P('INVOICE NO. & DATE', 6, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P('E-WAYBILL NO', 6, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P("AT OWNER'S RISK / CARRIER'S RISK", 6, bold=True, align=TA_CENTER, color=FDC_GREEN)
        ]
    ], colWidths=[30*mm, 45*mm, 35*mm], rowHeights=[5*mm])
    left_mid_headers.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    risk_text = f"<font size=4 color='{FDC_GREEN.hexval()}'>If insured, Details of Insurance Policy</font><br/><font size=4.5 color='black'>POLICY NO: ___________ DATE: ______<br/>INSURANCE CO: _____________________<br/>INSURED VALUE: ____________________</font>"
    
    # Display format for invoice and date, fallback to reference number
    inv_display = inv_no
    if inv_no and inv_date:
        inv_display = f"{inv_no} / {inv_date}"
    elif not inv_no:
        inv_display = ref_no

    left_mid_vals = Table([
        [
            P(inv_display, 7.5, align=TA_CENTER, color=colors.black), 
            P(eway_bill, 7.5, align=TA_CENTER, color=colors.black), 
            Paragraph(risk_text, style(4.5, leading=6, color=colors.black))
        ]
    ], colWidths=[30*mm, 45*mm, 35*mm], rowHeights=[12*mm])
    left_mid_vals.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('VALIGN', (2,0), (2,0), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (2,0), (2,0), 1),
    ]))

    # Default value declared to invoice amount if eway bill is added, otherwise blank
    val_display = inv_amt if eway_bill else ""

    val_declared_box = Table([
        [P('VALUE DECLARED (Rs.)', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P(val_display, 9, bold=True, align=TA_CENTER, color=colors.black)]
    ], colWidths=[30*mm], rowHeights=[5*mm, 10*mm])
    val_declared_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    add_services_content = Table([
        [
            P('CREDIT CUSTOMER', 5.5, align=TA_LEFT, color=colors.black),
            P('DACC [  ]<br/>COD  [  ]<br/>DOD  [  ]', 5.5, align=TA_LEFT, color=colors.black),
            P('TOPAY AMT:<br/>MR NO.:<br/>DATE:', 5.5, leading=7, align=TA_LEFT, color=colors.black)
        ]
    ], colWidths=[28*mm, 22*mm, 30*mm], rowHeights=[10*mm])
    add_services_content.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
    ]))

    add_services_box = Table([
        [P('ADD. SERVICES', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [add_services_content]
    ], colWidths=[80*mm], rowHeights=[5*mm, 10*mm])
    add_services_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('LEFTPADDING', (0,1), (-1,1), 0),
        ('RIGHTPADDING', (0,1), (-1,1), 0),
        ('TOPPADDING', (0,1), (-1,1), 0),
        ('BOTTOMPADDING', (0,1), (-1,1), 0),
    ]))

    left_bottom_row = Table([
        [val_declared_box, add_services_box]
    ], colWidths=[30*mm, 80*mm], rowHeights=[15*mm])
    left_bottom_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    left_part = Table([
        [left_headers],
        [left_vals],
        [left_mid_headers],
        [left_mid_vals],
        [left_bottom_row]
    ], colWidths=[110*mm], rowHeights=[7*mm, 13*mm, 5*mm, 12*mm, 15*mm])
    left_part.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # Right part (Pieces, Weight, Charges, Freight) -> 72mm wide
    pieces_wt_table = Table([
        [P('NO. OF PIECES', 5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P(pcs or '0', 8, bold=True, align=TA_CENTER, color=colors.black)],
        [P('ACTUAL WEIGHT', 5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P(wt or '0.000', 8, bold=True, align=TA_CENTER, color=colors.black)],
        [P('CHARGED WEIGHT', 5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [P(wt or '0.000', 8, bold=True, align=TA_CENTER, color=colors.black)]
    ], colWidths=[18*mm], rowHeights=[7*mm, 8.5*mm, 5*mm, 8.5*mm, 5*mm, 9*mm])
    pieces_wt_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('BACKGROUND', (0,2), (0,2), colors.HexColor('#dce2f9')),
        ('BACKGROUND', (0,4), (0,4), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    charges_list = [
        'COURIER CHARGES',
        'GST',
        'PACKING CHARGES',
        'FREIGHT CHARGES',
        'OTHERS',
        'TO PAY CHARGES',
        'RISK CHARGE',
        'HANDLING CHARGES',
        'TOTAL',
        'GRAND TOTAL'
    ]

    charges_rows = []
    charges_rows.append([
        P('CHARGES', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN),
        P('AMOUNT', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)
    ])

    charge_values = {
        'COURIER CHARGES': courier_charges,
        'GST': gst,
        'PACKING CHARGES': packing_charges,
        'FREIGHT CHARGES': freight_charges,
        'OTHERS': others,
        'TOTAL': total,
        'GRAND TOTAL': total
    }

    for charge in charges_list:
        val_str = charge_values.get(charge, '')
        
        charges_rows.append([
            P(charge, 4.5, bold=(charge in ['TOTAL', 'GRAND TOTAL']), align=TA_LEFT, color=colors.black),
            P(val_str, 6.5, bold=(charge in ['TOTAL', 'GRAND TOTAL']), align=TA_RIGHT, color=colors.black)
        ])

    row_heights = [7*mm] + [3.6*mm] * len(charges_list)
    charges_table = Table(charges_rows, colWidths=[36*mm, 18*mm], rowHeights=row_heights)
    charges_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#dce2f9')),
        ('RIGHTPADDING', (1,1), (1,-1), 2),
        ('LEFTPADDING', (0,1), (0,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    upper_block = Table([
        [pieces_wt_table, charges_table]
    ], colWidths=[18*mm, 54*mm], rowHeights=[43*mm])
    upper_block.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    gstin_row = Table([
        [
            P('GSTIN paid by', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN),
            P('[ ] Cnr', 5, bold=True, align=TA_CENTER, color=colors.black),
            P('[ ] Cee', 5, bold=True, align=TA_CENTER, color=colors.black),
            P('[ ] Tpr', 5, bold=True, align=TA_CENTER, color=colors.black)
        ]
    ], colWidths=[22*mm, 16*mm, 16*mm, 18*mm], rowHeights=[9*mm])
    gstin_row.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    right_part = Table([
        [upper_block],
        [gstin_row]
    ], colWidths=[72*mm], rowHeights=[43*mm, 9*mm])
    right_part.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # Combine Left and Right into wrapper_table
    wrapper_table = Table([
        [left_part, right_part]
    ], colWidths=[110*mm, 72*mm], rowHeights=[52*mm])
    wrapper_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # ── 5. Footer (32mm height total)
    left_footer = Table([
        [P('RECEIVED ABOVE SHIPMENT IN ORDER AND GOOD CONDITION', 5, bold=True, align=TA_CENTER, color=FDC_GREEN), ''],
        [P('EMP ID.', 5.5, bold=True, color=FDC_GREEN), P('SIGN & STAMP', 5.5, bold=True, color=FDC_GREEN)],
        [P('', 5), P('', 5)],
        [P('NAME:', 5.5, bold=True, color=FDC_GREEN), P('', 5)],
        [P('PHONE:', 5.5, bold=True, color=FDC_GREEN), P('', 5)]
    ], colWidths=[28*mm, 47*mm], rowHeights=[5*mm, 5*mm, 5*mm, 8.5*mm, 8.5*mm])
    left_footer.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('SPAN', (0,0), (1,0)),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#dce2f9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('VALIGN', (0,1), (-1,2), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    spec_inst_box = Table([
        [P('[  ] LIABILITY LIMITED TO RS 1000/- ONLY.', 5.5, color=colors.black)],
        [P("[  ] WE CARRY UNDER CARRIER'S ACT", 5.5, color=colors.black)]
    ], colWidths=[35*mm], rowHeights=[13.5*mm, 13.5*mm])
    spec_inst_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    middle_footer = Table([
        [P('SPECIAL INSTRUCTIONS', 5.5, bold=True, align=TA_CENTER, color=FDC_GREEN)],
        [spec_inst_box]
    ], colWidths=[35*mm], rowHeights=[5*mm, 27*mm])
    middle_footer.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dce2f9')),
        ('LEFTPADDING', (0,1), (-1,1), 0),
        ('RIGHTPADDING', (0,1), (-1,1), 0),
        ('TOPPADDING', (0,1), (-1,1), 0),
        ('BOTTOMPADDING', (0,1), (-1,1), 0),
    ]))

    terms_para = Paragraph(
        "I/we hereby agree to terms setout on reverse and declare contents are true and correct, to-pay Freight has our consent and will be paid by consignee at delivery.",
        style(4.2, leading=5, color=colors.black)
    )
    
    consignor_sign = Table([
        [P("CONSIGNOR'S SIGN", 5.5, align=TA_RIGHT, color=colors.black)],
        [P("NAME:", 5.5, align=TA_LEFT, color=colors.black)]
    ], colWidths=[72*mm], rowHeights=[5.5*mm, 5.5*mm])
    consignor_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    incharge_date = Table([
        [P("BOOKING INCHARGE", 5.5, bold=True, color=colors.black), P("DATE & TIME:", 5.5, bold=True, color=colors.black)]
    ], colWidths=[36*mm, 36*mm], rowHeights=[10*mm])
    incharge_date.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    right_footer = Table([
        [terms_para],
        [consignor_sign],
        [incharge_date]
    ], colWidths=[72*mm], rowHeights=[11*mm, 11*mm, 10*mm])
    right_footer.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 1),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))

    footer_row = Table([
        [left_footer, middle_footer, right_footer]
    ], colWidths=[75*mm, 35*mm, 72*mm], rowHeights=[32*mm])
    footer_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # Assembling the main form (182mm wide, 128mm tall)
    form_table = Table([
        [header_row],
        [origin_dest_row],
        [address_row],
        [wrapper_table],
        [Spacer(1, 1*mm)],
        [footer_row]
    ], colWidths=[182*mm])
    form_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    def make_page(copy_label):
        left_margin_text = ""
        
        right_lbl_style = ParagraphStyle(
            name=f'right_lbl_{copy_label.replace(" ", "_")}',
            fontSize=6,
            leading=7.5,
            alignment=TA_CENTER,
            textColor=FDC_GREEN,
            fontName='Helvetica-Bold'
        )
        right_margin_text = RotatedText(copy_label, right_lbl_style)
        
        page_table = Table([
            [left_margin_text, form_table, right_margin_text]
        ], colWidths=[6*mm, 182*mm, 6*mm], rowHeights=[128*mm])
        page_table.setStyle(TableStyle([
            ('BOX', (0,0),(-1,-1), 1.5, FDC_GREEN),
            ('INNERGRID', (0,0),(-1,-1), 1.0, FDC_GREEN),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0),(-1,-1), 'CENTER'),
            ('LEFTPADDING', (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
            ('TOPPADDING', (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
        ]))
        return page_table

    elements = []
    # Generate 2 copies on a single portrait page with a 9mm Spacer
    elements.append(make_page('CONSIGNOR COPY'))
    elements.append(Spacer(1, 9*mm))
    elements.append(make_page('CONSIGNEE COPY'))

    doc.build(elements)
    input3.seek(0)
    return input3.read()
