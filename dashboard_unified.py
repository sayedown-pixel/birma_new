# dashboard_unified.py - النسخة المتكاملة النهائية مع دعم كامل للغة
# تم إصلاح جميع النصوص الثابتة لاستخدام الترجمة من constants.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from functools import lru_cache
import time

from utils import get_auto_reorder_suggestions, get_stock_prediction_calculated
from oee_analytics import show_oee_dashboard
from alerts_viewer import show_alerts_panel
from database import db_manager
from helpers import normalize_line_name, send_telegram


# ============================================================================
# 1. دوال مع Caching لتحسين الأداء
# ============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def _cache_production_data(line: str, days: int):
    """تخزين بيانات الإنتاج في cache"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    df = db_manager.get_all_production(start_date=start_date, end_date=end_date, line=line)
    
    if not df.empty and 'type' in df.columns:
        df = df[df['type'] == 'Production']
    
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cache_inventory_data():
    """تخزين بيانات المخزون في cache"""
    from inventory import get_raw_materials_df, get_finished_goods_df
    return get_raw_materials_df(), get_finished_goods_df()


# ============================================================================
# 2. بطاقات KPI - نسخة نظيفة باستخدام st.metric
# ============================================================================

def show_kpi_cards(df_main, t):
    """عرض بطاقات KPIs - نسخة نظيفة باستخدام st.metric فقط"""
    
    lang = st.session_state.get('lang', 'ar')
    
    # تهيئة القيم الافتراضية
    total_production = 0
    avg_efficiency = 0
    avg_oee = 0
    today_prod = 0
    change_percent = 0
    
    if df_main is not None and not df_main.empty:
        prod_df = df_main[df_main['type'] == 'Production'] if 'type' in df_main.columns else df_main
        
        if not prod_df.empty:
            if 'output_units' in prod_df.columns:
                total_production = prod_df['output_units'].sum()
            if 'efficiency' in prod_df.columns:
                avg_efficiency = prod_df['efficiency'].mean()
            if 'oee' in prod_df.columns:
                avg_oee = prod_df['oee'].mean()
            
            if 'date' in prod_df.columns:
                prod_df['date'] = pd.to_datetime(prod_df['date'])
                today = datetime.now().date()
                today_prod = prod_df[prod_df['date'].dt.date == today]['output_units'].sum()
                
                yesterday = today - timedelta(days=1)
                yesterday_prod = prod_df[prod_df['date'].dt.date == yesterday]['output_units'].sum()
                change_percent = ((today_prod - yesterday_prod) / yesterday_prod * 100) if yesterday_prod > 0 else 0
    
    # عرض البطاقات باستخدام st.metric فقط
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if change_percent >= 0 else "inverse"
        st.metric(
            t.get("today_production", "Today's Production"),
            f"{today_prod:,.0f}",
            delta=f"{change_percent:+.1f}%" if change_percent != 0 else None,
            delta_color=delta_color
        )
    
    with col2:
        st.metric(t.get("total_production", "Total Production"), f"{total_production:,.0f}")
    
    with col3:
        st.metric(t.get("avg_efficiency", "Avg Efficiency"), f"{avg_efficiency:.1f}%")
    
    with col4:
        st.metric(t.get("avg_oee", "Avg OEE"), f"{avg_oee:.1f}%")


def show_performance_gauge(value, title, target, t):
    """عرض مقياس دائري للأداء"""
    
    color = "#22c55e" if value >= target else "#eab308" if value >= target * 0.7 else "#ef4444"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 16}},
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color},
            "steps": [
                {"range": [0, target * 0.7], "color": "#fee2e2"},
                {"range": [target * 0.7, target], "color": "#fef3c7"},
                {"range": [target, 100], "color": "#dcfce7"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": target
            }
        },
        number={"suffix": "%", "font": {"size": 40}}
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 3. دوال الرسوم البيانية
# ============================================================================

def show_production_trend(df_main, t, days=30):
    """عرض اتجاه الإنتاج خلال الفترة"""
    
    if df_main is None or df_main.empty:
        st.info(t.get("no_data", "No data available"))
        return
    
    prod_df = df_main[df_main['type'] == 'Production'] if 'type' in df_main.columns else df_main
    
    if prod_df.empty:
        st.info(t.get("no_data", "No production data"))
        return
    
    prod_df['date'] = pd.to_datetime(prod_df['date']).dt.date
    daily_prod = prod_df.groupby('date').agg({
        'output_units': 'sum',
        'efficiency': 'mean',
        'oee': 'mean'
    }).reset_index()
    
    daily_prod = daily_prod.sort_values('date')
    
    if len(daily_prod) > days:
        daily_prod = daily_prod.tail(days)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=daily_prod['date'],
        y=daily_prod['output_units'],
        name=t.get("production", "Production"),
        marker_color='#3b82f6',
        yaxis="y"
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_prod['date'],
        y=daily_prod['efficiency'],
        name=t.get("efficiency", "Efficiency"),
        mode='lines+markers',
        line=dict(color='#f59e0b', width=2),
        yaxis="y2"
    ))
    
    fig.update_layout(
        title=t.get("production_trend", "Production Trend"),
        xaxis_title=t.get("date", "Date"),
        yaxis_title=t.get("quantity", "Quantity"),
        yaxis2=dict(
            title=t.get("percentage", "Percentage %"),
            overlaying="y",
            side="right",
            range=[0, 100]
        ),
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def show_line_comparison(df_main, t):
    """مقارنة أداء خطوط الإنتاج"""
    
    if df_main is None or df_main.empty:
        st.info(t.get("no_data", "No data available"))
        return
    
    prod_df = df_main[df_main['type'] == 'Production'] if 'type' in df_main.columns else df_main
    
    if prod_df.empty or 'line' not in prod_df.columns:
        st.info(t.get("no_production_data", "No production data for comparison"))
        return
    
    line_stats = prod_df.groupby('line').agg({
        'output_units': 'sum',
        'efficiency': 'mean',
        'oee': 'mean',
        'downtime_minutes': 'sum'
    }).round(1)
    
    st.subheader(t.get("line_performance", "📊 Line Performance Comparison"))
    
    lines = line_stats.index.tolist()
    cols = st.columns(len(lines))
    
    for i, line in enumerate(lines):
        with cols[i]:
            stats = line_stats.loc[line]
            line_display = normalize_line_name(line)
            st.metric(f"🏭 {line_display}", f"{stats['output_units']:,.0f}")
            st.caption(f"⚡ {t.get('efficiency', 'Efficiency')}: {stats['efficiency']:.1f}%")
            st.caption(f"📈 {t.get('avg_oee', 'OEE')}: {stats['oee']:.1f}%")
            st.caption(f"⏰ {t.get('downtime', 'Downtime')}: {stats['downtime_minutes']:.0f} min")


# ============================================================================
# 4. دوال الفلاتر والمساعدة - محسنة للدعم الثنائي اللغة
# ============================================================================

def show_quick_filters(t):
    """عرض فلاتر سريعة - دعم كامل للغة"""
    
    lang = st.session_state.get('lang', 'ar')
    
    # قوائم الفلاتر حسب اللغة
    if lang == 'ar':
        period_options = ["آخر 7 أيام", "آخر 30 يوم", "آخر 90 يوم", "هذا العام"]
        chart_options = ["الإنتاج", "الكفاءة", "OEE", "التوقف"]
    else:
        period_options = ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year"]
        chart_options = ["Production", "Efficiency", "OEE", "Downtime"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period = st.selectbox(
            t.get("select_period", "Select Period"),
            period_options,
            index=1,
            key="dashboard_period"
        )
    
    with col2:
        chart_type = st.selectbox(
            t.get("chart_type", "Chart Type"),
            chart_options,
            key="dashboard_chart_type"
        )
    
    with col3:
        compare_lines = st.checkbox(
            t.get("compare_lines", "Compare Lines"),
            value=True,
            key="dashboard_compare_lines"
        )
    
    return period, chart_type, compare_lines


def get_date_range_from_period(period):
    """تحويل الفترة إلى نطاق تواريخ"""
    end_date = datetime.now()
    
    # دعم كل من العربية والإنجليزية
    if period in ["آخر 7 أيام", "Last 7 Days"]:
        start_date = end_date - timedelta(days=7)
    elif period in ["آخر 30 يوم", "Last 30 Days"]:
        start_date = end_date - timedelta(days=30)
    elif period in ["آخر 90 يوم", "Last 90 Days"]:
        start_date = end_date - timedelta(days=90)
    else:  # "هذا العام", "This Year"
        start_date = datetime(end_date.year, 1, 1)
    
    return start_date, end_date


def auto_refresh_section(t):
    """إضافة خيار التحديث التلقائي"""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        auto_refresh = st.checkbox(t.get("auto_refresh", "🔄 Auto refresh every 30 seconds"), key="auto_refresh")
    
    with col2:
        if auto_refresh:
            if 'last_refresh' not in st.session_state:
                st.session_state.last_refresh = time.time()
            
            elapsed = time.time() - st.session_state.last_refresh
            if elapsed >= 30:
                st.session_state.last_refresh = time.time()
                st.cache_data.clear()
                st.rerun()
            
            st.caption(f"{t.get('last_update', 'Last update')}: {datetime.now().strftime('%H:%M:%S')}")
    
    with col3:
        if st.button(t.get("manual_refresh", "🔄 Manual Refresh"), key="manual_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    return auto_refresh


# ============================================================================
# 5. حالة المخزون والتوصيات - محسنة للدعم الثنائي اللغة
# ============================================================================

def show_materials_depletion_status(df_raw, df_main, selected_line, t):
    """عرض حالة نفاذ المواد الخام - دعم كامل للغة"""
    from utils import calculate_days_until_depletion
    
    lang = st.session_state.get('lang', 'ar')
    
    if df_raw is None or df_raw.empty:
        return
    
    df_with_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_with_depletion is None or df_with_depletion.empty:
        return
    
    if 'Days_Until_Depletion' not in df_with_depletion.columns:
        return
    
    st.markdown("---")
    st.subheader("📅 " + t.get("materials_depletion", "Materials Depletion Time"))
    
    # تحديد أسماء الأعمدة حسب اللغة
    if lang == 'en' and 'Material_Name_EN' in df_with_depletion.columns:
        material_col = 'Material_Name_EN'
    elif 'Material_Name_AR' in df_with_depletion.columns:
        material_col = 'Material_Name_AR'
    else:
        material_col = 'Material_Display_Name' if 'Material_Display_Name' in df_with_depletion.columns else None
    
    stock_col = "Current_Stock" if "Current_Stock" in df_with_depletion.columns else "Stock"
    
    if material_col and stock_col in df_with_depletion.columns:
        depletion_data = []
        for _, row in df_with_depletion.iterrows():
            try:
                days = float(row['Days_Until_Depletion']) if pd.notna(row['Days_Until_Depletion']) else 999
                current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
                mat_name = str(row[material_col]) if pd.notna(row[material_col]) else ""
                
                if days <= 30:
                    # استخدام الترجمة من القاموس
                    if days <= 0:
                        status_display = t.get("status_out_of_stock", "🔴 Out of Stock")
                    elif days <= 7:
                        status_display = t.get("status_critical", "🔴 Critical (less than 7 days)")
                    elif days <= 14:
                        status_display = t.get("status_warning", "🟡 Warning (7-14 days)")
                    else:
                        status_display = t.get("status_info", "🟢 Remaining") + f" ({days:.0f} {t.get('days_word', 'days')})"
                    
                    depletion_data.append({
                        t.get("material", "Material"): mat_name,
                        t.get("current_stock", "Current Stock"): f"{int(current_stock):,}",
                        t.get("days_left", "Days Left"): f"{days:.1f}",
                        t.get("status", "Status"): status_display
                    })
            except Exception:
                continue
        
        if depletion_data:
            depletion_data.sort(key=lambda x: float(x[t.get("days_left", "Days Left")]))
            df_depletion = pd.DataFrame(depletion_data)
            st.dataframe(df_depletion, use_container_width=True, hide_index=True)



# dashboard_unified.py - تحديث الأجزاء الثابتة

def show_smart_recommendations(df_raw, df_main, selected_line, t):
    """عرض التوصيات الذكية - مع دعم كامل للغة"""
    
    st.markdown("---")
    st.subheader("📊 " + t.get("smart_recommendations", "Smart Recommendations"))
    
    # ==================== توصيات إعادة الطلب ====================
    st.markdown("#### 📦 " + t.get("auto_reorder", "Auto Reorder Alert"))
    
    reorder_suggestions = get_auto_reorder_suggestions(df_raw, df_main)
    
    critical_items = [r for r in reorder_suggestions if r.get('urgency') == 'critical']
    warning_items = [r for r in reorder_suggestions if r.get('urgency') == 'warning']
    
    lang = st.session_state.get('lang', 'ar')
    
    # عرض المواد الحرجة
    if critical_items:
        st.markdown(f"##### {t.get('critical_reorder', '🔴 Critical - Need Immediate Action')}")
        
        for rec in critical_items:
            if rec.get('current', 0) <= 0:
                # ✅ استخدام الترجمة
                out_of_stock_msg = t.get("out_of_stock_completely", "🚨 **{material}** - **Out of stock completely!**")
                st.error(out_of_stock_msg.format(material=rec['material']))
                st.error(f"""
- {t.get('balance_label', 'Balance')}: **0**
- {t.get('min_label', 'Min')}: {rec['min_stock']:,}
- {t.get('suggested_reorder', 'Suggested')}: **{rec['suggested_qty']:,}**
""")
            else:
                st.error(f"""
🔴 **{rec['material']}**
- {t.get('balance_label', 'Balance')}: {rec['current']:,}
- {t.get('min_label', 'Min')}: {rec['min_stock']:,}
- {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
- {t.get('percentage_of_min', 'Percentage of min')}: {rec.get('percentage', 0)}%
""")
    else:
        st.info(f"✅ {t.get('no_critical', 'No critical materials')}")
    
    # عرض المواد التحذيرية
    if warning_items:
        st.markdown(f"##### {t.get('warning_reorder', '🟡 Warning - Plan Reorder Soon')}")
        
        for rec in warning_items:
            st.warning(f"""
🟡 **{rec['material']}**
- {t.get('balance_label', 'Balance')}: {rec['current']:,}
- {t.get('min_label', 'Min')}: {rec['min_stock']:,}
- {t.get('suggested_reorder', 'Suggested')}: {rec['suggested_qty']:,}
- {t.get('percentage_of_min', 'Percentage of min')}: {rec.get('percentage', 0)}%
""")
    else:
        if not critical_items:
            st.info(f"✅ {t.get('no_warning', 'No warning materials')}")
    
    # ✅ عرض إجمالي المواد المنخفضة مع ترجمة
    total_low = len(critical_items) + len(warning_items)
    if total_low > 0:
        total_msg = t.get("total_low_materials", "📊 Total low materials: {count} items ({critical} critical, {warning} warning)")
        st.caption(total_msg.format(
            count=total_low, 
            critical=len(critical_items), 
            warning=len(warning_items)
        ))
    
    # ==================== توقع نفاذ المخزون ====================
    st.markdown("---")
    st.markdown("#### ⏰ " + t.get("stock_prediction", "Stock Depletion Prediction"))
    
    stock_predictions = get_stock_prediction_calculated(df_raw, df_main, selected_line)
    
    if stock_predictions:
        critical_pred = [p for p in stock_predictions if p.get('status') == 'critical']
        warning_pred = [p for p in stock_predictions if p.get('status') == 'warning']
        
        if critical_pred:
            for pred in critical_pred:
                if pred.get('days_left', 0) <= 0:
                    st.error(t.get("out_of_stock_completely", "🚨 **{material}** - **Out of stock completely!**").format(material=pred['material']))
                else:
                    st.error(f"🔴 **{pred['material']}** - {t.get('will_run_out', 'Will run out in')} {pred['days_left']} {t.get('days_word', 'days')}")
        
        if warning_pred:
            for pred in warning_pred:
                st.warning(f"🟡 **{pred['material']}** - {t.get('will_run_out', 'Will run out in')} {pred['days_left']} {t.get('days_word', 'days')}")
        
        if not critical_pred and not warning_pred:
            st.success(f"✅ {t.get('all_good', 'All materials have sufficient stock')}")
    else:
        st.success(f"✅ {t.get('all_good', 'All materials have sufficient stock')}")
    
    # زر تحديث
    if st.button(t.get("refresh_data", "🔄 Refresh Data"), key="refresh_recommendations"):
        st.cache_data.clear()
        st.session_state.inventory_version = st.session_state.get('inventory_version', 0) + 1
        st.rerun()


def show_oee_average(oee_value, t):
    """عرض متوسط OEE مع ترجمة"""
    lang = st.session_state.get('lang', 'ar')
    
    if oee_value >= 85:
        level = t.get("oee_excellent", "Excellent")
        if lang == 'ar':
            level = t.get("oee_excellent_ar", "ممتاز")
        st.success(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=oee_value, level=level))
    elif oee_value >= 60:
        level = t.get("oee_acceptable", "Acceptable")
        if lang == 'ar':
            level = t.get("oee_acceptable_ar", "مقبول")
        st.info(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=oee_value, level=level))
    else:
        level = t.get("oee_poor", "Poor - Needs improvement")
        if lang == 'ar':
            level = t.get("oee_poor_ar", "منخفض - يحتاج تحسين")
        st.warning(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=oee_value, level=level))
        st.rerun()

def show_shift_info_dashboard(t):
    """عرض معلومات الوردية"""
    try:
        from utils import get_shift_info
        
        shift_info = get_shift_info()
        lang = st.session_state.get('lang', 'ar')
        
        if shift_info.get("is_working", True):
            working_hours = shift_info.get('working_hours', 15)
            st.info(f"🕐 **{shift_info.get('shift_name', 'Shift')}** | {t.get('dashboard_shift_info', 'Actual Working Hours')}: {working_hours} {t.get('hours_word', 'hrs')}")
        else:
            st.warning(f"☕ **{t.get('break_time', 'Break Time')}**")
    except Exception as e:
        st.info(f"🕐 {t.get('shift_single', 'Single Shift (8:00 AM - 2:00 AM)')}")


def show_marquee(df_raw, df_main, df_fg, t, lang, selected_line):
    """عرض شريط التوصيات المتحرك - دعم كامل للغة"""
    from utils import calculate_days_until_depletion
    
    recommendations = []
    
    df_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_depletion is not None and not df_depletion.empty and 'Days_Until_Depletion' in df_depletion.columns:
        if lang == 'en' and 'Material_Name_EN' in df_depletion.columns:
            name_col = 'Material_Name_EN'
        elif 'Material_Name_AR' in df_depletion.columns:
            name_col = 'Material_Name_AR'
        else:
            name_col = 'Material_Display_Name' if 'Material_Display_Name' in df_depletion.columns else None
        
        if name_col:
            df_sorted = df_depletion.sort_values('Days_Until_Depletion')
            
            for _, row in df_sorted.iterrows():
                days = row['Days_Until_Depletion']
                material_name = row[name_col] if name_col in row else ""
                current_stock = row.get('Current_Stock', 0)
                
                if days <= 30:
                    if days <= 3:
                        if lang == 'ar':
                            recommendations.append(f"🔴 {material_name}: متبقي {current_stock:,.0f} - سينفذ خلال {days:.0f} يوم ⚠️ عاجل!")
                        else:
                            recommendations.append(f"🔴 {material_name}: {current_stock:,.0f} left - runs out in {days:.0f} days ⚠️ CRITICAL!")
                    elif days <= 7:
                        if lang == 'ar':
                            recommendations.append(f"🔴 {material_name}: سينفذ خلال {days:.0f} يوم")
                        else:
                            recommendations.append(f"🔴 {material_name}: runs out in {days:.0f} days")
                    elif days <= 14:
                        if lang == 'ar':
                            recommendations.append(f"🟡 {material_name}: سينفذ خلال {days:.0f} يوم")
                        else:
                            recommendations.append(f"🟡 {material_name}: runs out in {days:.0f} days")
                    else:
                        if lang == 'ar':
                            recommendations.append(f"🟢 {material_name}: متبقي {days:.0f} يوم")
                        else:
                            recommendations.append(f"🟢 {material_name}: {days:.0f} days left")
    
    if df_fg is not None and not df_fg.empty and "Balance" in df_fg.columns:
        fg_balance = df_fg["Balance"].sum()
        if fg_balance <= 0:
            if lang == 'ar':
                recommendations.append(f"🏭 {t.get('fg_balance', 'Finished Goods')}: {t.get('marquee_fg_empty', 'empty - increase production')}")
            else:
                recommendations.append(f"🏭 {t.get('fg_balance', 'Finished Goods')}: {t.get('marquee_fg_empty', 'empty - increase production')}")
    
    if not recommendations:
        if lang == 'ar':
            recommendations.append(f"✅ {t.get('all_good', 'All good')} ✅")
        else:
            recommendations.append(f"✅ {t.get('all_good', 'All good')} ✅")
    
    # عرض الشريط المتحرك
    items = []
    for rec in recommendations[:10]:
        if "🔴" in rec:
            bg = "#dc2626"
        elif "🟡" in rec:
            bg = "#ea580c"
        else:
            bg = "#16a34a"
        
        items.append(f'<span style="background:{bg};color:white;padding:6px 16px;border-radius:40px;margin:0 8px;display:inline-block;font-size:13px;white-space:nowrap;">{rec}</span>')
    
    all_items = "".join(items) + "".join(items)
    
    st.markdown(f'''
    <div style="background:#1e293b;border-radius:50px;padding:10px 0;margin:15px 0;overflow:hidden;">
        <div style="display:inline-block;white-space:nowrap;animation:scrollLine 20s linear infinite;">
            {all_items}
        </div>
    </div>
    <style>
        @keyframes scrollLine {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
        }}
    </style>
    ''', unsafe_allow_html=True)


def send_stock_alerts(df_raw, t):
    """إرسال تنبيهات المخزون عبر Telegram"""
    from utils import calculate_days_until_depletion
    
    if df_raw is None or df_raw.empty:
        return
    
    df_depletion = calculate_days_until_depletion(df_raw, None, None)
    
    if df_depletion is None or df_depletion.empty:
        return
    
    if 'Days_Until_Depletion' not in df_depletion.columns:
        return
    
    lang = st.session_state.get('lang', 'ar')
    
    if lang == 'en' and 'Material_Name_EN' in df_depletion.columns:
        name_col = 'Material_Name_EN'
    elif 'Material_Name_AR' in df_depletion.columns:
        name_col = 'Material_Name_AR'
    else:
        name_col = 'Material_Display_Name' if 'Material_Display_Name' in df_depletion.columns else None
    
    if not name_col:
        return
    
    for _, row in df_depletion.iterrows():
        try:
            days = float(row['Days_Until_Depletion']) if pd.notna(row['Days_Until_Depletion']) else 999
            material_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
            
            if 0 < days <= 7:
                alert_key = f"stock_alert_critical_{material_name}"
                if not st.session_state.get(alert_key, False):
                    if lang == 'ar':
                        msg = f"🔴 تنبيه عاجل: {material_name}\nسينفذ خلال {days:.0f} يوم"
                    else:
                        msg = f"🔴 CRITICAL Alert: {material_name}\nWill run out in {days:.0f} days"
                    #send_telegram(msg)
                    st.session_state[alert_key] = True
        except Exception:
            continue


# ============================================================================
# 6. الدالة الرئيسية للـ Dashboard
# ============================================================================

# dashboard_unified.py - دالة show_dashboard كاملة

def show_dashboard(df_main, df_raw, df_fg, t, selected_line):
    """الدالة الرئيسية للوحة التحكم - دعم كامل للغة"""
    
    # إرسال تنبيهات المخزون
    send_stock_alerts(df_raw, t)
    
    lang = st.session_state.get('lang', 'ar')
    
    # العنوان حسب اللغة
    if lang == 'ar':
        title_text = t.get("dashboard_title_text_ar", "🏭 نظام المصنع الذكي")
        subtitle_text = t.get("dashboard_subtitle_text_ar", "لوحة القيادة الرئيسية")
    else:
        title_text = "🏭 Smart Factory System"
        subtitle_text = "Main Dashboard"
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: #1e3a5f;">{title_text}</h1>
        <p style="color: #64748b;">{subtitle_text}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # معلومات الوردية والتنبيهات
    show_shift_info_dashboard(t)
    #show_alerts_panel(t)
    
    # الشريط المتحرك
    if df_raw is not None and df_fg is not None:
        show_marquee(df_raw, df_main, df_fg, t, lang, selected_line)
    
    # خيار التحديث التلقائي
    auto_refresh_section(t)
    
    # الفلاتر السريعة
    period, chart_type, compare_lines = show_quick_filters(t)
    start_date, end_date = get_date_range_from_period(period)
    
    # تحميل البيانات مع Caching
    with st.spinner(t.get("loading_data", "Loading data...")):
        df_cached = _cache_production_data(selected_line, days=90)
        
        if df_cached.empty:
            df_filtered = df_main
        else:
            df_filtered = df_cached
    
    # فلترة حسب التاريخ
    if df_filtered is not None and not df_filtered.empty and 'date' in df_filtered.columns:
        df_filtered['date'] = pd.to_datetime(df_filtered['date'])
        mask = (df_filtered['date'] >= start_date) & (df_filtered['date'] <= end_date)
        filtered_df = df_filtered[mask].copy()
    else:
        filtered_df = df_filtered
    
    # بطاقات KPIs
    show_kpi_cards(filtered_df, t)
    
    st.markdown("---")
    
    # ==================== مقاييس الأداء ====================
    st.subheader(t.get("performance_metrics", "📊 Performance Metrics"))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if filtered_df is not None and not filtered_df.empty:
            prod_df = filtered_df[filtered_df['type'] == 'Production'] if 'type' in filtered_df.columns else filtered_df
            if not prod_df.empty and 'oee' in prod_df.columns:
                avg_oee = prod_df['oee'].mean()
                show_performance_gauge(avg_oee, t.get("overall_oee", "Overall OEE"), 85, t)
    
    with col2:
        if filtered_df is not None and not filtered_df.empty:
            prod_df = filtered_df[filtered_df['type'] == 'Production'] if 'type' in filtered_df.columns else filtered_df
            if not prod_df.empty and 'efficiency' in prod_df.columns:
                avg_efficiency = prod_df['efficiency'].mean()
                show_performance_gauge(avg_efficiency, t.get("overall_efficiency", "Overall Efficiency"), 80, t)
    
    # ==================== عرض متوسط OEE مع ترجمة ====================
    st.markdown("---")
    
    if filtered_df is not None and not filtered_df.empty:
        prod_df = filtered_df[filtered_df['type'] == 'Production'] if 'type' in filtered_df.columns else filtered_df
        if not prod_df.empty and 'oee' in prod_df.columns:
            avg_oee = prod_df['oee'].mean()
            
            # ✅ عرض متوسط OEE مع ترجمة كاملة
            if avg_oee >= 85:
                level = t.get("oee_excellent", "Excellent")
                if lang == 'ar':
                    level = t.get("oee_excellent_ar", "ممتاز")
                st.success(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=round(avg_oee, 1), level=level))
            elif avg_oee >= 60:
                level = t.get("oee_acceptable", "Acceptable")
                if lang == 'ar':
                    level = t.get("oee_acceptable_ar", "مقبول")
                st.info(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=round(avg_oee, 1), level=level))
            else:
                level = t.get("oee_poor", "Poor - Needs improvement")
                if lang == 'ar':
                    level = t.get("oee_poor_ar", "منخفض - يحتاج تحسين")
                st.warning(t.get("oee_average", "📈 **Average OEE for period: {value}%** ({level})").format(value=round(avg_oee, 1), level=level))
    
    # ==================== اتجاه الإنتاج ====================
    st.markdown("---")
    show_production_trend(filtered_df, t, days=30)
    
    # ==================== مقارنة الخطوط ====================
    if compare_lines:
        st.markdown("---")
        show_line_comparison(filtered_df, t)
    
    # ==================== حالة المخزون ====================
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📦 {t.get('raw_balance', 'Raw Materials')}")
        if df_raw is not None and not df_raw.empty:
            if lang == 'en' and 'Material_Name_EN' in df_raw.columns:
                name_col = 'Material_Name_EN'
            else:
                name_col = 'Material_Name_AR'
            
            if name_col in df_raw.columns and 'Current_Stock' in df_raw.columns:
                raw_chart = df_raw.nlargest(10, 'Current_Stock')[[name_col, 'Current_Stock']].copy()
                raw_chart = raw_chart.rename(columns={
                    name_col: t.get("material", "Material"),
                    'Current_Stock': t.get("quantity", "Quantity"),
                })
                fig_raw = px.bar(
                    raw_chart,
                    x=t.get("material", "Material"),
                    y=t.get("quantity", "Quantity"),
                    title=t.get("chart_raw_title", "Raw Materials"),
                    color=t.get("quantity", "Quantity"),
                    color_continuous_scale="Blues",
                    text=t.get("quantity", "Quantity"),
                )
                fig_raw.update_traces(textposition='outside')
                fig_raw.update_layout(height=400)
                st.plotly_chart(fig_raw, width='stretch')
            else:
                st.info(t.get("no_raw_data", "No raw materials data"))
        else:
            st.info(t.get("no_raw_data", "No raw materials data"))
    
    with col2:
        st.subheader(f"🏭 {t.get('fg_balance', 'Finished Goods')}")
        if df_fg is not None and not df_fg.empty:
            if "Name" in df_fg.columns and "Balance" in df_fg.columns:
                fg_chart = df_fg[["Name", "Balance"]].copy()
                fg_chart = fg_chart.rename(columns={
                    "Name": t.get("product", "Product"),
                    "Balance": t.get("balance", "Balance"),
                })
                fig_fg = px.bar(
                    fg_chart,
                    x=t.get("product", "Product"),
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
        else:
            st.info(t.get("no_fg_data", "No finished goods data"))
    
    # ==================== مدة نفاذ المواد ====================
    show_materials_depletion_status(df_raw, filtered_df, selected_line, t)
    
    # ==================== تحليلات OEE المتقدمة ====================
    st.markdown("---")
    show_oee_dashboard(filtered_df, t, selected_line)
    
    # ==================== التوصيات الذكية ====================
    show_smart_recommendations(df_raw, df_main, selected_line, t)