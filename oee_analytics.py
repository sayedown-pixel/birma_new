# oee_analytics.py - نسخة مصححة

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import db_manager


def show_oee_dashboard(df_main, t, selected_line):
    """Display OEE Analytics Dashboard"""
    
    st.markdown("---")
    st.subheader(t.get("oee_downtime_analytics", "📊 OEE & Downtime Analytics"))
    
    if df_main is None or df_main.empty:
        st.info(t.get("oee_no_data", "No production data available for OEE analysis"))
        return
    
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox(
            t.get("oee_select_period", "Select period"), 
            [7, 14, 30, 60, 90], 
            index=2,
            key="oee_days_select"
        )
    with col2:
        view_type = st.selectbox(
            t.get("oee_view_by", "View by"), 
            ["Daily", "Weekly", "Monthly"],
            key="oee_view_type_select"
        )
    
    try:
        oee_trend = db_manager.get_oee_trend(line=selected_line, days=days)
    except Exception as e:
        st.warning(f"{t.get('oee_load_error', 'Failed to load OEE data')}: {e}")
        oee_trend = pd.DataFrame()
    
    if not oee_trend.empty and len(oee_trend) > 0:
        # ✅ إضافة متوسط OEE للسجل المعروض
        avg_oee_display = oee_trend['oee'].mean()
        
        # عرض المتوسط بشكل واضح
        if avg_oee_display >= 85:
            st.success(f"🏆 **متوسط OEE للفترة: {avg_oee_display:.1f}%** (ممتاز)")
        elif avg_oee_display >= 60:
            st.info(f"📈 **متوسط OEE للفترة: {avg_oee_display:.1f}%** (مقبول)")
        else:
            st.warning(f"⚠️ **متوسط OEE للفترة: {avg_oee_display:.1f}%** (منخفض - يحتاج تحسين)")
        
        # الرسم البياني
        fig_oee = go.Figure()
        
        fig_oee.add_trace(go.Scatter(
            x=oee_trend['date'],
            y=oee_trend['oee'],
            mode='lines+markers',
            name='OEE',
            line=dict(color='#2563eb', width=3),
            marker=dict(size=8)
        ))
        
        # ✅ إضافة خط المستهدف (60% و 85%)
        fig_oee.add_hline(y=60, line_dash="dash", line_color="orange", 
                         annotation_text="Minimum Target (60%)")
        fig_oee.add_hline(y=85, line_dash="dash", line_color="green",
                         annotation_text="World Class (85%)")
        
        fig_oee.update_layout(
            title=t.get("oee_trend_title", "OEE Trend Analysis"),
            xaxis_title=t.get("col_date", "Date"),
            yaxis_title="Percentage (%)",
            yaxis_range=[0, 100],
            height=450,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_oee, width='stretch')
        
        latest = oee_trend.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            oee_val = latest.get('oee', 0)
            oee_color = "#22c55e" if oee_val >= 85 else "#eab308" if oee_val >= 60 else "#ef4444"
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=oee_val,
                title={"text": t.get("oee_overall", "Overall OEE")},
                domain={"x": [0, 1], "y": [0, 1]},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": oee_color},
                    "steps": [
                        {"range": [0, 60], "color": "#fee2e2"},
                        {"range": [60, 85], "color": "#fef3c7"},
                        {"range": [85, 100], "color": "#dcfce7"}
                    ],
                    "threshold": {"line": {"color": "red", "width": 4}, "value": 85}
                },
                number={"suffix": "%"}
            ))
            fig_gauge.update_layout(height=250)
            st.plotly_chart(fig_gauge, width='stretch')
        
        with col2:
            avail_val = latest.get('availability', 0)
            st.metric(t.get("oee_availability", "Availability"), f"{avail_val:.1f}%")
        with col3:
            perf_val = latest.get('performance', 0)
            st.metric(t.get("oee_performance", "Performance"), f"{perf_val:.1f}%")
        with col4:
            qual_val = latest.get('quality', 0)
            st.metric(t.get("oee_quality", "Quality"), f"{qual_val:.1f}%")
    else:
        st.info(t.get("oee_no_enough_data", "Insufficient OEE data for analysis"))
    
    st.markdown("---")
    st.subheader(t.get("oee_downtime_title", "⏰ Downtime Analysis"))
    
    try:
        downtime_df = db_manager.get_downtime_analytics(
            start_date=datetime.now() - timedelta(days=days),
            line=selected_line
        )
    except Exception as e:
        st.warning(f"{t.get('oee_downtime_load_error', 'Failed to load downtime data')}: {e}")
        downtime_df = pd.DataFrame()
    
    if not downtime_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'category' in downtime_df.columns and 'duration_minutes' in downtime_df.columns:
                downtime_by_category = downtime_df.groupby('category')['duration_minutes'].sum().reset_index()
                if not downtime_by_category.empty:
                    fig_pie = px.pie(
                        downtime_by_category,
                        values='duration_minutes',
                        names='category',
                        title=t.get("oee_downtime_distribution", "Downtime Distribution by Category"),
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, width='stretch')
        
        with col2:
            if 'duration_minutes' in downtime_df.columns and 'machine' in downtime_df.columns:
                top_causes = downtime_df.nlargest(10, 'duration_minutes')[['machine', 'category', 'description', 'duration_minutes']] if 'description' in downtime_df.columns else downtime_df.nlargest(10, 'duration_minutes')[['machine', 'category', 'duration_minutes']]
                if not top_causes.empty:
                    fig_bar = px.bar(
                        top_causes,
                        x='duration_minutes',
                        y='machine',
                        color='category' if 'category' in top_causes.columns else None,
                        title=t.get("oee_top_causes", "Top Downtime Causes"),
                        orientation='h',
                        text='duration_minutes'
                    )
                    fig_bar.update_traces(textposition='outside')
                    fig_bar.update_layout(height=400)
                    st.plotly_chart(fig_bar, width='stretch')
        
        if 'date' in downtime_df.columns and 'duration_minutes' in downtime_df.columns:
            daily_downtime = downtime_df.groupby(downtime_df['date'])['duration_minutes'].sum().reset_index()
            if not daily_downtime.empty:
                fig_daily = px.line(
                    daily_downtime,
                    x='date',
                    y='duration_minutes',
                    title=t.get("oee_daily_trend", "Daily Downtime Trend"),
                    markers=True
                )
                fig_daily.update_layout(
                    xaxis_title=t.get("col_date", "Date"),
                    yaxis_title=t.get("oee_total_downtime", "Total Downtime"),
                    height=350
                )
                st.plotly_chart(fig_daily, width='stretch')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_downtime = downtime_df['duration_minutes'].sum() if 'duration_minutes' in downtime_df.columns else 0
            st.metric(t.get("oee_total_downtime", "Total Downtime"), f"{total_downtime:,} min", f"{total_downtime/60:.1f} hours" if total_downtime > 0 else "0")
        with col2:
            avg_downtime = downtime_df['duration_minutes'].mean() if 'duration_minutes' in downtime_df.columns else 0
            st.metric(t.get("oee_avg_per_event", "Average per Event"), f"{avg_downtime:.1f} min" if avg_downtime > 0 else "0")
        with col3:
            total_events = len(downtime_df)
            st.metric(t.get("oee_total_events", "Total Events"), total_events)
        with col4:
            if total_events > 0:
                mtbf = (days * 24 * 60 - total_downtime) / total_events if total_events > 0 else 0
                st.metric(t.get("oee_mtbf", "MTBF"), f"{mtbf:.0f} min" if mtbf > 0 else "N/A")
        
        with st.expander(t.get("oee_detailed_records", "📋 Detailed Downtime Records")):
            display_cols = []
            for col in ['date', 'line', 'machine', 'category', 'description', 'duration_minutes', 'shift', 'reported_by']:
                if col in downtime_df.columns:
                    display_cols.append(col)
            
            if display_cols:
                display_df = downtime_df[display_cols].copy()
                rename_map = {
                    'date': t.get("col_date", "Date"), 'line': t.get("col_line", "Line"), 'machine': t.get("col_machine", "Machine"),
                    'category': 'Category', 'description': 'Description',
                    'duration_minutes': 'Duration (min)', 'shift': 'Shift', 'reported_by': 'Reported By'
                }
                display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
                st.dataframe(display_df, width='stretch')
    
    else:
        st.info(t.get("oee_no_downtime_data", "No downtime data available for the selected period"))


def show_downtime_recording_form(t, selected_line):
    """Form to record downtime events"""
    with st.expander(t.get("oee_record_downtime", "📝 Record Downtime Event"), expanded=False):
        with st.form("downtime_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                machine = st.selectbox(t.get("oee_machine", "Machine"), [
                    "Blowing Machine", "Labeling Machine", "Filling Machine",
                    "Packing Machine", "Palletizer", "Shrink Machine", "Conveyor"
                ])
                category = st.selectbox(t.get("oee_downtime_category", "Downtime Category"), [
                    "Breakdown", "Setup", "Adjustment", "Cleaning", "Material Shortage", "Quality Issue", "Other"
                ])
                sub_category = st.text_input(t.get("oee_sub_category", "Sub-category (optional)"))
                
            with col2:
                shift = st.selectbox(t.get("oee_shift", "Shift"), ["Morning (6:00-14:00)", "Evening (14:00-22:00)", "Night (22:00-6:00)"])
                start_time = st.datetime_input(t.get("oee_start_time", "Start Time"), datetime.now())
                end_time = st.datetime_input(t.get("oee_end_time", "End Time"), datetime.now())
            
            description = st.text_area(t.get("oee_description", "Description of Issue"), height=100)
            reported_by = st.text_input(t.get("oee_reported_by", "Reported By"), value=st.session_state.get('user_name', ''))
            
            if st.form_submit_button(t.get("oee_save_record", "Save Downtime Record"), width='stretch'):
                if start_time and end_time and end_time > start_time:
                    duration = int((end_time - start_time).total_seconds() / 60)
                    data = {
                        'line': selected_line,
                        'machine': machine,
                        'category': category,
                        'sub_category': sub_category,
                        'description': description,
                        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'duration_minutes': duration,
                        'reported_by': reported_by,
                        'shift': shift
                    }
                    try:
                        db_manager.record_downtime(data)
                        st.success(t.get("oee_saved_success", "✅ Downtime recorded successfully"))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{t.get('oee_save_error', 'Error recording downtime')}: {e}")
                else:
                    st.error(t.get("oee_valid_time_error", "Please provide valid start and end times"))


def get_oee_level_color(oee, t=None):
    """Get color based on OEE level"""
    if t is None:
        if oee >= 85:
            return "🟢 Excellent"
        elif oee >= 60:
            return "🟡 Acceptable"
        else:
            return "🔴 Poor"
    if oee >= 85:
        return t.get("oee_level_excellent", "🟢 Excellent")
    elif oee >= 60:
        return t.get("oee_level_acceptable", "🟡 Acceptable")
    else:
        return t.get("oee_level_poor", "🔴 Poor")