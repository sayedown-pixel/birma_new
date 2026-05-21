import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta
from database import load_all_production
from utils import USERS, delete_production_record
import plotly.graph_objects as go
import plotly.express as px
from report_generator import generate_production_report_pdf, generate_maintenance_report_pdf
from email_sender import send_weekly_report_email
from database import db_manager

def show_users(t):
    """Display users management page"""
    st.header(t["users_title"])
    users_df = pd.DataFrame([{"Username": k, "Name": v["name"], "Role": v["role"]} for k, v in USERS.items()])
    st.dataframe(users_df, use_container_width=True)
# admin.py - قم بإضافة هذه الدوال الجديدة في نهاية الملف (قبل show_settings)


# ... (الكود الموجود يبقى كما هو) ...

def _show_reporting_tab(t):
    """عرض واجهة التقارير المتقدمة"""
    st.subheader("📊 إنشاء التقارير المتقدمة")
    
    # تبويبات للتقارير المختلفة
    report_tab1, report_tab2, report_tab3 = st.tabs([
        "📄 تقارير PDF", "✉️ إرسال تقرير أسبوعي", "📈 مقارنة الخطوط"
    ])
    
    with report_tab1:
        st.markdown("### إنشاء تقرير PDF فوري")
        col1, col2 = st.columns(2)
        with col1:
            report_type = st.selectbox("نوع التقرير", ["إنتاج", "صيانة"])
            start_date = st.date_input("تاريخ البداية", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("تاريخ النهاية", datetime.now())
            if report_type == "إنتاج":
                line_filter = st.selectbox("خط الإنتاج", ["الكل", "الخط الأول (line 1)", "الخط الثاني (line 2)"])
        
        if st.button("📑 إنشاء التقرير وتحميله", use_container_width=True):
            with st.spinner("جاري إنشاء التقرير..."):
                pdf_path = None
                if report_type == "إنتاج":
                    line_param = None if line_filter == "الكل" else line_filter
                    pdf_path = generate_production_report_pdf(start_date, end_date, line_param)
                else:
                    pdf_path = generate_maintenance_report_pdf(start_date, end_date)
                
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📥 تحميل التقرير (PDF)",
                            data=f,
                            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.error("❌ لا توجد بيانات لإنشاء التقرير في الفترة المحددة")
    
    with report_tab2:
        st.markdown("### إرسال تقرير أسبوعي تلقائي")
        st.info("سيتم إرسال التقرير إلى البريد الإلكتروني المحدد بشكل فوري (للتجربة)")
        
        recipient = st.text_input("البريد الإلكتروني للمستلم", placeholder="manager@company.com")
        schedule_type = st.selectbox("نوع التقرير", ["تقرير إنتاج", "تقرير الصيانة"])
        line_for_email = st.selectbox("خط الإنتاج (للتقرير فقط)", ["الكل", "الخط الأول (line 1)", "الخط الثاني (line 2)"])
        
        if st.button("✉️ إرسال التقرير الآن", use_container_width=True):
            if not recipient:
                st.error("⚠️ يرجى إدخال البريد الإلكتروني للمستلم")
            else:
                end = datetime.now()
                start = end - timedelta(days=7)
                success, msg = send_weekly_report_email(recipient, start, end, None if line_for_email == "الكل" else line_for_email)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
    
    with report_tab3:
        st.markdown("### مقارنة أداء خطوط الإنتاج")
        
        # جلب البيانات لآخر 30 يوم
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        df = db_manager.get_all_production(start_date=start_date)
        
        if df.empty:
            st.warning("لا توجد بيانات إنتاج للمقارنة")
            return
        
        # تجهيز البيانات للمقارنة
        df['date'] = pd.to_datetime(df['date']).dt.date
        df_grouped = df.groupby(['date', 'line']).agg({
            'oee': 'mean',
            'efficiency': 'mean',
            'output_units': 'sum'
        }).reset_index()
        
        # رسم مقارنة OEE بين الخطين
        fig_oee = px.line(
            df_grouped, 
            x='date', 
            y='oee', 
            color='line',
            title="📊 مقارنة OEE بين الخطوط (آخر 30 يوم)",
            labels={'oee': 'OEE %', 'date': 'التاريخ', 'line': 'خط الإنتاج'},
            markers=True
        )
        fig_oee.update_layout(height=450, hovermode='x unified')
        st.plotly_chart(fig_oee, use_container_width=True)
        
        # رسم مقارنة الكفاءة
        fig_eff = px.line(
            df_grouped, 
            x='date', 
            y='efficiency', 
            color='line',
            title="⚡ مقارنة الكفاءة بين الخطوط (آخر 30 يوم)",
            labels={'efficiency': 'الكفاءة %', 'date': 'التاريخ', 'line': 'خط الإنتاج'},
            markers=True
        )
        fig_eff.update_layout(height=450, hovermode='x unified')
        st.plotly_chart(fig_eff, use_container_width=True)
        
        # رسم مقارنة الإنتاج
        fig_prod = px.bar(
            df_grouped, 
            x='date', 
            y='output_units', 
            color='line',
            title="🏭 مقارنة كمية الإنتاج اليومي",
            labels={'output_units': 'كمية الإنتاج (وحدة)', 'date': 'التاريخ', 'line': 'خط الإنتاج'},
            barmode='group'
        )
        fig_prod.update_layout(height=450)
        st.plotly_chart(fig_prod, use_container_width=True)
        
        # إحصائيات المقارنة
        st.markdown("---")
        st.subheader("📈 ملخص المقارنة (آخر 30 يوم)")
        
        summary = df.groupby('line').agg({
            'oee': 'mean',
            'efficiency': 'mean',
            'output_units': 'sum',
            'downtime_minutes': 'sum'
        }).round(1)
        
        summary.columns = ['متوسط OEE %', 'متوسط الكفاءة %', 'إجمالي الإنتاج (وحدة)', 'إجمالي وقت التوقف (دقيقة)']
        st.dataframe(summary, use_container_width=True)

def show_settings(t):
    st.header(t["settings_title"])

        # أضف tab_reports إلى القائمة
    tab_general, tab_security, tab_password, tab_reports = st.tabs([
        "⚙️ عام", "🔒 الأمان", "🔑 تغيير كلمة المرور", "📊 التقارير"
    ])

    with tab_general:
        # ... (الكود الموجود يبقى كما هو) ...
        col1, col2 = st.columns(2)
        with col1:
            if st.button(t["backup_data"], use_container_width=True):
                if os.path.exists("smart_factory.db"):
                    shutil.copy(
                        "smart_factory.db",
                        f"backup_sfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    )
                    st.success("✅ تم إنشاء نسخة احتياطية")
                elif os.path.exists("birma_data.db"):
                    shutil.copy(
                        "birma_data.db",
                        f"backup_birma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    )
                    st.success("✅ تم إنشاء نسخة احتياطية")
        with col2:
            if st.button(t["clear_cache"], use_container_width=True):
                st.cache_data.clear()
                st.success("✅ تم مسح الذاكرة المؤقتة")

    with tab_security:
        # ... (الكود الموجود يبقى كما هو) ...
        st.subheader("🔒 إعدادات الأمان")
        st.info(
            f"⏰ **تسجيل الخروج التلقائي:** بعد **30 دقيقة** من عدم النشاط\n\n"
            f"🔒 **قفل الحساب:** بعد **5 محاولات** فاشلة لمدة **30 دقيقة**\n\n"
            f"📧 **تسجيل الدخول:** بالبريد الإلكتروني أو اسم المستخدم"
        )

        st.markdown("---")
        st.subheader("🔓 إلغاء قفل حساب")
        users = db_manager.get_all_users()
        locked = [u for u in users if (u.get('failed_attempts') or 0) >= 5]
        if locked:
            for u in locked:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.warning(f"🔒 {u['username']} — {u['name']} ({u.get('failed_attempts',0)} محاولة فاشلة)")
                with col2:
                    if st.button("فتح", key=f"unlock_{u['id']}"):
                        db_manager.unlock_user(u['id'])
                        st.success(f"✅ تم فتح حساب {u['username']}")
                        st.rerun()
        else:
            st.success("✅ لا توجد حسابات مقفلة حالياً")

    with tab_password:
        # ... (الكود الموجود يبقى كما هو) ...
        st.subheader("🔑 تغيير كلمة المرور")
        from auth import change_password
        username = st.session_state.get('user_name', '')

        with st.form("change_pw_form"):
            old_pw  = st.text_input("كلمة المرور الحالية", type="password")
            new_pw  = st.text_input("كلمة المرور الجديدة", type="password")
            conf_pw = st.text_input("تأكيد كلمة المرور الجديدة", type="password")

            if st.form_submit_button("تغيير كلمة المرور", use_container_width=True):
                if not all([old_pw, new_pw, conf_pw]):
                    st.error("⚠️ يرجى ملء جميع الحقول")
                elif new_pw != conf_pw:
                    st.error("⚠️ كلمتا المرور غير متطابقتين")
                elif len(new_pw) < 4:
                    st.error("⚠️ كلمة المرور يجب أن تكون 4 أحرف على الأقل")
                elif change_password(username, old_pw, new_pw):
                    st.success("✅ تم تغيير كلمة المرور بنجاح")
                else:
                    st.error("❌ كلمة المرور الحالية غير صحيحة")
    
    # التبويب الجديد للتقارير
    with tab_reports:
        _show_reporting_tab(t)

# ... (باقي الكود الموجود مثل show_delete_records يبقى كما هو) ...

def show_delete_records(df_raw, df_fg, t):
    """Display delete records section in sidebar"""
    st.sidebar.divider()
    with st.sidebar.expander("🔒 " + t["admin_title"]):
        pw = st.text_input(t["password"], type="password", key="del_pw")
        if pw in ["admin123", "100"]:
            df_prod = load_all_production()
            if not df_prod.empty:
                if 'id' not in df_prod.columns:
                    st.error("⚠️ ID column not found in database")
                else:
                    df_display = df_prod.copy()
                    df_display['desc'] = df_display.apply(
                        lambda row: f"📦 ID:{row['id']} | {row['date']} | {row['product']} | {row['output_units']} {t['quantity']}", 
                        axis=1
                    )
                    
                    selected_desc = st.selectbox("Select record to delete", options=df_display['desc'].tolist())
                    selected_id = int(selected_desc.split('|')[0].replace('📦 ID:', '').strip())
                    
                    if st.button("🗑️ " + t["delete_btn"], use_container_width=True):
                        ok, msg = delete_production_record(selected_id, df_raw, df_fg)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("No records to delete")


# أضف هذه الدوال الجديدة
def _show_reports_tab(t):
    """عرض واجهة التقارير المتقدمة"""
    st.markdown("### 📊 التقارير المتقدمة")
    
    tab_pdf, tab_email, tab_compare = st.tabs([
        "📄 تقرير PDF", "✉️ إرسال بالبريد", "📈 مقارنة الخطوط"
    ])
    
    with tab_pdf:
        st.markdown("#### إنشاء تقرير PDF")
        col1, col2 = st.columns(2)
        with col1:
            report_type = st.selectbox("نوع التقرير", ["إنتاج", "صيانة"])
            start_date = st.date_input("تاريخ البداية", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("تاريخ النهاية", datetime.now())
            if report_type == "إنتاج":
                line_filter = st.selectbox("خط الإنتاج", ["الكل", "الخط الأول (line 1)", "الخط الثاني (line 2)"])
        
        if st.button("📑 إنشاء التقرير", use_container_width=True):
            with st.spinner("جاري إنشاء التقرير..."):
                try:
                    from report_generator import generate_production_report_pdf, generate_maintenance_report_pdf
                    
                    pdf_path = None
                    if report_type == "إنتاج":
                        line_param = None if line_filter == "الكل" else line_filter
                        pdf_path = generate_production_report_pdf(start_date, end_date, line_param)
                    else:
                        pdf_path = generate_maintenance_report_pdf(start_date, end_date)
                    
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📥 تحميل التقرير (PDF)",
                                data=f,
                                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.error("❌ لا توجد بيانات لإنشاء التقرير في الفترة المحددة")
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with tab_email:
        st.markdown("#### إرسال تقرير بالبريد الإلكتروني")
        st.info("📧 سيتم إرسال التقرير إلى البريد الإلكتروني المحدد")
        
        col1, col2 = st.columns(2)
        with col1:
            recipient_email = st.text_input("البريد الإلكتروني للمستلم", placeholder="manager@company.com")
            email_start_date = st.date_input("تاريخ البداية", datetime.now() - timedelta(days=7))
        with col2:
            email_line = st.selectbox("خط الإنتاج", ["الكل", "الخط الأول (line 1)", "الخط الثاني (line 2)"], key="email_line")
            email_end_date = st.date_input("تاريخ النهاية", datetime.now())
        
        if st.button("✉️ إرسال التقرير", use_container_width=True):
            if not recipient_email:
                st.error("⚠️ يرجى إدخال البريد الإلكتروني للمستلم")
            else:
                with st.spinner("جاري إنشاء وإرسال التقرير..."):
                    try:
                        from email_sender import send_weekly_report_email
                        
                        line_param = None if email_line == "الكل" else email_line
                        success, message = send_weekly_report_email(
                            recipient_email, email_start_date, email_end_date, line_param
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
    
    with tab_compare:
        st.markdown("#### مقارنة أداء خطوط الإنتاج")
        
        compare_days = st.selectbox("الفترة", [7, 14, 30, 60], index=2)
        
        if st.button("📊 عرض المقارنة", use_container_width=True):
            with st.spinner("جاري تحميل البيانات..."):
                try:
                    from database import db_manager
                    
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=compare_days)
                    df = db_manager.get_all_production(start_date=start_date)
                    
                    if df.empty:
                        st.warning("⚠️ لا توجد بيانات إنتاج للمقارنة")
                    else:
                        df['date'] = pd.to_datetime(df['date']).dt.date
                        df_grouped = df.groupby(['date', 'line']).agg({
                            'oee': 'mean',
                            'efficiency': 'mean',
                            'output_units': 'sum'
                        }).reset_index()
                        
                        # رسم OEE
                        fig_oee = px.line(
                            df_grouped, x='date', y='oee', color='line',
                            title=f"📊 مقارنة OEE (آخر {compare_days} يوم)",
                            markers=True
                        )
                        fig_oee.update_layout(height=400)
                        st.plotly_chart(fig_oee, use_container_width=True)
                        
                        # رسم الكفاءة
                        fig_eff = px.line(
                            df_grouped, x='date', y='efficiency', color='line',
                            title=f"⚡ مقارنة الكفاءة (آخر {compare_days} يوم)",
                            markers=True
                        )
                        fig_eff.update_layout(height=400)
                        st.plotly_chart(fig_eff, use_container_width=True)
                        
                        # رسم الإنتاج
                        fig_prod = px.bar(
                            df_grouped, x='date', y='output_units', color='line',
                            title=f"🏭 مقارنة الإنتاج اليومي (آخر {compare_days} يوم)",
                            barmode='group'
                        )
                        fig_prod.update_layout(height=400)
                        st.plotly_chart(fig_prod, use_container_width=True)
                        
                        # جدول الملخص
                        st.subheader("📋 ملخص الأداء")
                        summary = df.groupby('line').agg({
                            'oee': 'mean',
                            'efficiency': 'mean',
                            'output_units': 'sum',
                            'downtime_minutes': 'sum'
                        }).round(1)
                        summary.columns = ['متوسط OEE %', 'متوسط الكفاءة %', 'إجمالي الإنتاج', 'إجمالي التوقف (دقيقة)']
                        st.dataframe(summary, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")