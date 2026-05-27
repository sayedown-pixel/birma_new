import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils import get_auto_reorder_suggestions, get_stock_prediction_calculated, get_marquee_recommendations
from oee_analytics import show_oee_dashboard
from ui_components import metric_card
from alerts_viewer import show_alerts_panel
from database import db_manager
from dashboard_enhanced import (
    show_kpi_cards,
    show_performance_gauge,
    show_production_trend,
    show_line_comparison,
    show_quick_filters,
    get_date_range_from_period
)
def show_materials_depletion_status(df_raw, df_main, selected_line, t):
    """عرض حالة نفاذ المواد الخام"""
    from utils import calculate_days_until_depletion
    
    if df_raw is None or df_raw.empty:
        return
    
    current_lang = st.session_state.get('lang', 'ar')
    df_with_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_with_depletion is None or df_with_depletion.empty:
        return
    
    if 'Days_Until_Depletion' not in df_with_depletion.columns:
        st.warning(t.get("no_data", "No data"))
        return
    
    st.markdown("---")
    st.subheader("📅 " + t.get("materials_depletion", "مدة نفاذ المواد الخام"))
    
    material_col = None
    for col in ["Material_Display_Name", "Material_Name_AR", "Material_Name_EN", "Name"]:
        if col in df_with_depletion.columns:
            material_col = col
            break
    
    stock_col = None
    for col in ["Current_Stock", "Stock"]:
        if col in df_with_depletion.columns:
            stock_col = col
            break
    
    if material_col and stock_col:
        depletion_data = []
        for _, row in df_with_depletion.iterrows():
            try:
                days = float(row['Days_Until_Depletion']) if pd.notna(row['Days_Until_Depletion']) else 999
                current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
                mat_name = str(row[material_col]) if pd.notna(row[material_col]) else ""
                
                if days <= 30:
                    if days <= 0:
                        status_display = t.get("status_out_of_stock", "🔴 Out of Stock")
                    elif days <= 7:
                        status_display = t.get("status_critical", "🔴 Critical (less than 7 days)")
                    elif days <= 14:
                        status_display = t.get("status_warning", "🟡 Warning (7-14 days)")
                    elif days <= 30:
                        status_display = t.get("status_info", "🟢 Remaining") + f" ({days:.0f} {t.get('days_word', 'days')})"
                    else:
                        status_display = t.get("status_safe", "✅ Safe")
                    
                    depletion_data.append({
                        t.get("material", "المادة"): mat_name,
                        t.get("current_stock", "المخزون"): f"{int(current_stock):,}",
                        t.get("days_left", "الأيام المتبقية"): f"{days:.1f}" if days > 0 else "0",
                        t.get("status", "الحالة"): status_display
                    })
            except Exception as e:
                continue
        
        if depletion_data:
            depletion_data.sort(key=lambda x: float(x[t.get("days_left", "الأيام المتبقية")]) if x[t.get("days_left", "الأيام المتبقية")] != "0" else 0)
            df_depletion = pd.DataFrame(depletion_data)
            st.dataframe(df_depletion, use_container_width=True, hide_index=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                critical = len([d for d in depletion_data if "🔴" in d[t.get("status", "الحالة")]])
                st.metric(t.get("dashboard_critical_materials", "⚠️ Critical Materials (less than 7 days)"), critical)
            with col2:
                warning = len([d for d in depletion_data if "🟡" in d[t.get("status", "الحالة")]])
                st.metric(t.get("dashboard_warning_materials", "📦 Warning Materials (7-14 days)"), warning)
            with col3:
                safe = len([d for d in depletion_data if "🟢" in d[t.get("status", "الحالة")]])
                st.metric(t.get("dashboard_safe_materials", "✅ Safe Materials (15-30 days)"), safe)
        else:
            st.success("✅ " + t.get("all_materials_safe", "All materials are safe, no depletion risk within 30 days"))
def show_shift_info_dashboard(t):
    """عرض معلومات الوردية في لوحة التحكم"""
    from utils import get_shift_info
    
    shift_info = get_shift_info()
    
    # الحصول على اللغة الحالية
    current_lang = st.session_state.get('lang', 'ar')
    
    if shift_info["is_working"]:
        st.info(f"🕐 **{shift_info['shift_name']}** | {t.get('dashboard_shift_info', 'Actual Working Hours')}: {shift_info['working_hours']} {t.get('hours_word', 'hrs')} | {t.get('dashboard_break_info', 'Breaks')}: {shift_info['total_break_hours']} {t.get('hours_word', 'hrs')}")
    else:
        break_desc = shift_info["current_break"]
        # ✅ ترجمة نص البريك بالكامل
        if current_lang == 'en':
            st.warning(f"☕ **Break Time** | From {break_desc['start'].strftime('%H:%M')} to {break_desc['end'].strftime('%H:%M')} | Duration: {break_desc['duration']} hours")
        else:
            st.warning(f"☕ **{t.get('break_time', 'وقت بريك')}** | من {break_desc['start'].strftime('%H:%M')} إلى {break_desc['end'].strftime('%H:%M')} | المدة: {break_desc['duration']} ساعة")

def show_marquee(df_raw, df_main, df_fg, t, lang, selected_line):
    """Display marquee with recommendations - CLEAN VERSION"""
    recommendations = get_marquee_recommendations(df_raw, df_main, df_fg, t, lang, selected_line)
    
    # بناء عناصر الشريط
    items = []
    for rec in recommendations:
        # تحديد لون الخلفية
        if "🔴" in rec or "⚠️" in rec:
            bg = "#dc2626"
        elif "🟡" in rec or "📦" in rec:
            bg = "#ea580c"
        elif "🏭" in rec:
            bg = "#2563eb"
        else:
            bg = "#16a34a"
        
        items.append(f'<span style="background:{bg};color:white;padding:8px 20px;border-radius:40px;margin:0 10px;display:inline-block;font-size:16px;font-weight:bold;white-space:nowrap;">{rec}</span>')
    
    # تكرار العناصر
    all_items = "".join(items) + "".join(items)
    
    st.markdown(f'''
    <div style="background:#1e293b;border-radius:50px;padding:12px 0;margin:15px 0;overflow:hidden;">
        <div style="display:inline-block;white-space:nowrap;animation:scrollLine 25s linear infinite;">
            {all_items}
        </div>
    </div>
    <style>
        @keyframes scrollLine {{
            0% {{ transform:translateX(0); }}
            100% {{ transform:translateX(-50%); }}
        }}
    </style>
    ''', unsafe_allow_html=True)


# dashboard.py - استبدل دالة show_dashboard بهذه النسخة المحسنة



def show_dashboard(df_main, df_raw, df_fg, t, selected_line):
    """Display dashboard page with enhanced features"""
    lang = st.session_state.get('lang', 'ar')
    
    st.markdown(f'<h1 class="gradient-title">🏭 Smart Factory - {t["dashboard_title"]}</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # عرض معلومات الوردية
    show_shift_info_dashboard(t)
    
    # عرض التنبيهات
    show_alerts_panel(t)
    period, chart_type, compare_lines = show_quick_filters(t)
    start_date, end_date = get_date_range_from_period(period)
    
    # فلترة البيانات حسب الفترة المحددة
    if df_main is not None and not df_main.empty and 'date' in df_main.columns:
        df_main['date'] = pd.to_datetime(df_main['date'])
        mask = (df_main['date'] >= start_date) & (df_main['date'] <= end_date)
        filtered_df = df_main[mask].copy()
    else:
        filtered_df = df_main
    
    # عرض بطاقات KPIs المتقدمة
    show_kpi_cards(filtered_df, t)
    
    st.markdown("---")
    
    # عرض مقاييس الأداء
    st.subheader(t.get("performance_metrics", "📊 Performance Metrics"))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if filtered_df is not None and not filtered_df.empty:
            prod_df = filtered_df[filtered_df['type'] == 'Production'] if 'type' in filtered_df.columns else filtered_df
            if not prod_df.empty:
                avg_oee = prod_df['oee'].mean() if 'oee' in prod_df.columns else 0
                show_performance_gauge(avg_oee, t.get("overall_oee", "Overall OEE"), 85, t)
    
    with col2:
        if filtered_df is not None and not filtered_df.empty:
            prod_df = filtered_df[filtered_df['type'] == 'Production'] if 'type' in filtered_df.columns else filtered_df
            if not prod_df.empty:
                avg_efficiency = prod_df['efficiency'].mean() if 'efficiency' in prod_df.columns else 0
                show_performance_gauge(avg_efficiency, t.get("overall_efficiency", "Overall Efficiency"), 80, t)
    
    # عرض اتجاه الإنتاج
    st.markdown("---")
    show_production_trend(filtered_df, t, days=30)
    
    # عرض مقارنة الخطوط
    if compare_lines:
        st.markdown("---")
        show_line_comparison(filtered_df, t)
    
    # عرض التوصيات الذكية
    if df_raw is not None and df_fg is not None:
        st.markdown("---")
        show_marquee(df_raw, filtered_df, df_fg, t, lang, selected_line)
    
    # عرض حالة المخزون
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📦 {t['raw_balance']}")
        if df_raw is not None and not df_raw.empty:
            # اختيار عمود الاسم حسب اللغة
            name_col = 'Material_Name_EN' if lang == 'en' and 'Material_Name_EN' in df_raw.columns else 'Material_Name_AR'
            qty_col = 'Current_Stock'
            
            raw_chart = df_raw.nlargest(10, qty_col)[[name_col, qty_col]].copy()
            raw_chart = raw_chart.rename(columns={
                name_col: t.get("chart_material", "Material"),
                qty_col: t.get("chart_quantity", "Quantity"),
            })
            fig_raw = px.bar(
                raw_chart,
                x=t.get("chart_material", "Material"),
                y=t.get("chart_quantity", "Quantity"),
                title=t.get("chart_raw_title", "Raw Materials"),
                color=t.get("chart_quantity", "Quantity"),
                color_continuous_scale="Blues",
                text=t.get("chart_quantity", "Quantity"),
            )
            fig_raw.update_traces(textposition='outside')
            fig_raw.update_layout(height=400)
            st.plotly_chart(fig_raw, use_container_width=True)
        else:
            st.info(t.get("no_raw_data", "No raw materials data"))
    
    with col2:
        st.subheader(f"🏭 {t['fg_balance']}")
        if df_fg is not None and not df_fg.empty:
            fg_chart = df_fg[["Name", "Balance"]].copy()
            fg_chart = fg_chart.rename(columns={
                "Name": t.get("chart_product", "Product"),
                "Balance": t.get("balance", "Balance"),
            })
            fig_fg = px.bar(
                fg_chart,
                x=t.get("chart_product", "Product"),
                y=t.get("balance", "Balance"),
                title=t.get("chart_fg_title", "Finished Goods"),
                color=t.get("balance", "Balance"),
                color_continuous_scale="Greens",
                text=t.get("balance", "Balance"),
            )
            fig_fg.update_traces(textposition='outside')
            fig_fg.update_layout(height=400)
            st.plotly_chart(fig_fg, use_container_width=True)
        else:
            st.info(t.get("no_fg_data", "No finished goods data"))
    
    # عرض مدة نفاذ المواد الخام
    show_materials_depletion_status(df_raw, filtered_df, selected_line, t)
    # عرض تحليلات توقع الأعطال (للمسؤول فقط)
    if st.session_state.get('user_role') == 'admin':
        st.markdown("---")
        from predictive_analytics import show_predictive_analytics
        show_predictive_analytics(t, selected_line)
        # ✅ ==================== إضافة توصيات المواد الخام ====================
    st.markdown("---")
    st.subheader("📦 " + t.get("smart_recommendations", "Smart Recommendations"))
    
    # توصيات إعادة الطلب
    if df_raw is not None and not df_raw.empty:
        reorder_suggestions = get_auto_reorder_suggestions(df_raw, df_main)
        
        if reorder_suggestions:
            col1, col2 = st.columns(2)
            
            # المواد الحرجة (high urgency)
            critical_items = [r for r in reorder_suggestions if r['urgency'] == 'high']
            if critical_items:
                with col1:
                    st.markdown("#### 🔴 " + t.get("critical_reorder", "Critical - Need Immediate Action"))
                    for rec in critical_items[:5]:
                        st.error(f"""
                        **{rec['material']}**
                        - {t.get('balance_label', 'Balance')}: {rec['current']:,}
                        - {t.get('min_label', 'Min')}: {rec['min_stock']:,}
                        - {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
                        """)
            
            # المواد التنبيهية (medium urgency)
            warning_items = [r for r in reorder_suggestions if r['urgency'] == 'medium']
            if warning_items:
                with col2:
                    st.markdown("#### 🟡 " + t.get("warning_reorder", "Warning - Plan Reorder Soon"))
                    for rec in warning_items[:5]:
                        st.warning(f"""
                        **{rec['material']}**
                        - {t.get('balance_label', 'Balance')}: {rec['current']:,}
                        - {t.get('min_label', 'Min')}: {rec['min_stock']:,}
                        - {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
                        """)
        else:
            st.success("✅ " + t.get("all_good", "All materials are above minimum stock levels"))    