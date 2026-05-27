# report_generator.py - نسخة بدون رموز تعبيرية

import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import os

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    print("Warning: FPDF not installed. Run: pip install fpdf")

from database import db_manager


class DetailedPDF(FPDF):
    """PDF محسن مع تنسيق احترافي"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'SMART FACTORY SYSTEM', 0, 1, 'C')
        
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Integrated Manufacturing Report', 0, 1, 'C')
        
        self.set_draw_color(0, 51, 102)
        self.line(10, 25, 200, 25)
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} - Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')
    
    def section_title(self, title):
        """عنوان القسم - بدون رموز تعبيرية"""
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 51, 102)
        self.set_fill_color(230, 240, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(3)
    
    def summary_card(self, label, value, x, y, width=45, height=12):
        """بطاقة ملخص"""
        self.set_xy(x, y)
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0, 0, 0)
        self.cell(width, height, label, 1, 0, 'C', 1)
        
        self.set_xy(x, y + height)
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(255, 255, 255)
        self.cell(width, height, str(value), 1, 0, 'C', 1)
    
    def add_table(self, headers, data, col_widths=None):
        """إضافة جدول محسن"""
        if not data:
            return
        
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        
        # رأس الجدول
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, str(header), 1, 0, 'C', 1)
        self.ln()
        
        # صفوف الجدول
        self.set_font('Arial', '', 8)
        self.set_text_color(0, 0, 0)
        fill = False
        
        for row in data:
            if fill:
                self.set_fill_color(245, 245, 245)
            else:
                self.set_fill_color(255, 255, 255)
            
            for i, cell in enumerate(row):
                align = 'R' if isinstance(cell, (int, float)) or (isinstance(cell, str) and cell.replace(',', '').replace('.', '').isdigit()) else 'L'
                self.cell(col_widths[i], 8, str(cell)[:30], 1, 0, align, fill)
            self.ln()
            fill = not fill


def generate_production_report_pdf(start_date, end_date, line=None):
    """إنشاء تقرير إنتاج PDF مفصل"""
    
    if not FPDF_AVAILABLE:
        st.error("FPDF library not installed. Run: pip install fpdf")
        return None
    
    try:
        # جلب البيانات
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            st.warning("لا توجد بيانات إنتاج للفترة المحددة")
            return None
        
        # إنشاء PDF
        pdf = DetailedPDF()
        pdf.add_page()
        
        # ==================== العنوان الرئيسي ====================
        title = "Production Report"
        subtitle = f"Period: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        if line:
            subtitle += f" | Line: {line}"
        
        pdf.set_font('Arial', 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, title, 0, 1, 'C')
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 8, subtitle, 0, 1, 'C')
        pdf.ln(10)
        
        # ==================== بطاقات الملخص ====================
        total_units = df['output_units'].sum() if 'output_units' in df.columns else 0
        avg_efficiency = df['efficiency'].mean() if 'efficiency' in df.columns else 0
        avg_oee = df['oee'].mean() if 'oee' in df.columns else 0
        total_records = len(df)
        total_waste = df['waste_bottles'].sum() if 'waste_bottles' in df.columns else 0
        total_downtime = df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df.columns else 0
        
        # صف البطاقات الأول
        pdf.summary_card("Total Records", f"{total_records:,}", 10, pdf.get_y(), 45, 12)
        pdf.summary_card("Total Production", f"{total_units:,}", 60, pdf.get_y(), 45, 12)
        pdf.summary_card("Total Waste", f"{total_waste:,}", 110, pdf.get_y(), 45, 12)
        pdf.summary_card("Total Downtime", f"{total_downtime:.1f} hrs", 160, pdf.get_y(), 45, 12)
        
        pdf.ln(28)
        
        # صف البطاقات الثاني
        pdf.summary_card("Avg Efficiency", f"{avg_efficiency:.1f}%", 10, pdf.get_y(), 45, 12)
        pdf.summary_card("Avg OEE", f"{avg_oee:.1f}%", 60, pdf.get_y(), 45, 12)
        pdf.summary_card("Best Efficiency", f"{df['efficiency'].max():.1f}%", 110, pdf.get_y(), 45, 12)
        pdf.summary_card("Worst Efficiency", f"{df['efficiency'].min():.1f}%", 160, pdf.get_y(), 45, 12)
        
        pdf.ln(28)
        
        # ==================== جدول التفاصيل الكاملة ====================
        pdf.section_title("Production Details")
        
        # تحضير بيانات الجدول
        headers = ['Date', 'Line', 'Product', 'Qty', 'Efficiency%', 'OEE%', 'Waste', 'Downtime']
        col_widths = [25, 25, 40, 20, 20, 20, 20, 20]
        
        data = []
        for _, row in df.iterrows():
            if hasattr(row['date'], 'strftime'):
                date_str = row['date'].strftime('%d/%m/%Y')
            else:
                date_str = str(row['date'])[:10]
            
            data.append([
                date_str,
                str(row.get('line', ''))[:12],
                str(row.get('product', ''))[:25],
                f"{row.get('output_units', 0):,}",
                f"{row.get('efficiency', 0):.1f}",
                f"{row.get('oee', 0):.1f}",
                f"{row.get('waste_bottles', 0):,}",
                f"{row.get('downtime_minutes', 0):.0f}"
            ])
        
        pdf.add_table(headers, data, col_widths)
        
        # ==================== إحصائيات إضافية ====================
        pdf.ln(10)
        pdf.section_title("Additional Statistics")
        
        # إحصائيات حسب المنتج
        if 'product' in df.columns:
            product_stats = df.groupby('product').agg({
                'output_units': 'sum',
                'efficiency': 'mean'
            }).round(1).head(10)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, "Top Products by Production:", 0, 1)
            
            prod_headers = ['Product', 'Total Qty', 'Avg Efficiency%']
            prod_col_widths = [70, 30, 30]
            prod_data = [[str(p)[:25], f"{row['output_units']:,}", f"{row['efficiency']:.1f}"] 
                        for p, row in product_stats.iterrows()]
            
            pdf.add_table(prod_headers, prod_data[:10], prod_col_widths)
        
        # حفظ الملف
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(tempfile.gettempdir(), f"production_report_{timestamp}.pdf")
        pdf.output(filename)
        return filename
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


def generate_maintenance_report_pdf(start_date, end_date):
    """إنشاء تقرير صيانة PDF مفصل"""
    
    if not FPDF_AVAILABLE:
        return None
    
    try:
        df = db_manager.get_all_maintenance()
        
        if df is None or df.empty:
            return None
        
        # فلترة حسب التاريخ
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return None
        
        pdf = DetailedPDF()
        pdf.add_page()
        
        # العنوان
        title = "Maintenance Report"
        subtitle = f"Period: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        
        pdf.set_font('Arial', 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, title, 0, 1, 'C')
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 8, subtitle, 0, 1, 'C')
        pdf.ln(10)
        
        # بطاقات الملخص
        breakdown_count = len(df[df['type'] == 'breakdown']) if 'type' in df.columns else 0
        planned_count = len(df[df['type'] == 'planned']) if 'type' in df.columns else 0
        total_downtime = df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df.columns else 0
        avg_downtime = df['downtime_minutes'].mean() / 60 if 'downtime_minutes' in df.columns else 0
        
        pdf.summary_card("Total Records", f"{len(df):,}", 10, pdf.get_y(), 45, 12)
        pdf.summary_card("Breakdowns", f"{breakdown_count:,}", 60, pdf.get_y(), 45, 12)
        pdf.summary_card("Planned", f"{planned_count:,}", 110, pdf.get_y(), 45, 12)
        pdf.summary_card("Total Downtime", f"{total_downtime:.1f} hrs", 160, pdf.get_y(), 45, 12)
        
        pdf.ln(28)
        
        pdf.summary_card("Avg Downtime", f"{avg_downtime:.1f} hrs", 10, pdf.get_y(), 45, 12)
        
        pdf.ln(28)
        
        # جدول التفاصيل
        pdf.section_title("Maintenance Details")
        
        headers = ['Date', 'Machine', 'Type', 'Technician', 'Downtime', 'Category']
        col_widths = [25, 35, 25, 30, 25, 30]
        
        data = []
        for _, row in df.iterrows():
            if hasattr(row['date'], 'strftime'):
                date_str = row['date'].strftime('%d/%m/%Y')
            else:
                date_str = str(row['date'])[:10]
            
            data.append([
                date_str,
                str(row.get('machine', ''))[:15],
                str(row.get('type', ''))[:10],
                str(row.get('technician', ''))[:12],
                f"{row.get('downtime_minutes', 0):.0f} min",
                str(row.get('downtime_category', ''))[:15]
            ])
        
        pdf.add_table(headers, data, col_widths)
        
        # حفظ الملف
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(tempfile.gettempdir(), f"maintenance_report_{timestamp}.pdf")
        pdf.output(filename)
        return filename
        
    except Exception as e:
        print(f"Error generating maintenance PDF: {e}")
        return None
    