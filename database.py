# database.py - النسخة الكاملة مع جميع النماذج والدوال المحدثة

import os
import logging
import bcrypt
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Index, text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv
import pandas as pd

# تحميل متغيرات البيئة من ملف .env محلياً
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

SQLITE_DB_PATH = "birma_data.db"

# ============================================================================
# Database Models
# ============================================================================

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), default="👤")
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    last_password_change = Column(DateTime, default=datetime.now)
# database.py - أضف هذا النموذج الجديد

class Alert(Base):
    """نموذج التنبيهات"""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)  # stock, maintenance, oee, general
    severity = Column(String(20), default='warning')  # info, warning, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    related_id = Column(Integer, nullable=True)  # material_id, machine_id, etc.
    related_name = Column(String(200), nullable=True)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    dismissed_at = Column(DateTime, nullable=True)
    dismissed_by = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_alert_type', 'alert_type'),
        Index('idx_alert_is_read', 'is_read'),
        Index('idx_alert_created_at', 'created_at'),
    )


class Production(Base):
    __tablename__ = 'production'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), default='Production')
    date = Column(DateTime, nullable=False)
    line = Column(String(100), nullable=False)
    supervisor = Column(String(100))
    product = Column(String(100), nullable=False)
    output_units = Column(Integer, nullable=False)
    preforms_used = Column(Integer, default=0)
    waste_bottles = Column(Integer, default=0)
    packaging_waste = Column(Float, default=0)
    line_speed = Column(Integer, default=0)
    efficiency = Column(Float, default=0)
    oee = Column(Float, default=0)
    availability = Column(Float, default=0)
    performance = Column(Float, default=0)
    quality = Column(Float, default=0)
    planned_production_time = Column(Integer, default=0)
    operating_time = Column(Integer, default=0)
    downtime_minutes = Column(Integer, default=0)
    ideal_run_rate = Column(Float, default=0)
    shift = Column(String(500))
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_production_date', 'date'),
        Index('idx_production_line', 'line'),
    )


class Maintenance(Base):
    __tablename__ = 'maintenance'

    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    date = Column(DateTime, nullable=False)
    line = Column(String(100))
    machine = Column(String(100))
    technician = Column(String(100))
    issue = Column(Text)
    task = Column(String(200))
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    downtime_minutes = Column(Integer, default=0)
    downtime_category = Column(String(50))
    spare_parts = Column(Text)
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_maintenance_date', 'date'),
        Index('idx_maintenance_machine', 'machine'),
    )


class Delivery(Base):
    __tablename__ = 'delivery'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    product = Column(String(100))
    quantity = Column(Integer)
    customer = Column(String(200))
    delivery_note = Column(String(100))
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)


class RawReceipt(Base):
    __tablename__ = 'raw_receipt'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    material = Column(String(100))
    quantity = Column(Integer)
    invoice = Column(String(100))
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)


class DowntimeRecord(Base):
    __tablename__ = 'downtime_records'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    line = Column(String(100), nullable=False)
    machine = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer, default=0)
    category = Column(String(50))
    sub_category = Column(String(100))
    description = Column(Text)
    reported_by = Column(String(100))
    shift = Column(String(20))
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_downtime_date', 'date'),
        Index('idx_downtime_line', 'line'),
        Index('idx_downtime_category', 'category'),
    )


class OEESummary(Base):
    __tablename__ = 'oee_summary'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    line = Column(String(100), nullable=False)
    shift = Column(String(20))
    oee = Column(Float)
    availability = Column(Float)
    performance = Column(Float)
    quality = Column(Float)
    total_downtime_minutes = Column(Integer)
    total_units_produced = Column(Integer)
    total_good_units = Column(Integer)
    total_defect_units = Column(Integer)
    planned_production_time = Column(Integer)
    operating_time = Column(Integer)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_oee_date', 'date'),
        Index('idx_oee_line', 'line'),
    )


class RawMaterial(Base):
    """مواد خام"""
    __tablename__ = 'raw_materials'

    id = Column(Integer, primary_key=True)
    material_id = Column(String(50), unique=True, nullable=True)
    name_ar = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=False)
    current_stock = Column(Float, default=0)
    min_stock = Column(Float, default=0)
    max_stock = Column(Float, default=0)
    unit = Column(String(50), default="قطعة")
    unit_cost = Column(Float, default=0)
    daily_consumption = Column(Float, default=0)
    last_updated = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_raw_material_id', 'material_id'),
        Index('idx_raw_name_ar', 'name_ar'),
        Index('idx_raw_name_en', 'name_en'),
    )


class FinishedGood(Base):
    """منتجات تامة"""
    __tablename__ = 'finished_goods'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    opening_balance = Column(Float, default=0)
    stock_in = Column(Float, default=0)
    stock_out = Column(Float, default=0)
    balance = Column(Float, default=0)
    unit = Column(String(50), default="قطعة")
    month_key = Column(String(10), default="")
    last_updated = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_fg_name', 'name'),
        Index('idx_fg_month_key', 'month_key'),
    )


class RawMaterialTransaction(Base):
    """حركات المواد الخام (وارد/صرف)"""
    __tablename__ = 'raw_material_transactions'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('raw_materials.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    reference = Column(String(100))
    notes = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_transaction_material', 'material_id'),
        Index('idx_transaction_type', 'transaction_type'),
        Index('idx_transaction_date', 'created_at'),
    )


class FinishedGoodTransaction(Base):
    """حركات المنتجات التامة (إنتاج/تسليم/تعديل)"""
    __tablename__ = 'finished_good_transactions'

    id = Column(Integer, primary_key=True)
    finished_good_id = Column(Integer, ForeignKey('finished_goods.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    reference = Column(String(100))
    customer = Column(String(200))
    notes = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_fg_transaction_fg', 'finished_good_id'),
        Index('idx_fg_transaction_type', 'transaction_type'),
        Index('idx_fg_transaction_date', 'created_at'),
    )


class SystemLog(Base):
    """سجل أحداث النظام"""
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    event_level = Column(String(20), default='INFO')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(100), nullable=True)
    action = Column(String(500), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_log_event_type', 'event_type'),
        Index('idx_log_user_id', 'user_id'),
        Index('idx_log_created_at', 'created_at'),
        Index('idx_log_event_level', 'event_level'),
    )


# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._connected = False
        self._init_error = None
        self._use_sqlite = False
        self._init_connection()

    def _init_connection(self):
        DATABASE_URL = ""

        try:
            import streamlit as st
            if "DATABASE_URL" in st.secrets:
                val = st.secrets["DATABASE_URL"]
                if isinstance(val, str) and val.strip():
                    DATABASE_URL = val.strip()
                    logger.info("✅ DATABASE_URL loaded from st.secrets")
            if not DATABASE_URL and "database" in st.secrets:
                sec = st.secrets["database"]
                if isinstance(sec, str) and sec.strip():
                    DATABASE_URL = sec.strip()
                elif hasattr(sec, "get"):
                    for k in ("url", "DATABASE_URL", "connection_string", "postgres_url"):
                        v = sec.get(k, "")
                        if isinstance(v, str) and v.strip():
                            DATABASE_URL = v.strip()
                            break
        except Exception as e:
            logger.warning(f"Could not read st.secrets: {e}")

        if not DATABASE_URL:
            DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
            if DATABASE_URL:
                logger.info("✅ DATABASE_URL loaded from environment variable")

        if DATABASE_URL:
            db_url = DATABASE_URL
            if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

            try:
                self.engine = create_engine(
                    db_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={"connect_timeout": 10},
                )
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()
                    logger.info(f"PostgreSQL connected: {version[0][:60]}...")

                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
                Base.metadata.create_all(bind=self.engine)
                self._migrate_schema()
                self._connected = True
                self._use_sqlite = False
                self._create_default_admin()
                logger.info("✅ Database initialized with PostgreSQL")
                return
            except Exception as e:
                logger.error(f"❌ PostgreSQL connection failed: {e}")
                self._init_error = str(e)

        else:
            logger.warning("⚠️ DATABASE_URL not found — falling back to SQLite")
            self._init_error = "DATABASE_URL not configured"

        logger.info("🔄 Initializing SQLite as fallback...")
        self._init_sqlite()
    
    def _init_sqlite(self):
        try:
            sqlite_url = f'sqlite:///{SQLITE_DB_PATH}'
            self.engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self._use_sqlite = True
            Base.metadata.create_all(bind=self.engine)
            self._migrate_schema()
            self._connected = True
            self._init_error = None
            logger.info(f"SQLite database initialized at {SQLITE_DB_PATH}")
            self._create_default_admin()
        except Exception as e:
            self._init_error = str(e)
            self._connected = False
            logger.error(f"SQLite initialization failed: {e}")

    def is_connected(self):
        return self._connected

    def get_init_error(self):
        return self._init_error
    
    def is_using_sqlite(self):
        return self._use_sqlite

    def get_session(self):
        if not self.SessionLocal:
            raise Exception("قاعدة البيانات غير متصلة")
        return self.SessionLocal()

    def _migrate_schema(self):
        """ترحيل المخطط - إضافة الأعمدة الجديدة"""
        new_cols = [
            ("production", "packaging_waste", "FLOAT", "0"),
            ("production", "line_speed", "INTEGER", "0"),
            ("delivery", "delivery_note", "VARCHAR(100)", "''"),
            ("maintenance", "spare_parts", "TEXT", "''"),
            ("users", "must_change_password", "BOOLEAN", "FALSE"),
            ("users", "last_password_change", "TIMESTAMP", "CURRENT_TIMESTAMP"),
        ]
        for table, column, col_type, default in new_cols:
            self._ensure_column(table, column, col_type, default)

    def _ensure_column(self, table: str, column: str, col_type: str, default: str):
        """إضافة عمود إذا لم يكن موجوداً مع دعم PostgreSQL"""
        if not self.engine:
            return
        try:
            with self.engine.connect() as conn:
                if self._use_sqlite:
                    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    if any(r[1] == column for r in rows):
                        return
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"))
                else:
                    pg_col_type = col_type
                    if col_type.upper() == 'DATETIME':
                        pg_col_type = 'TIMESTAMP'
                    
                    conn.execute(text(f"""
                        ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_col_type} DEFAULT {default}
                    """))
                conn.commit()
        except Exception as e:
            logger.warning(f"Schema migration skipped for {table}.{column}: {e}")

    def _create_default_admin(self):
        session = None
        try:
            session = self.get_session()
            default_users = [
                {"username": "admin", "password": "100", "role": "admin", "name": "مدير النظام", "icon": "👑", "must_change": False},  # ✅ changed to False
                {"username": "pro", "password": "400", "role": "supervisor", "name": "مشرف إنتاج", "icon": "👔", "must_change": False},
                {"username": "tec", "password": "300", "role": "technician", "name": "فني صيانة", "icon": "🔧", "must_change": False},
                {"username": "sto", "password": "200", "role": "storekeeper", "name": "أمين مخزن", "icon": "📦", "must_change": False},
                {"username": "quality", "password": "quality123", "role": "quality", "name": "مراقب جودة", "icon": "🔍", "must_change": False},
            ]
            for user_data in default_users:
                existing = session.query(User).filter(User.username == user_data["username"]).first()
                if not existing:
                    new_user = User(
                        username=user_data["username"],
                        password_hash=self.hash_password(user_data["password"]),
                        role=user_data["role"],
                        name=user_data["name"],
                        icon=user_data["icon"],
                        is_active=True,
                        created_at=datetime.now(),
                        must_change_password=user_data["must_change"],
                        last_password_change=datetime.now()
                    )
                    session.add(new_user)
                else:
                    # ✅ لا نغير must_change_password للمستخدمين الموجودين
                    pass
            session.commit()
            logger.info("Default users created/verified.")
        except Exception as e:
            logger.warning(f"Could not create default users: {e}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

    def hash_password(self, password: str) -> str:
        try:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        except Exception:
            import hashlib
            import secrets
            salt = secrets.token_hex(16)
            return f"{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            try:
                if ':' in hashed:
                    import hashlib
                    salt, hash_value = hashed.split(':')
                    return hash_value == hashlib.sha256((plain + salt).encode()).hexdigest()
            except:
                pass
            return False

    def authenticate_user(self, username: str, password: str):
        session = None
        try:
            session = self.get_session()
            user = session.query(User).filter(User.username == username, User.is_active == True).first()
            if user and self.verify_password(password, user.password_hash):
                user.last_login = datetime.now()
                session.commit()
                return {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'name': user.name,
                    'icon': user.icon,
                    'is_active': user.is_active,
                    'must_change_password': user.must_change_password,
                    'last_password_change': user.last_password_change
                }
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
        finally:
            if session:
                session.close()

    def update_user_password(self, username: str, new_password: str) -> bool:
        session = None
        try:
            session = self.get_session()
            user = session.query(User).filter(User.username == username).first()
            if user:
                import bcrypt
                new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                user.password_hash = new_hash
                user.must_change_password = False
                user.last_password_change = datetime.now()
                session.commit()
                
                logger.info(f"Password updated for user: {username}")
                return True
            return False
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"update_user_password error: {e}")
            return False
        finally:
            if session:
                session.close()

    def create_user(self, username: str, password: str, role: str, name: str, icon: str = "👤", must_change_password: bool = True) -> bool:
        session = None
        try:
            session = self.get_session()
            existing = session.query(User).filter(User.username == username).first()
            if existing:
                return False
            new_user = User(
                username=username,
                password_hash=self.hash_password(password),
                role=role,
                name=name,
                icon=icon,
                is_active=True,
                created_at=datetime.now(),
                must_change_password=must_change_password,
                last_password_change=datetime.now()
            )
            session.add(new_user)
            session.commit()
            return True
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"create_user error: {e}")
            return False
        finally:
            if session:
                session.close()

    def get_all_users(self):
        session = None
        try:
            session = self.get_session()
            users = session.query(User).all()
            return [{'id': u.id, 'username': u.username, 'role': u.role, 'name': u.name, 'icon': u.icon, 'is_active': u.is_active, 'created_at': u.created_at, 'last_login': u.last_login} for u in users]
        except Exception as e:
            logger.error(f"get_all_users error: {e}")
            return []
        finally:
            if session:
                session.close()

    def update_user(self, user_id: int, data: dict) -> bool:
        session = None
        try:
            session = self.get_session()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            if 'name' in data:
                user.name = data['name']
            if 'role' in data:
                user.role = data['role']
            if 'icon' in data:
                user.icon = data['icon']
            if 'is_active' in data:
                user.is_active = data['is_active']
            session.commit()
            return True
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"update_user error: {e}")
            return False
        finally:
            if session:
                session.close()

    def delete_user(self, user_id: int) -> bool:
        session = None
        try:
            session = self.get_session()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            if user.role == 'admin':
                admin_count = session.query(User).filter(User.role == 'admin', User.is_active == True).count()
                if admin_count <= 1:
                    return False
            session.delete(user)
            session.commit()
            return True
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"delete_user error: {e}")
            return False
        finally:
            if session:
                session.close()

    # ========================================================================
    # Production Functions with Advanced Filters
    # ========================================================================

# database.py - استبدل دالة calculate_oee بهذه النسخة

    def calculate_oee(self, data: dict) -> dict:
        """
        حساب OEE محسن باستخدام المعايير العالمية
        """
        # وقت الإنتاج المخطط (بالدقائق)
        working_minutes = int(data.get('working_minutes', 0) or 0)
        
        # إذا لم يتم توفير working_minutes، نحسبها من الوردية
        if working_minutes == 0:
            shift_start = data.get('shift_start', '08:00')
            shift_end = data.get('shift_end', '02:00')
            break_minutes = int(data.get('break_minutes', 180) or 180)
            
            try:
                start_parts = shift_start.split(':')
                end_parts = shift_end.split(':')
                start_total = int(start_parts[0]) * 60 + int(start_parts[1])
                end_total = int(end_parts[0]) * 60 + int(end_parts[1])
                
                if end_total <= start_total:
                    end_total += 24 * 60
                
                shift_minutes = end_total - start_total
                working_minutes = max(0, shift_minutes - break_minutes)
            except:
                working_minutes = 900  # 15 ساعة افتراضياً
        
        planned_time = working_minutes
        
        # وقت التوقف (بما في ذلك التوقف المخطط)
        downtime = max(0, int(data.get('downtime_minutes', 0) or 0))
        planned_downtime = max(0, int(data.get('planned_downtime', 0) or 0))
        
        # 1. حساب Availability
        total_downtime = downtime + planned_downtime
        operating_time = max(0, planned_time - total_downtime)
        
        if planned_time > 0:
            availability = (operating_time / planned_time) * 100
        else:
            availability = 0
        
        # 2. حساب Performance
        actual_output_units = int(data.get('output_units', 0) or 0)
        pieces_per_unit = max(1, int(data.get('pieces_per_unit', 1) or 1))
        actual_bottles = actual_output_units * pieces_per_unit
        
        ideal_run_rate = float(data.get('ideal_run_rate', 0) or 0)
        
        if operating_time > 0 and ideal_run_rate > 0:
            actual_rate = actual_bottles / operating_time
            performance = min(100.0, (actual_rate / ideal_run_rate) * 100)
        else:
            performance = 0
        
        # 3. حساب Quality
        waste = max(0, int(data.get('waste_bottles', 0) or 0))
        good_bottles = max(0, actual_bottles - waste)
        
        if actual_bottles > 0:
            quality = (good_bottles / actual_bottles) * 100
        else:
            quality = 0
        
        # 4. حساب OEE
        oee = (availability * performance * quality) / 10000
        oee = round(oee, 2)
        
        return {
            'oee': oee,
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'planned_time': planned_time,
            'operating_time': operating_time,
            'downtime': total_downtime,
            'planned_downtime': planned_downtime,
            'actual_bottles': actual_bottles,
            'good_bottles': good_bottles
        }

    def save_production(self, data: dict):
        session = None
        try:
            session = self.get_session()
            oee_data = self.calculate_oee(data)
            if isinstance(data['date'], str):
                prod_date = datetime.strptime(data['date'], "%Y-%m-%d")
            else:
                prod_date = data['date']
            shift_info = f"{data.get('shift_start', '08:00')}-{data.get('shift_end', '02:00')} بريك:{data.get('break_minutes', 180)}"
            production = Production(
                type='Production',
                date=prod_date,
                line=data.get('line', ''),
                supervisor=data.get('supervisor', ''),
                product=data.get('product', ''),
                output_units=int(data.get('output_units', 0)),
                preforms_used=int(data.get('preforms_used', 0)),
                waste_bottles=int(data.get('waste_bottles', 0)),
                packaging_waste=float(data.get('packaging_waste', 0)),
                line_speed=int(data.get('line_speed', 0)),
                efficiency=float(data.get('efficiency', 0)),
                oee=oee_data['oee'],
                availability=oee_data['availability'],
                performance=oee_data['performance'],
                quality=oee_data['quality'],
                planned_production_time=oee_data['planned_time'],
                operating_time=oee_data['operating_time'],
                downtime_minutes=int(data.get('downtime_minutes', 0)),
                ideal_run_rate=float(data.get('ideal_run_rate', 0)),
                shift=shift_info,
                timestamp=datetime.now()
            )
            session.add(production)
            session.commit()
            
            # محاولة إرسال تنبيه
            try:
                from helpers import send_telegram
                efficiency = float(data.get('efficiency', 0))
                if efficiency < 70:
                    send_telegram(f"⚠️ انخفاض الكفاءة - {data.get('product', 'منتج')} في {data.get('line', 'الخط')}: {efficiency}%")
            except Exception as e:
                logger.debug(f"Could not send telegram notification: {e}")
            
            db_type = "SQLite" if self._use_sqlite else "PostgreSQL"
            logger.info(f"✅ Production saved: ID={production.id} on {db_type}")
            return production.id
        except Exception as e:
            if session:
                session.rollback()
            db_type = "SQLite" if self._use_sqlite else "PostgreSQL"
            logger.error(f"❌ save_production error ({db_type}): {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_all_production(self, start_date=None, end_date=None, line=None, product=None, supervisor=None):
        """الحصول على سجلات الإنتاج مع فلترة متقدمة"""
        session = None
        try:
            session = self.get_session()
            query = session.query(Production)
            if start_date:
                query = query.filter(Production.date >= start_date)
            if end_date:
                query = query.filter(Production.date <= end_date)
            if line:
                query = query.filter(Production.line == line)
            if product:
                query = query.filter(Production.product == product)
            if supervisor:
                query = query.filter(Production.supervisor == supervisor)
            query = query.order_by(Production.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_all_production error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()
    # database.py - أضف هذه الدوال داخل class DatabaseManager

    # ========================================================================
    # Alert System
    # ========================================================================
    
    def add_alert(self, alert_type: str, title: str, message: str, 
                  severity: str = 'warning', related_id: int = None, 
                  related_name: str = None) -> int:
        """إضافة تنبيه جديد"""
        session = None
        try:
            session = self.get_session()
            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                related_id=related_id,
                related_name=related_name,
                is_read=False,
                is_dismissed=False,
                created_at=datetime.now()
            )
            session.add(alert)
            session.commit()
            
            # تسجيل في سجل النظام
            self.add_info_log('alert', f"New alert: {title}", message[:200])
            
            return alert.id
        except Exception as e:
            logger.error(f"Failed to add alert: {e}")
            if session:
                session.rollback()
            return None
        finally:
            if session:
                session.close()
    
    def get_active_alerts(self, limit: int = 50) -> list:
        """الحصول على التنبيهات النشطة (غير المحذوفة)"""
        session = None
        try:
            session = self.get_session()
            # نحصل على جميع التنبيهات (لأننا نحذفها فعلياً)
            alerts = session.query(Alert).order_by(
                # ترتيب حسب الخطورة: critical أولاً
                Alert.severity.desc(),
                Alert.created_at.desc()
            ).limit(limit).all()
            
            return [{
                'id': a.id,
                'alert_type': a.alert_type,
                'severity': a.severity,
                'title': a.title,
                'message': a.message,
                'related_id': a.related_id,
                'related_name': a.related_name,
                'is_read': a.is_read,
                'created_at': a.created_at
            } for a in alerts]
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def get_all_alerts(self, limit: int = 100, offset: int = 0, 
                       include_dismissed: bool = False) -> list:
        """الحصول على جميع التنبيهات"""
        session = None
        try:
            session = self.get_session()
            query = session.query(Alert)
            if not include_dismissed:
                query = query.filter(Alert.is_dismissed == False)
            query = query.order_by(Alert.created_at.desc()).limit(limit).offset(offset)
            
            return [{
                'id': a.id,
                'alert_type': a.alert_type,
                'severity': a.severity,
                'title': a.title,
                'message': a.message,
                'is_read': a.is_read,
                'is_dismissed': a.is_dismissed,
                'created_at': a.created_at,
                'dismissed_at': a.dismissed_at,
                'dismissed_by': a.dismissed_by
            } for a in query.all()]
        except Exception as e:
            logger.error(f"Failed to get all alerts: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def dismiss_alert(self, alert_id: int, dismissed_by: str = None) -> bool:
        """تأكيد وإزالة تنبيه - حذف فعلي من الجدول"""
        session = None
        try:
            session = self.get_session()
            
            # البحث عن التنبيه
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            
            if not alert:
                print(f"❌ Alert {alert_id} not found")
                return False
            
            # تسجيل المعلومات قبل الحذف
            alert_title = alert.title
            
            # حذف التنبيه نهائياً (بدلاً من وضع علامة dismissed)
            session.delete(alert)
            session.commit()
            
            # تسجيل في سجل النظام
            self.add_info_log('alert', f"Alert dismissed: {alert_title}", f"By: {dismissed_by}")
            print(f"✅ Alert {alert_id} deleted successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to dismiss alert: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()
    
    def mark_alert_read(self, alert_id: int) -> bool:
        """تحديد تنبيه كمقروء"""
        session = None
        try:
            session = self.get_session()
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.is_read = True
                session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark alert read: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()
    
# database.py - استبدل دالة check_and_create_alerts بهذه النسخة

# database.py - استبدل دالة check_and_create_alerts بهذه النسخة المحسنة

# database.py - استبدل دالة check_and_create_alerts بهذه النسخة

# database.py - استبدل جزء تنبيهات OEE في دالة check_and_create_alerts

    def check_and_create_alerts(self, df_raw=None, df_main=None):
        """فحص وإنشاء التنبيهات تلقائياً"""
        from datetime import datetime, timedelta
        
        alerts_created = []
        
        # 1. تنبيهات المخزون المنخفض
        if df_raw is not None and not df_raw.empty:
            name_col = None
            for col in ['Material_Name_AR', 'Material_Name_EN', 'Material_Name', 'Name']:
                if col in df_raw.columns:
                    name_col = col
                    break
            
            stock_col = None
            for col in ['Current_Stock', 'Stock', 'in_stock']:
                if col in df_raw.columns:
                    stock_col = col
                    break
            
            min_stock_col = 'Min_Stock' if 'Min_Stock' in df_raw.columns else None
            
            if name_col and stock_col:
                for _, row in df_raw.iterrows():
                    material_name = str(row.get(name_col, ''))
                    current = float(row.get(stock_col, 0)) if pd.notna(row.get(stock_col, 0)) else 0
                    min_stock = float(row.get(min_stock_col, 0)) if min_stock_col and pd.notna(row.get(min_stock_col, 0)) else 0
                    
                    severity = None
                    title = None
                    message = None
                    
                    if current <= 0:
                        severity = 'critical'
                        title = f"🚨 نفاذ كامل للمادة: {material_name}"
                        message = f"⚠️ المادة {material_name} قد نفدت بالكامل!"
                    elif min_stock > 0 and current <= min_stock:
                        if current <= min_stock / 2:
                            severity = 'critical'
                            title = f"🔴 تنبيه عاجل: {material_name}"
                            message = f"المخزون: {current:,.0f} (أقل من 50% من الحد الأدنى {min_stock:,.0f})"
                        else:
                            severity = 'warning'
                            title = f"🟡 تنبيه: {material_name} منخفض"
                            message = f"المخزون: {current:,.0f} (الحد الأدنى: {min_stock:,.0f})"
                    
                    if severity in ['critical', 'warning']:
                        # إرسال تنبيه التيليجرام
                        """try:
                            from helpers import send_telegram
                            if current <= 0:
                                telegram_msg = f"🚨 **نفاذ كامل للمادة**\n📦 {material_name}\n⚠️ المخزون: {current:,.0f}"
                            else:
                                percentage = (current / min_stock) * 100
                                telegram_msg = f"🔴 **تنبيه: نقص في المخزون**\n📦 المادة: {material_name}\n📊 المخزون الحالي: {current:,.0f}\n⚠️ الحد الأدنى: {min_stock:,.0f}\n📉 النسبة: {percentage:.1f}%"
                            send_telegram(telegram_msg)
                            print(f"📤 Telegram alert sent for: {material_name}")
                        except Exception as e:
                            print(f"Telegram error: {e}")"""
                        
                        existing = self._check_recent_alert('stock', material_name, hours=24)
                        if not existing:
                            alert_id = self.add_alert('stock', title, message, severity, None, material_name)
                            if alert_id:
                                alerts_created.append(alert_id)
        
        # 2. ✅ تحسين تنبيهات OEE - استخدام متوسط آخر 5 سجلات وليس سجل واحد
        if df_main is not None and not df_main.empty:
            prod_df = df_main[df_main['type'] == 'Production'] if 'type' in df_main.columns else df_main
            if not prod_df.empty and 'oee' in prod_df.columns:
                # ✅ استخدام آخر 5 سجلات OEE لحساب المتوسط
                oee_values = prod_df['oee'].dropna().tail(10)
                
                if len(oee_values) >= 3:
                    # حساب متوسط آخر 3-5 سجلات
                    recent_oee_avg = oee_values.tail(5).mean()
                    last_oee = oee_values.iloc[-1]
                    
                    print(f"📊 OEE Check - Last: {last_oee:.1f}%, Recent Avg (5): {recent_oee_avg:.1f}%")
                    
                    # ✅ تنبيه فقط إذا كان المتوسط أقل من 60% (وليس سجل فردي)
                    if recent_oee_avg < 60:
                        existing = self._check_recent_alert('oee', 'low_oee', hours=12)  # كل 12 ساعة
                        if not existing:
                            title = "📉 تنبيه: انخفاض متوسط OEE"
                            message = f"متوسط OEE لآخر 5 سجلات: {recent_oee_avg:.1f}% (المستهدف: 60%)"
                            alert_id = self.add_alert('oee', title, message, 'warning')
                            if alert_id:
                                alerts_created.append(alert_id)
                                
                                # إرسال تنبيه التيليجرام فقط إذا كان الانخفاض شديد
                               # if recent_oee_avg < 50:
                                #    try:
                                 #       from helpers import send_telegram
                                  #      telegram_msg = f"⚠️ **تنبيه: انخفاض متوسط OEE**\n📊 متوسط آخر 5 سجلات: {recent_oee_avg:.1f}%\n🎯 المستهدف: 60%"
                                   #     send_telegram(telegram_msg)
                                    #except:
                                     #   pass
                    elif last_oee < 45:
                        # ✅ تنبيه خفيف للسجل المنخفض جداً (أقل من 45%)
                        existing = self._check_recent_alert('oee', 'very_low_oee', hours=6)
                        if not existing:
                            title = "⚠️ تنبيه: سجل OEE منخفض جداً"
                            message = f"سجل OEE جديد: {last_oee:.1f}% (مستوى منخفض جداً)"
                            alert_id = self.add_alert('oee', title, message, 'info', None, None)
                            if alert_id:
                                alerts_created.append(alert_id)
        
        return alerts_created
    
    def _check_recent_alert(self, alert_type: str, related_name: str, hours: int = 24):
        """التحقق من وجود تنبيه مماثل خلال الساعات المحددة"""
        session = None
        try:
            from datetime import timedelta
            session = self.get_session()
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            alert = session.query(Alert).filter(
                Alert.alert_type == alert_type,
                Alert.related_name == related_name,
                Alert.created_at >= cutoff_time
            ).first()
            return alert is not None
        except Exception as e:
            print(f"Check recent alert error: {e}")
            return False
        finally:
            if session:
                session.close()
    # أضف هذه الدالة في DatabaseManager class

    def _check_recent_oee_alert(self, threshold=50, hours=12):
        """التحقق من وجود تنبيه OEE مماثل خلال الساعات المحددة"""
        session = None
        try:
            from datetime import timedelta
            session = self.get_session()
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # التحقق من وجود تنبيه OEE قريب
            alert = session.query(Alert).filter(
                Alert.alert_type == 'oee',
                Alert.created_at >= cutoff_time
            ).first()
            
            return alert is not None
        except Exception as e:
            print(f"Check OEE alert error: {e}")
            return False
        finally:
            if session:
                session.close()            
    
      

    def get_production_by_id(self, record_id: int):
        session = None
        try:
            session = self.get_session()
            record = session.query(Production).filter(Production.id == record_id).first()
            if record:
                return {
                    'id': record.id,
                    'date': record.date,
                    'line': record.line,
                    'product': record.product,
                    'output_units': record.output_units,
                    'preforms_used': record.preforms_used,
                    'waste_bottles': record.waste_bottles,
                    'packaging_waste': getattr(record, 'packaging_waste', 0) or 0,
                    'line_speed': getattr(record, 'line_speed', 0) or 0,
                    'efficiency': record.efficiency,
                    'downtime_minutes': record.downtime_minutes,
                }
            return None
        finally:
            if session:
                session.close()

    def delete_production(self, record_id: int):
        session = None
        try:
            session = self.get_session()
            record = session.query(Production).filter(Production.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Production record {record_id} deleted")
                return True
            return False
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"delete_production error: {e}")
            return False
        finally:
            if session:
                session.close()

    # ========================================================================
    # Maintenance Functions with Advanced Filters
    # ========================================================================

    def save_maintenance(self, data: dict):
        session = None
        try:
            session = self.get_session()
            if isinstance(data.get('date'), str):
                maint_date = datetime.strptime(data['date'], "%Y-%m-%d")
            elif isinstance(data.get('date'), date):
                maint_date = datetime.combine(data['date'], datetime.min.time())
            elif isinstance(data.get('date'), datetime):
                maint_date = data['date']
            else:
                maint_date = datetime.now()
            maintenance = Maintenance(
                type=data.get('type', 'planned'),
                date=maint_date,
                line=data.get('line', ''),
                machine=data.get('machine', ''),
                technician=data.get('technician', ''),
                issue=data.get('issue', ''),
                task=data.get('task', ''),
                start_time=str(data.get('start_time', '')),
                end_time=str(data.get('end_time', '')),
                downtime_minutes=int(data.get('downtime_minutes', 0)),
                downtime_category=data.get('downtime_category', ''),
                spare_parts=data.get('spare_parts', ''),
                notes=data.get('notes', ''),
                timestamp=datetime.now()
            )
            session.add(maintenance)
            session.commit()
            logger.info(f"Maintenance saved: ID={maintenance.id}")
            return maintenance.id
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"save_maintenance error: {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_all_maintenance(self, start_date=None, end_date=None, line=None, machine=None, technician=None, maint_type=None):
        """الحصول على سجلات الصيانة مع فلترة متقدمة"""
        session = None
        try:
            session = self.get_session()
            query = session.query(Maintenance)
            if start_date:
                query = query.filter(Maintenance.date >= start_date)
            if end_date:
                query = query.filter(Maintenance.date <= end_date)
            if line:
                query = query.filter(Maintenance.line == line)
            if machine:
                query = query.filter(Maintenance.machine == machine)
            if technician:
                query = query.filter(Maintenance.technician == technician)
            if maint_type:
                query = query.filter(Maintenance.type == maint_type)
            query = query.order_by(Maintenance.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_all_maintenance error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    def get_maintenance_by_id(self, record_id: int):
        session = None
        try:
            session = self.get_session()
            record = session.query(Maintenance).filter(Maintenance.id == record_id).first()
            if record:
                return {'id': record.id, 'date': record.date, 'type': record.type, 'machine': record.machine, 'issue': record.issue}
            return None
        finally:
            if session:
                session.close()

    # ========================================================================
    # Delivery Functions with Advanced Filters
    # ========================================================================

    def save_delivery(self, data: dict):
        session = None
        try:
            session = self.get_session()
            if isinstance(data['date'], str):
                delivery_date = datetime.strptime(data['date'], "%Y-%m-%d")
            else:
                delivery_date = data['date']
            delivery = Delivery(
                date=delivery_date,
                product=data.get('product', ''),
                quantity=int(data.get('quantity', 0)),
                customer=data.get('customer', ''),
                delivery_note=data.get('delivery_note', ''),
                notes=data.get('notes', ''),
                timestamp=datetime.now()
            )
            session.add(delivery)
            session.commit()
            logger.info(f"Delivery saved: ID={delivery.id}")
            return delivery.id
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"save_delivery error: {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_all_delivery(self, start_date=None, end_date=None, product=None, customer=None):
        """الحصول على سجلات التحميل مع فلترة متقدمة"""
        session = None
        try:
            session = self.get_session()
            query = session.query(Delivery)
            if start_date:
                query = query.filter(Delivery.date >= start_date)
            if end_date:
                query = query.filter(Delivery.date <= end_date)
            if product:
                query = query.filter(Delivery.product == product)
            if customer:
                query = query.filter(Delivery.customer == customer)
            query = query.order_by(Delivery.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_all_delivery error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ========================================================================
    # Raw Receipts Functions with Advanced Filters
    # ========================================================================

    def save_raw_receipt(self, data: dict):
        session = None
        try:
            session = self.get_session()
            if isinstance(data['date'], str):
                receipt_date = datetime.strptime(data['date'], "%Y-%m-%d")
            else:
                receipt_date = data['date']
            receipt = RawReceipt(
                date=receipt_date,
                material=data.get('material', ''),
                quantity=int(data.get('quantity', 0)),
                invoice=data.get('invoice', ''),
                notes=data.get('notes', ''),
                timestamp=datetime.now()
            )
            session.add(receipt)
            session.commit()
            logger.info(f"Raw receipt saved: ID={receipt.id}")
            return receipt.id
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"save_raw_receipt error: {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_all_raw_receipts(self, start_date=None, end_date=None, material=None, invoice=None):
        """الحصول على سجلات مشتريات المواد الخام مع فلترة متقدمة"""
        session = None
        try:
            session = self.get_session()
            query = session.query(RawReceipt)
            if start_date:
                query = query.filter(RawReceipt.date >= start_date)
            if end_date:
                query = query.filter(RawReceipt.date <= end_date)
            if material:
                query = query.filter(RawReceipt.material == material)
            if invoice:
                query = query.filter(RawReceipt.invoice == invoice)
            query = query.order_by(RawReceipt.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_all_raw_receipts error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ========================================================================
    # OEE and Downtime Analytics
    # ========================================================================

    def get_oee_trend(self, line=None, days=30):
        session = None
        try:
            session = self.get_session()
            start_date = datetime.now() - timedelta(days=days)
            query = session.query(Production).filter(Production.date >= start_date)
            if line:
                query = query.filter(Production.line == line)
            query = query.order_by(Production.date)
            df = pd.read_sql(query.statement, session.bind)
            if df.empty:
                return pd.DataFrame()
            df['date'] = pd.to_datetime(df['date']).dt.date
            daily = df.groupby('date').agg(oee=('oee', 'mean'), availability=('availability', 'mean'), performance=('performance', 'mean'), quality=('quality', 'mean')).reset_index()
            return daily.round(2)
        except Exception as e:
            logger.error(f"get_oee_trend error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    def record_downtime(self, data: dict):
        session = None
        try:
            session = self.get_session()
            start_time = data['start_time']
            if isinstance(start_time, str):
                start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_time = data.get('end_time')
            if end_time and isinstance(end_time, str):
                end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            duration = data.get('duration_minutes', 0)
            if not duration and end_time:
                duration = max(0, int((end_time - start_time).total_seconds() / 60))
            downtime = DowntimeRecord(
                date=start_time.date(),
                line=data.get('line', ''),
                machine=data.get('machine', ''),
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                category=data.get('category', ''),
                sub_category=data.get('sub_category', ''),
                description=data.get('description', ''),
                reported_by=data.get('reported_by', ''),
                shift=data.get('shift', ''),
                is_resolved=end_time is not None,
                resolution_notes=data.get('resolution_notes', ''),
                timestamp=datetime.now()
            )
            session.add(downtime)
            session.commit()
            logger.info(f"Downtime recorded: ID={downtime.id}")
            return downtime.id
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"record_downtime error: {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_downtime_analytics(self, start_date=None, end_date=None, line=None):
        session = None
        try:
            session = self.get_session()
            query = session.query(DowntimeRecord)
            if start_date:
                query = query.filter(DowntimeRecord.date >= start_date)
            if end_date:
                query = query.filter(DowntimeRecord.date <= end_date)
            if line:
                query = query.filter(DowntimeRecord.line == line)
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_downtime_analytics error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ========================================================================
    # Raw Materials Management
    # ========================================================================
    
    def get_all_raw_materials(self):
        """الحصول على جميع المواد الخام"""
        session = None
        try:
            session = self.get_session()
            materials = session.query(RawMaterial).filter(RawMaterial.is_active == True).all()
            return [{
                'id': m.id,
                'material_id': m.material_id,
                'name_ar': m.name_ar,
                'name_en': m.name_en,
                'current_stock': m.current_stock,
                'min_stock': m.min_stock,
                'max_stock': m.max_stock,
                'unit': m.unit,
                'unit_cost': m.unit_cost,
                'daily_consumption': m.daily_consumption,
                'last_updated': m.last_updated
            } for m in materials]
        except Exception as e:
            logger.error(f"get_all_raw_materials error: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def get_raw_material_by_name(self, name: str, lang: str = 'ar'):
        """الحصول على مادة خام بالاسم"""
        session = None
        try:
            from helpers import normalize_material_name
            session = self.get_session()
            raw_name = name or ''
            if lang == 'ar':
                material = session.query(RawMaterial).filter(RawMaterial.name_ar == raw_name, RawMaterial.is_active == True).first()
                if not material:
                    material = session.query(RawMaterial).filter(RawMaterial.name_en == raw_name, RawMaterial.is_active == True).first()
            else:
                material = session.query(RawMaterial).filter(RawMaterial.name_en == raw_name, RawMaterial.is_active == True).first()
                if not material:
                    material = session.query(RawMaterial).filter(RawMaterial.name_ar == raw_name, RawMaterial.is_active == True).first()
            
            if not material:
                normalized = normalize_material_name(raw_name)
                all_materials = session.query(RawMaterial).filter(RawMaterial.is_active == True).all()
                for m in all_materials:
                    if normalize_material_name(m.name_ar) == normalized or normalize_material_name(m.name_en) == normalized:
                        material = m
                        break
            
            if material:
                return {
                    'id': material.id,
                    'material_id': material.material_id,
                    'name_ar': material.name_ar,
                    'name_en': material.name_en,
                    'current_stock': material.current_stock,
                    'min_stock': material.min_stock,
                    'max_stock': material.max_stock,
                    'unit': material.unit,
                    'unit_cost': material.unit_cost,
                    'daily_consumption': material.daily_consumption
                }
            return None
        finally:
            if session:
                session.close()
    
    def update_raw_material_stock(self, material_id: int, quantity: float, transaction_type: str, reference: str = '', notes: str = '', created_by: str = ''):
        """تحديث مخزون المادة الخام وتسجيل الحركة"""
        session = None
        try:
            session = self.get_session()
            material = session.query(RawMaterial).filter(RawMaterial.id == material_id).first()
            if not material:
                return False, "Material not found"
            
            if transaction_type == 'receipt':
                material.current_stock += quantity
            elif transaction_type == 'consumption':
                if material.current_stock < quantity:
                    return False, f"Insufficient stock! Available: {material.current_stock}"
                material.current_stock -= quantity
            elif transaction_type == 'adjustment':
                material.current_stock = quantity
            
            material.last_updated = datetime.now()
            
            transaction = RawMaterialTransaction(
                material_id=material_id,
                transaction_type=transaction_type,
                quantity=quantity,
                reference=reference,
                notes=notes,
                created_by=created_by,
                created_at=datetime.now()
            )
            session.add(transaction)
            session.commit()
            
            return True, f"Stock updated successfully. New stock: {material.current_stock}"
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"update_raw_material_stock error: {e}")
            return False, str(e)
        finally:
            if session:
                session.close()
    
    def add_raw_material(self, data: dict):
        """إضافة مادة خام جديدة"""
        session = None
        try:
            session = self.get_session()
            material = RawMaterial(
                material_id=data.get('material_id'),
                name_ar=data.get('name_ar'),
                name_en=data.get('name_en'),
                current_stock=data.get('current_stock', 0),
                min_stock=data.get('min_stock', 0),
                max_stock=data.get('max_stock', 0),
                unit=data.get('unit', 'قطعة'),
                unit_cost=data.get('unit_cost', 0),
                daily_consumption=data.get('daily_consumption', 0),
                last_updated=datetime.now(),
                is_active=True
            )
            session.add(material)
            session.commit()
            return True, material.id
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"add_raw_material error: {e}")
            return False, str(e)
        finally:
            if session:
                session.close()

    # ========================================================================
    # Finished Goods Management
    # ========================================================================
    
    def get_all_finished_goods(self):
        """الحصول على جميع المنتجات التامة"""
        session = None
        try:
            session = self.get_session()
            goods = session.query(FinishedGood).all()
            return [{
                'id': g.id,
                'name': g.name,
                'opening_balance': g.opening_balance,
                'stock_in': g.stock_in,
                'stock_out': g.stock_out,
                'balance': g.balance,
                'unit': g.unit,
                'month_key': g.month_key,
                'last_updated': g.last_updated
            } for g in goods]
        except Exception as e:
            logger.error(f"get_all_finished_goods error: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def get_finished_good_by_name(self, name: str):
        """الحصول على منتج تام بالاسم"""
        session = None
        try:
            session = self.get_session()
            good = session.query(FinishedGood).filter(FinishedGood.name == name).first()
            if good:
                return {
                    'id': good.id,
                    'name': good.name,
                    'opening_balance': good.opening_balance,
                    'stock_in': good.stock_in,
                    'stock_out': good.stock_out,
                    'balance': good.balance,
                    'unit': good.unit,
                    'month_key': good.month_key
                }
            return None
        finally:
            if session:
                session.close()
    
    def update_finished_good_stock(self, finished_good_id: int, quantity: float, transaction_type: str, reference: str = '', customer: str = '', notes: str = '', created_by: str = ''):
        """تحديث مخزون المنتج التام وتسجيل الحركة"""
        session = None
        try:
            session = self.get_session()
            good = session.query(FinishedGood).filter(FinishedGood.id == finished_good_id).first()
            if not good:
                return False, "Product not found"
            
            if transaction_type == 'production':
                good.stock_in += quantity
                good.balance += quantity
            elif transaction_type == 'delivery':
                if good.balance < quantity:
                    return False, f"Insufficient stock! Available: {good.balance}"
                good.stock_out += quantity
                good.balance -= quantity
            elif transaction_type == 'adjustment':
                good.balance = quantity
            
            good.last_updated = datetime.now()
            
            transaction = FinishedGoodTransaction(
                finished_good_id=finished_good_id,
                transaction_type=transaction_type,
                quantity=quantity,
                reference=reference,
                customer=customer,
                notes=notes,
                created_by=created_by,
                created_at=datetime.now()
            )
            session.add(transaction)
            session.commit()
            
            return True, f"Stock updated successfully. New balance: {good.balance}"
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"update_finished_good_stock error: {e}")
            return False, str(e)
        finally:
            if session:
                session.close()

    # ========================================================================
    # Distinct Values for Filters
    # ========================================================================

    def get_distinct_products(self):
        """الحصول على قائمة المنتجات المميزة"""
        session = None
        try:
            session = self.get_session()
            products = session.query(Production.product).distinct().all()
            return [p[0] for p in products if p[0]]
        except Exception as e:
            logger.error(f"get_distinct_products error: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_distinct_supervisors(self):
        """الحصول على قائمة المشرفين المميزين"""
        session = None
        try:
            session = self.get_session()
            supervisors = session.query(Production.supervisor).distinct().all()
            return [s[0] for s in supervisors if s[0]]
        except Exception as e:
            logger.error(f"get_distinct_supervisors error: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_distinct_machines(self):
        """الحصول على قائمة الماكينات المميزة"""
        session = None
        try:
            session = self.get_session()
            machines = session.query(Maintenance.machine).distinct().all()
            return [m[0] for m in machines if m[0]]
        except Exception as e:
            logger.error(f"get_distinct_machines error: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_distinct_customers(self):
        """الحصول على قائمة العملاء المميزين"""
        session = None
        try:
            session = self.get_session()
            customers = session.query(Delivery.customer).distinct().all()
            return [c[0] for c in customers if c[0]]
        except Exception as e:
            logger.error(f"get_distinct_customers error: {e}")
            return []
        finally:
            if session:
                session.close()

    # ========================================================================
    # DELETE RECORDS METHODS
    # ========================================================================

    def delete_maintenance(self, record_id: int) -> bool:
        """Delete a maintenance record"""
        session = None
        try:
            session = self.get_session()
            record = session.query(Maintenance).filter(Maintenance.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Maintenance record {record_id} deleted")
                return True
            return False
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"delete_maintenance error: {e}")
            return False
        finally:
            if session:
                session.close()

    def delete_delivery(self, record_id: int) -> bool:
        """Delete a delivery record"""
        session = None
        try:
            session = self.get_session()
            record = session.query(Delivery).filter(Delivery.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Delivery record {record_id} deleted")
                return True
            return False
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"delete_delivery error: {e}")
            return False
        finally:
            if session:
                session.close()

    def delete_raw_receipt(self, record_id: int) -> bool:
        """Delete a raw receipt record"""
        session = None
        try:
            session = self.get_session()
            record = session.query(RawReceipt).filter(RawReceipt.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Raw receipt record {record_id} deleted")
                return True
            return False
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"delete_raw_receipt error: {e}")
            return False
        finally:
            if session:
                session.close()

    # ========================================================================
    # Logging System
    # ========================================================================
    
    def add_log(self, event_type: str, action: str, event_level: str = 'INFO', 
                details: str = None, user_id: int = None, username: str = None):
        """إضافة سجل حدث جديد"""
        session = None
        try:
            session = self.get_session()
            
            if user_id is None or username is None:
                try:
                    import streamlit as st
                    if user_id is None:
                        user_id = st.session_state.get('user_id')
                    if username is None:
                        username = st.session_state.get('username') or st.session_state.get('user_name')
                except:
                    pass
            
            log = SystemLog(
                event_type=event_type,
                event_level=event_level,
                user_id=user_id,
                username=username,
                action=action,
                details=details,
                created_at=datetime.now()
            )
            session.add(log)
            session.commit()
            return log.id
        except Exception as e:
            logger.error(f"Failed to add log: {e}")
            if session:
                session.rollback()
            return None
        finally:
            if session:
                session.close()
    
    def add_info_log(self, event_type: str, action: str, details: str = None):
        """إضافة سجل معلومات"""
        return self.add_log(event_type, action, 'INFO', details)
    
    def add_warning_log(self, event_type: str, action: str, details: str = None):
        """إضافة سجل تحذير"""
        return self.add_log(event_type, action, 'WARNING', details)
    
    def add_error_log(self, event_type: str, action: str, details: str = None):
        """إضافة سجل خطأ"""
        return self.add_log(event_type, action, 'ERROR', details)
    
    def add_critical_log(self, event_type: str, action: str, details: str = None):
        """إضافة سجل خطأ حرج"""
        return self.add_log(event_type, action, 'CRITICAL', details)
    
    def get_logs(self, limit: int = 100, offset: int = 0, event_type: str = None, 
                 event_level: str = None, username: str = None, start_date=None, end_date=None):
        """الحصول على سجلات الأحداث مع إمكانية التصفية"""
        session = None
        try:
            session = self.get_session()
            query = session.query(SystemLog)
            
            if event_type:
                query = query.filter(SystemLog.event_type == event_type)
            if event_level:
                query = query.filter(SystemLog.event_level == event_level)
            if username:
                query = query.filter(SystemLog.username == username)
            if start_date:
                query = query.filter(SystemLog.created_at >= start_date)
            if end_date:
                query = query.filter(SystemLog.created_at <= end_date)
            
            query = query.order_by(SystemLog.created_at.desc()).limit(limit).offset(offset)
            
            return [{
                'id': log.id,
                'event_type': log.event_type,
                'event_level': log.event_level,
                'user_id': log.user_id,
                'username': log.username,
                'action': log.action,
                'details': log.details,
                'created_at': log.created_at
            } for log in query.all()]
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def cleanup_old_logs(self, days: int = 30):
        """حذف السجلات القديمة"""
        session = None
        try:
            session = self.get_session()
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted = session.query(SystemLog).filter(SystemLog.created_at < cutoff_date).delete()
            session.commit()
            logger.info(f"Deleted {deleted} old logs (older than {days} days)")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            if session:
                session.rollback()
            return 0
        finally:
            if session:
                session.close()


# ============================================================================
# Global instance
# ============================================================================
db_manager = DatabaseManager()


# ============================================================================
# Compatibility functions
# ============================================================================

def init_database():
    pass

def save_production_to_db(data):
    return db_manager.save_production(data)

def save_maintenance_to_db(data):
    return db_manager.save_maintenance(data)

def save_delivery_to_db(data):
    return db_manager.save_delivery(data)

def save_raw_receipt_to_db(data):
    return db_manager.save_raw_receipt(data)

def load_all_production():
    return db_manager.get_all_production()

def load_all_maintenance():
    return db_manager.get_all_maintenance()

def load_all_delivery():
    return db_manager.get_all_delivery()

def delete_production_by_id(record_id):
    return db_manager.delete_production(record_id)


# ============================================================================
# Delete Records - Public Functions
# ============================================================================

def delete_maintenance_record(record_id: int) -> bool:
    return db_manager.delete_maintenance(record_id)

def delete_delivery_record(record_id: int) -> bool:
    return db_manager.delete_delivery(record_id)

def delete_raw_receipt_record(record_id: int) -> bool:
    return db_manager.delete_raw_receipt(record_id)


def get_database_url():
    try:
        import streamlit as st
        if 'database' in st.secrets:
            db = st.secrets['database']
            if 'url' in db:
                url = db['url']
                if 'supabase' in url and '+psycopg2' not in url:
                    url = url.replace('postgresql://', 'postgresql+psycopg2://')
                return url
            elif all(k in db for k in ['host', 'user', 'password', 'database']):
                port = db.get('port', '5432')
                return f"postgresql+psycopg2://{db['user']}:{db['password']}@{db['host']}:{port}/{db['database']}"
        if 'postgresql' in st.secrets:
            return st.secrets['postgresql']
    except Exception as e:
        logger.warning(f"Could not read from st.secrets: {e}")
    load_dotenv()
    return os.getenv("DATABASE_URL", "")


if __name__ == "__main__":
    print(f"Database connected: {db_manager.is_connected()}")
    print(f"Using SQLite: {db_manager.is_using_sqlite()}")