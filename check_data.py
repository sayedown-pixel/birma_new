# check_data.py
from database import db_manager
from datetime import datetime, timedelta

print("🔍 جاري فحص بيانات الإنتاج...")

# جلب كل البيانات
df = db_manager.get_all_production()

if df.empty:
    print("❌ لا توجد أي بيانات إنتاج في قاعدة البيانات")
    print("💡 قم بتسجيل تقرير إنتاج أولاً من صفحة Production")
else:
    print(f"✅ يوجد {len(df)} سجل إنتاج")
    print("\n📊 آخر 5 سجلات:")
    print(df[['id', 'date', 'line', 'product', 'output_units']].head())

# جلب بيانات آخر 30 يوم
start = datetime.now() - timedelta(days=30)
df_recent = db_manager.get_all_production(start_date=start)

print(f"\n📅 آخر 30 يوم: {len(df_recent)} سجل")