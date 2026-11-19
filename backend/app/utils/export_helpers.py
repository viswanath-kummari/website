import io
import csv
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def export_to_csv(data_list: list, fieldnames: list = None) -> bytes:
    """Exports list of dictionaries to CSV byte string."""
    output = io.StringIO()
    if not data_list:
        return b""
    if not fieldnames:
        fieldnames = list(data_list[0].keys())
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data_list:
        filtered_row = {k: row.get(k, '') for k in fieldnames}
        writer.writerow(filtered_row)
    return output.getvalue().encode('utf-8')

def export_to_excel(data_list: list) -> bytes:
    """Exports list of dictionaries to Excel (.xlsx) bytes via pandas."""
    output = io.BytesIO()
    if not data_list:
        df = pd.DataFrame([{"Message": "No data available"}])
    else:
        df = pd.DataFrame(data_list)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

def generate_invoice_pdf(sale_data: dict) -> bytes:
    """
    Generates a professional retail invoice PDF for Fresh Cut Meat Shop.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    story = []

    # Shop Header
    shop = sale_data.get('shop', {})
    shop_title = shop.get('shop_name', 'Fresh Cut Meat Shop')
    tagline = shop.get('tagline', 'Premium Fresh Meat & Poultry')
    phone = shop.get('phone', '+91 98765 43210')
    address = shop.get('address', 'Market Main Road, Hyderabad')

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#202522'),
        alignment=1
    )
    tagline_style = ParagraphStyle(
        'InvoiceTagline',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#D97745'),
        alignment=1
    )
    address_style = ParagraphStyle(
        'InvoiceAddress',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555'),
        alignment=1
    )

    story.append(Paragraph(shop_title, title_style))
    story.append(Paragraph(tagline, tagline_style))
    story.append(Paragraph(f"{address} | Tel: {phone}", address_style))
    story.append(Spacer(1, 15))

    # Invoice & Customer Details
    inv_num = sale_data.get('invoice_number', 'INV-0000')
    date_str = str(sale_data.get('created_at', ''))[:19]
    cust_name = sale_data.get('customer_name', 'Counter Walk-in')
    cust_phone = sale_data.get('customer_phone') or 'N/A'
    pay_method = sale_data.get('payment_method', 'Cash')

    info_data = [
        [f"Invoice No: {inv_num}", f"Date: {date_str}"],
        [f"Customer: {cust_name}", f"Phone: {cust_phone}"],
        [f"Payment Mode: {pay_method}", f"Status: PAID"]
    ]
    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#202522')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7F4ED'))
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Items Table
    items_header = ['#', 'Item Description', 'Category', 'Qty & Unit', 'Rate (₹)', 'Amount (₹)']
    table_rows = [items_header]

    for idx, it in enumerate(sale_data.get('items', []), start=1):
        p_name = it.get('product_name', 'Item')
        cat = it.get('category', '')
        qty = f"{float(it.get('quantity', 0)):.3f} {it.get('unit', 'KG')}"
        rate = f"₹{float(it.get('unit_price', 0)):.2f}"
        tot = f"₹{float(it.get('line_total', 0)):.2f}"
        table_rows.append([str(idx), p_name, cat, qty, rate, tot])

    # Subtotals & Grand Total
    subtotal = float(sale_data.get('subtotal', 0))
    discount = float(sale_data.get('discount', 0))
    tax = float(sale_data.get('tax_amount', 0))
    grand_total = float(sale_data.get('grand_total', 0))

    table_rows.append(['', '', '', '', 'Subtotal:', f"₹{subtotal:.2f}"])
    if discount > 0:
        table_rows.append(['', '', '', '', 'Discount:', f"-₹{discount:.2f}"])
    if tax > 0:
        table_rows.append(['', '', '', '', 'Tax:', f"₹{tax:.2f}"])
    table_rows.append(['', '', '', '', 'Grand Total:', f"₹{grand_total:.2f}"])

    items_table = Table(table_rows, colWidths=[30, 200, 100, 70, 60, 60])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#202522')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (4,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-len(table_rows)+len(sale_data.get('items', []))+1), 0.5, colors.HexColor('#DDDDDD')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('FONTNAME', (4,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (4,-1), (-1,-1), 11),
        ('TEXTCOLOR', (4,-1), (-1,-1), colors.HexColor('#D97745'))
    ]))
    story.append(items_table)
    story.append(Spacer(1, 20))

    # Footer note
    footer_text = shop.get('invoice_footer_message', 'Thank you for shopping at Fresh Cut Meat Shop!')
    story.append(Paragraph(footer_text, ParagraphStyle(
        'FooterStyle', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.HexColor('#666666')
    )))

    doc.build(story)
    return buffer.getvalue()

