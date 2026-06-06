# oee_analytics.py - نسخة مصححة

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import db_manager
import io
import numpy as np


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
        level_key = "oee_excellent" if avg_oee_display >= 85 else ("oee_acceptable" if avg_oee_display >= 60 else "oee_poor")
        level_text = {"oee_excellent": t.get("oee_excellent", "Excellent"), "oee_acceptable": t.get("oee_acceptable", "Acceptable"), "oee_poor": t.get("oee_poor", "Poor - Needs improvement")}
        if avg_oee_display >= 85:
            st.success(f"🏆 **{t.get('oee_average', 'Average OEE for period: {value}%** ({level})').format(value=f'{avg_oee_display:.1f}', level=level_text[level_key])}")
        elif avg_oee_display >= 60:
            st.info(f"📈 **{t.get('oee_average', 'Average OEE for period: {value}%** ({level})').format(value=f'{avg_oee_display:.1f}', level=level_text[level_key])}")
        else:
            st.warning(f"⚠️ **{t.get('oee_average', 'Average OEE for period: {value}%** ({level})').format(value=f'{avg_oee_display:.1f}', level=level_text[level_key])}")
        
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
  # oee_analytics.py - استبدل قسم Downtime Analysis بهذا الكود

# oee_analytics.py - استبدل قسم Downtime Analysis من show_oee_dashboard

    # ==================== تحليل التوقف المحسن ====================
    st.markdown("---")
    st.subheader(t.get("downtime_analysis_title", "⏰ Advanced Downtime Analysis"))
    
    # جلب بيانات الصيانة للتحليل المتقدم
    try:
        df_maintenance = db_manager.get_all_maintenance()
    except Exception as e:
        df_maintenance = pd.DataFrame()
    
    # استخدام التحليل المحسن
    from utils import get_enhanced_downtime_analysis
    
    with st.spinner(t.get("msg_analyzing_downtime", "Analyzing downtime data...")):
        analysis = get_enhanced_downtime_analysis(
            df_maintenance, 
            df_main, 
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now(),
            selected_line=selected_line
        )
    
    if analysis and analysis['stats']['total_events'] > 0:
        stats = analysis['stats']
        
        # بطاقات الإحصائيات الأساسية
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(t.get("oee_total_downtime", "Total Downtime"), 
                     f"{stats['total_downtime_hours']:.1f} hrs", 
                     f"{stats['total_downtime_minutes']:.0f} min")
        with col2:
            st.metric(t.get("oee_total_events", "Total Events"), stats['total_events'])
        with col3:
            st.metric(t.get("oee_avg_per_event", "Average per Event"), 
                     f"{stats['avg_downtime_per_event']:.0f} min")
        with col4:
            if stats['total_events'] > 0:
                mtbf = (days * 24 * 60 - stats['total_downtime_minutes']) / stats['total_events'] if stats['total_events'] > 0 else 0
                st.metric(t.get("oee_mtbf", "MTBF"), f"{mtbf:.0f} min" if mtbf > 0 else "N/A")
        
        st.markdown("---")
        
        # ==================== تحليل Pareto (أكبر الفئات) ====================
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### {t.get('downtime_pareto_title', '📊 Pareto Analysis - Top Downtime Categories')}")
            category_df = analysis['category_analysis'].reset_index()
            
            if not category_df.empty:
                # تنسيق الأسماء للعرض
                category_df['display_name'] = category_df.apply(
                    lambda row: row['category_ar'] if 'category_ar' in row and row['category_ar'] else row['category'], 
                    axis=1
                )
                
                fig_pareto = go.Figure()
                
                # أعمدة التوقف
                fig_pareto.add_trace(go.Bar(
                    x=category_df['display_name'].head(8),
                    y=category_df['total_minutes'].head(8),
                    name=t.get('col_total_minutes', 'Downtime (min)'),
                    marker_color='#ef4444',
                    text=category_df['total_minutes'].head(8).apply(lambda x: f'{x:.0f} min'),
                    textposition='outside'
                ))
                
                # خط النسبة التراكمية
                fig_pareto.add_trace(go.Scatter(
                    x=category_df['display_name'].head(8),
                    y=category_df['cumulative_percentage'].head(8),
                    name=t.get('col_cumulative_percentage', 'Cumulative %'),
                    yaxis='y2',
                    line=dict(color='#3b82f6', width=3, dash='dash'),
                    marker=dict(size=8)
                ))
                
                fig_pareto.update_layout(
                    title=t.get('downtime_pareto_title', 'Downtime by Category (80/20 Rule)'),
                    xaxis_title=t.get('downtime_category_uncategorized', 'Category'),
                    yaxis_title=t.get('col_total_minutes', 'Downtime (minutes)'),
                    yaxis2=dict(
                        title=t.get('col_cumulative_percentage', 'Cumulative Percentage (%)'),
                        overlaying="y",
                        side="right",
                        range=[0, 100]
                    ),
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig_pareto, width='stretch')
                
                # عرض الجدول مع تصنيف ABC
                st.caption(t.get("downtime_pareto_subtitle", "🏷️ ABC Classification: A (80%) Top Priority | B (95%) Monitor | C (100%) Low Priority"))
                display_cat = category_df[['display_name', 'total_minutes', 'event_count', 'avg_minutes', 'cumulative_percentage', 'pareto_class']].head(10)
                display_cat.columns = [
                    t.get('downtime_category_uncategorized', 'Category'),
                    t.get('col_total_minutes', 'Total (min)'),
                    t.get('col_event_count', 'Count'),
                    t.get('col_avg_minutes', 'Avg (min)'),
                    t.get('col_cumulative_percentage', 'Cumulative %'),
                    t.get('col_pareto_class', 'Priority')
                ]
                st.dataframe(display_cat, width='stretch', hide_index=True)
        
        with col2:
            # ==================== تحليل الماكينات ====================
            st.markdown(f"#### {t.get('downtime_by_machine', '🏭 Machines with Highest Downtime')}")
            machine_df = analysis['machine_analysis'].reset_index()
            machine_df.columns = [
                t.get('col_machine', 'Machine'),
                t.get('col_total_minutes', 'Total (min)'),
                t.get('col_event_count', 'Count'),
                t.get('col_avg_minutes', 'Avg (min)')
            ]
            
            if not machine_df.empty:
                fig_machine = px.bar(
                    machine_df.head(8),
                    x=t.get('col_machine', 'Machine'),
                    y=t.get('col_total_minutes', 'Total (min)'),
                    color=t.get('col_total_minutes', 'Total (min)'),
                    color_continuous_scale='Reds',
                    title=t.get('downtime_by_machine', 'Downtime by Machine'),
                    text=t.get('col_total_minutes', 'Total (min)')
                )
                fig_machine.update_traces(textposition='outside')
                fig_machine.update_layout(height=400)
                st.plotly_chart(fig_machine, width='stretch')
                
                st.dataframe(machine_df.head(10), width='stretch', hide_index=True)
        
        # ==================== الاتجاه الزمني مع التوقع ====================
        st.markdown("---")
        st.markdown(f"#### {t.get('downtime_trend_title', '📈 Downtime Trend & Forecast')}")
        
        daily_df = analysis['daily_trend']
        forecast = analysis['trend_forecast']
        
        if not daily_df.empty:
            fig_trend = go.Figure()
            
            # البيانات الفعلية
            fig_trend.add_trace(go.Scatter(
                x=daily_df['date'],
                y=daily_df['total_minutes'],
                mode='lines+markers',
                name=t.get('oee_downtime_title', 'Actual Downtime'),
                line=dict(color='#ef4444', width=3),
                marker=dict(size=8)
            ))
            
            # توقع الأيام القادمة (إذا كان متاحاً)
            if forecast and 'forecast_values' in forecast and len(forecast['forecast_values']) >= 7:
                last_date = daily_df['date'].iloc[-1]
                future_dates = [last_date + timedelta(days=i+1) for i in range(7)]
                
                fig_trend.add_trace(go.Scatter(
                    x=future_dates,
                    y=forecast['forecast_values'],
                    mode='lines+markers',
                    name=t.get('downtime_forecast_7days', 'Forecast (Next 7 days)'),
                    line=dict(color='#3b82f6', width=2, dash='dash'),
                    marker=dict(size=6, symbol='diamond')
                ))
            
            direction_text = forecast.get('direction', 'N/A')
            # ترجمة اتجاه الاتجاه
            if direction_text == '📈 تزايد':
                direction_text = t.get('trend_increasing', '📈 Increasing')
            elif direction_text == '📉 تناقص':
                direction_text = t.get('trend_decreasing', '📉 Decreasing')
            elif direction_text == '➡️ مستقر':
                direction_text = t.get('trend_stable', '➡️ Stable')
            
            fig_trend.update_layout(
                title=f"{t.get('downtime_trend_title', 'Daily Downtime Trend')} - {t.get('downtime_trend_direction', 'Direction')}: {direction_text}",
                xaxis_title=t.get("col_date", "Date"),
                yaxis_title=t.get("col_total_minutes", "Downtime (minutes)"),
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig_trend, width='stretch')
            
            # عرض معلومات التوقع
            st.info(f"""
            📊 **{t.get('downtime_trend_title', 'Trend Analysis')}:**
            - **{t.get('downtime_trend_direction', 'Direction')}:** {direction_text}
            - **{t.get('downtime_forecast_7days', 'Forecast (7 days avg)')}:** {forecast.get('forecast_7days_avg', 0):.0f} {t.get('col_total_minutes', 'minutes')}/day
            - **{t.get('downtime_data_points', 'Data Points')}:** {len(daily_df)} {t.get('days_word', 'days')}
            """)
        
        # ==================== التوصيات الذكية ====================
        st.markdown("---")
        st.markdown(f"#### {t.get('downtime_smart_recommendations', '💡 Smart Recommendations')}")
        
        for rec in analysis['recommendations']:
            if rec['priority'] == 'high':
                st.error(f"🔴 **{rec['suggestion']}**")
                st.write(f"   📋 **{t.get('logs_action', 'Action')}:** {rec['action']}")
                st.write(f"   🎯 **{t.get('rec_impact_reduce_downtime', 'Expected Impact')}:** {rec['impact']}")
                st.markdown("---")
            elif rec['priority'] == 'medium':
                st.warning(f"🟡 **{rec['suggestion']}**")
                st.write(f"   📋 **{t.get('logs_action', 'Action')}:** {rec['action']}")
                st.write(f"   🎯 **{t.get('rec_impact_reduce_downtime', 'Expected Impact')}:** {rec['impact']}")
                st.markdown("---")
            else:
                st.success(f"✅ **{rec['suggestion']}**")
                st.write(f"   📋 **{t.get('logs_action', 'Action')}:** {rec['action']}")
        
        # ==================== السجل التفصيلي ====================
        with st.expander(t.get("oee_detailed_records", "📋 Detailed Downtime Records"), expanded=False):
            events_df = analysis['events']
            display_cols = ['date', 'machine', 'category_ar', 'duration_minutes', 'description', 'technician', 'spare_parts']
            available_cols = [c for c in display_cols if c in events_df.columns]
            
            if available_cols:
                display_df = events_df[available_cols].copy()
                rename_map = {
                    'date': t.get("col_date", "Date"),
                    'machine': t.get("col_machine", "Machine"),
                    'category_ar': t.get("downtime_category_uncategorized", "Category"),
                    'duration_minutes': t.get("col_total_minutes", "Duration (min)"),
                    'description': t.get("oee_description", "Description"),
                    'technician': t.get("col_technician", "Technician"),
                    'spare_parts': t.get("col_spare_parts", "Spare Parts")
                }
                display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
                st.dataframe(display_df, width='stretch', height=300)
                
                # زر تصدير
                if st.button(t.get("btn_export_downtime", "📥 Export Downtime Analysis to Excel"), key="export_downtime"):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        events_df.to_excel(writer, sheet_name='Downtime Events', index=False)
                        analysis['category_analysis'].reset_index().to_excel(writer, sheet_name='Category Analysis', index=False)
                        analysis['machine_analysis'].reset_index().to_excel(writer, sheet_name='Machine Analysis', index=False)
                    st.download_button(
                        label=t.get("export_excel", "📥 Download Excel File"),
                        data=output.getvalue(),
                        file_name=f"downtime_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success(t.get("msg_downtime_exported", "✅ Downtime analysis exported successfully"))
    
    else:
        st.info(t.get("msg_no_downtime_data", "Insufficient downtime data for analysis"))

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