import io
import json
import webbrowser # Keep for local run
import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime as dt

# --- NEW IMPORTS ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# --- END NEW IMPORTS ---

# --- PLATYPUS IMPORTS ---
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

# --- FONT IMPORTS ---
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

app = Flask(__name__)

# --- CONFIGURATION FROM ENVIRONMENT VARIABLES ---
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///invoices_pro_users_test.db')
SECRET_KEY = os.environ.get('SECRET_KEY', 'a-default-fallback-secret-key-for-local-test')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Initialize Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info'

# -----------------------------
# DATABASE MODELS
# -----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    profile = db.relationship('CompanyProfile', backref='user', lazy=True, uselist=False, cascade="all, delete-orphan")
    customers = db.relationship('Customer', backref='user', lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship('Invoice', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def __repr__(self): return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

class CompanyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    gstin = db.Column(db.String(50), nullable=False)
    pan = db.Column(db.String(50))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    account_no = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(50))
    currency = db.Column(db.String(10), nullable=False, default='USD')
    date_format = db.Column(db.String(20), nullable=False, default='DD/MM/YYYY')
    terms_and_conditions = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    billing_address = db.Column(db.String(300), nullable=False)
    shipping_address = db.Column(db.String(300))
    gstin = db.Column(db.String(50))
    state = db.Column(db.String(50))
    contact_person = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invoices = db.relationship('Invoice', backref='customer_for_delete_check', lazy=True)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    po_number = db.Column(db.String(100))
    subtotal = db.Column(db.Float, nullable=False)
    total_gst = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    po_date = db.Column(db.String(50))
    eway_bill_no = db.Column(db.String(100))
    place_of_supply = db.Column(db.String(100))
    transport_name = db.Column(db.String(100))
    vehicle_no = db.Column(db.String(50))
    delivery_location = db.Column(db.String(200))
    profile_id = db.Column(db.Integer, db.ForeignKey('company_profile.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")
    profile = db.relationship('CompanyProfile')
    customer = db.relationship('Customer')
    status = db.Column(db.String(20), nullable=False, default='Draft') # Add this line
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    hsn = db.Column(db.String(50))
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    tax_percent = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def get_currency_symbol(currency_code): symbols = {'USD': '$', 'INR': '₹', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}; return symbols.get(currency_code, '$')

def format_date(date_str, format_str):
    if not date_str:
        return 'N/A'
    try:
        date_obj = dt.strptime(date_str, '%Y-%m-%d')
        if format_str == 'DD/MM/YYYY':
            return date_obj.strftime('%d/%m/%Y')
        if format_str == 'MM/DD/YYYY':
            return date_obj.strftime('%m/%d/%Y')
        if format_str == 'YYYY-MM-DD':
            return date_obj.strftime('%Y-%m-%d')
        return date_str # Fallback
    except ValueError:
        return date_str # Return original if parsing fails

import datetime # Add this near the top imports if not already there

@app.context_processor
def inject_helpers():
    logged_in_user = current_user if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
    return dict(
        get_currency_symbol=get_currency_symbol,
        format_date=format_date,
        current_user=logged_in_user,
        now=datetime.datetime.utcnow() # ADD THIS LINE
    )

# -----------------------------
# CORE APPLICATION ROUTES
# -----------------------------

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required # ADDED
def dashboard():
    profile = CompanyProfile.query.filter_by(user_id=current_user.id).first() # CHANGED

    if not profile:
         flash("Welcome! Please create your company profile to get started.", "info")
         return redirect(url_for('profile')) 

    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.date.desc()).all() # CHANGED
    return render_template('dashboard.html', invoices=invoices, profile=profile)


@app.route('/profile', methods=['GET', 'POST'])
@login_required # ADDED
def profile():
    profile = CompanyProfile.query.filter_by(user_id=current_user.id).first() # CHANGED

    if request.method == 'POST':
        if profile:
            # Update existing profile logic
            profile.name=request.form['name']; profile.address=request.form['address']; profile.gstin=request.form['gstin']; profile.pan=request.form['pan']; profile.email=request.form['email']; profile.phone=request.form['phone']; profile.bank_name=request.form['bank_name']; profile.account_no=request.form['account_no']; profile.ifsc_code=request.form['ifsc_code']; profile.currency=request.form['currency']; profile.date_format=request.form['date_format']; profile.terms_and_conditions=request.form['terms_and_conditions']
            flash("Profile updated successfully!", "success")
        else:
            # Create new profile logic, link to current user
            new_profile = CompanyProfile( 
                name = request.form['name'], address = request.form['address'], 
                gstin = request.form['gstin'], pan = request.form['pan'], 
                email = request.form['email'], phone = request.form['phone'], 
                bank_name = request.form['bank_name'], account_no = request.form['account_no'], 
                ifsc_code = request.form['ifsc_code'], currency = request.form['currency'], 
                date_format = request.form['date_format'], 
                terms_and_conditions = request.form['terms_and_conditions'], 
                user_id = current_user.id # CHANGED
            )
            db.session.add(new_profile)
            flash("Profile created successfully!", "success")
        try: db.session.commit()
        except Exception as e: db.session.rollback(); flash(f"Error saving profile: {e}", "error")
        return redirect(url_for('profile'))
    return render_template('profile.html', profile=profile)

@app.route('/customers')
@login_required # ADDED
def customer_management():
    customers = Customer.query.filter_by(user_id=current_user.id).all() # CHANGED
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required # ADDED
def add_customer():
    if request.method == 'POST':
        new_customer = Customer( 
            name=request.form['name'], 
            billing_address=request.form['billing_address'], 
            shipping_address=request.form.get('shipping_address', ''), 
            gstin=request.form.get('gstin', ''), 
            state=request.form.get('state', ''), 
            contact_person=request.form.get('contact_person', ''), 
            user_id = current_user.id # CHANGED
        )
        db.session.add(new_customer)
        try: db.session.commit(); flash(f"Customer '{new_customer.name}' added.", "success")
        except Exception as e: db.session.rollback(); flash(f"Error adding customer: {e}", "error")
        return redirect(url_for('customer_management'))
    return render_template('customer_form.html', customer={}, mode='add')

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required # ADDED
def edit_customer(customer_id):
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404() # CHANGED
    if request.method == 'POST':
        customer.name = request.form['name']; customer.billing_address = request.form['billing_address']; customer.shipping_address = request.form.get('shipping_address', ''); customer.gstin = request.form.get('gstin', ''); customer.state = request.form.get('state', ''); customer.contact_person = request.form.get('contact_person', '')
        try: db.session.commit(); flash(f"Customer '{customer.name}' updated.", "success")
        except Exception as e: db.session.rollback(); flash(f"Error updating customer: {e}", "error")
        return redirect(url_for('customer_management'))
    return render_template('customer_form.html', customer=customer, mode='edit')

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required # ADDED
def delete_customer(customer_id):
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first() # CHANGED
    if customer:
        if customer.invoices:
             flash(f"Cannot delete '{customer.name}'. Linked to invoices.", "error")
        else:
            try: db.session.delete(customer); db.session.commit(); flash(f"Customer '{customer.name}' deleted.", "success")
            except Exception as e: db.session.rollback(); flash(f"Error deleting customer: {e}", "error")
    else: flash("Customer not found or permission denied.", "error")
    return redirect(url_for('customer_management'))

@app.route('/invoice/add', methods=['GET', 'POST'])
@login_required # ADDED
def add_invoice():
    profile = CompanyProfile.query.filter_by(user_id=current_user.id).first() # CHANGED
    if not profile: flash("Please create profile first.", "warning"); return redirect(url_for('profile'))
    customers = Customer.query.filter_by(user_id=current_user.id).all() # CHANGED
    today = datetime.date.today().strftime('%Y-%m-%d')

    def rerender_form(error_msg="An error occurred.", customer_id_sel=None):
         flash(error_msg, "error")
         return render_template('invoice_form.html', customers=customers, profile=profile, today=today, invoice_data=request.form, selected_customer=int(customer_id_sel) if customer_id_sel else None)

    if request.method == 'POST':
        invoice_no_from_form = request.form['invoice_no']; customer_id = request.form.get('customer')
        existing_invoice = Invoice.query.filter_by(invoice_no=invoice_no_from_form, user_id=current_user.id).first() # CHANGED
        if existing_invoice: return rerender_form(f"Error: Invoice number '{invoice_no_from_form}' already exists.", customer_id)
        selected_cust_obj = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first() # CHANGED
        if not selected_cust_obj: return rerender_form("Invalid customer selected.", customer_id)

        new_invoice = Invoice( 
            invoice_no = invoice_no_from_form, 
            date = request.form['date'], 
            po_number = request.form.get('po_number'), 
            profile_id = profile.id, 
            customer_id = customer_id, 
            user_id = current_user.id, # CHANGED
            subtotal = 0, total_gst = 0, grand_total = 0, 
            po_date = request.form.get('po_date'), 
            eway_bill_no = request.form.get('eway_bill_no'), 
            place_of_supply = request.form.get('place_of_supply'), 
            transport_name = request.form.get('transport_name'), 
            vehicle_no = request.form.get('vehicle_no'), 
            delivery_location = request.form.get('delivery_location')
        )
        try: db.session.add(new_invoice); db.session.commit()
        except Exception as e: db.session.rollback(); print(f"DB Error: {e}"); return rerender_form(f"Error creating invoice header: {e}", customer_id)

        item_names = request.form.getlist('item_name'); hsns = request.form.getlist('hsn'); qtys = request.form.getlist('qty'); units = request.form.getlist('unit'); rates = request.form.getlist('rate'); taxes = request.form.getlist('tax_percent'); subtotal_calc = 0; total_gst_calc = 0; items_to_add = []
        for i in range(len(item_names)):
             try:
                 if not item_names[i]: continue
                 qty = int(qtys[i]); rate = float(rates[i]); tax_percent = float(taxes[i]); line_total = qty * rate; gst_amount = line_total * (tax_percent / 100.0); subtotal_calc += line_total; total_gst_calc += gst_amount
                 new_item = InvoiceItem(name = item_names[i], hsn = hsns[i], qty = qty, unit = units[i], rate = rate, tax_percent = tax_percent, invoice_id = new_invoice.id)
                 items_to_add.append(new_item)
             except (ValueError, IndexError) as e: print(f"Skipping bad item row {i}: {e}"); continue
        try: db.session.add_all(items_to_add); new_invoice.subtotal = subtotal_calc; new_invoice.total_gst = total_gst_calc; new_invoice.grand_total = subtotal_calc + total_gst_calc; db.session.commit(); flash(f"Invoice {new_invoice.invoice_no} created.", "success"); return redirect(url_for('dashboard'))
        except Exception as e: db.session.rollback(); print(f"DB Error Items: {e}"); return rerender_form(f"Error saving invoice items: {e}", customer_id)

    return render_template('invoice_form.html', customers=customers, profile=profile, today=today, invoice_data={}, selected_customer=None)


@app.route('/invoice/view/<int:invoice_id>')
@login_required # ADDED
def view_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404() # CHANGED
    profile = invoice.profile
    customer = invoice.customer
    tax_summary = {}
    for item in invoice.items:
        tax_rate = item.tax_percent
        taxable_amount = item.qty * item.rate
        gst_amount = taxable_amount * (tax_rate / 100.0)
        if tax_rate in tax_summary:
            tax_summary[tax_rate]['taxable_amount'] += taxable_amount
            tax_summary[tax_rate]['gst_amount'] += gst_amount
        else: 
            tax_summary[tax_rate] = {
                'taxable_amount': taxable_amount,
                'gst_amount': gst_amount
            }
    return render_template('invoice_preview.html', invoice=invoice, profile=profile, customer=customer, tax_summary=tax_summary)


@app.route('/invoice/delete/<int:invoice_id>', methods=['POST'])
@login_required # ADDED
def delete_invoice(invoice_id):
    """Delete an invoice belonging to the current user."""
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first() # CHANGED

    if invoice:
        try:
            db.session.delete(invoice)
            db.session.commit()
            flash(f"Invoice #{invoice.invoice_no} deleted successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting invoice: {e}", "error")
            print(f"Error deleting invoice: {e}")
    else:
        flash("Invoice not found or permission denied.", "error")
    return redirect(url_for('dashboard'))


@app.route('/invoice/pdf/<int:invoice_id>')
@login_required # ADDED
def download_invoice_pdf(invoice_id):
    profile = CompanyProfile.query.filter_by(user_id=current_user.id).first() # CHANGED
    if not profile: flash("Cannot generate PDF without profile.", "warning"); return redirect(url_for('profile'))

    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404() # CHANGED
    customer = invoice.customer; buffer = io.BytesIO()
    
    # --- Font Registration & Styles ---
    FONT_NORMAL='Helvetica'; FONT_BOLD='Helvetica-Bold';
    try: 
        # Ensure you have 'arial.ttf' and 'arialbd.ttf' in your project directory
        arial_normal_path='arial.ttf'; arial_bold_path='arialbd.ttf'
        pdfmetrics.registerFont(TTFont('Arial', arial_normal_path))
        pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
        addMapping('Arial', 1, 0, 'Arial-Bold')
        FONT_NORMAL='Arial'; FONT_BOLD='Arial-Bold'
    except Exception as e: 
        print(f"WARNING: Arial font registration failed. Using Helvetica. Error: {e}")
    
    styles=getSampleStyleSheet(); theme_color=colors.HexColor('#4A90E2'); light_bg_color=colors.HexColor('#F8F9FA')
    style_normal=ParagraphStyle(name='NormalBase', parent=styles['Normal'], fontName=FONT_NORMAL, fontSize=9, leading=12)
    style_normal_right=ParagraphStyle(name='Normal_Right', parent=style_normal, alignment=TA_RIGHT)
    style_bold=ParagraphStyle(name='Bold', parent=style_normal, fontName=FONT_BOLD)
    style_bold_right=ParagraphStyle(name='Bold_Right', parent=style_bold, alignment=TA_RIGHT)
    style_small=ParagraphStyle(name='Small', parent=style_normal, fontSize=8, leading=10)
    style_small_right=ParagraphStyle(name='Small_Right', parent=style_small, alignment=TA_RIGHT)
    style_title=ParagraphStyle(name='Title', parent=styles['h1'], fontName=FONT_BOLD, fontSize=18, alignment=TA_CENTER)
    style_table_header=ParagraphStyle(name='TableHeader', parent=style_small, fontName=FONT_BOLD, textColor=colors.white)
    style_table_header_right=ParagraphStyle(name='TableHeaderRight', parent=style_table_header, alignment=TA_RIGHT)
    
    currency = get_currency_symbol(profile.currency)
    
    def format_date_pdf(date_str):
        return format_date(date_str, profile.date_format) if date_str else 'N/A'
    def nl_to_br(text):
        return text.replace('\n', '<br/>') if text else ''
    
    story=[]; doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    story.append(Paragraph("TAX INVOICE", style_title)); story.append(Spacer(1, 8*mm))
    
    supplier_details = f"<b>{profile.name}</b><br/>{nl_to_br(profile.address)}<br/><b>GSTIN:</b> {profile.gstin}<br/><b>Phone:</b> {profile.phone or 'N/A'}<br/><b>Email:</b> {profile.email or 'N/A'}"
    bill_to_details = f"<b>Bill To:</b><br/><b>{customer.name}</b><br/>{nl_to_br(customer.billing_address)}<br/><b>GSTIN:</b> {customer.gstin or 'N/A'}"
    ship_to_address = customer.shipping_address or customer.billing_address
    ship_to_details = f"<b>Ship To:</b><br/><b>{customer.name}</b><br/>{nl_to_br(ship_to_address)}"
    
    invoice_details_data = [
        [Paragraph("<b>Invoice No.:</b>", style_normal), Paragraph(invoice.invoice_no, style_normal_right)], 
        [Paragraph("<b>Invoice Date:</b>", style_normal), Paragraph(format_date_pdf(invoice.date), style_normal_right)], 
        [Paragraph("<b>E-Way Bill No.:</b>", style_normal), Paragraph(invoice.eway_bill_no or 'N/A', style_normal_right)], 
        [Paragraph("<b>Place of Supply:</b>", style_normal), Paragraph(invoice.place_of_supply or customer.state or 'N/A', style_normal_right)]
    ]
    invoice_details_table = Table(invoice_details_data, colWidths=['*', 1.8*inch])
    invoice_details_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    
    header_data = [[Paragraph(supplier_details, style_normal), [Paragraph(bill_to_details, style_normal), Spacer(1, 4*mm), Paragraph(ship_to_details, style_normal)], invoice_details_table]]
    header_table = Table(header_data, colWidths=[2.7*inch, 2.7*inch, 2.4*inch])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 5*mm)]))
    story.append(header_table)
    
    transport_data = [[
        Paragraph(f"<b>P.O. Number:</b><br/>{invoice.po_number or 'N/A'}", style_small), 
        Paragraph(f"<b>P.O. Date:</b><br/>{format_date_pdf(invoice.po_date)}", style_small), 
        Paragraph(f"<b>Transport:</b><br/>{invoice.transport_name or 'N/A'}", style_small), 
        Paragraph(f"<b>Vehicle No.:</b><br/>{invoice.vehicle_no or 'N/A'}", style_small), 
        Paragraph(f"<b>Delivery At:</b><br/>{invoice.delivery_location or 'N/A'}", style_small)
    ]]
    transport_table = Table(transport_data, colWidths='*')
    transport_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), light_bg_color), ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey), ('PADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(transport_table); story.append(Spacer(1, 6*mm))
    
    item_table_data = [[Paragraph("Item Description", style_table_header), Paragraph("HSN/SAC", style_table_header), Paragraph("Qty", style_table_header_right), Paragraph("Unit", style_table_header_right), Paragraph("Rate", style_table_header_right), Paragraph("Tax %", style_table_header_right), Paragraph("Amount", style_table_header_right)]]
    tax_summary = {}
    
    for item in invoice.items: 
        line_total = item.qty * item.rate
        item_table_data.append([
            Paragraph(item.name, style_small), 
            Paragraph(item.hsn or '', style_small), 
            Paragraph(str(item.qty), style_small_right), 
            Paragraph(item.unit or '', style_small_right), 
            Paragraph(f"{currency}{item.rate:.2f}", style_small_right), 
            Paragraph(f"{item.tax_percent:.0f}%", style_small_right), 
            Paragraph(f"{currency}{line_total:.2f}", style_small_right)
        ])
        tax_rate = item.tax_percent; taxable_amount = line_total; gst_amount = taxable_amount * (tax_rate / 100.0)
        if tax_rate in tax_summary: 
            tax_summary[tax_rate]['taxable_amount'] += taxable_amount
            tax_summary[tax_rate]['gst_amount'] += gst_amount
        else: 
            tax_summary[tax_rate] = {'taxable_amount': taxable_amount, 'gst_amount': gst_amount}
            
    item_table = Table(item_table_data, colWidths=[2.8*inch, 0.8*inch, 0.5*inch, 0.6*inch, 0.9*inch, 0.6*inch, 1.1*inch], repeatRows=1)
    item_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), theme_color), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), FONT_BOLD), ('BOTTOMPADDING', (0,0), (-1,0), 6), ('TOPPADDING', (0,0), (-1,0), 6), ('ALIGN', (0,0), (-1,0), 'CENTER'), ('FONTNAME', (0,1), (-1,-1), FONT_NORMAL), ('FONTSIZE', (0,1), (-1,-1), 8), ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4), ('LINEBELOW', (0,0), (-1,0), 1, theme_color), ('LINEBELOW', (0,-1), (-1,-1), 0.5, colors.grey), ('ALIGN', (2,1), (-1,-1), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(item_table); story.append(Spacer(1, 8*mm))
    
    tax_table_data = [[Paragraph("<b>Tax Rate</b>", style_small), Paragraph("<b>Taxable Amount</b>", style_small_right), Paragraph("<b>GST Amount</b>", style_small_right)]]
    for rate, data in sorted(tax_summary.items()): 
        tax_table_data.append([Paragraph(f"{rate:.0f}%", style_small), Paragraph(f"{currency}{data['taxable_amount']:.2f}", style_small_right), Paragraph(f"{currency}{data['gst_amount']:.2f}", style_small_right)])
    
    tax_table = Table(tax_table_data, colWidths='*')
    tax_table.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey), ('BOX', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), light_bg_color), ('FONTNAME', (0,0), (-1,-1), FONT_NORMAL)]))
    
    bank_details = f"<b>Bank Details:</b><br/><b>Bank:</b> {profile.bank_name or 'N/A'}<br/><b>A/C No:</b> {profile.account_no or 'N/A'}<br/><b>IFSC:</b> {profile.ifsc_code or 'N/A'}"
    terms = f"<b>Terms & Conditions:</b><br/>{nl_to_br(profile.terms_and_conditions) or 'Thank you for your business.'}"
    
    left_footer_content = [Paragraph("<b>Tax Summary:</b>", style_bold), Spacer(1, 1*mm), tax_table, Spacer(1, 5*mm), Paragraph(bank_details, style_small), Spacer(1, 5*mm), Paragraph(terms, style_small)]
    
    totals_data = [
        [Paragraph("Subtotal:", style_bold), Paragraph(f"{currency}{invoice.subtotal:.2f}", style_bold_right)], 
        [Paragraph("Total GST:", style_bold), Paragraph(f"{currency}{invoice.total_gst:.2f}", style_bold_right)], 
        [Paragraph("Grand Total:", style_bold), Paragraph(f"{currency}{invoice.grand_total:.2f}", style_bold_right)]
    ]
    totals_table = Table(totals_data, colWidths=['*', 1.5*inch])
    totals_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('LINEABOVE', (0, -1), (-1, -1), 1, colors.grey), ('BACKGROUND', (0, -1), (-1, -1), light_bg_color), ('FONTNAME', (0,0), (-1,-1), FONT_BOLD)]))
    
    signature = f"For: {profile.name}<br/><br/><br/><br/>Authorized Signatory"
    right_footer_content = [totals_table, Spacer(1, 15*mm), Paragraph(signature, style_small_right)]
    
    footer_table = Table([[left_footer_content, right_footer_content]], colWidths=[4.8*inch, 2.5*inch])
    footer_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    story.append(footer_table)
    
    try: doc.build(story)
    except Exception as e: 
        print(f"ERROR building PDF: {e}"); flash(f"Error generating PDF: {e}", "error"); 
        return redirect(url_for('dashboard'))
        
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Invoice-{invoice.invoice_no}.pdf", mimetype='application/pdf')

# -----------------------------
# AUTHENTICATION ROUTES
# -----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if email or username already exists
        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Email address already registered.', 'error')
            return redirect(url_for('register'))

        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {e}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            # Check if user has a profile, redirect to create one if not
            profile = CompanyProfile.query.filter_by(user_id=user.id).first()
            if not profile:
                flash('Welcome! Please create your company profile to get started.', 'info')
                return redirect(url_for('profile'))
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check email and password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# -----------------------------
# END AUTHENTICATION ROUTES
# -----------------------------
# --- ADDED DEVELOPMENT SERVER BLOCK FOR LOCAL TESTING ---
if __name__ == "__main__":
    is_debug = os.environ.get('FLASK_DEBUG') == '1' or app.debug
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true' and is_debug:
         import threading, time
         def open_browser():
              time.sleep(1) # Give server a second to start
              try: webbrowser.open("http://122.170.106.196:5000/dashboard")
              except Exception:
                   try: webbrowser.open("http://122.170.106.196:5000/profile")
                   except Exception as e: print(f"Could not open browser: {e}")
         threading.Thread(target=open_browser).start()
    # Run with debug=True for local testing on http://122.170.106.196:5000
    app.run(debug=True, host='127.0.0.1', port=5000)
# --- END DEVELOPMENT SERVER BLOCK ---