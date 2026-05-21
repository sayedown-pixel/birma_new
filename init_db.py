# init_db.py
from database import db_manager
from database import User, Production, Maintenance, Delivery, RawReceipt, AuditLog
from datetime import datetime

def init_database():
    """تهيئة قاعدة البيانات وجميع الجداول"""
    print("🔄 جاري تهيئة قاعدة البيانات...")
    
    if not db_manager.is_connected():
        print(f"❌ غير متصل بقاعدة البيانات: {db_manager.get_init_error()}")
        return False
    
    print(f"✅ متصل بقاعدة البيانات (PostgreSQL: {not db_manager._use_sqlite})")
    
    # إنشاء جميع الجداول
    from database import Base
    Base.metadata.create_all(db_manager.engine)
    print("✅ تم إنشاء جميع الجداول")
    
    # إضافة المستخدمين الافتراضيين
    session = db_manager.get_session()
    
    try:
        # حذف المستخدمين الموجودين (اختياري - للتنظيف)
        # session.query(User).delete()
        
        # إنشاء المستخدمين
        default_users = [
            {"username": "admin", "password": "100", "role": "admin", "name": "مدير النظام", "icon": "👑"},
            {"username": "pro", "password": "400", "role": "supervisor", "name": "مشرف إنتاج", "icon": "👔"},
            {"username": "tec", "password": "300", "role": "technician", "name": "فني صيانة", "icon": "🔧"},
            {"username": "sto", "password": "200", "role": "storekeeper", "name": "أمين مخزن", "icon": "📦"},
            {"username": "quality", "password": "quality123", "role": "quality", "name": "مراقب جودة", "icon": "🔍"},
        ]
        
        for user_data in default_users:
            existing = session.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                new_user = User(
                    username=user_data["username"],
                    password_hash=db_manager.hash_password(user_data["password"]),
                    role=user_data["role"],
                    name=user_data["name"],
                    icon=user_data["icon"],
                    is_active=True,
                    created_at=datetime.now()
                )
                session.add(new_user)
                print(f"✅ تم إنشاء مستخدم: {user_data['username']}")
            else:
                print(f"ℹ️ المستخدم موجود بالفعل: {user_data['username']}")
        
        session.commit()
        print("✅ تم حفظ المستخدمين في قاعدة البيانات")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        session.rollback()
    finally:
        session.close()
    
    return True

if __name__ == "__main__":
    init_database()