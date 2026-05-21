# check_users.py
from database import db_manager
from database import User

session = db_manager.get_session()
users = session.query(User).all()

print(f"📋 عدد المستخدمين في قاعدة البيانات: {len(users)}")
for user in users:
    print(f"   - {user.username} | {user.role} | {user.name}")

session.close()