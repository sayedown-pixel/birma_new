import os
import logging
import bcrypt
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    spare_parts = Column(Text)  # قطع الغيار المستخدمة
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
    delivery_note = Column(String(100))  # رقم سند التحميل
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
        # محاولة قراءة من Streamlit secrets أولاً (للويب/السحابة)
        try:
            import streamlit as st

            # الحالة 1: DATABASE_URL مباشرة كـ key في الـ secrets
            if "DATABASE_URL" in st.secrets:
                url = st.secrets["DATABASE_URL"]
                if isinstance(url, str) and url.strip():
                    os.environ["DATABASE_URL"] = url.strip()
                    logger.info("✅ DATABASE_URL loaded from st.secrets (top-level)")

            # الحالة 2: [database] section في secrets.toml
            elif "database" in st.secrets:
                db_section = st.secrets["database"]
                # إذا كان string مباشرة
                if isinstance(db_section, str) and db_section.strip():
                    os.environ["DATABASE_URL"] = db_section.strip()
                    logger.info("✅ DATABASE_URL loaded from st.secrets['database'] string")
                # إذا كان dict (section) يحتوي على url أو DATABASE_URL
                elif hasattr(db_section, 'get'):
                    url = db_section.get("url") or db_section.get("DATABASE_URL") or db_section.get("connection_string", "")
                    if url and url.strip():
                        os.environ["DATABASE_URL"] = url.strip()
                        logger.info("✅ DATABASE_URL loaded from st.secrets['database'] section")

        except Exception as e:
            logger.warning(f"Could not read st.secrets: {e}")

        DATABASE_URL = os.getenv("DATABASE_URL", "")

        if DATABASE_URL and DATABASE_URL.strip():
            db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

            try:
                self.engine = create_engine(
                    db_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                )

                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()
                    logger.info(f"PostgreSQL connected: {version[0][:50]}...")

                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
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
                self._connected = False
                raise Exception(f"PostgreSQL connection required but failed: {e}")

        # PostgreSQL is required - do not fall back to SQLite
        logger.error("❌ DATABASE_URL not configured. PostgreSQL is required.")
        self._init_error = "DATABASE_URL not configured"
        self._connected = False
        raise Exception("DATABASE_URL environment variable must be set for PostgreSQL connection")
    
    def _init_sqlite(self):
        try:
            sqlite_url = f'sqlite:///{SQLITE_DB_PATH}'
            
            self.engine = create_engine(
                sqlite_url, 
                echo=False, 
                connect_args={"check_same_thread": False}
            )
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
        """Add new columns to existing databases without losing data."""
        new_cols = [
            ("production", "packaging_waste", "FLOAT", "0"),
            ("production", "line_speed", "INTEGER", "0"),
            ("delivery", "delivery_note", "VARCHAR(100)", "''"),
            ("maintenance", "spare_parts", "TEXT", "''"),
        ]
        for table, column, col_type, default in new_cols:
            self._ensure_column(table, column, col_type, default)

    def _ensure_column(self, table: str, column: str, col_type: str, default: str):
        if not self.engine:
            return
        try:
            with self.engine.connect() as conn:
                if self._use_sqlite:
                    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    if any(r[1] == column for r in rows):
                        return
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"
                    ))
                else:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type} DEFAULT {default}"
                    ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Schema migration skipped for {table}.{column}: {e}")

    def _create_default_admin(self):
        session = None
        try:
            session = self.get_session()
            
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
                        password_hash=self.hash_password(user_data["password"]),
                        role=user_data["role"],
                        name=user_data["name"],
                        icon=user_data["icon"],
                        is_active=True,
                        created_at=datetime.now()
                    )
                    session.add(new_user)
            
            session.commit()
            logger.info("Default users created/verified.")
            
        except Exception as e:
            logger.warning(f"Could not create default users: {e}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def authenticate_user(self, username: str, password: str):
        session = None
        try:
            session = self.get_session()
            user = session.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if user and self.verify_password(password, user.password_hash):
                user.last_login = datetime.now()
                session.commit()
                return {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'name': user.name,
                    'icon': user.icon,
                    'is_active': user.is_active
                }
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
        finally:
            if session:
                session.close()

    def create_user(self, username: str, password: str, role: str, name: str, icon: str = "👤") -> bool:
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
                created_at=datetime.now()
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
            return [
                {
                    'id': u.id,
                    'username': u.username,
                    'role': u.role,
                    'name': u.name,
                    'icon': u.icon,
                    'is_active': u.is_active,
                    'created_at': u.created_at,
                    'last_login': u.last_login
                }
                for u in users
            ]
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

    # ------------------------------------------------------------------
    # OEE Calculation
    # ------------------------------------------------------------------

    def calculate_oee(self, data: dict) -> dict:
        working = int(data.get('working_minutes', 0) or 0)
        planned_time = working if working > 0 else int(data.get('planned_production_time', 900) or 900)
        downtime = max(0, int(data.get('downtime_minutes', 0) or 0))
        operating_time = max(0, planned_time - downtime)
        availability = (operating_time / planned_time * 100) if planned_time > 0 else 0

        ideal_run_rate = float(data.get('ideal_run_rate', 0) or 0)
        actual_output_units = int(data.get('output_units', 0) or 0)
        pieces = max(1, int(data.get('pieces_per_unit', 1) or 1))
        actual_bottles = actual_output_units * pieces
        if operating_time > 0 and ideal_run_rate > 0:
            actual_rate = actual_bottles / operating_time
            performance = min(100.0, (actual_rate / ideal_run_rate) * 100)
        else:
            performance = 0.0

        waste = max(0, int(data.get('waste_bottles', 0) or 0))
        bottles_total = actual_bottles
        good_bottles = max(0, bottles_total - waste)
        quality = (good_bottles / bottles_total * 100) if bottles_total > 0 else 0

        oee = (availability * performance * quality) / 10000

        return {
            'oee': round(oee, 2),
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'planned_time': planned_time,
            'operating_time': operating_time,
            'downtime': downtime
        }

    # ------------------------------------------------------------------
    # Production CRUD
    # ------------------------------------------------------------------

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
            logger.info(f"Production saved: ID={production.id}")
            return production.id
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"save_production error: {e}")
            raise e
        finally:
            if session:
                session.close()

    def get_all_production(self, start_date=None, end_date=None, line=None):
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
                
            query = query.order_by(Production.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            logger.info(f"Retrieved {len(df)} production records")
            return df
            
        except Exception as e:
            logger.error(f"get_all_production error: {e}")
            return pd.DataFrame()
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

    # ------------------------------------------------------------------
    # Maintenance CRUD
    # ------------------------------------------------------------------

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

    def get_all_maintenance(self):
        session = None
        try:
            session = self.get_session()
            query = session.query(Maintenance).order_by(Maintenance.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            logger.info(f"Retrieved {len(df)} maintenance records")
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
                return {
                    'id': record.id,
                    'date': record.date,
                    'type': record.type,
                    'machine': record.machine,
                    'issue': record.issue
                }
            return None
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # Delivery CRUD
    # ------------------------------------------------------------------

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

    def get_all_delivery(self):
        session = None
        try:
            session = self.get_session()
            query = session.query(Delivery).order_by(Delivery.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            logger.info(f"Retrieved {len(df)} delivery records")
            return df
        except Exception as e:
            logger.error(f"get_all_delivery error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # Raw Receipt CRUD
    # ------------------------------------------------------------------

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

    def get_all_raw_receipts(self):
        session = None
        try:
            session = self.get_session()
            query = session.query(RawReceipt).order_by(RawReceipt.date.desc())
            df = pd.read_sql(query.statement, session.bind)
            return df
        except Exception as e:
            logger.error(f"get_all_raw_receipts error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # OEE Trend
    # ------------------------------------------------------------------

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
            daily = df.groupby('date').agg(
                oee=('oee', 'mean'),
                availability=('availability', 'mean'),
                performance=('performance', 'mean'),
                quality=('quality', 'mean')
            ).reset_index()
            
            return daily.round(2)
            
        except Exception as e:
            logger.error(f"get_oee_trend error: {e}")
            return pd.DataFrame()
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # Downtime
    # ------------------------------------------------------------------

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


if __name__ == "__main__":
    print(f"Database connected: {db_manager.is_connected()}")
    print(f"Using SQLite: {db_manager.is_using_sqlite()}")
def get_database_url():
    """الحصول على رابط قاعدة البيانات من Streamlit Secrets أو .env"""
    
    try:
        import streamlit as st
        
        # دعم Supabase
        if 'database' in st.secrets:
            db = st.secrets['database']
            if 'url' in db:
                url = db['url']
                # تأكد من الصيغة الصحيحة لـ Supabase
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