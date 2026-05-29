# report_generator.py - نسخة كاملة مع جميع التفاصيل

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


def generate_production_report_pdf(start_date, end_date, line=None):
    """إنشاء تقرير إنتاج PDF بجميع التفاصيل"""
    
    if not FPDF_AVAILABLE:
        st.error("FPDF library not installed. Run: pip install fpdf")
        return None
    
    try:
        # جلب البيانات
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            st.warning("No production data found for the selected period")
            return None
        
        # تنظيف أسماء الخطوط
        df_clean = df.copy()
        if 'line' in df_clean.columns:
            df_clean['line'] = df_clean['line'].apply(
                lambda x: "Line 1" if "الخط الأول" in str(x) else "Line 2" if "الخط الثاني" in str(x) else str(x)[:10]
            )
        
        # إنشاء PDF
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
                line_name = "Line 1" if "الخط الأول" in line else "Line 2" if "الخط الثاني" in line else line
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
        
        # عنوان التقرير
        date_range = f"Maintenance Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, date_range, 0, 1, 'C')
        pdf.ln(5)
        
        # إحصائيات
        breakdown_count = len(df[df['type'] == 'breakdown']) if 'type' in df.columns else 0
        planned_count = len(df[df['type'] == 'planned']) if 'type' in df.columns else 0
        total_downtime = df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df.columns else 0
        total_records = len(df)
        
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
        for _, row in df.head(100).iterrows():
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
        filename = os.path.join(tempfile.gettempdir(), f"maintenance_report_{timestamp}.pdf")
        pdf.output(filename)
        return filename
        
    except Exception as e:
        st.error(f"Error generating maintenance PDF: {str(e)}")
        return None