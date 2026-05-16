import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import db_manager

def show_oee_dashboard(df_main, t, selected_line):
    """Display OEE Analytics Dashboard"""
    st.markdown("---")
    st.subheader("📊 OEE & Downtime Analytics")
    
    # التحقق من وجود البيانات
    if df_main is None or df_main.empty:
        st.info("لا توجد بيانات إنتاج لعرض تحليلات OEE")
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox("Select period", [7, 14, 30, 60, 90], index=2)
    with col2:
        view_type = st.selectbox("View by", ["Daily", "Weekly", "Monthly"])
    
    # Get OEE trend data
    try:
        oee_trend = db_manager.get_oee_trend(line=selected_line, days=days)
    except Exception as e:
        st.warning(f"تعذر تحميل بيانات OEE: {e}")
        oee_trend = pd.DataFrame()
    
    if not oee_trend.empty and len(oee_trend) > 0:
        # OEE Trend Chart
        fig_oee = go.Figure()
        
        fig_oee.add_trace(go.Scatter(
            x=oee_trend['date'],
            y=oee_trend['oee'],
            mode='lines+markers',
            name='OEE',
            line=dict(color='#2563eb', width=3),
            marker=dict(size=8)
        ))
        
        if 'availability' in oee_trend.columns:
            fig_oee.add_trace(go.Scatter(
                x=oee_trend['date'],
                y=oee_trend['availability'],
                mode='lines',
                name='Availability',
                line=dict(color='#10b981', width=2, dash='dash')
            ))
        
        if 'performance' in oee_trend.columns:
            fig_oee.add_trace(go.Scatter(
                x=oee_trend['date'],
                y=oee_trend['performance'],
                mode='lines',
                name='Performance',
                line=dict(color='#f59e0b', width=2, dash='dash')
            ))
        
        if 'quality' in oee_trend.columns:
            fig_oee.add_trace(go.Scatter(
                x=oee_trend['date'],
                y=oee_trend['quality'],
                mode='lines',
                name='Quality',
                line=dict(color='#ef4444', width=2, dash='dash')
            ))
        
        fig_oee.update_layout(
            title="OEE Trend Analysis",
            xaxis_title="Date",
            yaxis_title="Percentage (%)",
            yaxis_range=[0, 100],
            height=450,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_oee, use_container_width=True)
        
        # OEE Gauge Chart for Latest Day
        latest = oee_trend.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            oee_val = latest.get('oee', 0)
            oee_color = "#22c55e" if oee_val >= 85 else "#eab308" if oee_val >= 60 else "#ef4444"
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=oee_val,
                title={"text": "Overall OEE"},
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
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            avail_val = latest.get('availability', 0)
            st.metric("Availability", f"{avail_val:.1f}%")
        with col3:
            perf_val = latest.get('performance', 0)
            st.metric("Performance", f"{perf_val:.1f}%")
        with col4:
            qual_val = latest.get('quality', 0)
            st.metric("Quality", f"{qual_val:.1f}%")
    else:
        st.info("لا توجد بيانات OEE كافية للتحليل")
    
    # Downtime Analytics
    st.markdown("---")
    st.subheader("⏰ Downtime Analysis")
    
    try:
        # Get downtime data
        downtime_df = db_manager.get_downtime_analytics(
            start_date=datetime.now() - timedelta(days=days),
            line=selected_line
        )
    except Exception as e:
        st.warning(f"تعذر تحميل بيانات وقت التوقف: {e}")
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
                        title="Downtime Distribution by Category",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            if 'duration_minutes' in downtime_df.columns and 'machine' in downtime_df.columns:
                top_causes = downtime_df.nlargest(10, 'duration_minutes')[['machine', 'category', 'description', 'duration_minutes']] if 'description' in downtime_df.columns else downtime_df.nlargest(10, 'duration_minutes')[['machine', 'category', 'duration_minutes']]
                if not top_causes.empty:
                    fig_bar = px.bar(
                        top_causes,
                        x='duration_minutes',
                        y='machine',
                        color='category' if 'category' in top_causes.columns else None,
                        title="Top Downtime Causes",
                        orientation='h',
                        text='duration_minutes'
                    )
                    fig_bar.update_traces(textposition='outside')
                    fig_bar.update_layout(height=400)
                    st.plotly_chart(fig_bar, use_container_width=True)
        
        # Daily Downtime Trend
        if 'date' in downtime_df.columns and 'duration_minutes' in downtime_df.columns:
            daily_downtime = downtime_df.groupby(downtime_df['date'])['duration_minutes'].sum().reset_index()
            if not daily_downtime.empty:
                fig_daily = px.line(
                    daily_downtime,
                    x='date',
                    y='duration_minutes',
                    title="Daily Downtime Trend",
                    markers=True
                )
                fig_daily.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Downtime (minutes)",
                    height=350
                )
                st.plotly_chart(fig_daily, use_container_width=True)
        
        # Downtime Summary Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_downtime = downtime_df['duration_minutes'].sum() if 'duration_minutes' in downtime_df.columns else 0
            st.metric("Total Downtime", f"{total_downtime:,} min", f"{total_downtime/60:.1f} hours" if total_downtime > 0 else "0")
        with col2:
            avg_downtime = downtime_df['duration_minutes'].mean() if 'duration_minutes' in downtime_df.columns else 0
            st.metric("Average per Event", f"{avg_downtime:.1f} min" if avg_downtime > 0 else "0")
        with col3:
            total_events = len(downtime_df)
            st.metric("Total Events", total_events)
        with col4:
            if total_events > 0:
                mtbf = (days * 24 * 60 - total_downtime) / total_events if total_events > 0 else 0
                st.metric("MTBF", f"{mtbf:.0f} min" if mtbf > 0 else "N/A")
        
        # Detailed Downtime Table
        with st.expander("📋 Detailed Downtime Records"):
            display_cols = []
            for col in ['date', 'line', 'machine', 'category', 'description', 'duration_minutes', 'shift', 'reported_by']:
                if col in downtime_df.columns:
                    display_cols.append(col)
            
            if display_cols:
                display_df = downtime_df[display_cols].copy()
                rename_map = {
                    'date': 'Date', 'line': 'Line', 'machine': 'Machine',
                    'category': 'Category', 'description': 'Description',
                    'duration_minutes': 'Duration (min)', 'shift': 'Shift', 'reported_by': 'Reported By'
                }
                display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
                st.dataframe(display_df, use_container_width=True)
    
    else:
        st.info("No downtime data available for the selected period")

def show_downtime_recording_form(t, selected_line):
    """Form to record downtime events"""
    with st.expander("📝 Record Downtime Event", expanded=False):
        with st.form("downtime_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                machine = st.selectbox("Machine", [
                    "Blowing Machine", "Labeling Machine", "Filling Machine",
                    "Packing Machine", "Palletizer", "Shrink Machine", "Conveyor"
                ])
                category = st.selectbox("Downtime Category", [
                    "Breakdown", "Setup", "Adjustment", "Cleaning", "Material Shortage", "Quality Issue", "Other"
                ])
                sub_category = st.text_input("Sub-category (optional)")
                
            with col2:
                shift = st.selectbox("Shift", ["Morning (6:00-14:00)", "Evening (14:00-22:00)", "Night (22:00-6:00)"])
                start_time = st.datetime_input("Start Time", datetime.now())
                end_time = st.datetime_input("End Time", datetime.now())
            
            description = st.text_area("Description of Issue", height=100)
            reported_by = st.text_input("Reported By", value=st.session_state.get('user_name', ''))
            
            if st.form_submit_button("Save Downtime Record", use_container_width=True):
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
                        st.success("✅ Downtime recorded successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error recording downtime: {e}")
                else:
                    st.error("Please provide valid start and end times")

def get_oee_level_color(oee):
    """Get color based on OEE level"""
    if oee >= 85:
        return "🟢 Excellent"
    elif oee >= 60:
        return "🟡 Acceptable"
    else:
        return "🔴 Poor"