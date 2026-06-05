# report_generator.py - نسخة متكاملة ومحسنة

import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import os
import re

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    st.error("FPDF library not installed. Run: pip install fpdf")

from database import db_manager


def normalize_line_name(line):
    """تطبيع اسم الخط"""
    if not line:
        return ""
    line_str = str(line)
    if "الخط الأول" in line_str or "Line 1" in line_str:
        return "Line 1"
    elif "الخط الثاني" in line_str or "Line 2" in line_str:
        return "Line 2"
    return line_str[:10]


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


class DetailedPDF(FPDF):
    """كلاس PDF محسن مع دعم الجداول المتقدمة"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'SMART FACTORY SYSTEM', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Production Report - All Details', 0, 1, 'C')
        self.set_draw_color(0, 51, 102)
        self.line(10, 28, 200, 28)
        self.ln(8)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} - Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')
    
    def add_table(self, headers, data, col_widths=None):
        """إضافة جدول محسن مع تنسيق احترافي"""
        if not data:
            return
        
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        
        # رأس الجدول
        self.set_font('Arial', 'B', 7)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, str(header), 1, 0, 'C', 1)
        self.ln()
        
        # صفوف الجدول
        self.set_font('Arial', '', 6.5)
        self.set_text_color(0, 0, 0)
        fill = False
        
        for row in data:
            if fill:
                self.set_fill_color(240, 240, 240)
            else:
                self.set_fill_color(255, 255, 255)
            
            for i, cell in enumerate(row):
                align = 'R' if isinstance(cell, (int, float)) or (isinstance(cell, str) and cell.replace(',', '').replace('.', '').isdigit()) else 'L'
                self.cell(col_widths[i], 6, str(cell)[:25], 1, 0, align, fill)
            self.ln()
            fill = not fill


class SimplePDF(FPDF):
    """كلاس PDF مبسط للتقارير السريعة"""
    
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


def generate_production_report_pdf(start_date, end_date, line=None, detailed=True):
    """
    إنشاء تقرير إنتاج PDF
    
    Parameters:
    - start_date: تاريخ البداية
    - end_date: تاريخ النهاية
    - line: اسم الخط (اختياري)
    - detailed: إذا كان True يستخدم التقرير المفصل، وإلا يستخدم التقرير المبسط
    """
    
    if not FPDF_AVAILABLE:
        st.error("FPDF library not installed. Run: pip install fpdf")
        return None
    
    try:
        # جلب البيانات
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            st.warning("No production data found for the selected period")
            return None
        
        # تنظيف البيانات
        df_clean = df.copy()
        
        # تنظيف أسماء الخطوط
        if 'line' in df_clean.columns:
            df_clean['line'] = df_clean['line'].apply(normalize_line_name)
        
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
            df_clean['product'] = df_clean['product'].apply(lambda x: product_map.get(str(x), str(x)[:20]))
        
        # تنظيف أسماء المشرفين من العربية
        if 'supervisor' in df_clean.columns:
            df_clean['supervisor'] = df_clean['supervisor'].apply(remove_arabic)
        
        # اختيار نوع التقرير
        if detailed:
            return _generate_detailed_production_report(df_clean, start_date, end_date, line)
        else:
            return _generate_simple_production_report(df_clean, start_date, end_date, line)
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


def _generate_detailed_production_report(df_clean, start_date, end_date, line):
    """توليد تقرير إنتاج مفصل"""
    
    pdf = DetailedPDF()
    
    # حساب عدد الصفحات المطلوبة (كل صفحة 25 سجل)
    rows_per_page = 25
    total_pages = (len(df_clean) + rows_per_page - 1) // rows_per_page
    
    for page in range(total_pages):
        pdf.add_page()
        
        # عنوان الصفحة
        start_idx = page * rows_per_page
        end_idx = min(start_idx + rows_per_page, len(df_clean))
        page_df = df_clean.iloc[start_idx:end_idx]
        
        # عنوان التقرير
        date_range = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        if line:
            line_name = normalize_line_name(line)
            date_range += f" | Line: {line_name}"
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, date_range, 0, 1, 'C')
        pdf.ln(3)
        
        # إحصائيات الصفحة الحالية
        page_total = page_df['output_units'].sum() if 'output_units' in page_df.columns else 0
        page_avg_eff = page_df['efficiency'].mean() if 'efficiency' in page_df.columns else 0
        
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(0, 6, f"Page {page+1} of {total_pages} | Records: {len(page_df)} | Total Qty: {page_total:,.0f} | Avg Eff: {page_avg_eff:.1f}%", 0, 1, 'R')
        pdf.ln(3)
        
        # جميع أعمدة التقرير
        headers = [
            'ID', 'Date', 'Line', 'Product', 'Qty', 
            'Preforms', 'Waste', 'PackWaste', 'Speed', 
            'Eff%', 'OEE%', 'Downtime', 'Supervisor'
        ]
        col_widths = [10, 18, 15, 35, 15, 15, 12, 15, 15, 12, 12, 15, 20]
        
        # إعداد البيانات
        data = []
        for _, row in page_df.iterrows():
            date_str = row['date'].strftime('%d/%m/%Y') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
            
            data.append([
                row.get('id', ''),
                date_str,
                row.get('line', '')[:8],
                row.get('product', '')[:20],
                f"{row.get('output_units', 0):,}",
                f"{row.get('preforms_used', 0):,}",
                f"{row.get('waste_bottles', 0):,}",
                f"{row.get('packaging_waste', 0):.0f}",
                f"{row.get('line_speed', 0):,}",
                f"{row.get('efficiency', 0):.1f}",
                f"{row.get('oee', 0):.1f}",
                f"{row.get('downtime_minutes', 0):.0f}",
                row.get('supervisor', '')[:12]
            ])
        
        pdf.add_table(headers, data, col_widths)
        
        # إحصائيات إضافية في نهاية التقرير (آخر صفحة فقط)
        if page == total_pages - 1:
            pdf.ln(8)
            pdf.set_font('Arial', 'B', 9)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 8, "SUMMARY STATISTICS", 0, 1, 'L', 1)
            
            total_units = df_clean['output_units'].sum() if 'output_units' in df_clean.columns else 0
            total_preforms = df_clean['preforms_used'].sum() if 'preforms_used' in df_clean.columns else 0
            total_waste = df_clean['waste_bottles'].sum() if 'waste_bottles' in df_clean.columns else 0
            total_downtime = df_clean['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df_clean.columns else 0
            avg_eff = df_clean['efficiency'].mean() if 'efficiency' in df_clean.columns else 0
            avg_oee = df_clean['oee'].mean() if 'oee' in df_clean.columns else 0
            total_records = len(df_clean)
            
            pdf.set_font('Arial', '', 8)
            pdf.cell(60, 6, f"Total Records: {total_records}", 0, 0)
            pdf.cell(60, 6, f"Total Production: {total_units:,} units", 0, 0)
            pdf.cell(60, 6, f"Total Preforms: {total_preforms:,}", 0, 1)
            
            pdf.cell(60, 6, f"Total Waste: {total_waste:,}", 0, 0)
            pdf.cell(60, 6, f"Total Downtime: {total_downtime:.1f} hrs", 0, 0)
            pdf.cell(60, 6, f"Average Efficiency: {avg_eff:.1f}%", 0, 1)
            
            pdf.cell(60, 6, f"Average OEE: {avg_oee:.1f}%", 0, 0)
            pdf.cell(60, 6, f"Best Efficiency: {df_clean['efficiency'].max():.1f}%", 0, 0)
            pdf.cell(60, 6, f"Worst Efficiency: {df_clean['efficiency'].min():.1f}%", 0, 1)
    
    # حفظ الملف
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(tempfile.gettempdir(), f"production_report_detailed_{timestamp}.pdf")
    pdf.output(filename)
    return filename


def _generate_simple_production_report(df_clean, start_date, end_date, line):
    """توليد تقرير إنتاج مبسط"""
    
    pdf = SimplePDF()
    pdf.add_page()
    
    # عنوان التقرير
    date_range = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    if line:
        line_name = normalize_line_name(line)
        date_range += f" | Line: {line_name}"
    
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
    
    # حفظ الملف
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(tempfile.gettempdir(), f"production_report_simple_{timestamp}.pdf")
    pdf.output(filename)
    return filename


def generate_maintenance_report_pdf(start_date, end_date, detailed=True):
    """
    إنشاء تقرير صيانة PDF
    
    Parameters:
    - start_date: تاريخ البداية
    - end_date: تاريخ النهاية
    - detailed: إذا كان True يستخدم التقرير المفصل، وإلا يستخدم التقرير المبسط
    """
    
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
        
        # تنظيف البيانات
        df_clean = df.copy()
        
        # تنظيف أسماء الماكينات والفنيين من العربية
        if 'machine' in df_clean.columns:
            df_clean['machine'] = df_clean['machine'].apply(remove_arabic)
        
        if 'technician' in df_clean.columns:
            df_clean['technician'] = df_clean['technician'].apply(remove_arabic)
        
        if detailed:
            return _generate_detailed_maintenance_report(df_clean, start_date, end_date)
        else:
            return _generate_simple_maintenance_report(df_clean, start_date, end_date)
        
    except Exception as e:
        st.error(f"Error generating maintenance PDF: {str(e)}")
        return None


def _generate_detailed_maintenance_report(df_clean, start_date, end_date):
    """توليد تقرير صيانة مفصل"""
    
    pdf = DetailedPDF()
    pdf.add_page()
    
    # عنوان التقرير
    date_range = f"Maintenance Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, date_range, 0, 1, 'C')
    pdf.ln(5)
    
    # إحصائيات
    breakdown_count = len(df_clean[df_clean['type'] == 'breakdown']) if 'type' in df_clean.columns else 0
    planned_count = len(df_clean[df_clean['type'] == 'planned']) if 'type' in df_clean.columns else 0
    total_downtime = df_clean['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df_clean.columns else 0
    total_records = len(df_clean)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 7, "SUMMARY:", 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.cell(50, 6, f"Total Records: {total_records}", 0, 0)
    pdf.cell(50, 6, f"Breakdowns: {breakdown_count}", 0, 0)
    pdf.cell(50, 6, f"Planned: {planned_count}", 0, 0)
    pdf.cell(50, 6, f"Total Downtime: {total_downtime:.1f} hrs", 0, 1)
    pdf.ln(5)
    
    # جدول التفاصيل
    headers = ['Date', 'Machine', 'Type', 'Technician', 'Downtime', 'Category']
    col_widths = [22, 35, 20, 30, 22, 35]
    
    data = []
    for _, row in df_clean.head(100).iterrows():
        date_str = row['date'].strftime('%d/%m/%Y') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
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
    filename = os.path.join(tempfile.gettempdir(), f"maintenance_report_detailed_{timestamp}.pdf")
    pdf.output(filename)
    return filename


def _generate_simple_maintenance_report(df_clean, start_date, end_date):
    """توليد تقرير صيانة مبسط"""
    
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
    
    # حفظ الملف
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(tempfile.gettempdir(), f"maintenance_report_simple_{timestamp}.pdf")
    pdf.output(filename)
    return filename