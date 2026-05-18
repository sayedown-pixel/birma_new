import math
import os
import pandas as pd
import requests
import urllib.parse
from datetime import datetime, timedelta

# ============================================================================
# User Management
# ============================================================================
USERS = {
    "admin": {"password": "100",        "role": "admin",       "name": "مدير النظام",   "icon": "👑"},
    "pro":   {"password": "400",        "role": "supervisor",  "name": "مشرف إنتاج",   "icon": "👔"},
    "tec":   {"password": "300",        "role": "technician",  "name": "فني صيانة",    "icon": "🔧"},
    "sto":   {"password": "200",        "role": "storekeeper", "name": "أمين مخزن",    "icon": "📦"},
    "quality":{"password":"quality123", "role": "quality",     "name": "مراقب جودة",   "icon": "🔍"},
}

ROLE_PERMISSIONS = {
    "admin":       ["🏠 Dashboard","📈 Production","🔧 Maintenance","📊 Records",
                    "📦 Raw Materials","🏭 Finished Goods","👥 Users","⚙️ Settings"],
    "supervisor":  ["🏠 Dashboard","📈 Production","🔧 Maintenance","📊 Records",
                    "📦 Raw Materials","🏭 Finished Goods"],
    "technician":  ["🏠 Dashboard","🔧 Maintenance","📊 Records"],
    "storekeeper": ["🏠 Dashboard","📦 Raw Materials","🏭 Finished Goods","📊 Records"],
    "quality":     ["🏠 Dashboard","📊 Records","📈 Production"],
}

# ============================================================================
# Language Dictionary
# ============================================================================
LANG = {
    "ar": {
        "designer": "م/ السيد عون",
        "login_title": "تسجيل الدخول",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "login_btn": "دخول",
        "login_error": "خطأ في اسم المستخدم أو كلمة المرور",
        "logout": "تسجيل خروج",
        "logout_btn": "تسجيل الخروج",
        "welcome": "مرحباً",
        "role": "الدور",
        "dark_mode": "الوضع الليلي",
        "app_title": "نظام المصنع الذكي",
        "dashboard": "🏠 لوحة القيادة",
        "production": "📈 إدارة الإنتاج",
        "maintenance": "🔧 مركز الصيانة",
        "records": "📊 السجلات",
        "raw_materials": "📦 المخازن (مواد خام)",
        "finished_goods": "🏭 مخزن الإنتاج التام",
        "users": "👥 المستخدمين",
        "settings": "⚙️ الإعدادات",
        "line_label": "خط العمل",
        "sup_label": "المشرف",
        "prod_label": "المنتج",
        "target_label": "الكمية المستهدفة",
        "preform_label": "البريفورم المستخدم",
        "raw_label": "خامة التغليف",
        "date_label": "التاريخ",
        "maint_header": "مركز الصيانة",
        "maint_types": ["صيانة دورية", "بلاغ عطل"],
        "tech_label": "اسم الفني",
        "issue_label": "وصف العطل",
        "start_t": "بداية التوقف",
        "end_t": "نهاية الإصلاح",
        "note_label": "ملاحظات",
        "save_btn": "حفظ",
        "success_msg": "تم الحفظ بنجاح",
        "eff_title": "مؤشر الكفاءة",
        "waste_title": "تحليل الهالك",
        "history_p": "سجل الإنتاج",
        "history_m": "سجل الصيانة",
        "history_delivery": "سجل التحميل",
        "admin_title": "لوحة التحكم - حذف السجل",
        "delete_btn": "حذف السجل",
        "del_success": "تم الحذف",
        "tools_label": "الأدوات المطلوبة:",
        "proc_label": "الإجراءات:",
        "weekend_msg": "الجمعة عطلة رسمية",
        "inventory_header": "إدارة المخازن",
        "current_stock": "المخزون الحالي",
        "receipt": "استلام مشتريات",
        "material": "المادة",
        "quantity": "الكمية",
        "invoice": "رقم الفاتورة",
        "receipt_date": "تاريخ الاستلام",
        "register_receipt": "تسجيل الاستلام",
        "low_stock_alert": "تنبيه: مواد منخفضة",
        "all_good": "جميع المواد آمنة",
        "edit_stock": "تعديل الرصيد يدوياً",
        "new_stock": "الرصيد الجديد",
        "update": "تحديث",
        "stock_updated": "تم تحديث الرصيد",
        "export_btn": "تصدير",
        "dashboard_title": "لوحة القيادة الرئيسية",
        "total_production": "إجمالي الإنتاج",
        "monthly_production": "إنتاج الشهر الحالي",
        "line1_efficiency": "كفاءة الخط الأول",
        "line2_efficiency": "كفاءة الخط الثاني",
        "smart_recommendations": "التوصيات الذكية",
        "users_title": "إدارة المستخدمين",
        "settings_title": "إعدادات النظام",
        "backup_data": "نسخ احتياطي",
        "clear_cache": "مسح الذاكرة المؤقتة",
        "machine_select": "اختر الماكينة",
        "task_name": "المهمة",
        "done": "تم التنفيذ",
        "no_data": "لا توجد بيانات",
        "no_production": "لا توجد سجلات إنتاج",
        "no_maintenance": "لا توجد سجلات صيانة",
        "no_delivery": "لا توجد سجلات تحميل",
        "add_new_item": "إضافة صنف جديد",
        "item_id": "الرقم",
        "item_name": "اسم المادة",
        "item_unit": "الوحدة",
        "min_stock": "الحد الأدنى",
        "info_title": "معلومات النظام",
        "info_text": "يتم حفظ البيانات في قاعدة البيانات",
        "shipping": "شحن منتجات",
        "customer": "اسم العميل",
        "register_shipping": "تسجيل الشحن",
        "balance": "الرصيد الحالي",
        "in": "وارد",
        "out": "صادر",
        "pallet_count": "عدد الباليتات",
        "last_10_days": "آخر 10 أيام",
        "remember_me": "تذكرني",
        "clear_saved": "مسح البيانات المحفوظة",
        "auto_reorder": "تنبيه إعادة الطلب",
        "stock_prediction": "توقع نفاذ المخزون",
        "raw_balance": "أرصدة المواد الخام",
        "fg_balance": "أرصدة المنتج التام",
        "delivery": "تسليم بضاعة",
        "product": "المنتج",
        "quantity_to_deliver": "كمية التسليم",
        "manual_adjust": "تعديل يدوي",
        "waste_bottles": "هالك العبوات",
        # الكلمات الجديدة
        "materials_depletion": "مدة نفاذ المواد الخام",
        "days_left": "الأيام المتبقية",
        "status": "الحالة",
        "all_materials_safe": "جميع المواد آمنة ولا يوجد خطر نفاذ خلال 30 يوم",
        "shift_info": "معلومات الوردية",
        "shift_start": "بداية الوردية",
        "shift_end": "نهاية الوردية",
        "working_hours": "ساعات العمل الفعلية",
        "currently_working": "الوردية تعمل حالياً",
        "break_time": "وقت بريك حالياً",
        "menu": "القائمة",
        "connected": "متصل",
        "disconnected": "غير متصل",
        "line1": "الخط الأول (line 1)",
        "line2": "الخط الثاني (line 2)",
        "prod_report_title": "تسجيل تقرير إنتاج جديد",
        "prod_qty_label": "الكمية المنتجة",
        "preform_actual": "عدد البريفورم المستخدم",
        "packaging_actual": "كمية خامة التغليف المستخدمة",
        "line_speed_label": "سرعة الخط",
        "units_per_hour": "عبوة/ساعة",
        "save_report": "حفظ التقرير",
        "raw_stock_expander": "المخزون الحالي للمواد الخام",
        "no_raw_stock": "لا توجد بيانات مخزون متاحة",
        "report_saved": "تم حفظ التقرير",
        "record_no": "رقم السجل",
        "col_id": "رقم",
        "col_date": "التاريخ",
        "col_line": "الخط",
        "col_product": "المنتج",
        "col_qty": "الكمية",
        "col_waste_bottles": "هالك العبوات",
        "col_packaging_waste": "هالك التغليف",
        "col_line_speed": "سرعة الخط",
        "col_efficiency": "الكفاءة %",
        "col_supervisor": "المشرف",
        "col_oee": "OEE %",
        "col_type": "النوع",
        "col_machine": "الماكينة",
        "col_technician": "الفني",
        "col_task": "المهمة",
        "col_issue": "العطل",
        "col_customer": "العميل",
        "col_notes": "ملاحظات",
        "records_count": "عدد السجلات",
        "total_units": "إجمالي الإنتاج",
        "avg_oee": "متوسط OEE",
        "avg_efficiency": "متوسط الكفاءة",
        "maint_records_count": "عدد سجلات الصيانة",
        "delivery_records_count": "عدد سجلات التسليم",
        "tip_production": "قم بتسجيل تقرير إنتاج جديد من صفحة الإنتاج",
        "tip_maintenance": "قم بتسجيل تقرير صيانة جديد من صفحة الصيانة",
        "no_delivery_records": "لا توجد سجلات تسليم مسجلة",
        "marquee_stock": "الرصيد",
        "marquee_suggested": "الكمية المقترحة",
        "marquee_deplete_in": "سينفذ خلال",
        "marquee_days": "يوم",
        "marquee_fg_empty": "فارغ - يرجى زيادة الإنتاج",
        "marquee_fg_units": "وحدة",
        "opening_balance": "رصيد مرحل",
        "month_rollover_done": "تم ترحيل رصيد الشهر الجديد",
        "chart_material": "المادة",
        "chart_quantity": "الكمية",
        "chart_product": "المنتج",
        "chart_raw_title": "أرصدة المواد الخام",
        "chart_fg_title": "أرصدة المنتج التام",
        "no_raw_data": "لا توجد بيانات مواد خام",
        "no_fg_data": "لا توجد بيانات منتج تام",
        "suggested_reorder": "مقترح إعادة الطلب",
        "balance_label": "الرصيد",
        "min_label": "الحد الأدنى",
        "will_run_out": "سينفذ خلال",
        "days_word": "يوم",
        "records_label": "سجل",
        "break_minutes_label": "مدة البريك (دقائق)",
        "auto_calc_title": "الحسابات التلقائية",
        "working_hours_label": "ساعات التشغيل",
        "minutes_word": "دقيقة",
        "col_downtime": "مدة التوقف",
        "col_operating_time": "وقت التشغيل",
        "preform_help": "إجباري — يُسجّل في السجل كما أدخلته",
        "preform_required": "يرجى إدخال عدد البريفورم/العبوات المستخدم",
        "delete_production_title": "حذف سجل إنتاج",
        "delete_confirm": "حذف السجل المحدد",
        "delete_success": "تم حذف السجل وإرجاع المخزون",
        "delete_failed": "فشل حذف السجل",
        "select_record_delete": "اختر السجل للحذف",
        "prod_qty_units": "كمية الإنتاج (بالوحدة)",
        "unit_hint": "الوحدة = كرتون/باكيت حسب المنتج (مثال: كرتون 200مل = 48 عبوة)",
        "hours_word": "ساعة",
        "col_qty_units": "الكمية (وحدة)",
        "packaging_help": "0 = نفس عدد وحدات الإنتاج (كرتون/شرنك)",
        "packaging_carton": "وحدات التغليف (كرتون)",
        "packaging_shrink": "وحدات التغليف (شرنك)",
        "bottles_per_hour": "عبوة/ساعة",
        "col_line_speed_bottles": "سرعة الخط (عبوة/ساعة)",
        "units_word": "وحدة",
    },
    "en": {
        "designer": "Eng. Elsayed Aoun",
        "login_title": "Login",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "login_error": "Invalid username or password",
        "logout": "Logout",
        "logout_btn": "Logout",
        "welcome": "Welcome",
        "role": "Role",
        "dark_mode": "Dark Mode",
        "app_title": "Smart Factory System",
        "dashboard": "🏠 Dashboard",
        "production": "📈 Production",
        "maintenance": "🔧 Maintenance",
        "records": "📊 Records",
        "raw_materials": "📦 Raw Materials",
        "finished_goods": "🏭 Finished Goods",
        "users": "👥 Users",
        "settings": "⚙️ Settings",
        "line_label": "Production Line",
        "sup_label": "Supervisor",
        "prod_label": "Product",
        "target_label": "Target Quantity",
        "preform_label": "Preforms Used",
        "raw_label": "Packaging Material",
        "date_label": "Date",
        "maint_header": "Maintenance Center",
        "maint_types": ["Planned Maintenance", "Breakdown"],
        "tech_label": "Technician Name",
        "issue_label": "Issue Description",
        "start_t": "Stop Start",
        "end_t": "Repair End",
        "note_label": "Notes",
        "save_btn": "Save",
        "success_msg": "Saved successfully",
        "eff_title": "Efficiency Indicator",
        "waste_title": "Waste Analysis",
        "history_p": "Production Logs",
        "history_m": "Maintenance Logs",
        "history_delivery": "Delivery Logs",
        "admin_title": "Admin Panel - Delete Record",
        "delete_btn": "Delete Record",
        "del_success": "Deleted",
        "tools_label": "Required Tools:",
        "proc_label": "Procedures:",
        "weekend_msg": "Friday is official holiday",
        "inventory_header": "Inventory Management",
        "current_stock": "Current Stock",
        "receipt": "Receive Purchases",
        "material": "Material",
        "quantity": "Quantity",
        "invoice": "Invoice Number",
        "receipt_date": "Receipt Date",
        "register_receipt": "Register Receipt",
        "low_stock_alert": "Alert: Low Stock",
        "all_good": "All Materials Safe",
        "edit_stock": "Manual Stock Edit",
        "new_stock": "New Stock",
        "update": "Update",
        "stock_updated": "Stock Updated",
        "export_btn": "Export",
        "dashboard_title": "Main Dashboard",
        "total_production": "Total Production",
        "monthly_production": "Monthly Production",
        "line1_efficiency": "Line 1 Efficiency",
        "line2_efficiency": "Line 2 Efficiency",
        "smart_recommendations": "Smart Recommendations",
        "users_title": "User Management",
        "settings_title": "System Settings",
        "backup_data": "Backup Data",
        "clear_cache": "Clear Cache",
        "machine_select": "Select Machine",
        "task_name": "Task",
        "done": "Completed",
        "no_data": "No data available",
        "no_production": "No production records",
        "no_maintenance": "No maintenance records",
        "no_delivery": "No delivery records",
        "add_new_item": "Add New Item",
        "item_id": "ID",
        "item_name": "Material Name",
        "item_unit": "Unit",
        "min_stock": "Minimum Stock",
        "info_title": "System Information",
        "info_text": "Data is saved in the database",
        "shipping": "Shipping Products",
        "customer": "Customer Name",
        "register_shipping": "Register Shipping",
        "balance": "Current Balance",
        "in": "Incoming",
        "out": "Outgoing",
        "pallet_count": "Number of Pallets",
        "last_10_days": "Last 10 Days",
        "remember_me": "Remember Me",
        "clear_saved": "Clear Saved Data",
        "auto_reorder": "Auto Reorder Alert",
        "stock_prediction": "Stock Depletion Prediction",
        "raw_balance": "Raw Materials Balance",
        "fg_balance": "Finished Goods Balance",
        "delivery": "Product Delivery",
        "product": "Product",
        "quantity_to_deliver": "Delivery Quantity",
        "manual_adjust": "Manual Adjustment",
        "waste_bottles": "Waste Bottles",
        # New keys
        "materials_depletion": "Materials Depletion Time",
        "days_left": "Days Left",
        "status": "Status",
        "all_materials_safe": "All materials are safe, no depletion risk within 30 days",
        "shift_info": "Shift Information",
        "shift_start": "Shift Start",
        "shift_end": "Shift End",
        "working_hours": "Actual Working Hours",
        "currently_working": "Shift is currently working",
        "break_time": "Break time currently",
        "menu": "Menu",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "line1": "Line 1",
        "line2": "Line 2",
        "prod_report_title": "New Production Report",
        "prod_qty_label": "Produced Quantity",
        "preform_actual": "Preforms Used",
        "packaging_actual": "Packaging Material Used",
        "line_speed_label": "Line Speed",
        "units_per_hour": "units/hr",
        "save_report": "Save Report",
        "raw_stock_expander": "Current Raw Materials Stock",
        "no_raw_stock": "No inventory data available",
        "report_saved": "Report saved",
        "record_no": "Record ID",
        "col_id": "ID",
        "col_date": "Date",
        "col_line": "Line",
        "col_product": "Product",
        "col_qty": "Quantity",
        "col_waste_bottles": "Bottle Waste",
        "col_packaging_waste": "Packaging Waste",
        "col_line_speed": "Line Speed",
        "col_efficiency": "Efficiency %",
        "col_supervisor": "Supervisor",
        "col_oee": "OEE %",
        "col_type": "Type",
        "col_machine": "Machine",
        "col_technician": "Technician",
        "col_task": "Task",
        "col_issue": "Issue",
        "col_customer": "Customer",
        "col_notes": "Notes",
        "records_count": "Records Count",
        "total_units": "Total Production",
        "avg_oee": "Average OEE",
        "avg_efficiency": "Average Efficiency",
        "maint_records_count": "Maintenance Records",
        "delivery_records_count": "Delivery Records",
        "tip_production": "Register a new production report from the Production page",
        "tip_maintenance": "Register a new maintenance report from the Maintenance page",
        "no_delivery_records": "No delivery records found",
        "marquee_stock": "Stock",
        "marquee_suggested": "Suggested qty",
        "marquee_deplete_in": "runs out in",
        "marquee_days": "days",
        "marquee_fg_empty": "empty - increase production",
        "marquee_fg_units": "units",
        "opening_balance": "Opening Balance",
        "month_rollover_done": "Monthly balance carried forward",
        "chart_material": "Material",
        "chart_quantity": "Quantity",
        "chart_product": "Product",
        "chart_raw_title": "Raw Materials Balance",
        "chart_fg_title": "Finished Goods Balance",
        "no_raw_data": "No raw materials data",
        "no_fg_data": "No finished goods data",
        "suggested_reorder": "Suggested reorder",
        "balance_label": "Balance",
        "min_label": "Min",
        "will_run_out": "Will run out in",
        "days_word": "days",
        "records_label": "records",
        "break_minutes_label": "Break duration (minutes)",
        "auto_calc_title": "Auto calculations",
        "working_hours_label": "Operating time",
        "minutes_word": "min",
        "col_downtime": "Downtime",
        "col_operating_time": "Operating time",
        "preform_help": "Required — saved in records exactly as entered",
        "preform_required": "Enter total preforms/bottles used",
        "delete_production_title": "Delete production record",
        "delete_confirm": "Delete selected record",
        "delete_success": "Record deleted and inventory restored",
        "delete_failed": "Failed to delete record",
        "select_record_delete": "Select record to delete",
        "prod_qty_units": "Production quantity (units)",
        "unit_hint": "Unit = carton/pack per product (e.g. 200ml carton = 48 bottles)",
        "hours_word": "hrs",
        "col_qty_units": "Quantity (units)",
        "packaging_help": "0 = same as production units (carton/shrink)",
        "packaging_carton": "Packaging units (cartons)",
        "packaging_shrink": "Packaging units (shrink)",
        "bottles_per_hour": "bottles/hr",
        "col_line_speed_bottles": "Line speed (bottles/hr)",
        "units_word": "units",
    }
}

# ============================================================================
# Helper Functions
# ============================================================================

def load_language(lang_code='ar'):
    return LANG.get(lang_code, LANG['ar'])


def get_text(key, lang_code='ar'):
    return load_language(lang_code).get(key, key)


# ============================================================================
# Production Configuration
# ============================================================================
CONFIG = {
    "الخط الأول (line 1)": {
        "products": ["200 ml Carton", "200 ml Shrink", "600 ml Carton", "1.5 L Shrink"],
        "pack_per_unit": {
            "200 ml Carton": 48,
            "200 ml Shrink": 20,
            "600 ml Carton": 30,
            "1.5 L Shrink": 6,
        },
        "speed": {
            "200 ml Carton": 35000,
            "200 ml Shrink": 35000,
            "600 ml Carton": 20000,
            "1.5 L Shrink": 12000,
        }
    },
    "الخط الثاني (line 2)": {
        "products": ["200 ml Carton", "200 ml Shrink", "330 ml Carton", "330 ml Shrink"],
        "pack_per_unit": {
            "200 ml Carton": 48,
            "200 ml Shrink": 20,
            "330 ml Carton": 40,
            "330 ml Shrink": 20,
        },
        "speed": {
            "200 ml Carton": 40000,
            "200 ml Shrink": 40000,
            "330 ml Carton": 40000,
            "330 ml Shrink": 40000,
        }
    }
}

# ============================================================================
# Bill of Materials (BOM)
# ============================================================================
BOM = {
    "200 ml Carton": {
        "بريفورم 200 مل": 48,
        "غطاء":           48,
        "ليبل 200 مل":    48,
        "كرتون 200 مل":   1,
    },
    "200 ml Shrink": {
        "بريفورم 200 مل": 20,
        "غطاء":           20,
        "ليبل 200 مل":    20,
        "شرنك 200 مل":    0.0005,
    },
    "600 ml Carton": {
        "بريفورم 600 مل": 30,
        "غطاء":           30,
        "ليبل 600 مل":    30,
        "كرتون 600 مل":   1,
    },
    "1.5 L Shrink": {
        "بريفورم 1.5 لتر": 6,
        "غطاء":             6,
        "ليبل 1.5 لتر":    6,
        "شرنك 1.5 لتر":   0.000625,
    },
    "330 ml Carton": {
        "بريفورم 330 مل": 40,
        "غطاء":           40,
        "ليبل 330 مل":    40,
        "كرتون 330 مل":   1,
    },
    "330 ml Shrink": {
        "بريفورم 330 مل": 20,
        "غطاء":           20,
        "ليبل 330 مل":    20,
        "شرنك 330 مل":    0.0005,
    },
}

FIXED_CAP_CONSUMPTION = 900000

SHRINK_PALLET_CONFIG = {
    "200 ml Shrink": {"units_per_pallet": 180, "spacers_per_pallet": 7},
    "330 ml Shrink": {"units_per_pallet": 144, "spacers_per_pallet": 5},
    "1.5 L Shrink":  {"units_per_pallet": 88,  "spacers_per_pallet": 5},
}

# ============================================================================
# Machine Mapping for Maintenance
# ============================================================================
MACHINE_FILES = [
    "blowing_machine.xlsx",
    "labeling_machine.xlsx",
    "Conveyor_machine.xlsx",
    "packing_machine.xlsx",
    "paletizer_machine.xlsx",
    "shrink_machine.xlsx",
    "Filling_machine.xlsx",
    "AF_Compressor_Maintenance_LTR.xlsx",
]

MACHINE_LABELS = {
    "ar": [
        "النفخ(blowing)",
        "الليبل(labeling)",
        "السيور(Conveyor)",
        "الكرتون(packing)",
        "البالتايزر(paletizer)",
        "الشرنك(shrink)",
        "التعبئة(filling)",
        "كمبروسر الهواء (Air Compressor)",
    ],
    "en": [
        "Blowing",
        "Labeling",
        "Conveyor",
        "Carton Packing",
        "Palletizer",
        "Shrink",
        "Filling",
        "Air Compressor",
    ],
}

MACHINE_MAP = dict(zip(MACHINE_LABELS["ar"], MACHINE_FILES))


def get_machine_map(lang_code="ar"):
    """Machine display names by language → Excel file path."""
    labels = MACHINE_LABELS.get(lang_code, MACHINE_LABELS["ar"])
    return dict(zip(labels, MACHINE_FILES))


def get_bom_unit_info(product):
    """
    معلومات الوحدة الواحدة من BOM: عبوات/بريفورم لكل وحدة إنتاج + التغليف.
    quantity في التقرير = عدد الوحدات (مثلاً كراتين).
    """
    info = {
        "pieces_per_unit": 1,
        "packaging_per_unit": 1.0,
        "packaging_is_weight": False,
        "preform_material": None,
    }
    if product not in BOM:
        return info

    for material, qty in BOM[product].items():
        if "بريفورم" in material:
            info["pieces_per_unit"] = int(qty)
            info["preform_material"] = material
        elif "كرتون" in material:
            info["packaging_per_unit"] = float(qty)
            info["packaging_is_weight"] = False
        elif "شرنك" in material:
            info["packaging_per_unit"] = float(qty)
            info["packaging_is_weight"] = True
    return info


def calculate_production_metrics(
    product, units, shift_start, shift_end, break_minutes,
    speed_bottles_per_hour, preforms_used=0, packaging_used=0.0,
):
    """
    units = كمية الإنتاج بالوحدة (كرتون/شرنك حسب المنتج).
    speed_bottles_per_hour = عبوات أو بريفورم في الساعة (مثال: 35000).
    التغليف والهالك التغليف بالوحدة (كرتون/شرنك).
    """
    bom = get_bom_unit_info(product)
    pieces_per_unit = max(1, bom["pieces_per_unit"])
    units = int(units)
    bottles_produced = units * pieces_per_unit

    try:
        start_total = shift_start.hour * 60 + shift_start.minute
        end_total = shift_end.hour * 60 + shift_end.minute
        if end_total <= start_total:
            end_total += 24 * 60

        shift_minutes = end_total - start_total
        working_minutes = max(0, shift_minutes - int(break_minutes))
        working_hours = working_minutes / 60.0

        # الكفاءة والتوقف بناءً على العبوات/الساعة (سرعة الخط)
        theoretical_bottles = speed_bottles_per_hour * working_hours if working_hours > 0 else 0

        if theoretical_bottles > 0:
            efficiency = min(100.0, round((bottles_produced / theoretical_bottles) * 100, 1))
        else:
            efficiency = 0.0

        if speed_bottles_per_hour > 0:
            required_hours = bottles_produced / speed_bottles_per_hour
            downtime_hours = max(0.0, working_hours - required_hours)
        else:
            downtime_hours = 0.0

        downtime_minutes = int(round(downtime_hours * 60))

        # حساب البريفورم المتوقع والهالك
        expected_preforms = bottles_produced  # المتوقع = عدد العبوات المنتجة
        final_preforms = int(preforms_used) if preforms_used > 0 else expected_preforms
        waste_bottles = max(0, final_preforms - expected_preforms)

        # حساب التغليف المتوقع والهالك
        expected_packaging_units = units  # المتوقع = عدد الوحدات (كراتين/شرنك)
        if packaging_used > 0:
            final_packaging_units = int(packaging_used)
            packaging_waste = max(0, final_packaging_units - expected_packaging_units)
        else:
            final_packaging_units = expected_packaging_units
            packaging_waste = 0  # إذا لم يتم إدخال قيمة، لا يوجد هالك

        return {
            "pieces_per_unit": pieces_per_unit,
            "bottles_produced": bottles_produced,
            "working_minutes": working_minutes,
            "working_hours": round(working_hours, 2),
            "downtime_minutes": downtime_minutes,
            "downtime_hours": round(downtime_hours, 2),
            "theoretical_bottles": int(theoretical_bottles),
            "efficiency": efficiency,
            "waste_bottles": int(waste_bottles),
            "packaging_waste": int(packaging_waste),
            "final_preforms": final_preforms,
            "final_packaging": float(final_packaging_units),
            "line_speed": int(speed_bottles_per_hour),
            "ideal_run_rate": speed_bottles_per_hour / 60.0,
        }
    except Exception:
        return {
            "pieces_per_unit": pieces_per_unit,
            "bottles_produced": bottles_produced,
            "working_minutes": 0,
            "working_hours": 0.0,
            "downtime_minutes": 0,
            "downtime_hours": 0.0,
            "theoretical_bottles": 0,
            "efficiency": 0.0,
            "waste_bottles": 0,
            "packaging_waste": max(0, int(round(units * 0.01))),
            "final_preforms": int(preforms_used),
            "final_packaging": float(units),
            "line_speed": int(speed_bottles_per_hour),
            "ideal_run_rate": speed_bottles_per_hour / 60.0,
        }


def get_production_record_labels(t):
    """Column labels for production records table."""
    return {
        "id": t.get("col_id", "ID"),
        "date": t.get("col_date", "Date"),
        "line": t.get("col_line", "Line"),
        "product": t.get("col_product", "Product"),
        "output_units": t.get("col_qty_units", "Qty (units)"),
        "waste_bottles": t.get("col_waste_bottles", "Bottle Waste"),
        "packaging_waste": t.get("col_packaging_waste", "Packaging Waste"),
        "line_speed": t.get("col_line_speed_bottles", "Line speed (bottles/hr)"),
        "preforms_used": t.get("preform_actual", "Preforms used"),
        "efficiency": t.get("col_efficiency", "Efficiency %"),
        "downtime_hours": t.get("col_downtime", "Downtime (hrs)"),
        "operating_hours": t.get("col_operating_time", "Operating (hrs)"),
        "supervisor": t.get("col_supervisor", "Supervisor"),
        "oee": t.get("col_oee", "OEE %"),
    }


def delete_production_record(record_id, df_raw, df_fg):
    """
    Delete a production record and restore raw + finished goods inventory.
    Returns (success: bool, message: str)
    """
    from database import db_manager
    from inventory import (
        update_raw_materials,
        update_finished_goods,
        restore_finished_goods_from_production,
    )

    record = db_manager.get_production_by_id(int(record_id))
    if not record:
        return False, "السجل غير موجود"

    product = record["product"]
    quantity = int(record["output_units"])

    new_raw, raw_ok, raw_msg = restore_materials(product, quantity, df_raw)
    if not raw_ok:
        return False, raw_msg

    if not update_raw_materials(new_raw):
        return False, "فشل تحديث مخزون المواد الخام"

    fg_msg = ""
    if df_fg is not None and not df_fg.empty:
        new_fg, fg_ok, fg_msg = restore_finished_goods_from_production(product, quantity, df_fg.copy())
        if not fg_ok:
            return False, fg_msg
        if not update_finished_goods(new_fg):
            return False, "فشل تحديث مخزن المنتج التام"

    if not db_manager.delete_production(int(record_id)):
        return False, "فشل حذف السجل من قاعدة البيانات"

    msg = raw_msg
    if fg_msg:
        msg += f" | {fg_msg}"
    return True, msg

# ============================================================================
# Internal helpers
# ============================================================================

def _get_material_col(df: pd.DataFrame):
    """يرجع اسم عمود المادة المتوفر في الـ DataFrame"""
    for col in ["Material_Name_AR", "Material_Name", "Name", "المادة", "material"]:
        if col in df.columns:
            return col
    return None


def _get_stock_col(df: pd.DataFrame):
    """يرجع اسم عمود المخزون المتوفر في الـ DataFrame"""
    for col in ["Current_Stock", "Stock", "الكمية", "quantity", "in_stock"]:
        if col in df.columns:
            return col
    return None


def _normalize(name: str) -> str:
    """تطبيع اسم المادة: strip + توحيد المسافات المتعددة"""
    import re
    return re.sub(r'\s+', ' ', str(name).strip())


# ============================================================================
# Utility Functions
# ============================================================================

def send_telegram(msg):
    """إرسال إشعار تيليجرام"""
    try:
        import streamlit as st
        token   = st.secrets.get("telegram", {}).get("bot_token", "")
        chat_id = st.secrets.get("telegram", {}).get("chat_id", "")
        if token and chat_id:
            requests.get(
                f"https://api.telegram.org/bot{token}/sendMessage"
                f"?chat_id={chat_id}&text={urllib.parse.quote(msg)}&parse_mode=Markdown",
                timeout=5
            )
    except Exception:
        pass


def get_materials_required(product, quantity):
    """
    يحسب المواد المطلوبة لإنتاج كمية معينة من منتج.
    يرجع (dict_المواد, None) أو (None, رسالة_خطأ)
    """
    if product not in BOM:
        return None, f"المنتج '{product}' غير موجود في BOM"

    required = {}
    for material, qty in BOM[product].items():
        norm_material = _normalize(material)
        if qty < 1:
            required[norm_material] = math.ceil(quantity * qty)
        else:
            required[norm_material] = qty * quantity

    # إضافة فواصل الشرنك
    if "Shrink" in product and product in SHRINK_PALLET_CONFIG:
        cfg = SHRINK_PALLET_CONFIG[product]
        spacers = math.ceil(quantity / cfg["units_per_pallet"]) * cfg["spacers_per_pallet"]
        if spacers > 0:
            required[_normalize("فواصل شرنك")] = spacers

    return required, None


def consume_materials(product, quantity, df_raw):
    """
    يصرف المواد من مخزون المواد الخام.
    يرجع (df_new, success, message)
    """
    if df_raw is None or df_raw.empty:
        return df_raw, False, "⚠️ ملف المواد الخام فارغ أو غير موجود"

    if product not in BOM:
        return df_raw, False, f"⚠️ المنتج '{product}' غير موجود في BOM"

    required, error = get_materials_required(product, quantity)
    if error:
        return df_raw, False, error

    material_col = _get_material_col(df_raw)
    stock_col    = _get_stock_col(df_raw)

    if not material_col:
        return df_raw, False, "⚠️ لم يُعثر على عمود اسم المادة في ملف المخزون"
    if not stock_col:
        return df_raw, False, "⚠️ لم يُعثر على عمود الكمية في ملف المخزون"

    new_df = df_raw.copy()
    new_df['_norm_name'] = new_df[material_col].apply(_normalize)

    shortages       = []
    consumed_items  = []

    for norm_material, req in required.items():
        mask = new_df['_norm_name'] == norm_material
        matched = new_df[mask]

        if matched.empty:
            consumed_items.append(f"⚠️ {norm_material}: غير موجودة في الملف (تم تجاهلها)")
            continue

        idx     = matched.index[0]
        current = float(new_df.at[idx, stock_col]) if pd.notna(new_df.at[idx, stock_col]) else 0

        if current < req:
            shortages.append(
                f"{norm_material} (مطلوب {req:,.0f} ، متوفر {current:,.0f})"
            )
        else:
            new_df.at[idx, stock_col]    = current - req
            new_df.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d")
            consumed_items.append(f"{norm_material}: {req:,.0f}")

    new_df.drop(columns=['_norm_name'], inplace=True, errors='ignore')

    if shortages:
        return df_raw, False, f"⚠️ عجز في المواد: {', '.join(shortages[:5])}"

    return new_df, True, f"✅ تم صرف: {', '.join(consumed_items)}"


def restore_materials(product, quantity, df_raw):
    """
    يُعيد المواد إلى المخزون عند حذف سجل إنتاج.
    يرجع (df_new, success, message)
    """
    if df_raw is None or df_raw.empty:
        return df_raw, False, "⚠️ ملف المواد الخام فارغ أو غير موجود"

    required, error = get_materials_required(product, quantity)
    if error:
        return df_raw, False, error

    material_col = _get_material_col(df_raw)
    stock_col    = _get_stock_col(df_raw)

    if not material_col:
        return df_raw, False, "⚠️ لم يُعثر على عمود اسم المادة في ملف المخزون"
    if not stock_col:
        return df_raw, False, "⚠️ لم يُعثر على عمود الكمية في ملف المخزون"

    new_df = df_raw.copy()
    new_df['_norm_name'] = new_df[material_col].apply(_normalize)

    restored_items = []

    for norm_material, req in required.items():
        mask    = new_df['_norm_name'] == norm_material
        matched = new_df[mask]
        if matched.empty:
            continue
        idx     = matched.index[0]
        current = float(new_df.at[idx, stock_col]) if pd.notna(new_df.at[idx, stock_col]) else 0
        new_df.at[idx, stock_col]    = current + req
        new_df.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d")
        restored_items.append(f"{norm_material}: +{req:,.0f}")

    new_df.drop(columns=['_norm_name'], inplace=True, errors='ignore')

    msg = f"✅ تم إعادة المواد: {', '.join(restored_items)}" if restored_items else "لم يتم إعادة أي مادة"
    return new_df, True, msg


def add_to_finished_goods(product_name, quantity, df_fg):
    """إضافة الكمية المنتجة إلى مخزن المنتج التام"""
    mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink":  "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    fg_name = mapping.get(product_name, product_name)

    if df_fg is None or df_fg.empty:
        return df_fg, False, "⚠️ ملف المنتج التام فارغ"

    idx = df_fg[df_fg["Name"] == fg_name].index
    if len(idx) == 0:
        idx = df_fg[df_fg["Name"].str.contains(fg_name, case=False, na=False)].index

    if len(idx) == 0:
        return df_fg, False, f"⚠️ المنتج '{product_name}' غير موجود في مخزن المنتج التام"

    idx = idx[0]
    old_in      = float(df_fg.at[idx, "In"])      if pd.notna(df_fg.at[idx, "In"])      else 0
    old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0

    df_fg.at[idx, "In"]          = old_in + quantity
    df_fg.at[idx, "Balance"]     = old_balance + quantity
    df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df_fg, True, f"✅ تم إضافة {quantity:,.0f} وحدة إلى مخزن {fg_name}"


# ============================================================================
# Smart Recommendations
# ============================================================================

def get_auto_reorder_suggestions(df_raw, df_main):
    """اقتراحات إعادة الطلب بناءً على مستوى المخزون"""
    suggestions = []
    if df_raw is None or df_raw.empty:
        return suggestions

    material_col = _get_material_col(df_raw)
    stock_col    = _get_stock_col(df_raw)
    if not material_col or not stock_col:
        return suggestions

    for _, row in df_raw.iterrows():
        current   = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
        min_stock = float(row.get('Min_Stock', 0)) if pd.notna(row.get('Min_Stock', 0)) else 0

        if current <= min_stock and min_stock > 0:
            suggested_qty = max(0, int(min_stock * 2 - current))
            urgency = "high" if current < min_stock / 2 else "medium"
            suggestions.append({
                "material":     str(row[material_col]),
                "current":      int(current),
                "min_stock":    int(min_stock),
                "suggested_qty": suggested_qty,
                "urgency":      urgency
            })

    return suggestions


def calculate_daily_consumption_for_material(df_main, material_name):
    """يحسب متوسط الاستهلاك اليومي لمادة معينة من سجل الإنتاج"""
    if df_main is None or df_main.empty:
        return 0

    prod_df = df_main[df_main.get('type', pd.Series(['Production'] * len(df_main))) == 'Production'].copy()
    if prod_df.empty or 'date' not in prod_df.columns:
        return 0

    prod_df['date'] = pd.to_datetime(prod_df['date'])
    last_30 = prod_df[prod_df['date'] >= datetime.now() - timedelta(days=30)]
    if last_30.empty:
        return 0

    norm_target = _normalize(material_name)
    total = 0
    for _, row in last_30.iterrows():
        required, _ = get_materials_required(row.get('product', ''), row.get('output_units', 0))
        if required:
            for mat, qty in required.items():
                if _normalize(mat) == norm_target:
                    total += qty

    return total / 30 if total > 0 else 0


def get_stock_prediction_calculated(df_raw, df_main, selected_line):
    """
    توقع نفاذ المخزون بناءً على الاستهلاك اليومي من ملف materials working times.xlsx
    """
    predictions = []
    if df_raw is None or df_raw.empty:
        return predictions

    material_col = _get_material_col(df_raw)
    stock_col = _get_stock_col(df_raw)
    if not material_col or not stock_col:
        return predictions

    # تعريف الاستهلاك اليومي الثابت من البيانات الفعلية
    DAILY_CONSUMPTION = {
        "غطاء": 1000000,
        "caps blue": 1000000,
        "بريفورم 200 مل": 600000,
        "preform 200": 600000,
        "بريفورم 330 مل": 600000,
        "preform 330": 600000,
        "بريفورم 600 مل": 300000,
        "preform 600": 300000,
        "بريفورم 1.5 لتر": 150000,
        "preform 1.5": 150000,
        "ليبل 200 مل": 600000,
        "label 200": 600000,
        "ليبل 330 مل": 600000,
        "label 330": 600000,
        "ليبل 600 مل": 300000,
        "label 600": 300000,
        "ليبل 1.5 لتر": 150000,
        "label 1.5": 150000,
        "كرتون 200 مل": 12500,
        "raw cartoon 200": 12500,
        "كرتون 330 مل": 15000,
        "raw cartoon 330": 15000,
        "كرتون 600 مل": 10000,
        "raw cartoon 600": 10000,
        "شرنك 200 مل": 15,
        "shrink 200": 15,
        "شرنك 330 مل": 15,
        "shrink 330": 15,
        "شرنك 1.5 لتر": 12,
        "shrink 1.5": 12,
        "فواصل شرنك": 5000,
        "shrink spacers": 5000,
        "غراء الليبل": 5,
        "adhesive": 5,
        "غراء الكرتون": 20,
        "hotmelt": 20,
    }

    for _, row in df_raw.iterrows():
        mat_name = str(row[material_col]) if pd.notna(row[material_col]) else ""
        current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
        
        # البحث عن الاستهلاك اليومي
        daily_consumption = 0
        for key, value in DAILY_CONSUMPTION.items():
            if key in mat_name or mat_name in key:
                daily_consumption = value
                break
        
        if daily_consumption > 0 and current_stock > 0:
            days_left = current_stock / daily_consumption
            
            if days_left < 60:
                if days_left <= 3:
                    status = "critical"
                elif days_left <= 7:
                    status = "warning"
                else:
                    status = "info"
                
                predictions.append({
                    "material": mat_name,
                    "current": int(current_stock),
                    "days_left": round(days_left, 1),
                    "daily_consumption": daily_consumption,
                    "status": status
                })
        elif current_stock <= 0 and current_stock == 0:
            predictions.append({
                "material": mat_name,
                "current": 0,
                "days_left": 0,
                "daily_consumption": daily_consumption,
                "status": "critical"
            })

    predictions.sort(key=lambda x: x["days_left"])
    return predictions


def calculate_days_until_depletion(df_raw, df_main, selected_line):
    """
    حساب المدة المتبقية لنفاذ المواد الخام (بالأيام)
    """
    if df_raw is None or df_raw.empty:
        return df_raw
    
    material_col = _get_material_col(df_raw)
    stock_col = _get_stock_col(df_raw)
    
    if not material_col or not stock_col:
        if df_raw is not None:
            df_raw['Days_Until_Depletion'] = 999.0
        return df_raw
    
    # تعريف الاستهلاك اليومي مباشرة في الدالة
    DAILY_CONSUMPTION = {
        "غطاء": 1000000,
        "caps blue": 1000000,
        "بريفورم 200 مل": 600000,
        "preform 200": 600000,
        "بريفورم 330 مل": 600000,
        "preform 330": 600000,
        "بريفورم 600 مل": 300000,
        "preform 600": 300000,
        "بريفورم 1.5 لتر": 150000,
        "preform 1.5": 150000,
        "ليبل 200 مل": 600000,
        "label 200": 600000,
        "ليبل 330 مل": 600000,
        "label 330": 600000,
        "ليبل 600 مل": 300000,
        "label 600": 300000,
        "ليبل 1.5 لتر": 150000,
        "label 1.5": 150000,
        "كرتون 200 مل": 12500,
        "raw cartoon 200": 12500,
        "كرتون 330 مل": 15000,
        "raw cartoon 330": 15000,
        "كرتون 600 مل": 10000,
        "raw cartoon 600": 10000,
        "شرنك 200 مل": 15,
        "shrink 200": 15,
        "شرنك 330 مل":15,
        "shrink 330": 15,
        "شرنك 1.5 لتر": 12,
        "shrink 1.5": 12,
        "فواصل شرنك": 5000,
        "shrink spacers": 5000,
        "غراء الليبل": 5,
        "adhesive": 5,
        "غراء الكرتون": 20,
        "hotmelt": 20,
    }
    
    # إنشاء نسخة من DataFrame
    df_result = df_raw.copy()
    
    # إنشاء قائمة للقيم
    depletion_days = []
    
    for idx, row in df_result.iterrows():
        mat_name = str(row[material_col]) if pd.notna(row[material_col]) else ""
        mat_name_normalized = _normalize(mat_name)
        
        # تحويل المخزون الحالي إلى float
        try:
            current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0.0
        except (ValueError, TypeError):
            current_stock = 0.0
        
        # البحث عن الاستهلاك اليومي
        daily_usage = 0.0
        for key, value in DAILY_CONSUMPTION.items():
            if _normalize(key) == mat_name_normalized or key in mat_name or mat_name in key:
                daily_usage = value
                break
        
        if daily_usage > 0 and current_stock > 0:
            days = current_stock / daily_usage
            depletion_days.append(round(days, 1))
        elif current_stock <= 0:
            depletion_days.append(0.0)
        else:
            depletion_days.append(999.0)
    
    # إضافة العمود الجديد
    df_result['Days_Until_Depletion'] = depletion_days
    
    return df_result


def calculate_daily_production_target(df_main, selected_line):
    """
    حساب الإنتاج اليومي المتوقع بناءً على سجلات الإنتاج السابقة
    """
    if df_main is None or df_main.empty:
        return 80000  # قيمة افتراضية
    
    prod_df = df_main[df_main.get('type', 'Production') == 'Production'].copy()
    if prod_df.empty or 'date' not in prod_df.columns:
        return 80000
    
    prod_df['date'] = pd.to_datetime(prod_df['date'])
    last_30 = prod_df[prod_df['date'] >= datetime.now() - timedelta(days=30)]
    
    if last_30.empty or 'output_units' not in last_30.columns:
        return 80000
    
    avg_daily = last_30.groupby(last_30['date'].dt.date)['output_units'].sum().mean()
    return max(avg_daily, 50000) if not pd.isna(avg_daily) else 80000


def get_shift_info():
    """
    معلومات الوردية الواحدة (8 صباحاً - 2 صباحاً اليوم التالي)
    3 ساعات بريك موزعة على اليوم
    """
    now = datetime.now()
    
    # وقت بداية الوردية: 8:00 صباحاً
    shift_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    
    # وقت نهاية الوردية: 2:00 صباحاً اليوم التالي
    next_day = now + timedelta(days=1)
    shift_end = next_day.replace(hour=2, minute=0, second=0, microsecond=0)
    
    # إجمالي ساعات الوردية = 18 ساعة
    shift_duration_hours = 18
    
    # أوقات البريك (3 ساعات موزعة)
    break_times = [
        {"start": now.replace(hour=10, minute=0, second=0), "end": now.replace(hour=10, minute=30, second=0), "duration": 0.5},  # 10:00-10:30
        {"start": now.replace(hour=13, minute=0, second=0), "end": now.replace(hour=14, minute=0, second=0), "duration": 1.0},  # 13:00-14:00
        {"start": now.replace(hour=18, minute=0, second=0), "end": now.replace(hour=18, minute=30, second=0), "duration": 0.5},  # 18:00-18:30
        {"start": now.replace(hour=23, minute=0, second=0), "end": next_day.replace(hour=0, minute=30, second=0), "duration": 1.0},  # 23:00-00:30
    ]
    
    # تحديد إذا كان الوقت الحالي ضمن وقت العمل أو الراحة
    is_working = True
    current_break = None
    for bt in break_times:
        if bt["start"] <= now <= bt["end"]:
            is_working = False
            current_break = bt
            break
    
    return {
        "shift_start": shift_start,
        "shift_end": shift_end,
        "shift_duration_hours": shift_duration_hours,
        "break_times": break_times,
        "is_working": is_working,
        "current_break": current_break,
        "total_break_hours": 3,
        "working_hours": shift_duration_hours - 3,  # 15 ساعة عمل فعلية
        "shift_name": "الوردية الواحدة (8 صباحاً - 2 صباحاً)"
    }


def get_marquee_recommendations(df_raw, df_main, df_fg, t, lang, selected_line):
    """بناء قائمة التوصيات لشريط الـ marquee"""
    recommendations = []
    en = lang == "en"

    reorder = get_auto_reorder_suggestions(df_raw, df_main)
    for rec in reorder[:3]:
        if rec["urgency"] == "high":
            if en:
                recommendations.append(
                    f"🔴 {t.get('auto_reorder', '')}: {rec['material']} - "
                    f"{t.get('marquee_stock', 'Stock')} {rec['current']:,}"
                )
            else:
                recommendations.append(
                    f"🔴 {t.get('auto_reorder', '')}: {rec['material']} - "
                    f"{t.get('marquee_stock', 'الرصيد')} {rec['current']:,}"
                )
        else:
            if en:
                recommendations.append(
                    f"🟡 {t.get('auto_reorder', '')}: {rec['material']} - "
                    f"{t.get('marquee_suggested', 'Suggested')} {rec['suggested_qty']:,}"
                )
            else:
                recommendations.append(
                    f"🟡 {t.get('auto_reorder', '')}: {rec['material']} - "
                    f"{t.get('marquee_suggested', 'الكمية المقترحة')} {rec['suggested_qty']:,}"
                )

    stock_pred = get_stock_prediction_calculated(df_raw, df_main, selected_line)
    for pred in stock_pred[:3]:
        if pred["status"] == "critical":
            if en:
                recommendations.append(
                    f"⚠️ {t.get('stock_prediction', '')}: {pred['material']} "
                    f"{t.get('marquee_deplete_in', 'runs out in')} {pred['days_left']} "
                    f"{t.get('marquee_days', 'days')}"
                )
            else:
                recommendations.append(
                    f"⚠️ {t.get('stock_prediction', '')}: {pred['material']} "
                    f"{t.get('marquee_deplete_in', 'سينفذ خلال')} {pred['days_left']} "
                    f"{t.get('marquee_days', 'يوم')}"
                )
        elif pred["status"] == "warning":
            if en:
                recommendations.append(
                    f"📦 {t.get('stock_prediction', '')}: {pred['material']} "
                    f"{t.get('marquee_deplete_in', 'runs out in')} {pred['days_left']} "
                    f"{t.get('marquee_days', 'days')}"
                )
            else:
                recommendations.append(
                    f"📦 {t.get('stock_prediction', '')}: {pred['material']} "
                    f"{t.get('marquee_deplete_in', 'سينفذ خلال')} {pred['days_left']} "
                    f"{t.get('marquee_days', 'يوم')}"
                )

    if df_fg is not None and not df_fg.empty and "Balance" in df_fg.columns:
        fg_balance = df_fg["Balance"].sum()
        if fg_balance <= 0:
            recommendations.append(
                f"🏭 {t.get('fg_balance', '')}: {t.get('marquee_fg_empty', '')}"
            )
        elif fg_balance < 10000:
            recommendations.append(
                f"📦 {t.get('fg_balance', '')}: {fg_balance:,.0f} "
                f"{t.get('marquee_fg_units', 'units')}"
            )

    if not recommendations:
        recommendations.append(f"✅ {t.get('all_good', 'All good')} ✅")

    return recommendations


# ============================================================================
# Maintenance helpers
# ============================================================================

def create_machine_file(filepath):
    """إنشاء ملف صيانة ماكينة إذا لم يكن موجوداً"""
    if "Compressor" in filepath or "AF_Compressor" in filepath:
        sample_data = pd.DataFrame({
            "Cat":   ["Daily checks","Operation check","Cleaning & Lubrication",
                      "Cleaning & Lubrication","Mechanical check","Mechanical check",
                      "Auxiliary systems","Auxiliary systems","Electrical",
                      "Advanced maintenance","Advanced maintenance","Advanced maintenance"],
            "No":    [1,1,1,2,1,2,1,2,1,1,2,3],
            "Name":  ["Fill weekly performance log","Check emergency stop button",
                      "Check oil level","Replace or clean oil filter",
                      "Check belt tension and alignment","Clean intake air filter",
                      "Check Bekomats drain operation","Clean dryer cooler",
                      "Electrical cabinet filter","Valve cover bolt torque",
                      "Motor bearing lubrication","Clean main motor"],
            "Photo": [""]*12,
            "Tools": ["Pen","Manual","Oil gauge","Filter wrench","Tension gauge",
                      "Compressed air","Visual inspection","Soft brush",
                      "Vacuum/air","Torque wrench","Grease gun","Compressed air"],
            "Proc":  ["Record data","Manual test","Check correct marking","Clean or replace",
                      "Check tension and alignment","Clean from dust",
                      "Check for no blockage","Clean fins","Clean for ventilation",
                      "Per specifications","Sufficient grease","Free from contaminants"],
            "Freq":  ["Daily","Daily","Daily","Weekly","Weekly","Weekly",
                      "Weekly","Weekly","Weekly","Monthly","Yearly","Yearly"],
            "Stat":  ["Active"]*12, "Note": [""]*12, "Staff": [""]*12,
        })
        sample_data.to_excel(filepath, index=False)
    else:
        sample = pd.DataFrame({
            "Cat":   ["Mechanical","Mechanical","Electrical","Mechanical","Electrical"],
            "No":    [1,2,3,4,5],
            "Name":  ["Check bearings","Clean filters","Calibrate sensors",
                      "Lubricate parts","Check belts"],
            "Photo": [""]*5,
            "Tools": ["Wrench","Brush + air","Calibration device","Grease","Wrench"],
            "Proc":  ["Check vibrations","Clean with air","Calibrate per manual",
                      "Lubricate every 100 hours","Check tension"],
            "Freq":  ["Daily","Daily","Weekly","Weekly","Monthly"],
            "Stat":  ["Active"]*5, "Note": [""]*5, "Staff": [""]*5,
        })
        sample.to_excel(filepath, index=False)


def find_image_path(photo_name):
    """إيجاد مسار الصورة لمهمة الصيانة"""
    if not photo_name or pd.isna(photo_name) or str(photo_name).strip() == "":
        return None
    possible = [
        photo_name,
        os.path.join("images", photo_name),
        os.path.join("images", os.path.basename(str(photo_name)))
    ]
    for path in possible:
        if os.path.exists(path):
            return path
    return None


def get_scheduled_tasks(df_tasks):
    """إرجاع مهام اليوم بناءً على التردد المجدول"""
    if df_tasks is None or df_tasks.empty:
        return pd.DataFrame()

    today           = datetime.now()
    day_name        = today.strftime('%A')
    is_first_month  = (today.day == 1)

    freq_col = next(
        (c for c in ['Freq', 'Frequency'] if c in df_tasks.columns), None
    )
    if freq_col is None:
        return pd.DataFrame()

    if day_name == 'Friday':
        return pd.DataFrame()

    allowed = ['Daily']
    if day_name == 'Saturday':
        allowed.append('Weekly')
    if is_first_month:
        allowed += ['Monthly', '1000h', 'Yearly']

    df = df_tasks.copy()
    df[freq_col] = df[freq_col].astype(str).replace('4 months', 'Monthly')
    result = df[df[freq_col].isin(allowed)]
    return result.reset_index(drop=True)