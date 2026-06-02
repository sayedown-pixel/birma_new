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
from helpers import clean_line_name
from helpers import normalize_line_name
from datetime import timedelta
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
            st.dataframe(df_depletion, width='stretch', hide_index=True)
            
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
# dashboard.py - استبدل دالة show_shift_info_dashboard

def show_shift_info_dashboard(t):
    """عرض معلومات الوردية في لوحة التحكم - مع معالجة شاملة للأخطاء"""
    try:
        from utils import get_shift_info
        
        shift_info = get_shift_info()
        
        # الحصول على اللغة الحالية
        current_lang = st.session_state.get('lang', 'ar')
        
        if shift_info["is_working"]:
            st.info(f"🕐 **{shift_info['shift_name']}** | {t.get('dashboard_shift_info', 'Actual Working Hours')}: {shift_info['working_hours']} {t.get('hours_word', 'hrs')} | {t.get('dashboard_break_info', 'Breaks')}: {shift_info['total_break_hours']} {t.get('hours_word', 'hrs')}")
        else:
            break_desc = shift_info.get("current_break", {})
            
            # ✅ التحقق الشامل من نوع break_desc
            if isinstance(break_desc, dict) and break_desc:
                # إذا كان قاموساً (كما هو متوقع)
                start_time = break_desc.get('start')
                end_time = break_desc.get('end')
                duration = break_desc.get('duration', 0)
                
                # تنسيق الوقت إذا كان كائن datetime
                start_str = ''
                if start_time is not None:
                    if hasattr(start_time, 'strftime'):
                        start_str = start_time.strftime('%H:%M')
                    else:
                        start_str = str(start_time)
                else:
                    start_str = "N/A"
                
                end_str = ''
                if end_time is not None:
                    if hasattr(end_time, 'strftime'):
                        end_str = end_time.strftime('%H:%M')
                    else:
                        end_str = str(end_time)
                else:
                    end_str = "N/A"
                
                # تحويل duration إلى string آمن
                duration_str = str(duration) if duration is not None else "0"
                
                if current_lang == 'en':
                    st.warning(f"☕ **Break Time** | From {start_str} to {end_str} | Duration: {duration_str} hours")
                else:
                    st.warning(f"☕ **{t.get('break_time', 'وقت بريك')}** | من {start_str} إلى {end_str} | المدة: {duration_str} ساعة")
            else:
                # إذا كان نصاً أو قيمة أخرى (fallback)
                break_str = str(break_desc) if break_desc else "وقت استراحة"
                if current_lang == 'en':
                    st.warning(f"☕ **Break Time** | {break_str}")
                else:
                    st.warning(f"☕ **{t.get('break_time', 'وقت بريك')}** | {break_str}")
    except Exception as e:
        import logging
        logging.error(f"Error in show_shift_info_dashboard: {e}")
        st.warning(f"⚠️ {t.get('shift_info_error', 'Unable to display shift information')}")

# dashboard.py - استبدل الدوال التالية

def show_marquee(df_raw, df_main, df_fg, t, lang, selected_line):
    """Display marquee with recommendations - شريط متحرك في أعلى الصفحة"""
    from utils import calculate_days_until_depletion
    
    recommendations = []
    en = lang == "en"
    
    # ✅ استخدام مدة النفاذ كمصدر رئيسي للتنبيهات
    df_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_depletion is not None and not df_depletion.empty and 'Days_Until_Depletion' in df_depletion.columns:
        name_col = 'Material_Display_Name'
        if name_col not in df_depletion.columns:
            name_col = 'Material_Name_AR'
        
        # ترتيب حسب الأيام المتبقية
        df_sorted = df_depletion.sort_values('Days_Until_Depletion')
        
        for _, row in df_sorted.iterrows():
            days = row['Days_Until_Depletion']
            material_name = row[name_col]
            current_stock = row.get('Current_Stock', 0)
            
            if days <= 30:  # عرض المواد التي ستنفذ خلال 30 يوم
                if days <= 3:
                    recommendations.append(f"🔴 {material_name}: متبقي {current_stock:,.0f} - سينفذ خلال {days:.0f} يوم ⚠️ عاجل!")
                elif days <= 7:
                    recommendations.append(f"🔴 {material_name}: سينفذ خلال {days:.0f} يوم")
                elif days <= 14:
                    recommendations.append(f"🟡 {material_name}: سينفذ خلال {days:.0f} يوم")
                else:
                    recommendations.append(f"🟢 {material_name}: متبقي {days:.0f} يوم")
    
    # تنبيهات المنتج التام
    if df_fg is not None and not df_fg.empty and "Balance" in df_fg.columns:
        fg_balance = df_fg["Balance"].sum()
        if fg_balance <= 0:
            recommendations.append(f"🏭 {t.get('fg_balance', 'Finished Goods')}: {t.get('marquee_fg_empty', 'فارغ - يرجى زيادة الإنتاج')}")
        elif fg_balance < 10000:
            recommendations.append(f"📦 {t.get('fg_balance', 'Finished Goods')}: {fg_balance:,.0f} {t.get('marquee_fg_units', 'وحدة')}")
    
    if not recommendations:
        recommendations.append(f"✅ {t.get('all_good', 'All good' if en else 'جميع المواد آمنة')} ✅")
    
    # بناء عناصر الشريط
    items = []
    for rec in recommendations[:15]:
        if "🔴" in rec:
            bg = "#dc2626"
        elif "🟡" in rec:
            bg = "#ea580c"
        elif "🏭" in rec or "📦" in rec:
            bg = "#2563eb"
        else:
            bg = "#16a34a"
        
        items.append(f'<span style="background:{bg};color:white;padding:8px 20px;border-radius:40px;margin:0 10px;display:inline-block;font-size:14px;font-weight:bold;white-space:nowrap;">{rec}</span>')
    
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


def show_smart_recommendations(df_raw, df_main, selected_line, t):
    """عرض التوصيات الذكية في أسفل لوحة القيادة (أعمدة منفصلة)"""
    from utils import get_auto_reorder_suggestions, get_stock_prediction_calculated
    from helpers import send_telegram
    
    current_lang = st.session_state.get('lang', 'ar')
    
    st.markdown("---")
    st.subheader("📊 " + t.get("smart_recommendations", "Smart Recommendations"))
    
    # ==================== العمود الأول: توصيات إعادة الطلب ====================
    st.markdown("#### 📦 " + t.get("auto_reorder", "Auto Reorder Alert"))
    
    reorder_suggestions = get_auto_reorder_suggestions(df_raw, df_main)
    
    if reorder_suggestions:
        # تقسيم حسب الخطورة
        critical_items = [r for r in reorder_suggestions if r['urgency'] == 'high']
        warning_items = [r for r in reorder_suggestions if r['urgency'] == 'medium']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if critical_items:
                st.markdown("##### 🔴 " + t.get("critical_reorder", "Critical - Need Immediate Action"))
                for rec in critical_items[:5]:
                    percentage = (rec['current'] / rec['min_stock'] * 100) if rec['min_stock'] > 0 else 0
                    st.error(f"""
                    **{rec['material']}**
                    - {t.get('balance_label', 'Balance')}: {rec['current']:,}
                    - {t.get('min_label', 'Min')}: {rec['min_stock']:,}
                    - {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
                    - النسبة: {percentage:.0f}%
                    """)
            else:
                st.info("✅ لا توجد مواد حرجة")
        
        with col2:
            if warning_items:
                st.markdown("##### 🟡 " + t.get("warning_reorder", "Warning - Plan Reorder Soon"))
                for rec in warning_items[:5]:
                    percentage = (rec['current'] / rec['min_stock'] * 100) if rec['min_stock'] > 0 else 0
                    st.warning(f"""
                    **{rec['material']}**
                    - {t.get('balance_label', 'Balance')}: {rec['current']:,}
                    - {t.get('min_label', 'Min')}: {rec['min_stock']:,}
                    - {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
                    - النسبة: {percentage:.0f}%
                    """)
            else:
                st.info("✅ لا توجد مواد تنبيه")
    else:
        st.success("✅ " + t.get("all_good", "All materials are above minimum stock levels"))
    
    # ==================== العمود الثاني: توقع نفاذ المخزون ====================
    st.markdown("---")
    st.markdown("#### ⏰ " + t.get("stock_prediction", "Stock Depletion Prediction"))
    
    stock_predictions = get_stock_prediction_calculated(df_raw, df_main, selected_line)
    
    if stock_predictions:
        # عرض المواد التي ستنفذ خلال 30 يوم
        critical_pred = [p for p in stock_predictions if p['status'] == 'critical']
        warning_pred = [p for p in stock_predictions if p['status'] == 'warning']
        info_pred = [p for p in stock_predictions if p['status'] == 'info']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if critical_pred:
                st.markdown("##### 🔴 " + t.get("critical_depletion", "Critical - Will run out soon"))
                for pred in critical_pred[:5]:
                    st.error(f"""
                    **{pred['material']}**
                    - {t.get('balance_label', 'Balance')}: {pred['current']:,}
                    - {t.get('will_run_out', 'Will run out in')}: {pred['days_left']} {t.get('days_word', 'days')}
                    """)
        
        with col2:
            if warning_pred:
                st.markdown("##### 🟡 " + t.get("warning_depletion", "Warning - Will run out within 14 days"))
                for pred in warning_pred[:5]:
                    st.warning(f"""
                    **{pred['material']}**
                    - {t.get('balance_label', 'Balance')}: {pred['current']:,}
                    - {t.get('will_run_out', 'Will run out in')}: {pred['days_left']} {t.get('days_word', 'days')}
                    """)
        
        with col3:
            if info_pred:
                st.markdown("##### 🟢 " + t.get("info_depletion", "Info - Will run out within 30 days"))
                for pred in info_pred[:5]:
                    st.info(f"""
                    **{pred['material']}**
                    - {t.get('balance_label', 'Balance')}: {pred['current']:,}
                    - {t.get('will_run_out', 'Will run out in')}: {pred['days_left']} {t.get('days_word', 'days')}
                    """)
    else:
        st.success("✅ " + t.get("all_good", "All materials have sufficient stock"))
    
    # ==================== العمود الثالث: توصيات إضافية ====================
    st.markdown("---")
    st.markdown("#### 💡 " + t.get("additional_recommendations", "Additional Recommendations"))
    
    # عرض إحصائيات سريعة
    if df_raw is not None and not df_raw.empty:
        total_materials = len(df_raw)
        low_stock_count = len([r for r in reorder_suggestions]) if reorder_suggestions else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 إجمالي المواد", total_materials)
        with col2:
            st.metric("⚠️ مواد منخفضة", low_stock_count)
        with col3:
            st.metric("📊 تنبيهات نشطة", len(stock_predictions) if stock_predictions else 0)
        
        # زر تحديث البيانات
        if st.button("🔄 تحديث البيانات", key="refresh_recommendations"):
            st.cache_data.clear()
            st.session_state.inventory_version = st.session_state.get('inventory_version', 0) + 1
            st.rerun()
def send_stock_alerts(df_raw, t):
    """إرسال تنبيهات المخزون المنخفض عبر Telegram بناءً على مدة النفاذ"""
    from helpers import send_telegram
    from utils import calculate_days_until_depletion
    
    print("\n" + "=" * 40)
    print("🔍 DEBUG: send_stock_alerts called")
    print("=" * 40)
    
    if df_raw is None or df_raw.empty:
        print("❌ df_raw is None or empty")
        return
    
    current_lang = st.session_state.get('lang', 'ar')
    
    # ✅ حساب مدة نفاذ المواد
    df_depletion = calculate_days_until_depletion(df_raw, None, None)
    
    if df_depletion is None or df_depletion.empty:
        print("❌ No depletion data")
        return
    
    if 'Days_Until_Depletion' not in df_depletion.columns:
        print("❌ Days_Until_Depletion column not found")
        return
    
    # تحديد عمود الاسم
    name_col = 'Material_Display_Name'
    if name_col not in df_depletion.columns:
        name_col = 'Material_Name_AR'
    
    print(f"\n📊 Processing {len(df_depletion)} materials")
    
    # إرسال تنبيهات لجميع المواد التي ستنفذ خلال 30 يوم
    for _, row in df_depletion.iterrows():
        try:
            days = float(row['Days_Until_Depletion']) if pd.notna(row['Days_Until_Depletion']) else 999
            material_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
            current_stock = float(row.get('Current_Stock', 0)) if pd.notna(row.get('Current_Stock', 0)) else 0
            
            # ✅ تنبيه للمواد التي ستنفذ خلال 30 يوم
            if days <= 30:
                if days <= 7:
                    urgency = "critical"
                    icon = "🔴"
                    title = "تنبيه عاجل: مخزون حرج - سينفذ خلال أيام!"
                elif days <= 14:
                    urgency = "warning"
                    icon = "🟡"
                    title = "تنبيه: مخزون منخفض - سينفذ خلال أسبوعين"
                else:
                    urgency = "info"
                    icon = "🔵"
                    title = "تنبيه: مخزون سي少 خلال شهر"
                
                # التحقق من عدم إرسال نفس التنبيه مراراً (مرة كل 24 ساعة)
                alert_key = f"stock_alert_{urgency}_{material_name}"
                last_sent = st.session_state.get(alert_key, "")
                
                # بسيط: نرسل مرة واحدة فقط لكل مادة
                if not st.session_state.get(alert_key, False):
                    print(f"📤 Sending {urgency} alert for: {material_name} (days left: {days:.1f})")
                    
                    if current_lang == 'ar':
                        msg = f"""{icon} <b>{title}</b>
📦 المادة: {material_name}
📊 المخزون: {current_stock:,.0f}
⏰ المتبقي: {days:.0f} يوم
📅 سينفذ بتاريخ: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}"""
                    else:
                        msg = f"""{icon} <b>Stock Alert</b>
📦 Material: {material_name}
📊 Stock: {current_stock:,.0f}
⏰ Days until depletion: {days:.0f}
📅 Depletion date: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}"""
                    
                    send_telegram(msg)
                    st.session_state[alert_key] = True
                    print(f"   ✅ Alert sent for {material_name}")
                else:
                    print(f"   ⏭️ Skipping {material_name} (already sent)")
                    
        except Exception as e:
            print(f"❌ Error processing {material_name}: {e}")



def show_dashboard(df_main, df_raw, df_fg, t, selected_line):
    """Display dashboard page with enhanced features"""
    from helpers import normalize_line_name, send_telegram
    from utils import get_auto_reorder_suggestions, get_stock_prediction_calculated
    
    line_display = normalize_line_name(selected_line)
    lang = st.session_state.get('lang', 'ar')
    
    st.markdown(f'<h1 class="gradient-title">🏭 Smart Factory - {t["dashboard_title"]}</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # عرض معلومات الوردية
    show_shift_info_dashboard(t)
    
    # عرض التنبيهات
    show_alerts_panel(t)
    
    # ==================== الشريط المتحرك (أعلى) ====================
    if df_raw is not None and df_fg is not None:
        show_marquee(df_raw, df_main, df_fg, t, lang, selected_line)
    
    # ==================== الفلاتر السريعة ====================
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
    
    # عرض حالة المخزون
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📦 {t['raw_balance']}")
        if df_raw is not None and not df_raw.empty:
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
            st.plotly_chart(fig_raw, width='stretch')
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
            st.plotly_chart(fig_fg, width='stretch')
        else:
            st.info(t.get("no_fg_data", "No finished goods data"))
    
    # عرض مدة نفاذ المواد الخام
    show_materials_depletion_status(df_raw, filtered_df, selected_line, t)
    
    # عرض تحليلات توقع الأعطال (للمسؤول فقط)
    if st.session_state.get('user_role') == 'admin':
        st.markdown("---")
        from predictive_analytics import show_predictive_analytics
        show_predictive_analytics(t, selected_line)
    
    # ==================== التوصيات الذكية (أسفل) ====================
    show_smart_recommendations(df_raw, df_main, selected_line, t)