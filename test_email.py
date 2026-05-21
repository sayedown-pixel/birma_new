# test_email.py - نسخة محسنة
import streamlit as st
from datetime import datetime, timedelta

st.title("📧 اختبار إرسال التقارير عبر البريد الإلكتروني")

# اختيار الفترة الزمنية
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("تاريخ البداية", datetime.now() - timedelta(days=30))
with col2:
    end_date = st.date_input("تاريخ النهاية", datetime.now())

line_option = st.selectbox("خط الإنتاج", ["الكل", "الخط الأول (line 1)", "الخط الثاني (line 2)"])

# زر لفحص البيانات أولاً
if st.button("🔍 فحص البيانات أولاً"):
    from database import db_manager
    
    df = db_manager.get_all_production(
        start_date=start_date, 
        end_date=end_date,
        line=None if line_option == "الكل" else line_option
    )
    
    if df.empty:
        st.error(f"❌ لا توجد بيانات إنتاج في الفترة {start_date} إلى {end_date}")
        st.info("💡 يمكنك إضافة بيانات تجريبية باستخدام ملف add_test_data.py")
    else:
        st.success(f"✅ تم العثور على {len(df)} سجل إنتاج")
        st.dataframe(df[['date', 'line', 'product', 'output_units', 'efficiency']].head(10), 
                    use_container_width=True)

st.markdown("---")

# إرسال التقرير
recipient = st.text_input("البريد الإلكتروني للمستلم:", value="sayedown@hotmail.com")

if st.button("📨 إنشاء وإرسال التقرير"):
    with st.spinner("جاري إنشاء التقرير..."):
        try:
            from report_generator import generate_production_report_pdf
            from email_sender import send_weekly_report_email
            
            # أولاً: التحقق من وجود بيانات
            from database import db_manager
            df_check = db_manager.get_all_production(start_date=start_date, end_date=end_date)
            
            if df_check.empty:
                st.error("❌ لا توجد بيانات إنتاج للفترة المحددة")
                st.info("💡 رجاءً قم بإضافة بيانات إنتاج أولاً، أو قم بتوسيع نطاق التواريخ")
            else:
                st.info(f"📊 تم العثور على {len(df_check)} سجل إنتاج. جاري إنشاء التقرير...")
                
                # إنشاء التقرير
                line_param = None if line_option == "الكل" else line_option
                pdf_path = generate_production_report_pdf(start_date, end_date, line_param)
                
                if pdf_path:
                    st.success("✅ تم إنشاء ملف PDF بنجاح!")
                    
                    # عرض زر لتحميل الملف
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📥 تحميل التقرير (PDF)",
                            data=f,
                            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                    
                    # محاولة الإرسال
                    if recipient:
                        st.info(f"📧 جاري إرسال البريد إلى {recipient}...")
                        success, message = send_weekly_report_email(recipient, start_date, end_date, line_param)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ لم يتم إرسال البريد لأنه لم يتم تحديد بريد مستلم")
                else:
                    st.error("❌ فشل في إنشاء ملف PDF")
                    
        except Exception as e:
            st.error(f"❌ خطأ: {e}")
            import traceback
            st.code(traceback.format_exc())