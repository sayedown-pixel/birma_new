# report_generator.py - نسخة مبسطة وآمنة
import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import os

# محاولة استيراد FPDF مع معالجة الأخطاء
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    print("Warning: FPDF not installed. PDF generation will not work.")

from database import db_manager

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Smart Factory System - Performance Report', 0, 1, 'C')
        self.ln(5)
        self.set_draw_color(180, 180, 180)
        self.line(10, 30, 200, 30)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_production_report_pdf(start_date, end_date, line=None):
    """Generates a PDF report for production data"""
    
    if not FPDF_AVAILABLE:
        print("FPDF not available")
        return None
    
    try:
        # Fetch data
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            print("No production data found")
            return None
        
        # Create PDF object
        pdf = PDFReport()
        pdf.add_page()
        
        # Title
        date_range_str = f"From {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        if line:
            date_range_str += f" - Line: {line}"
        
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 10, date_range_str, 0, 1, 'C')
        pdf.ln(5)
        
        # Summary statistics
        total_output = df['output_units'].sum() if 'output_units' in df.columns else 0
        avg_efficiency = df['efficiency'].mean() if 'efficiency' in df.columns else 0
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, f"Total Output: {total_output:,.0f} units", 0, 1)
        pdf.cell(0, 8, f"Average Efficiency: {avg_efficiency:.1f}%", 0, 1)
        pdf.ln(5)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
            
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def generate_maintenance_report_pdf(start_date, end_date):
    """Generates a PDF report for maintenance data"""
    
    if not FPDF_AVAILABLE:
        return None
    
    try:
        df = db_manager.get_all_maintenance()
        
        if df is None or df.empty:
            return None
            
        # Filter by date
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return None
        
        pdf = PDFReport()
        pdf.add_page()
        
        date_range_str = f"Maintenance Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 10, date_range_str, 0, 1, 'C')
        pdf.ln(5)
        
        breakdown_count = len(df[df['type'] == 'breakdown']) if 'type' in df.columns else 0
        total_downtime = df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df.columns else 0
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, f"Total Breakdowns: {breakdown_count}", 0, 1)
        pdf.cell(0, 8, f"Total Downtime: {total_downtime:.1f} hours", 0, 1)
        pdf.ln(5)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
            
    except Exception as e:
        print(f"Error generating maintenance PDF: {e}")
        return None