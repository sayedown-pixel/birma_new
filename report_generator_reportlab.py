# report_generator_reportlab.py - مع تعديل أسماء الخطوط

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database import db_manager
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)


def clean_line_name(line):
    """تنظيف اسم الخط للعرض في التقرير"""
    if not line:
        return ""
    # استبدال الأسماء العربية الطويلة بأسماء قصيرة
    if "الخط الأول" in line or "line 1" in line.lower():
        return "Line 1"
    elif "الخط الثاني" in line or "line 2" in line.lower():
        return "Line 2"
    return line[:15]


def generate_production_report_pdf(start_date, end_date, line=None):
    """إنشاء تقرير إنتاج PDF"""
    
    try:
        # جلب البيانات
        df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
        
        if df is None or df.empty:
            st.warning("لا توجد بيانات إنتاج للفترة المحددة")
            return None
        
        # اسم الملف
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(REPORT_DIR, f"production_report_{timestamp}.pdf")
        
        # إنشاء المستند
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        story = []
        
        # الأنماط
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#003366'),
            alignment=1,
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#003366'),
            spaceAfter=10
        )
        
        # تنظيف اسم الخط للعرض
        clean_line = clean_line_name(line) if line else ""
        
        # العنوان
        story.append(Paragraph("Smart Factory System", title_style))
        story.append(Paragraph(f"Production Report", subtitle_style))
        story.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", subtitle_style))
        if line:
            story.append(Paragraph(f"Line: {clean_line}", subtitle_style))
        story.append(Spacer(1, 10))
        
        # إحصائيات سريعة
        total_units = df['output_units'].sum() if 'output_units' in df.columns else 0
        avg_efficiency = df['efficiency'].mean() if 'efficiency' in df.columns else 0
        avg_oee = df['oee'].mean() if 'oee' in df.columns else 0
        total_records = len(df)
        
        stats_data = [
            ['Total Records', 'Total Production', 'Avg Efficiency', 'Avg OEE'],
            [f'{total_records:,}', f'{total_units:,}', f'{avg_efficiency:.1f}%', f'{avg_oee:.1f}%']
        ]
        
        stats_table = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # جدول البيانات
        if len(df) > 0:
            story.append(Paragraph("Production Details", heading_style))
            
            # تحضير البيانات للجدول
            table_data = [['Date', 'Line', 'Product', 'Qty', 'Eff%', 'OEE%', 'Waste', 'Downtime']]
            
            for _, row in df.iterrows():
                if hasattr(row['date'], 'strftime'):
                    date_str = row['date'].strftime('%Y-%m-%d')
                else:
                    date_str = str(row['date'])[:10]
                
                # تنظيف اسم الخط
                line_name = clean_line_name(row.get('line', ''))
                
                table_data.append([
                    date_str,
                    line_name,  # ✅ استخدام الاسم المختصر
                    str(row.get('product', ''))[:15],
                    f"{row.get('output_units', 0):,}",
                    f"{row.get('efficiency', 0):.1f}",
                    f"{row.get('oee', 0):.1f}",
                    f"{row.get('waste_bottles', 0):,}",
                    f"{row.get('downtime_minutes', 0):.0f}"
                ])
            
            # إنشاء الجدول
            col_widths = [2.2*cm, 2.2*cm, 3.5*cm, 1.8*cm, 1.5*cm, 1.5*cm, 1.8*cm, 1.8*cm]
            data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(data_table)
        
        # بناء PDF
        doc.build(story)
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
        
        # فلترة حسب التاريخ
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(REPORT_DIR, f"maintenance_report_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(filename, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#003366'),
            alignment=1,
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#003366'),
            spaceAfter=10
        )
        
        story.append(Paragraph("Smart Factory System", title_style))
        story.append(Paragraph(f"Maintenance Report", subtitle_style))
        story.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", subtitle_style))
        story.append(Spacer(1, 10))
        
        # إحصائيات
        breakdown_count = len(df[df['type'] == 'breakdown']) if 'type' in df.columns else 0
        total_downtime = df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in df.columns else 0
        
        stats_data = [
            ['Total Records', 'Breakdowns', 'Planned', 'Total Downtime'],
            [f'{len(df):,}', f'{breakdown_count:,}', f'{len(df)-breakdown_count:,}', f'{total_downtime:.1f} hrs']
        ]
        
        stats_table = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # جدول البيانات
        if len(df) > 0:
            story.append(Paragraph("Maintenance Details", heading_style))
            
            table_data = [['Date', 'Machine', 'Type', 'Technician', 'Downtime', 'Category']]
            
            for _, row in df.iterrows():
                if hasattr(row['date'], 'strftime'):
                    date_str = row['date'].strftime('%Y-%m-%d')
                else:
                    date_str = str(row['date'])[:10]
                
                table_data.append([
                    date_str,
                    str(row.get('machine', ''))[:12],
                    str(row.get('type', ''))[:8],
                    str(row.get('technician', ''))[:10],
                    f"{row.get('downtime_minutes', 0):.0f} min",
                    str(row.get('downtime_category', ''))[:12]
                ])
            
            col_widths = [2.2*cm, 3*cm, 2.2*cm, 2.5*cm, 2.2*cm, 2.5*cm]
            data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(data_table)
        
        doc.build(story)
        return filename
        
    except Exception as e:
        st.error(f"Error generating maintenance PDF: {str(e)}")
        return None