"""
PDF Generation Utility for DRS and Manifest Documents using ReportLab
Generates PDF on-demand without cloud storage
"""

import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import cloudinary
import cloudinary.uploader
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64


def generate_barcode_image(data, barcode_type='code128'):
    """
    Generate barcode as PIL Image
    
    Args:
        data: Data to encode in barcode
        barcode_type: Type of barcode (default: code128)
    
    Returns:
        BytesIO buffer containing barcode image
    """
    try:
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_instance = barcode_class(str(data), writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer, options={
            'write_text': False,
            'module_height': 10,
            'module_width': 0.2,
            'quiet_zone': 1
        })
        buffer.seek(0)
        return buffer
    except Exception:
        # Silently fail on barcode error to prevent stdout pollution
        return None


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
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    # Header Section
    header_data = []
    
    # Company name
    company_name = Paragraph('<b><font color="#2e7d32">FDC</font> <font color="#1b5e20">Couriers and Cargo</font></b>', title_style)
    tagline = Paragraph('Fast, Reliable, Trusted Delivery Services', subtitle_style)
    
    # Branch info
    branch_info = Paragraph(f'<b>{drs_data["branch_name"]}</b><br/>{drs_data["branch_address"]}', styles['Normal'])
    
    # DRS Barcode
    drs_barcode_buffer = generate_barcode_image(drs_data['drs_number'])
    drs_barcode_img = None
    if drs_barcode_buffer:
        drs_barcode_img = Image(drs_barcode_buffer, width=80*mm, height=15*mm)
    
    drs_info = Paragraph(f'<b>{drs_data["drs_number"]}</b><br/>Page: 1', 
                         ParagraphStyle('DRSInfo', parent=styles['Normal'], alignment=TA_RIGHT))
    
    # Create header table
    header_table_data = [
        [company_name, ''],
        [tagline, ''],
        [branch_info, drs_barcode_img if drs_barcode_img else ''],
        ['', drs_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[120*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('LINEBELOW', (0, 3), (-1, 3), 2, colors.black),
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
    awb_table_data = [['#', 'Center', 'Doc No', 'Party Name', 'Signature']]
    
    for idx, item in enumerate(drs_data.get('awb_items', []), 1):
        # Center column with STD and remarks
        center_text = f"{item['center']}<br/><font size=8>STD: {item['doc_type']}</font>"
        # Add Pcs and Wt
        if item.get('pieces') or item.get('weight'):
             center_text += f"<br/><font size=8>Pcs: {item['pieces']} | Wt: {item['weight']}</font>"
        
        if item.get('remarks'):
            center_text += f"<br/><font size=8><i>Remarks: {item['remarks']}</i></font>"
        center_cell = Paragraph(center_text, styles['Normal'])
        
        
        # Doc No with barcode
        awb_barcode_buffer = generate_barcode_image(item['awb_number'])
        if awb_barcode_buffer:
            awb_barcode_img = Image(awb_barcode_buffer, width=40*mm, height=10*mm)
            doc_cell = [Paragraph(item['awb_number'], styles['Normal']), awb_barcode_img]
        else:
            doc_cell = Paragraph(item['awb_number'], styles['Normal'])
        
        # Party details
        party_text = f"<b>{item['party_name']}</b><br/><font size=8>{item['party_phone']}</font>"
        # if item.get('pieces') or item.get('weight'):
            # party_text += f"<br/><font size=8>Pcs: {item['pieces']} | Wt: {item['weight']} kg</font>"
        party_cell = Paragraph(party_text, styles['Normal'])
        
        awb_table_data.append([
            str(idx),
            center_cell,
            doc_cell,
            party_cell,
            ''
        ])
    
    awb_table = Table(awb_table_data, colWidths=[10*mm, 35*mm, 50*mm, 65*mm, 30*mm])
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
                awb_items.append({
                    'center': booking.destination_code or branch_name,
                    'doc_type': booking.doc_type or 'NON-DOX',
                    'awb_number': awb,
                    'party_name': booking.recievername or '',
                    'party_phone': booking.recieverphonenumber or '',
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
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    # Header Section
    company_name = Paragraph('<b><font color="#2e7d32">FDC</font> <font color="#2e7d32">Couriers and Cargo</font></b>', title_style)
    tagline = Paragraph('Fast, Reliable, Trusted Delivery Services', subtitle_style)
    
    # Origin info
    origin_info = Paragraph(f'<b>Origin:</b> {manifest_data["origin"]}<br/>{manifest_data.get("origin_address", "")}', styles['Normal'])
    
    # Manifest Barcode
    manifest_barcode_buffer = generate_barcode_image(manifest_data['manifest_number'])
    manifest_barcode_img = None
    if manifest_barcode_buffer:
        manifest_barcode_img = Image(manifest_barcode_buffer, width=80*mm, height=15*mm)
    
    manifest_info = Paragraph(f'<b>{manifest_data["manifest_number"]}</b><br/>Page: 1', 
                             ParagraphStyle('ManifestInfo', parent=styles['Normal'], alignment=TA_RIGHT))
    
    # Create header table
    header_table_data = [
        [company_name, ''],
        [tagline, ''],
        [origin_info, manifest_barcode_img if manifest_barcode_img else ''],
        ['', manifest_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[120*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('LINEBELOW', (0, 3), (-1, 3), 2, colors.black),
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
    
    
    # AWB Table with Sender, Destination, Pieces and Weight
    awb_table_data = [['#', 'AWB No', 'Sender', 'Dest', 'Pcs', 'Wt']]
    
    for idx, awb_item in enumerate(manifest_data.get('awb_list', []), 1):
        awb_number = awb_item['awb_number']
        pcs = awb_item.get('pcs', 0)
        wt = awb_item.get('wt', 0.0)
        sender = awb_item.get('sender', '')
        destination = awb_item.get('destination', '')
        
        # Truncate sender if too long
        if len(sender) > 20:
            sender = sender[:18] + '..'
            
        awb_table_data.append([
            str(idx),
            Paragraph(awb_number, styles['Normal']),
            Paragraph(sender, styles['Normal']),
            Paragraph(destination, styles['Normal']),
            str(pcs),
            f"{wt:.2f}"
        ])
    
    # Adjusted column widths for new layout
    awb_table = Table(awb_table_data, colWidths=[10*mm, 35*mm, 85*mm, 20*mm, 15*mm, 25*mm])
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
            destination = ""
            
            # Try to get booking details for pieces and weight
            try:
                from ..models import BookingDetails
                booking = BookingDetails.objects.filter(awbno=awb_no).first()
                if booking:
                    pcs = booking.pcs or 0
                    wt = float(booking.wt) if booking.wt else 0.0
                    sender = booking.sendername or ""
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


# ==================== BOOKING PDF GENERATION ====================
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


def generate_barcode_image(awb_number, width=160*mm, height=15*mm):
    """Generate barcode as BytesIO PNG image"""
    try:
        from reportlab.graphics.barcode import code128
        from reportlab.pdfgen import canvas as rl_canvas
        import tempfile, os, subprocess

        tmp_pdf = tempfile.mktemp(suffix='.pdf')
        c = rl_canvas.Canvas(tmp_pdf, pagesize=(width, height))
        barcode = code128.Code128(awb_number, barWidth=1.2, barHeight=height * 0.75, humanReadable=False)
        barcode.drawOn(c, (width - barcode.width) / 2, height * 0.1)
        c.save()

        tmp_png_base = tempfile.mktemp()
        subprocess.run(['pdftoppm', '-r', '150', '-png', '-singlefile', tmp_pdf, tmp_png_base], capture_output=True)
        os.unlink(tmp_pdf)
        
        png_path = tmp_png_base + '.png'
        if os.path.exists(png_path):
            data = open(png_path, 'rb').read()
            os.unlink(png_path)
            return BytesIO(data)
        return None
    except Exception as e:
        print(f"Barcode error: {e}")
        return None


from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from reportlab.platypus.flowables import Flowable
from reportlab.graphics.barcode import code128

class BarcodeFlowable(Flowable):
    """Pure ReportLab barcode - no external tools, works on Windows & Linux."""
    def __init__(self, awb_number, total_width=190*mm, bar_height=14*mm):
        Flowable.__init__(self)
        self.awb_number = awb_number
        self.width = total_width
        self.height = bar_height

    def draw(self):
        barcode = code128.Code128(
            self.awb_number,
            barWidth=1.1,
            barHeight=self.height,
            humanReadable=False
        )
        x_offset = (self.width - barcode.width) / 2
        barcode.drawOn(self.canv, x_offset, 0)

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.barcode import code128


class BarcodeFlowable(Flowable):
    """Pure ReportLab barcode - no external tools, works on Windows & Linux."""
    def __init__(self, awb_number, total_width=190*mm, bar_height=14*mm):
        Flowable.__init__(self)
        self.awb_number = awb_number
        self.width = total_width
        self.height = bar_height

    def draw(self):
        barcode = code128.Code128(
            self.awb_number,
            barWidth=1.1,
            barHeight=self.height,
            humanReadable=False
        )
        x_offset = (self.width - barcode.width) / 2
        barcode.drawOn(self.canv, x_offset, 0)


def P(text, size=8, bold=False, align=TA_CENTER, leading=None):
    return Paragraph(
        text,
        ParagraphStyle(
            '_',
            fontName='Helvetica-Bold' if bold else 'Helvetica',
            fontSize=size,
            leading=leading or (size + 2),
            alignment=align
        )
    )

from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128


class BarcodeFlowable(Flowable):
    def __init__(self, value, total_width, bar_height=12*mm):
        Flowable.__init__(self)
        self.value = value
        self.width = total_width
        self.height = bar_height

    def draw(self):
        bc = code128.Code128(self.value, barWidth=0.9,
                             barHeight=self.height, humanReadable=False)
        bc.drawOn(self.canv, (self.width - bc.width) / 2, 0)


def P(text, size=8, bold=False, align=TA_LEFT, leading=None, color=colors.black):
    return Paragraph(text, ParagraphStyle(
        '_', fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size, leading=leading or (size * 1.25),
        alignment=align, textColor=color,
    ))


LGREY = colors.Color(0.88, 0.88, 0.88)
GRID = [
    ('GRID',          (0,0), (-1,-1), 0.5, colors.black),
    ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING',    (0,0), (-1,-1), 1),
    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ('LEFTPADDING',   (0,0), (-1,-1), 2),
    ('RIGHTPADDING',  (0,0), (-1,-1), 2),
]


from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas as rl_canvas


class BarcodeFlowable(Flowable):
    def __init__(self, value, total_width, bar_height=10*mm):
        Flowable.__init__(self)
        self.value = value
        self.width = total_width
        self.height = bar_height

    def draw(self):
        bc = code128.Code128(self.value, barWidth=0.85,
                             barHeight=self.height, humanReadable=False)
        bc.drawOn(self.canv, (self.width - bc.width) / 2, 0)


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


def generate_booking_pdf(booking_data):
    buffer = BytesIO()

    # A4 portrait: usable = 210-8-8 = 194mm wide, 297-3-3 = 291mm tall
    # 3 slips + 2 gaps of 1mm = 289mm → each slip ~96mm tall
    W  = 194 * mm
    SH = 95  * mm   # slip height

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=3*mm, bottomMargin=3*mm,
        leftMargin=8*mm, rightMargin=8*mm,
    )

    awb   = booking_data.get('awb_number', '')
    org   = booking_data.get('origin_name', '').upper()
    dst   = booking_data.get('destination_name', '').upper()
    sn    = booking_data.get('sender_name', '')
    sa    = booking_data.get('sender_address', '')
    sp    = booking_data.get('sender_phone', '')
    rn    = booking_data.get('receiver_name', '')
    ra    = booking_data.get('receiver_address', '')
    rp    = booking_data.get('receiver_phone', '')
    dt    = booking_data.get('date', '')
    tm    = booking_data.get('time', '')
    pcs   = str(booking_data.get('pieces', ''))
    wt    = str(booking_data.get('weight', ''))
    cont  = str(booking_data.get('contents', ''))
    amt   = str(booking_data.get('amount', ''))
    bookingbranch = booking_data.get('booked_branch_address', '')

    # ── Panel widths ──────────────────────────────────────────────────────────
    # Image: left ~58% right ~42%
    LP = 112 * mm
    RP = W - LP   # 82mm

    def make_slip(copy_label):

        # ════════════════════════════════════════════════════════════════════
        # LEFT PANEL
        # ════════════════════════════════════════════════════════════════════

        # ── L1: Branding row ─────────────────────────────────────────────────
        # [icon 12mm | FDC COURIER & CARGO large]
        brand = Table([[
            P('✈', 14, bold=True, align=TA_CENTER),
            Paragraph(
                '<b><font size=11>FDC COURIER &amp; CARGO</font></b><br/>'
                '<font size=7>(LOCAL &amp; DOMESTIC CARGO SERVICES)</font><br/>'
                f'<font size=8>Booked Branch: <b>{bookingbranch}</b></font>',
                style(8, leading=13, align=TA_LEFT)
            ),
           
        ]], colWidths=[12*mm, LP-12*mm], rowHeights=[18*mm])
        brand.setStyle(TableStyle([
            ('BOX',          (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
            ('LEFTPADDING',  (0,0),(-1,-1), 2),
        ]))

        # ── L2: CONSIGNOR label ──────────────────────────────────────────────
        consignor_label = Table([[
            P('CONSIGNOR', 9, bold=True, align=TA_CENTER),
        ]], colWidths=[LP], rowHeights=[6*mm])
        consignor_label.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0),(-1,-1), 2),
            ('TOPPADDING',  (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── L3: Consignor address (tall blank writing area) ──────────────────
        consignor_info = Table([[
            Paragraph(
                f'<b>{sn}</b><br/>{sa}' if sn else '',
                style(11, leading=9.5, align=TA_CENTER)
            ),
        ]], colWidths=[LP], rowHeights=[15*mm])
        consignor_info.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
            ('TOPPADDING',  (0,0),(-1,-1), 3),
            ('LEFTPADDING', (0,0),(-1,-1), 3),
        ]))
        # booked_branch_label = Table([[
        #     P('BOOKED BRANCH', 9, bold=True, align=TA_LEFT),
        # ]], colWidths=[LP], rowHeights=[6*mm])
        # booked_branch_label.setStyle(TableStyle([
        #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
        #     ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        #     ('LEFTPADDING', (0,0),(-1,-1), 2),
        #     ('TOPPADDING',  (0,0),(-1,-1), 1),
        #     ('BOTTOMPADDING',(0,0),(-1,-1),1),
        # ]))
        # booked_branch_info = Table([[
        #     Paragraph(
        #         f'<b>{bookingbranch}</b>' if bookingbranch else '',
        #         style(7, leading=9.5, align=TA_LEFT)
        #     ),
        # ]], colWidths=[LP], rowHeights=[5*mm])
        # booked_branch_info.setStyle(TableStyle([
        #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
        #     ('VALIGN', (0,0),(-1,-1), 'TOP'),
        #     ('TOPPADDING',  (0,0),(-1,-1), 1),
        #     ('LEFTPADDING', (0,0),(-1,-1), 3),
        # ]))

        # ── L4: Barcode ──────────────────────────────────────────────────────
        bc = Table([
            [BarcodeFlowable(awb, total_width=LP, bar_height=11*mm)],
            [P(f'* {awb} *', 14, bold=True, align=TA_CENTER)],
        ], colWidths=[LP], rowHeights=[12*mm, 5*mm])
        bc.setStyle(TableStyle([
            ('BOX',      (0,0),(-1,-1), 0.5, colors.black),
            ('LINEABOVE',(0,1),(0,1),   0.5, colors.black),
            ('ALIGN',    (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',   (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
        ]))

        # ── L5: Footer ───────────────────────────────────────────────────────
        # Matches image exactly:
        # [small warrant text] | Date | Time | Amount Rs. |        |
        #                      |      |      | GST        |        |
        #                      | Recd By     | Total Rs.  |        |
        #                      | FDC         | CASH | CREDIT       |
        # [Sender Signature]
        warrant = Paragraph(' ', style(4.5, leading=6))
        sig = Paragraph('Sender Signature', style(5, align=TA_CENTER))

        # col widths must sum to LP=112mm
        # [warrant+sig=24mm | date=18 | time=18 | amt=22 | cash=15 | credit=15]
        fc = [24*mm, 18*mm, 18*mm, 22*mm, 15*mm, 15*mm]

        footer = Table([
            # row0: warrant | Date(hdr) | Time(hdr) | Amount Rs(hdr) | blank | blank
            [warrant,
             P('Date',       6, bold=True, align=TA_CENTER),
             P('Time',       6, bold=True, align=TA_CENTER),
             P('Amount Rs.', 6, bold=True, align=TA_CENTER),
             P('', 6), P('', 6)],
            # row1: '' | date val | time val | blank | blank | blank
            ['',
             P(dt, 7, align=TA_CENTER),
             P(tm, 7, align=TA_CENTER),
             P('', 7), P('', 7), P('', 7)],
            # row2: '' | '' | '' | GST(hdr) | blank | blank
            ['', '', '',
             P('GST', 6, bold=True, align=TA_CENTER),
             P('', 6), P('', 6)],
            # row3: '' | Recd By(hdr, span2) | Total Rs(hdr) | blank | blank
            ['',
             P('Recd By', 6, bold=True, align=TA_CENTER),
             P('', 6),
             P('Total Rs.', 6, bold=True, align=TA_CENTER),
             P('', 6), P('', 6)],
            # row4: sig | FDC(span2) | CASH | CREDIT | blank
            [sig,
             P('FDC', 7, bold=True, align=TA_CENTER),
             P('', 6),
             P('CASH',   7, bold=True, align=TA_CENTER),
             P('CREDIT', 7, bold=True, align=TA_CENTER),
             P('', 6)],
        ], colWidths=fc, rowHeights=[5*mm, 4*mm, 4*mm, 4*mm, 5*mm])

        footer.setStyle(TableStyle([
            ('BOX',          (0,0),(-1,-1), 0.5, colors.black),
            # vertical dividers between main columns
            ('LINEAFTER',    (0,0),(0,-1),  0.5, colors.black),
            ('LINEAFTER',    (1,0),(2,-1),  0.5, colors.black),  # after time col
            ('LINEAFTER',    (3,0),(3,-1),  0.5, colors.black),
            ('LINEAFTER',    (4,0),(4,-1),  0.5, colors.black),
            # horizontal line below header row
            ('LINEBELOW',    (1,0),(5,0),   0.5, colors.black),
            ('LINEBELOW',    (1,2),(5,2),   0.5, colors.black),
            ('LINEBELOW',    (1,3),(5,3),   0.5, colors.black),
            # spans
            ('SPAN', (0,0),(0,4)),   # warrant text full height
            ('SPAN', (1,1),(1,2)),   # date value spans rows 1-2
            ('SPAN', (2,1),(2,2)),   # time value spans rows 1-2
            ('SPAN', (1,3),(2,3)),   # Recd By header spans cols 1-2
            ('SPAN', (1,4),(2,4)),   # FDC value spans cols 1-2
            # backgrounds
            ('BACKGROUND',   (1,0),(3,0),   LGREY),
            ('BACKGROUND',   (1,3),(2,3),   LGREY),
            ('BACKGROUND',   (3,2),(3,2),   LGREY),
            ('BACKGROUND',   (3,3),(3,3),   LGREY),
            # alignment
            ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
            ('VALIGN',       (0,0),(0,0),   'TOP'),
            ('ALIGN',        (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
            ('LEFTPADDING',  (0,0),(-1,-1), 1),
            ('RIGHTPADDING', (0,0),(-1,-1), 1),
        ]))

        left = Table([
            [brand],
            [consignor_label],
            [consignor_info],
            # [booked_branch_label],
            # [booked_branch_info],
            [bc],
            [footer],
        ], colWidths=[LP])
        left.setStyle(TableStyle([
            ('TOPPADDING',   (0,0),(-1,-1), 0),
            ('BOTTOMPADDING',(0,0),(-1,-1), 0),
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))

        # ════════════════════════════════════════════════════════════════════
        # RIGHT PANEL
        # ════════════════════════════════════════════════════════════════════

        # ── R1: CARGO CONSIGNMENT NOTE header (grey bg) ──────────────────────
        r_title = Table([[
            P(copy_label, 7, bold=True, align=TA_CENTER),
        ]], colWidths=[RP], rowHeights=[5*mm])
        r_title.setStyle(TableStyle([
            ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0),(-1,-1), LGREY),
            ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R2: SURFACE BOOKING | ORIGIN | DESTN (grey bg header) ───────────
        # col widths inside RP=82mm: [42 | 22 | 18]
        r_hdr = Table([[
            P('', 7, bold=True, align=TA_CENTER),
            P('ORIGIN',          7, bold=True, align=TA_CENTER),
            P('DESTN',           7, bold=True, align=TA_CENTER),
        ]], colWidths=[10*mm, 36*mm, 36*mm], rowHeights=[5*mm])
        r_hdr.setStyle(TableStyle([
            ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
            ('LINEAFTER', (0,0),(1,-1),  0.5, colors.black),
            ('BACKGROUND',(0,0),(-1,-1), LGREY),
            ('VALIGN',    (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R3: blank | ORIGIN city large | DESTN city ──────────────────────
        r_cities = Table([[
            P('Surface', 4),
            P(f'<b>{org}</b>', 10, align=TA_CENTER),
            P(f'<b>{dst}</b>', 10, align=TA_CENTER),
        ]], colWidths=[10*mm, 36*mm, 36*mm], rowHeights=[8*mm])
        r_cities.setStyle(TableStyle([
            ('BOX',      (0,0),(-1,-1), 0.5, colors.black),
            ('LINEAFTER',(0,0),(1,-1),  0.5, colors.black),
            ('VALIGN',   (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R4: CONSIGNEE label ──────────────────────────────────────────────
        r_conslabel = Table([[
            P('CONSIGNEE', 9 , bold=True, align=TA_CENTER),
        ]], colWidths=[RP], rowHeights=[6*mm])
        r_conslabel.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1), 2),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R5: Consignee address blank writing area ─────────────────────────
        r_consinfo = Table([[
            Paragraph(
                f'<b>{rn}</b><br/>{ra}' if rn else '',
                style(11, leading=9.5, align=TA_CENTER)
            ),
        ]], colWidths=[RP], rowHeights=[24*mm])
        r_consinfo.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
            ('TOPPADDING', (0,0),(-1,-1), 3),
            ('LEFTPADDING',(0,0),(-1,-1), 3),
        ]))

        # ── R6: Phone | Pincode ──────────────────────────────────────────────
        r_phone = Table([[
            P(f'Phone :{rp}',   7, align=TA_LEFT),
            P(f'Pincode :', 7, align=TA_LEFT),
        ]], colWidths=[RP*0.55, RP*0.45], rowHeights=[5*mm])
        r_phone.setStyle(TableStyle([
            # ('LINEBEFORE',  (0,0),(0,-1),  0, colors.black),
            # ('LINEAFTER',   (-1,0),(-1,-1),0, colors.black),
            # ('LINEBELOW',   (0,-1),(-1,-1),0, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1), 3),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R7: Terms text (small italic) ────────────────────────────────────
        # r_terms = Table([[
        #     Paragraph(
        #         '',
        #         style(4.5, leading=6, align=TA_LEFT)
        #     ),
        # ]], colWidths=[RP], rowHeights=[9*mm])
        # r_terms.setStyle(TableStyle([
        #     ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
        #     ('VALIGN', (0,0),(-1,-1), 'TOP'),
        #     ('TOPPADDING', (0,0),(-1,-1), 2),
        #     ('LEFTPADDING',(0,0),(-1,-1), 2),
        # ]))

        # ── R8: Declared Value | Contents | No Pieces | Weight (grey header) ─
        cw8 = [RP*0.27, RP*0.27, RP*0.23, RP*0.23]
        r_sumhdr = Table([[
            P('Declared Value', 6, bold=True, align=TA_CENTER),
            P('Contents',       6, bold=True, align=TA_CENTER),
            P('No Pieces',      6, bold=True, align=TA_CENTER),
            P('Weight',         6, bold=True, align=TA_CENTER),
        ]], colWidths=cw8, rowHeights=[5*mm])
        r_sumhdr.setStyle(TableStyle([
            ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
            ('INNERGRID',  (0,0),(-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0),(-1,-1), LGREY),
            ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R9: Summary values ───────────────────────────────────────────────
        r_sumval = Table([[
            P(amt,  7, align=TA_CENTER),
            P(cont, 7, align=TA_CENTER),
            P(pcs,  7, align=TA_CENTER),
            P(f'{wt} kg', 7, align=TA_CENTER),
        ]], colWidths=cw8, rowHeights=[6*mm])
        r_sumval.setStyle(TableStyle([
            ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN',    (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R10: Self Cheques prohibited (grey) ──────────────────────────────
        r_prohib = Table([[
            P('Self Cheques, Jewellery, Cell Phones & Cash is Strictly Prohibited',
              6, bold=True, align=TA_CENTER),
        ]], colWidths=[RP], rowHeights=[5*mm])
        r_prohib.setStyle(TableStyle([
            ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0),(-1,-1), LGREY),
            ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R11: THANKS FOR UTILISING OUR SERVICES ───────────────────────────
        r_thanks = Table([[
            P('Signature', 6, bold=True, align=TA_CENTER),
        ]], colWidths=[RP], rowHeights=[5*mm])
        r_thanks.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        # ── R12: SHIPPER COPY large ───────────────────────────────────────────
        r_copy = Table([[
            P('', 14, bold=True, align=TA_CENTER),
        ]], colWidths=[RP], rowHeights=[10*mm])
        r_copy.setStyle(TableStyle([
            ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),1),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))

        right = Table([
            [r_title],
            [r_hdr],
            [r_cities],
            [r_conslabel],
            [r_consinfo],
            [r_phone],
            # [r_terms],
            [r_sumhdr],
            [r_sumval],
            [r_prohib],
            [r_thanks],
            [r_copy],
        ], colWidths=[RP])
        right.setStyle(TableStyle([
            ('TOPPADDING',   (0,0),(-1,-1), 0),
            ('BOTTOMPADDING',(0,0),(-1,-1), 0),
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))

        # ── Combine into full slip ────────────────────────────────────────────
        slip = Table([[left, right]], colWidths=[LP, RP])
        slip.setStyle(TableStyle([
            ('BOX',     (0,0),(-1,-1), 1.0, colors.black),
            ('VALIGN',  (0,0),(-1,-1), 'TOP'),
            ('LINEAFTER',(0,0),(0,0),  1.0, colors.black),
            ('TOPPADDING',   (0,0),(-1,-1), 0),
            ('BOTTOMPADDING',(0,0),(-1,-1), 0),
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ]))

        return slip

    elements = []
    for i, label in enumerate(['SHIPPER COPY', 'POD COPY', 'OFFICE COPY']):
        elements.append(make_slip(label))
        if i < 2:
            elements.append(Spacer(1, 10*mm))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


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
        if HubDetails.objects.filter(hub_code=origin_code).exists():
            h = HubDetails.objects.get(hub_code=origin_code)
            branch_name_address = h.address
        elif BranchDetails.objects.filter(branch_code=origin_code).exists():
            b = BranchDetails.objects.get(branch_code=origin_code)
            branch_name_address = b.address
        # elif UserDetails.objects.filter(code=origin_code).exists():
        #     branch_name_address = UserDetails.objects.get(code=origin_code).code_name

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
            'amount':           getattr(booking, 'amount', ''),
            'booked_branch_address': branch_name_address,
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


