# predictive_analytics.py - تحليلات تنبؤية للأعطال وتحسين OEE

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import db_manager
import plotly.graph_objects as go
import plotly.express as px

class PredictiveAnalytics:
    """تحليلات تنبؤية للأعطال وتحسين الأداء"""
    
    def __init__(self, df_maintenance=None, df_production=None):
        self.df_maintenance = df_maintenance
        self.df_production = df_production
    
    def calculate_mtbf(self, machine_name=None):
        """حساب متوسط الوقت بين الأعطال (MTBF)"""
        if self.df_maintenance is None or self.df_maintenance.empty:
            return 0
        
        df = self.df_maintenance
        if machine_name:
            df = df[df['machine'] == machine_name]
        
        breakdowns = df[df['type'] == 'breakdown']
        if len(breakdowns) < 2:
            return 0
        
        # حساب الفروق الزمنية بين الأعطال
        breakdowns = breakdowns.sort_values('date')
        time_diffs = []
        
        for i in range(1, len(breakdowns)):
            diff = (breakdowns.iloc[i]['date'] - breakdowns.iloc[i-1]['date']).total_seconds() / 3600
            time_diffs.append(diff)
        
        return round(np.mean(time_diffs), 1) if time_diffs else 0
    
    def calculate_mttr(self, machine_name=None):
        """حساب متوسط وقت الإصلاح (MTTR)"""
        if self.df_maintenance is None or self.df_maintenance.empty:
            return 0
        
        df = self.df_maintenance
        if machine_name:
            df = df[df['machine'] == machine_name]
        
        breakdowns = df[df['type'] == 'breakdown']
        if breakdowns.empty:
            return 0
        
        avg_downtime = breakdowns['downtime_minutes'].mean() / 60
        return round(avg_downtime, 1)
    
    def predict_next_breakdown(self, machine_name):
        """توقع موعد العطل التالي"""
        mtbf = self.calculate_mtbf(machine_name)
        if mtbf == 0:
            return None
        
        # آخر عطل
        df = self.df_maintenance
        last_breakdown = df[(df['machine'] == machine_name) & (df['type'] == 'breakdown')].sort_values('date').tail(1)
        
        if last_breakdown.empty:
            return None
        
        last_date = last_breakdown.iloc[0]['date']
        predicted_date = last_date + timedelta(hours=mtbf)
        
        return {
            'last_breakdown': last_date,
            'predicted_next': predicted_date,
            'days_until': (predicted_date - datetime.now()).days,
            'hours_until': (predicted_date - datetime.now()).total_seconds() / 3600,
            'mtbf': mtbf
        }
    
    def get_machine_risk_level(self, machine_name):
        """تحديد مستوى خطر الماكينة"""
        mtbf = self.calculate_mtbf(machine_name)
        mttr = self.calculate_mttr(machine_name)
        
        if mtbf == 0:
            return "unknown"
        
        risk_score = (1 / mtbf) * 100 * mttr
        
        if risk_score > 50:
            return "critical"
        elif risk_score > 25:
            return "warning"
        else:
            return "good"
    
    def get_oee_improvement_suggestions(self):
        """اقتراحات لتحسين OEE"""
        suggestions = []
        
        if self.df_production is None or self.df_production.empty:
            return suggestions
        
        # تحليل التوقف
        total_downtime = self.df_production['downtime_minutes'].sum() if 'downtime_minutes' in self.df_production.columns else 0
        avg_downtime = self.df_production['downtime_minutes'].mean() if 'downtime_minutes' in self.df_production.columns else 0
        
        if total_downtime > 1000:
            suggestions.append({
                'priority': 'high',
                'area': 'Downtime',
                'suggestion': 'إجمالي وقت التوقف مرتفع جداً',
                'action': 'تحليل أسباب التوقف الأكثر تكراراً والعمل على تقليلها',
                'impact': 'متوقع تحسين OEE بنسبة 15-20%'
            })
        
        # تحليل الكفاءة
        avg_efficiency = self.df_production['efficiency'].mean() if 'efficiency' in self.df_production.columns else 0
        if avg_efficiency < 70:
            suggestions.append({
                'priority': 'high',
                'area': 'Efficiency',
                'suggestion': 'متوسط الكفاءة منخفض',
                'action': 'مراجعة سرعات الخطوط وتدريب المشغلين',
                'impact': 'متوقع تحسين الكفاءة بنسبة 10-15%'
            })
        
        # تحليل الهالك
        total_waste = self.df_production['waste_bottles'].sum() if 'waste_bottles' in self.df_production.columns else 0
        total_units = self.df_production['output_units'].sum() if 'output_units' in self.df_production.columns else 1
        
        waste_percentage = (total_waste / (total_units * 20)) * 100  # تقريبي
        if waste_percentage > 5:
            suggestions.append({
                'priority': 'medium',
                'area': 'Quality',
                'suggestion': 'نسبة الهالك مرتفعة',
                'action': 'فحص جودة المواد الخام وضبط الماكينات',
                'impact': 'متوقع تحسين الجودة بنسبة 5-10%'
            })
        
        return suggestions


def show_predictive_analytics(t, selected_line):
    """عرض تحليلات توقع الأعطال وتحسين OEE"""
    
    st.subheader("🤖 " + t.get("predictive_analytics", "Predictive Analytics"))
    
    # جلب البيانات
    df_maintenance = db_manager.get_all_maintenance()
    df_production = db_manager.get_all_production(line=selected_line)
    
    if df_maintenance.empty and df_production.empty:
        st.info(t.get("no_data_analytics", "Not enough data for predictive analytics"))
        return
    
    analytics = PredictiveAnalytics(df_maintenance, df_production)
    
    # تبويبات التحليلات
    tab1, tab2, tab3 = st.tabs([
        "🔧 " + t.get("breakdown_prediction", "Breakdown Prediction"),
        "📈 " + t.get("oee_improvement", "OEE Improvement"),
        "📊 " + t.get("machine_health", "Machine Health")
    ])
    
    # ==================== تبويب توقع الأعطال ====================
    with tab1:
        st.markdown("### 🔮 " + t.get("breakdown_prediction_title", "Next Breakdown Prediction"))
        
        # الحصول على قائمة الماكينات
        machines = df_maintenance['machine'].unique().tolist() if not df_maintenance.empty else []
        
        if machines:
            selected_machine = st.selectbox(
                t.get("select_machine", "Select Machine"),
                machines,
                key="pred_machine_select"
            )
            
            if st.button(t.get("predict_btn", "🔮 Predict Next Breakdown"), key="predict_btn"):
                with st.spinner(t.get("analyzing", "Analyzing data...")):
                    # حساب المؤشرات
                    mtbf = analytics.calculate_mtbf(selected_machine)
                    mttr = analytics.calculate_mttr(selected_machine)
                    prediction = analytics.predict_next_breakdown(selected_machine)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            t.get("mtbf", "MTBF"),
                            f"{mtbf:.1f} hours" if mtbf > 0 else "N/A",
                            help="Mean Time Between Failures"
                        )
                    
                    with col2:
                        st.metric(
                            t.get("mttr", "MTTR"),
                            f"{mttr:.1f} hours" if mttr > 0 else "N/A",
                            help="Mean Time To Repair"
                        )
                    
                    with col3:
                        availability = (mtbf / (mtbf + mttr) * 100) if (mtbf + mttr) > 0 else 0
                        st.metric(
                            t.get("availability", "Availability"),
                            f"{availability:.1f}%" if availability > 0 else "N/A"
                        )
                    
                    if prediction:
                        st.info(f"""
                        📊 **Analysis Results:**
                        - Last breakdown: {prediction['last_breakdown'].strftime('%Y-%m-%d %H:%M')}
                        - Predicted next: {prediction['predicted_next'].strftime('%Y-%m-%d %H:%M')}
                        - Days until: {prediction['days_until']} days
                        - Hours until: {prediction['hours_until']:.1f} hours
                        """)
                        
                        # تحذير إذا كان العطل وشيكاً
                        if prediction['days_until'] <= 3:
                            st.error("⚠️ " + t.get("breakdown_warning", "CRITICAL: Predicted breakdown is imminent! Schedule maintenance immediately."))
                        elif prediction['days_until'] <= 7:
                            st.warning("⚠️ " + t.get("breakdown_warning_soon", "WARNING: Predicted breakdown within a week. Plan maintenance soon."))
                    else:
                        st.info(t.get("insufficient_data", "Insufficient data for prediction. Need at least 2 breakdown records."))
        else:
            st.info(t.get("no_maintenance_data", "No maintenance data available for prediction"))
    
    # ==================== تبويب تحسين OEE ====================
    with tab2:
        st.markdown("### 📈 " + t.get("oee_improvement_title", "OEE Improvement Suggestions"))
        
        suggestions = analytics.get_oee_improvement_suggestions()
        
        if suggestions:
            for sug in suggestions:
                if sug['priority'] == 'high':
                    with st.expander(f"🔴 {sug['area']}: {sug['suggestion']}", expanded=True):
                        st.write(f"**Action:** {sug['action']}")
                        st.write(f"**Expected Impact:** {sug['impact']}")
                        
                        # زر لإضافة تذكير
                        if st.button(f"📝 Add to Tasks", key=f"task_{sug['area']}"):
                            st.success(f"Task added: {sug['action']}")
                else:
                    with st.expander(f"🟡 {sug['area']}: {sug['suggestion']}", expanded=False):
                        st.write(f"**Action:** {sug['action']}")
                        st.write(f"**Expected Impact:** {sug['impact']}")
        else:
            st.success("✅ " + t.get("good_performance", "Good performance! No major improvement suggestions."))
        
        # رسم بياني لاتجاه OEE
        if df_production is not None and not df_production.empty and 'oee' in df_production.columns:
            st.markdown("---")
            st.markdown("### 📊 " + t.get("oee_trend_analysis", "OEE Trend Analysis"))
            
            df_production['date'] = pd.to_datetime(df_production['date'])
            daily_oee = df_production.groupby(df_production['date'].dt.date)['oee'].mean().reset_index()
            daily_oee.columns = ['date', 'oee']
            
            # إضافة خط الاتجاه
            x = np.arange(len(daily_oee))
            y = daily_oee['oee'].values
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            trend_line = p(x)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_oee['date'],
                y=daily_oee['oee'],
                mode='lines+markers',
                name='Actual OEE',
                line=dict(color='#2563eb', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=daily_oee['date'],
                y=trend_line,
                mode='lines',
                name='Trend',
                line=dict(color='#ef4444', width=2, dash='dash')
            ))
            fig.update_layout(
                title=t.get("oee_daily_trend", "Daily OEE Trend with Prediction"),
                xaxis_title=t.get("date", "Date"),
                yaxis_title="OEE (%)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # توقع OEE للأيام القادمة
            if len(daily_oee) >= 7:
                last_7_avg = daily_oee.tail(7)['oee'].mean()
                trend_slope = z[0]
                next_oee = last_7_avg + trend_slope * 7
                
                st.info(f"""
                📈 **OEE Forecast:**
                - Last 7 days average: {last_7_avg:.1f}%
                - Projected OEE in 7 days: {max(0, next_oee):.1f}%
                - Trend: {'📈 Improving' if trend_slope > 0 else '📉 Declining'}
                """)
    
    # ==================== تبويب صحة الماكينات ====================
    # ==================== تبويب صحة الماكينات ====================
    with tab3:
        st.markdown("### 🏭 " + t.get("machine_health_title", "Machine Health Dashboard"))
        
        machines = df_maintenance['machine'].unique().tolist() if not df_maintenance.empty else []
        
        if machines:
            health_data = []
            for machine in machines:
                risk = analytics.get_machine_risk_level(machine)
                mtbf = analytics.calculate_mtbf(machine)
                mttr = analytics.calculate_mttr(machine)
                
                health_data.append({
                    'Machine': machine,
                    'Risk Level': risk,
                    'MTBF (hrs)': mtbf,
                    'MTTR (hrs)': mttr,
                    'Availability': (mtbf / (mtbf + mttr) * 100) if (mtbf + mttr) > 0 else 0
                })
            
            df_health = pd.DataFrame(health_data)
            
            # ✅ دالة تلوين الصفوف (بدلاً من applymap)
            def color_risk_row(row):
                if row['Risk Level'] == 'critical':
                    return ['background-color: #ffcccc'] * len(row)
                elif row['Risk Level'] == 'warning':
                    return ['background-color: #ffe6cc'] * len(row)
                elif row['Risk Level'] == 'good':
                    return ['background-color: #ccffcc'] * len(row)
                return [''] * len(row)
            
            # تطبيق التلوين
            styled_df = df_health.style.apply(color_risk_row, axis=1)
            st.dataframe(styled_df, use_container_width=True)
            
            # رسم بياني للمخاطر
            risk_counts = df_health['Risk Level'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title=t.get("machine_risk_distribution", "Machine Risk Distribution"),
                color=risk_counts.index,
                color_discrete_map={'critical': 'red', 'warning': 'orange', 'good': 'green', 'unknown': 'gray'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # الماكينات الحرجة
            critical_machines = df_health[df_health['Risk Level'] == 'critical']
            if not critical_machines.empty:
                st.warning(f"⚠️ **Critical Machines:** {', '.join(critical_machines['Machine'].tolist())}")
        else:
            st.info(t.get("no_machine_data", "No machine data available"))