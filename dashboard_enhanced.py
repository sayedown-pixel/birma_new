# dashboard_enhanced.py - تحسينات Dashboard

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import db_manager
from helpers import clean_line_name  # ✅ استيراد الدالة

from helpers import normalize_line_name
def show_kpi_cards(df_main, t):
    """عرض بطاقات KPIs المتقدمة"""
    
    # حساب المؤشرات
    if df_main is not None and not df_main.empty:
        prod_df = df_main[df_main['type'] == 'Production'] if 'type' in df_main.columns else df_main
        
        if not prod_df.empty:
            total_production = prod_df['output_units'].sum() if 'output_units' in prod_df.columns else 0
            avg_efficiency = prod_df['efficiency'].mean() if 'efficiency' in prod_df.columns else 0
            avg_oee = prod_df['oee'].mean() if 'oee' in prod_df.columns else 0
            total_downtime = prod_df['downtime_minutes'].sum() / 60 if 'downtime_minutes' in prod_df.columns else 0
            
            today = datetime.now().date()
            today_prod = prod_df[pd.to_datetime(prod_df['date']).dt.date == today]['output_units'].sum() if 'date' in prod_df.columns else 0
            
            yesterday = today - timedelta(days=1)
            yesterday_prod = prod_df[pd.to_datetime(prod_df['date']).dt.date == yesterday]['output_units'].sum() if 'date' in prod_df.columns else 0
            
            change_percent = ((today_prod - yesterday_prod) / yesterday_prod * 100) if yesterday_prod > 0 else 0
    else:
        total_production = 0
        avg_efficiency = 0
        avg_oee = 0
        total_downtime = 0
        today_prod = 0
        change_percent = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if change_percent >= 0 else "inverse"
        st.metric(
            t.get("today_production", "Today's Production"),
            f"{today_prod:,.0f}",
            delta=f"{change_percent:.1f}% vs yesterday",
            delta_color=delta_color
        )
    
    with col2:
        st.metric(t.get("total_production", "Total Production"), f"{total_production:,.0f}")
    
    with col3:
        eff_color = "🟢" if avg_efficiency >= 80 else "🟡" if avg_efficiency >= 60 else "🔴"
        st.metric(f"{eff_color} {t.get('avg_efficiency', 'Avg Efficiency')}", f"{avg_efficiency:.1f}%")
    
    with col4:
        oee_color = "🟢" if avg_oee >= 85 else "🟡" if avg_oee >= 60 else "🔴"
        st.metric(f"{oee_color} {t.get('avg_oee', 'Avg OEE')}", f"{avg_oee:.1f}%")


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
    
    # إحصائيات كل خط
    line_stats = prod_df.groupby('line').agg({
        'output_units': 'sum',
        'efficiency': 'mean',
        'oee': 'mean',
        'downtime_minutes': 'sum'
    }).round(1)
    
    st.subheader(t.get("line_performance", "📊 Line Performance Comparison"))
    
    # عرض كبطاقات مع تنظيف اسم الخط
    lines = line_stats.index.tolist()
    cols = st.columns(len(lines))
    
    for i, line in enumerate(lines):
        with cols[i]:
            stats = line_stats.loc[line]
            # ✅ استخدام الدالة المركزية
            line_display = normalize_line_name(line)
            st.metric(f"🏭 {line_display}", f"{stats['output_units']:,.0f}")
            
            st.metric(f"🏭 {line_display}", f"{stats['output_units']:,.0f}")
            st.caption(f"⚡ {t.get('efficiency', 'Efficiency')}: {stats['efficiency']:.1f}%")
            st.caption(f"📈 {t.get('avg_oee', 'OEE')}: {stats['oee']:.1f}%")
            st.caption(f"⏰ {t.get('downtime', 'Downtime')}: {stats['downtime_minutes']:.0f} min")


def show_quick_filters(t):
    """عرض فلاتر سريعة للأداء"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period = st.selectbox(
            t.get("select_period", "Select Period"),
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year"],
            index=1,
            key="dashboard_period"
        )
    
    with col2:
        chart_type = st.selectbox(
            t.get("chart_type", "Chart Type"),
            ["Production", "Efficiency", "OEE", "Downtime"],
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
    
    if period == "Last 7 Days":
        start_date = end_date - timedelta(days=7)
    elif period == "Last 30 Days":
        start_date = end_date - timedelta(days=30)
    elif period == "Last 90 Days":
        start_date = end_date - timedelta(days=90)
    else:  # This Year
        start_date = datetime(end_date.year, 1, 1)
    
    return start_date, end_date