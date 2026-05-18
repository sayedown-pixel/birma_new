import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils import get_auto_reorder_suggestions, get_stock_prediction_calculated, get_marquee_recommendations
from oee_analytics import show_oee_dashboard
# dashboard.py - أضف هذه الدوال الجديدة في بداية الملف

def show_materials_depletion_status(df_raw, df_main, selected_line, t):
    """عرض حالة نفاذ المواد الخام"""
    from utils import calculate_days_until_depletion
    
    if df_raw is None or df_raw.empty:
        return
    
    # حساب أيام النفاذ
    df_with_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_with_depletion is None or df_with_depletion.empty:
        return
    
    if 'Days_Until_Depletion' not in df_with_depletion.columns:
        st.warning(t.get("no_data", "No data"))
        return
    
    st.markdown("---")
    st.subheader("📅 " + t.get("materials_depletion", "مدة نفاذ المواد الخام"))
    
    # إعداد البيانات للعرض
    material_col = None
    for col in ["Material_Name_AR", "Material_Name", "Name"]:
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
                
                if days <= 30:  # فقط المواد التي ستنفذ خلال 30 يوم
                    if days <= 0:
                        status_display = "🔴 منفذ"
                        status_class = "critical"
                    elif days <= 7:
                        status_display = "🔴 عاجل (أقل من 7 أيام)"
                        status_class = "critical"
                    elif days <= 14:
                        status_display = "🟡 تنبيه (7-14 يوم)"
                        status_class = "warning"
                    elif days <= 30:
                        status_display = f"🟢 متبقٍ ({days:.0f} يوم)"
                        status_class = "info"
                    else:
                        status_display = "✅ آمن"
                        status_class = "success"
                    
                    depletion_data.append({
                        t.get("material", "المادة"): mat_name,
                        t.get("current_stock", "المخزون"): f"{int(current_stock):,}",
                        t.get("days_left", "الأيام المتبقية"): f"{days:.1f}" if days > 0 else "0",
                        t.get("status", "الحالة"): status_display
                    })
            except Exception as e:
                continue
        
        if depletion_data:
            # ترتيب حسب الأيام المتبقية
            depletion_data.sort(key=lambda x: float(x[t.get("days_left", "الأيام المتبقية")]) if x[t.get("days_left", "الأيام المتبقية")] != "0" else 0)
            
            df_depletion = pd.DataFrame(depletion_data)
            st.dataframe(df_depletion, use_container_width=True, hide_index=True)
            
            # عرض ملخص
            col1, col2, col3 = st.columns(3)
            with col1:
                critical = len([d for d in depletion_data if "🔴" in d[t.get("status", "الحالة")]])
                st.metric("⚠️ مواد عاجلة (أقل من 7 أيام)", critical)
            with col2:
                warning = len([d for d in depletion_data if "🟡" in d[t.get("status", "الحالة")]])
                st.metric("📦 مواد تنبيه (7-14 يوم)", warning)
            with col3:
                safe = len([d for d in depletion_data if "🟢" in d[t.get("status", "الحالة")]])
                st.metric("✅ مواد آمنة (15-30 يوم)", safe)
        else:
            st.success("✅ جميع المواد آمنة ولا يوجد خطر نفاذ خلال 30 يوم")
    """عرض حالة نفاذ المواد الخام"""
    from utils import calculate_days_until_depletion
    
    if df_raw is None or df_raw.empty:
        return
    
    # حساب أيام النفاذ
    df_with_depletion = calculate_days_until_depletion(df_raw, df_main, selected_line)
    
    if df_with_depletion is None or df_with_depletion.empty:
        return
    
    st.markdown("---")
    st.subheader("📅 " + t.get("materials_depletion", "مدة نفاذ المواد الخام"))
    
    # إعداد البيانات للعرض
    material_col = None
    for col in ["Material_Name_AR", "Material_Name", "Name"]:
        if col in df_with_depletion.columns:
            material_col = col
            break
    
    stock_col = None
    for col in ["Current_Stock", "Stock"]:
        if col in df_with_depletion.columns:
            stock_col = col
            break
    
    if material_col and stock_col and 'Days_Until_Depletion' in df_with_depletion.columns:
        depletion_data = []
        for _, row in df_with_depletion.iterrows():
            days = row['Days_Until_Depletion']
            if days <= 30:  # فقط المواد التي ستنفذ خلال 30 يوم
                if days <= 0:
                    status_display = "🔴 منفذ"
                elif days <= 7:
                    status_display = "🔴 عاجل"
                elif days <= 14:
                    status_display = "🟡 تنبيه"
                else:
                    status_display = "🟢 متبقٍ"
                
                depletion_data.append({
                    t.get("material", "المادة"): row[material_col],
                    t.get("current_stock", "المخزون"): f"{int(row[stock_col]):,}",
                    t.get("days_left", "الأيام المتبقية"): days if days > 0 else 0,
                    t.get("status", "الحالة"): status_display
                })
        
        if depletion_data:
            df_depletion = pd.DataFrame(depletion_data)
            st.dataframe(df_depletion, use_container_width=True, hide_index=True)
            
            # عرض ملخص
            col1, col2, col3 = st.columns(3)
            with col1:
                critical = len([d for d in depletion_data if "🔴" in d[t.get("status", "الحالة")]])
                st.metric("⚠️ " + t.get("critical_materials", "مواد عاجلة"), critical)
            with col2:
                warning = len([d for d in depletion_data if "🟡" in d[t.get("status", "الحالة")]])
                st.metric("📦 " + t.get("warning_materials", "مواد تنبيه"), warning)
            with col3:
                safe = len([d for d in depletion_data if "🟢" in d[t.get("status", "الحالة")]])
                st.metric("✅ " + t.get("safe_materials", "مواد آمنة"), safe)
        else:
            st.success("✅ " + t.get("all_materials_safe", "جميع المواد آمنة ولا يوجد خطر نفاذ خلال 30 يوم"))


def show_shift_info_dashboard(t):
    """عرض معلومات الوردية في لوحة التحكم"""
    from utils import get_shift_info
    
    shift_info = get_shift_info()
    
    if shift_info["is_working"]:
        st.info(f"🕐 **{shift_info['shift_name']}** | وقت العمل الفعلي: {shift_info['working_hours']} ساعة | البريك: {shift_info['total_break_hours']} ساعات")
    else:
        break_desc = shift_info["current_break"]
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


def show_dashboard(df_main, df_raw, df_fg, t, selected_line):
    """Display dashboard page with OEE analytics"""
    lang = st.session_state.get('lang', 'ar')
    
    st.markdown(f'<h1 class="gradient-title">🏭 Smart Factory - {t["dashboard_title"]}</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # عرض معلومات الوردية
    show_shift_info_dashboard(t)
    
    if df_raw is not None and df_fg is not None:
        show_marquee(df_raw, df_main, df_fg, t, lang, selected_line)
    
    total_prod = 0
    monthly_prod = 0
    line1_efficiency = 0
    line2_efficiency = 0
    line1_count = 0
    line2_count = 0
    
    if df_main is not None and not df_main.empty:
        prod_df = df_main[df_main['type'] == 'Production']
        if not prod_df.empty:
            total_prod = int(prod_df['output_units'].sum()) if 'output_units' in prod_df.columns else 0
            if 'date' in prod_df.columns:
                prod_df['date'] = pd.to_datetime(prod_df['date'])
                current_year = datetime.now().year
                current_month = datetime.now().month
                monthly_prod_df = prod_df[(prod_df['date'].dt.year == current_year) & (prod_df['date'].dt.month == current_month)]
                monthly_prod = int(monthly_prod_df['output_units'].sum()) if not monthly_prod_df.empty else 0
            
            if 'line' in prod_df.columns and 'efficiency' in prod_df.columns:
                line1_data = prod_df[prod_df['line'] == "الخط الأول (line 1)"]
                line2_data = prod_df[prod_df['line'] == "الخط الثاني (line 2)"]
                if not line1_data.empty:
                    line1_efficiency = round(line1_data['efficiency'].mean(), 1)
                    line1_count = len(line1_data)
                if not line2_data.empty:
                    line2_efficiency = round(line2_data['efficiency'].mean(), 1)
                    line2_count = len(line2_data)
    
    fg_balance = int(df_fg["Balance"].sum()) if df_fg is not None and not df_fg.empty and "Balance" in df_fg.columns else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t["total_production"], f"{total_prod:,}")
    with col2:
        st.metric(t["monthly_production"], f"{monthly_prod:,}")
    with col3:
        st.metric(t["fg_balance"], f"{fg_balance:,}")
    
    st.markdown("---")
    
    st.subheader(f"⚡ {t['eff_title']}")
    col1, col2 = st.columns(2)

    with col1:
        color1 = "#22c55e" if line1_efficiency >= 80 else "#eab308" if line1_efficiency >= 60 else "#ef4444"
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=line1_efficiency,
            title={"text": f"{t['line1_efficiency']}<br><span style='font-size:14px'>({line1_count} {t.get('records_label', 'records')})</span>", "font": {"size": 18, "color": "#1e293b"}},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue", "tickfont": {"size": 12}},
                "bar": {"color": color1, "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 60], "color": "#fee2e2"},
                    {"range": [60, 80], "color": "#fef3c7"},
                    {"range": [80, 100], "color": "#dcfce7"}
                ],
                "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 85}
            },
            number={"font": {"size": 44, "color": color1}, "suffix": "%"},
            delta={"reference": 80, "increasing": {"color": "green"}, "decreasing": {"color": "red"}}
        ))
        fig1.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        color2 = "#22c55e" if line2_efficiency >= 80 else "#eab308" if line2_efficiency >= 60 else "#ef4444"
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=line2_efficiency,
            title={"text": f"{t['line2_efficiency']}<br><span style='font-size:14px'>({line2_count} {t.get('records_label', 'records')})</span>", "font": {"size": 18, "color": "#1e293b"}},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue", "tickfont": {"size": 12}},
                "bar": {"color": color2, "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 60], "color": "#fee2e2"},
                    {"range": [60, 80], "color": "#fef3c7"},
                    {"range": [80, 100], "color": "#dcfce7"}
                ],
                "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 85}
            },
            number={"font": {"size": 44, "color": color2}, "suffix": "%"},
            delta={"reference": 80, "increasing": {"color": "green"}, "decreasing": {"color": "red"}}
        ))
        fig2.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
    
    # OEE Analytics Dashboard
    show_oee_dashboard(df_main, t, selected_line)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📦 {t['raw_balance']}")
        if df_raw is not None and not df_raw.empty:
            raw_chart = df_raw.nlargest(10, "Current_Stock")[["Material_Name_AR", "Current_Stock"]].copy()
            raw_chart = raw_chart.rename(columns={
                "Material_Name_AR": t.get("chart_material", "Material"),
                "Current_Stock": t.get("chart_quantity", "Quantity"),
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
    show_materials_depletion_status(df_raw, df_main, selected_line, t)
    
    st.markdown("---")
    
    st.subheader(f"🤖 {t['smart_recommendations']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if df_raw is not None:
            reorder = get_auto_reorder_suggestions(df_raw, df_main)
            if reorder:
                st.markdown(f"#### 📦 {t['auto_reorder']}")
                for rec in reorder[:3]:
                    if rec["urgency"] == "high":
                        st.error(
                            f"🔴 **{rec['material']}** : "
                            f"{t.get('balance_label', 'Balance')} {rec['current']:,} "
                            f"({t.get('min_label', 'Min')} {rec['min_stock']:,})"
                        )
                        st.warning(
                            f"   ➕ {t.get('suggested_reorder', 'Suggested')}: "
                            f"{rec['suggested_qty']:,}"
                        )
                    else:
                        st.warning(
                            f"🟡 **{rec['material']}** : "
                            f"{t.get('balance_label', 'Balance')} {rec['current']:,} "
                            f"({t.get('min_label', 'Min')} {rec['min_stock']:,})"
                        )
                        st.info(
                            f"   ➕ {t.get('suggested_reorder', 'Suggested')}: "
                            f"{rec['suggested_qty']:,}"
                        )
            else:
                st.success(f"✅ {t['all_good']}")
    
    with col2:
        if df_raw is not None:
            stock_pred = get_stock_prediction_calculated(df_raw, df_main, selected_line)
            if stock_pred:
                st.markdown(f"#### ⏰ {t['stock_prediction']}")
                for pred in stock_pred[:5]:
                    msg = (
                        f"**{pred['material']}** : "
                        f"{t.get('balance_label', 'Balance')} {pred['current']:,} - "
                        f"{t.get('will_run_out', 'Runs out in')} {pred['days_left']} "
                        f"{t.get('days_word', 'days')}"
                    )
                    if pred["status"] == "critical":
                        st.error(f"🔴 {msg}")
                    elif pred["status"] == "warning":
                        st.warning(f"🟡 {msg}")
                    else:
                        st.info(f"ℹ️ {msg}")
            else:
                st.success(f"✅ {t['all_good']}")
