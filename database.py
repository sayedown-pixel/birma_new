import os
import logging
import bcrypt
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Index, text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import pandas as pd
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()
SQLITE_DB_PATH = "birma_data.db"

def get_database_url():
    """الحصول على رابط قاعدة البيانات من Streamlit Secrets"""
    
    # طباعة جميع secrets للتأكد (لأغراض debug فقط)
    try:
        logger.info(f"Available secrets keys: {list(st.secrets.keys())}")
    except:
        pass
    
    # الطريقة 1: postgresql مباشرة
    try:
        if 'postgresql' in st.secrets:
            url = st.secrets['postgresql']
            if url and url.startswith('postgresql://'):
                logger.info("✅ Found postgresql in secrets")
                return url
    except Exception as e:
        logger.warning(f"Error reading postgresql: {e}")
    
    # الطريقة 2: database section مع url
    try:
        if 'database' in st.secrets:
            db = st.secrets['database']
            if isinstance(db, dict) and 'url' in db:
                url = db['url']
                if url and url.startswith('postgresql://'):
                    logger.info("✅ Found database.url in secrets")
                    return url
    except Exception as e:
        logger.warning(f"Error reading database.url: {e}")
    
    # الطريقة 3: DATABASE_URL
    try:
        if 'DATABASE_URL' in st.secrets:
            url = st.secrets['DATABASE_URL']
            if url and url.startswith('postgresql://'):
                logger.info("✅ Found DATABASE_URL in secrets")
                return url
    except Exception as e:
        logger.warning(f"Error reading DATABASE_URL: {e}")
    
    # للتشغيل المحلي
    load_dotenv()
    url = os.getenv("DATABASE_URL", "")
    if url:
        logger.info("Using DATABASE_URL from .env")
    else:
        logger.warning("No database URL found, will use SQLite")
    
    return url

# ... باقي تعريفات الـ Models (User, Production, Maintenance, Delivery, RawReceipt, DowntimeRecord, OEESummary)
# ... ضع هنا تعريفات الـ Models كما هي موجودة في ملفك الحالي

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._connected = False
        self._init_error = None
        self._use_sqlite = False
        self._init_connection()

    def _init_connection(self):
        """تهيئة الاتصال بقاعدة البيانات"""
        
        DATABASE_URL = get_database_url()
        
        # طباعة للتأكد (إخفاء كلمة المرور)
        if DATABASE_URL:
            # إخفاء كلمة المرور للطباعة
            parts = DATABASE_URL.split('@')
            if len(parts) > 1:
                logger.info(f"Connecting to database at: {parts[1]}")
            else:
                logger.info("Database URL found (format unknown)")
        else:
            logger.info("No DATABASE_URL, using SQLite")
        
        if DATABASE_URL and DATABASE_URL.strip():
            # تحويل URL لصيغة SQLAlchemy
            if DATABASE_URL.startswith("postgresql://"):
                db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
            else:
                db_url = DATABASE_URL
            
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
                    logger.info(f"✅ PostgreSQL connected: {version[0][:50] if version else 'OK'}")
                
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                Base.metadata.create_all(bind=self.engine)
                self._migrate_schema()
                self._connected = True
                self._use_sqlite = False
                self._create_default_admin()
                logger.info("Database initialized with PostgreSQL")
                return
                
            except Exception as e:
                logger.warning(f"PostgreSQL connection failed: {e}, falling back to SQLite")
                self._init_error = str(e)
        
        # استخدام SQLite كبديل
        self._init_sqlite()
    
    def _init_sqlite(self):
        """تهيئة SQLite كقاعدة بيانات محلية"""
        try:
            self.engine = create_engine(f'sqlite:///{SQLITE_DB_PATH}', echo=False)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            self._migrate_schema()
            self._connected = True
            self._use_sqlite = True
            self._init_error = None
            logger.info(f"✅ SQLite database initialized at {SQLITE_DB_PATH}")
            self._create_default_admin()
        except Exception as e:
            self._init_error = str(e)
            self._connected = False
            logger.error(f"❌ SQLite initialization failed: {e}")

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

    # ... باقي دوال DatabaseManager (hash_password, verify_password, authenticate_user, save_production, get_all_production, etc.)
    # ضع هنا جميع الدوال الأخرى كما هي موجودة في ملفك الحالي

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