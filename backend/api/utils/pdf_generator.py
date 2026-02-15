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
    company_name = Paragraph('<b><font color="#1e3a8a">FDC</font> <font color="#c41e3a">Couriers and Cargo</font></b>', title_style)
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
        if item.get('pieces') or item.get('weight'):
            party_text += f"<br/><font size=8>Pcs: {item['pieces']} | Wt: {item['weight']} kg</font>"
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
    company_name = Paragraph('<b><font color="#1e3a8a">FDC</font> <font color="#c41e3a">Couriers and Cargo</font></b>', title_style)
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
    
    
    # AWB Table with Pieces and Weight
    awb_table_data = [['#', 'AWB Number', 'Barcode', 'Pcs', 'Wt (kg)']]
    
    for idx, awb_item in enumerate(manifest_data.get('awb_list', []), 1):
        awb_number = awb_item['awb_number']
        pcs = awb_item.get('pcs', 0)
        wt = awb_item.get('wt', 0.0)
        
        # AWB barcode
        awb_barcode_buffer = generate_barcode_image(awb_number)
        if awb_barcode_buffer:
            awb_barcode_img = Image(awb_barcode_buffer, width=50*mm, height=10*mm)
            barcode_cell = awb_barcode_img
        else:
            barcode_cell = ''
        
        awb_table_data.append([
            str(idx),
            Paragraph(awb_number, styles['Normal']),
            barcode_cell,
            str(pcs),
            f"{wt:.2f}"
        ])
    
    awb_table = Table(awb_table_data, colWidths=[12*mm, 60*mm, 70*mm, 20*mm, 28*mm])
    awb_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (4, -1), 'CENTER'),  # Center align Pcs and Wt columns
        
        # All cells
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
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
            
            # Try to get booking details for pieces and weight
            try:
                from ..models import BookingDetails
                booking = BookingDetails.objects.filter(awbno=awb_no).first()
                if booking:
                    pcs = booking.pcs or 0
                    wt = float(booking.wt) if booking.wt else 0.0
            except:
                pass
            
            awb_list.append({
                'awb_number': awb_no,
                'pcs': pcs,
                'wt': wt
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
