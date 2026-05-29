# report_generator_simple.py - تقارير PDF بدون عربية

import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from database import db_manager
from fpdf import FPDF
from helpers import normalize_line_name
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)


def remove_arabic(text):
    """إزالة الأحرف العربية من النص"""
    if not text or not isinstance(text, str):
        return ""
    # إزالة الأحرف العربية
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+')
    cleaned = arabic_pattern.sub('', text)
    # إزالة المسافات الزائدة
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # إزالة الرموز التعبيرية
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"
                               u"\U0001F300-\U0001F5FF"
                               u"\U0001F680-\U0001F6FF"
                               u"\U0001F1E0-\U0001F1FF"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    cleaned = emoji_pattern.sub('', cleaned)
    return cleaned.strip() if cleaned else "-"
class SimplePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'SMART FACTORY SYSTEM - PRODUCTION REPORT', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_production_report_pdf(start_date, end_date, line=None):
    """إنشاء تقرير إنتاج PDF"""
    
    try:
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            st.warning("No production data found")
            return None
        
        df_clean = df.copy()
        
        # ✅ تنظيف أسماء الخطوط في البيانات
        if 'line' in df_clean.columns:
            df_clean['line'] = df_clean['line'].apply(clean_line_name)
        
        # تنظيف أسماء المنتجات
        if 'product' in df_clean.columns:
            product_map = {
                "200 ml Carton": "200ml Carton",
                "200 ml Shrink": "200ml Shrink",
                "330 ml Carton": "330ml Carton",
                "330 ml Shrink": "330ml Shrink",
                "600 ml Carton": "600ml Carton",
                "1.5 L Shrink": "1.5L Shrink"
            }
            df_clean['product'] = df_clean['product'].apply(lambda x: product_map.get(str(x), "Product"))
        
        # تنظيف أسماء المشرفين
        if 'supervisor' in df_clean.columns:
            df_clean['supervisor'] = df_clean['supervisor'].apply(remove_arabic)
        
        # تنظيف اسم الخط للعرض في العنوان
        line_name = clean_line_name(line) if line else ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(REPORT_DIR, f"production_report_{timestamp}.pdf")
        
        pdf = SimplePDF()
        pdf.add_page()
        
        # عنوان التقرير
        date_range = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        if 'line' in df_clean.columns:
            df_clean['line'] = df_clean['line'].apply(normalize_line_name)
        
        line_name = normalize_line_name(line) if line else ""
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, date_range, 0, 1, 'C')
        pdf.ln(5)
        
        # إحصائيات
        total_units = df_clean['output_units'].sum() if 'output_units' in df_clean.columns else 0
        avg_efficiency = df_clean['efficiency'].mean() if 'efficiency' in df_clean.columns else 0
        total_records = len(df_clean)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 8, "SUMMARY:", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 6, f"  - Total Records: {total_records}", 0, 1)
        pdf.cell(0, 6, f"  - Total Production: {total_units:,} units", 0, 1)
        pdf.cell(0, 6, f"  - Average Efficiency: {avg_efficiency:.1f}%", 0, 1)
        pdf.ln(5)
        
        # جدول البيانات
        pdf.set_font('Arial', 'B', 8)
        
        headers = ['ID', 'Date', 'Line', 'Product', 'Qty', 'Eff%', 'OEE%', 'Downtime']
        col_widths = [12, 22, 18, 30, 18, 15, 15, 20]
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 7, header, 1, 0, 'C')
        pdf.ln()
        
        pdf.set_font('Arial', '', 7)
        for _, row in df_clean.head(50).iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
            
            pdf.cell(col_widths[0], 6, str(row.get('id', ''))[:5], 1, 0, 'C')
            pdf.cell(col_widths[1], 6, date_str, 1, 0, 'C')
            pdf.cell(col_widths[2], 6, str(row.get('line', ''))[:8], 1, 0, 'C')
            pdf.cell(col_widths[3], 6, str(row.get('product', ''))[:15], 1, 0, 'L')
            pdf.cell(col_widths[4], 6, f"{row.get('output_units', 0):,}", 1, 0, 'R')
            pdf.cell(col_widths[5], 6, f"{row.get('efficiency', 0):.0f}", 1, 0, 'R')
            pdf.cell(col_widths[6], 6, f"{row.get('oee', 0):.0f}", 1, 0, 'R')
            pdf.cell(col_widths[7], 6, f"{row.get('downtime_minutes', 0):.0f}", 1, 1, 'R')
        
        pdf.output(filename)
        return filename
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


def generate_maintenance_report_pdf(start_date, end_date):
    """إنشاء تقرير صيانة PDF"""
    
    try:
        df = db_manager.get_all_maintenance()
        
        if df is None or df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return None
        
        df_clean = df.copy()
        
        # تنظيف أسماء الماكينات
        if 'machine' in df_clean.columns:
            df_clean['machine'] = df_clean['machine'].apply(remove_arabic)
        
        # تنظيف أسماء الفنيين
        if 'technician' in df_clean.columns:
            df_clean['technician'] = df_clean['technician'].apply(remove_arabic)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(REPORT_DIR, f"maintenance_report_{timestamp}.pdf")
        
        pdf = SimplePDF()
        pdf.add_page()
        
        date_range = f"Maintenance Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, date_range, 0, 1, 'C')
        pdf.ln(5)
        
        breakdown_count = len(df_clean[df_clean['type'] == 'breakdown']) if 'type' in df_clean.columns else 0
        total_downtime = df_clean['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df_clean.columns else 0
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 8, "SUMMARY:", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 6, f"  - Total Records: {len(df_clean)}", 0, 1)
        pdf.cell(0, 6, f"  - Breakdowns: {breakdown_count}", 0, 1)
        pdf.cell(0, 6, f"  - Total Downtime: {total_downtime:.1f} hours", 0, 1)
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 8)
        
        headers = ['Date', 'Machine', 'Type', 'Technician', 'Downtime']
        col_widths = [25, 40, 25, 35, 30]
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 7, header, 1, 0, 'C')
        pdf.ln()
        
        pdf.set_font('Arial', '', 7)
        for _, row in df_clean.head(50).iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
            
            pdf.cell(col_widths[0], 6, date_str, 1, 0, 'C')
            pdf.cell(col_widths[1], 6, str(row.get('machine', ''))[:12], 1, 0, 'L')
            pdf.cell(col_widths[2], 6, str(row.get('type', ''))[:8], 1, 0, 'C')
            pdf.cell(col_widths[3], 6, str(row.get('technician', ''))[:10], 1, 0, 'L')
            pdf.cell(col_widths[4], 6, f"{row.get('downtime_minutes', 0):.0f} min", 1, 1, 'R')
        
        pdf.output(filename)
        return filename
        
    except Exception as e:
        st.error(f"Error generating maintenance PDF: {str(e)}")
        return None