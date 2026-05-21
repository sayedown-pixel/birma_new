# fix_login.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db_manager, Factory
from datetime import datetime
from sqlalchemy import text

# فتح الجلسة مع قاعدة البيانات
session = db_manager.get_session()

try:
    print("⏳ جاري فحص المصانع المتاحة في النظام...")
    # 1. التأكد من وجود مصنع واحد على الأقل لربط الأدمن به
    factory = session.query(Factory).first()
    
    if not factory:
        print("⚠️ لم يتم العثور على أي مصنع. جاري إنشاء مصنع افتراضي للنظام...")
        factory = Factory(
            code="main_factory",
            name="المصنع الرئيسي",
            name_en="Main Factory"
        )
        session.add(factory)
        session.flush()  # استخراج معرف المصنع (ID) قبل الحفظ النهائي

    factory_id = factory.id

    print("🗑️ جاري تنظيف الحسابات القديمة باسم admin...")
    # حذف أي مستخدم قديم باسم admin باستخدام استعلام مباشر لضمان الأمان
    session.execute(text("DELETE FROM users WHERE username = :uname"), {"uname": "admin"})
    session.commit()

    print("👑 جاري إنشاء حساب مدير النظام عبر استعلام مباشر آمن...")
    # 2. إدخال مستخدم admin بالأعمدة الأساسية فقط المتواجدة بالتأكيد في السيرفر
    sql_query = text("""
        INSERT INTO users (factory_id, username, password_hash, role, name, icon, is_active, created_at)
        VALUES (:factory_id, :username, :password_hash, :role, :name, :icon, :is_active, :created_at)
    """)
    
    session.execute(sql_query, {
        "factory_id": factory_id,
        "username": "admin",
        "password_hash": db_manager.hash_password("100"),
        "role": "admin",
        "name": "مدير النظام",
        "icon": "👑",
        "is_active": True,
        "created_at": datetime.now()
    })
    session.commit()
    
    print("\n" + "="*40)
    print(f"✅ تم إصلاح مستخدم admin بنجاح وتخطي تعارض الأعمدة!")
    print(f"🏭 الحساب مرتبط بمصنع: {factory.name}")
    print("🔐 يمكنك الآن العودة للتطبيق وتسجيل الدخول بـ:")
    print("   👤 اسم المستخدم: admin")
    print("   🔑 كلمة المرور: 100")
    print("="*40)

except Exception as e:
    session.rollback()
    print(f"❌ حدث خطأ غير متوقع أثناء عملية الإصلاح: {e}")

finally:
    session.close()