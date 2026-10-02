# ============================================================
#   🏢 عمارة هيال - نظام إدارة العمارة السكنية
#   HAYAL TOWER - Property Management System
#   نسخة 1.0 - نسخة محلية (بدون إنترنت)
# ============================================================

import os
import io
import csv
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Flask, render_template_string, request, redirect,
                   url_for, flash, session, send_from_directory, Response)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_

# ---------------- الإعدادات ----------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hayal-tower-2026-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'hayal_tower.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)


# ============================================================
#                     النماذج (Models)
# ============================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='manager')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])


class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    floor = db.Column(db.Integer)
    rooms = db.Column(db.Integer, default=3)
    area_sqm = db.Column(db.Float, default=0)
    monthly_rent = db.Column(db.Float, default=0)
    currency = db.Column(db.String(10), default='ر.ي')
    status = db.Column(db.String(20), default='فارغة')
    notes = db.Column(db.Text)
    future = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(30))
    phone = db.Column(db.String(20))
    phone2 = db.Column(db.String(20))
    job = db.Column(db.String(100))
    family_size = db.Column(db.Integer, default=1)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    address_prev = db.Column(db.String(200))
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    monthly_rent = db.Column(db.Float, default=0)
    deposit = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(30))
    currency = db.Column(db.String(10), default='ر.ي')
    status = db.Column(db.String(20), default='ساري')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tenant = db.relationship('Tenant', foreign_keys=[tenant_id])
    unit = db.relationship('Unit', foreign_keys=[unit_id])


class RentPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    month = db.Column(db.String(10))
    amount_due = db.Column(db.Float, default=0)
    amount_paid = db.Column(db.Float, default=0)
    payment_date = db.Column(db.Date)
    method = db.Column(db.String(20))
    currency = db.Column(db.String(10), default='ر.ي')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contract = db.relationship('Contract', foreign_keys=[contract_id])
    tenant = db.relationship('Tenant', foreign_keys=[tenant_id])
    unit = db.relationship('Unit', foreign_keys=[unit_id])


class UtilityBill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    service_type = db.Column(db.String(20))
    month = db.Column(db.String(10))
    prev_reading = db.Column(db.Float, default=0)
    curr_reading = db.Column(db.Float, default=0)
    consumption = db.Column(db.Float, default=0)
    unit_price = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='غير مدفوع')
    paid_date = db.Column(db.Date)
    image = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    unit = db.relationship('Unit', foreign_keys=[unit_id])


class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    category = db.Column(db.String(30))
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='عادي')
    technician = db.Column(db.String(100))
    cost = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='جديد')
    request_date = db.Column(db.Date, default=date.today)
    done_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    unit = db.relationship('Unit', foreign_keys=[unit_id])
    tenant = db.relationship('Tenant', foreign_keys=[tenant_id])


class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job = db.Column(db.String(30))
    phone = db.Column(db.String(20))
    salary = db.Column(db.Float, default=0)
    hire_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    amount = db.Column(db.Float, default=0)
    currency = db.Column(db.String(10), default='ر.ي')
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(500))


# ============================================================
#                     مساعدات
# ============================================================

def get_setting(key, default=''):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default


def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if s:
        s.value = str(value)
    else:
        db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or u.role not in ('admin', 'manager'):
            flash('⛔ غير مصرح لك بالدخول', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrapper


def next_number(model, prefix):
    last = model.query.order_by(model.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"{prefix}-{n:05d}"


def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def log_activity(action, details=''):
    try:
        u = current_user()
        if u:
            db.session.add(ActivityLog(user_id=u.id, action=action, details=details))
            db.session.commit()
    except:
        db.session.rollback()


def get_alerts_count():
    try:
        count = 0
        today = date.today()
        future = date.fromordinal(today.toordinal() + 30)
        count += Contract.query.filter(
            Contract.status == 'ساري',
            Contract.end_date <= future,
            Contract.end_date >= today
        ).count()
        count += RentPayment.query.filter(RentPayment.amount_paid < RentPayment.amount_due).count()
        count += MaintenanceRequest.query.filter_by(status='قيد التنفيذ').count()
        return count
    except:
        return 0


app.jinja_env.globals['current_user'] = current_user
app.jinja_env.globals['get_setting'] = get_setting
app.jinja_env.globals['get_alerts_count'] = get_alerts_count


# ============================================================
#                     القالب الأساسي (بدون إنترنت)
# ============================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}🏢 عمارة هيال{% endblock %}</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/bootstrap.rtl.min.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/bootstrap-icons.css') }}">
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #eef1f6; margin: 0; }

  .sidebar {
    width: 250px; height: 100vh;
    background: linear-gradient(180deg, #1a3a5c 0%, #0f2740 100%);
    position: fixed; right: 0; top: 0;
    overflow-y: auto; z-index: 1000;
    scrollbar-width: thin; scrollbar-color: #4a9eff #1a3a5c;
  }
  .sidebar::-webkit-scrollbar { width: 6px; }
  .sidebar::-webkit-scrollbar-track { background: #1a3a5c; }
  .sidebar::-webkit-scrollbar-thumb { background: #4a9eff; border-radius: 3px; }

  .sidebar h4 {
    color: #ffc107; padding: 18px; margin: 0;
    border-bottom: 1px solid #2c5273; text-align: center;
    font-weight: bold; position: sticky; top: 0;
    background: #1a3a5c; z-index: 10;
  }
  .sidebar h4 small { display:block; color:#8fb8dc; font-size: 11px; margin-top:4px; letter-spacing:2px; }

  .menu-group { border-bottom: 1px solid #2c5273; }
  .group-header {
    color: #a8c8e0; font-size: 12px; padding: 12px 18px; cursor: pointer;
    display: flex; justify-content: space-between; align-items: center;
    font-weight: bold; user-select: none;
  }
  .group-header:hover { background: #234a70; color: #ffc107; }
  .group-header i.arrow { transition: transform .3s; font-size: 11px; }
  .group-header.collapsed i.arrow { transform: rotate(-90deg); }
  .group-body { max-height: 600px; overflow: hidden; transition: max-height .3s; }
  .group-body.collapsed { max-height: 0; }

  .sidebar a {
    color: #c7dae8; padding: 9px 18px 9px 40px;
    display: flex; align-items: center; text-decoration: none;
    font-size: 13.5px; border-right: 3px solid transparent;
  }
  .sidebar a:hover, .sidebar a.active { background: #234a70; color: #fff; border-right-color: #ffc107; }
  .sidebar a i { margin-left: 8px; width: 18px; }
  .sidebar .badge-alert { background:#dc3545; color:#fff; font-size:10px; padding:2px 6px; border-radius:10px; margin-right:auto; }

  .main { margin-right: 250px; padding: 20px; min-height: 100vh; }
  .topbar {
    background: #fff; padding: 12px 20px; border-radius: 10px;
    margin-bottom: 20px; display: flex; justify-content: space-between;
    align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,.06);
  }
  .topbar .user-info { display:flex; align-items:center; gap:12px; }
  .topbar .avatar {
    width: 40px; height: 40px; background: #ffc107; color: #000;
    border-radius: 50%; display:flex; align-items:center; justify-content:center;
    font-weight: bold; font-size: 18px;
  }

  .stat-card {
    background: #fff; border-radius: 12px; padding: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,.06);
    border-right: 4px solid #4a9eff; transition: transform .2s;
  }
  .stat-card:hover { transform: translateY(-3px); }
  .stat-card h3 { margin: 0; font-size: 26px; color: #1a3a5c; }
  .stat-card p { margin: 0; color: #6c757d; font-size: 13px; }
  .stat-card.green { border-color: #198754; }
  .stat-card.red { border-color: #dc3545; }
  .stat-card.orange { border-color: #fd7e14; }
  .stat-card.purple { border-color: #6f42c1; }
  .stat-card.cyan { border-color: #0dcaf0; }

  .card { border: none; box-shadow: 0 2px 10px rgba(0,0,0,.06); border-radius: 12px; overflow:hidden; }
  .card-header { background: #fff; border-bottom: 1px solid #eee; font-weight: bold; padding: 14px 18px; }
  .table thead { background: #1a3a5c; color: #fff; }
  .table thead th { border: none; padding: 12px; font-weight: 600; }
  .btn-warning { background: #ffc107; border: none; color: #000; font-weight: 600; }

  .help-text {
    color: #6c757d; font-size: 11px; margin-top: 4px;
    display: flex; align-items: center; gap: 4px;
  }
  .help-text::before { content: "💡"; }

  body.dark-mode { background: #0f1729; color: #e5e9f0; }
  body.dark-mode .card { background: #1a2233; color: #e5e9f0; }
  body.dark-mode .card-header { background: #263048; color: #fff; border-color: #2c3a52; }
  body.dark-mode .table { color: #e5e9f0; }
  body.dark-mode .table thead { background: #0a0f1c; }
  body.dark-mode .table td, body.dark-mode .table th { border-color: #2c3a52; }
  body.dark-mode .topbar { background: #1a2233; }
  body.dark-mode .stat-card { background: #1a2233; }
  body.dark-mode .stat-card h3 { color: #4a9eff; }
  body.dark-mode .form-control, body.dark-mode .form-select {
    background: #263048; border-color: #2c3a52; color: #e5e9f0;
  }
  body.dark-mode .form-control::placeholder { color: #8fa3bf; }
  body.dark-mode .text-muted { color: #8fa3bf !important; }
  body.dark-mode .help-text { color: #8fa3bf; }

  .theme-toggle {
    background: #ffc107; border: none; color: #000; font-size: 18px;
    padding: 6px 12px; border-radius: 50%; cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,.2); transition: .2s;
  }
  .theme-toggle:hover { transform: scale(1.1) rotate(20deg); }

  @media print {
    .sidebar, .topbar, .no-print { display: none !important; }
    .main { margin-right: 0 !important; padding: 0 !important; }
  }

  @media (max-width: 768px) {
    .sidebar { right: -250px; }
    .sidebar.open { right: 0; }
    .main { margin-right: 0; }
    .menu-toggle { display: block !important; }
  }
  .menu-toggle { display: none; background: #ffc107; border: none;
    font-size: 22px; padding: 4px 12px; border-radius: 6px; cursor: pointer; }

  .invoice-print { max-width: 800px; margin: auto; }
  .logo-print { text-align: center; padding-bottom: 12px; border-bottom: 2px solid #333; margin-bottom: 16px; }

  .empty-state { text-align: center; padding: 40px 20px; color: #6c757d; }
  .empty-state .icon { font-size: 60px; margin-bottom: 12px; }
  .empty-state h5 { margin: 10px 0; }
</style>
</head>
<body>

{% if session.get('user_id') %}
<aside class="sidebar" id="sidebar">
  <h4>🏢 عمارة هيال<small>HAYAL TOWER</small></h4>

  <div class="menu-group">
    <div class="group-header" onclick="toggleGroup(this)">
      <span><i class="bi bi-house-door"></i> الرئيسية</span>
      <i class="bi bi-chevron-down arrow"></i>
    </div>
    <div class="group-body">
      <a href="{{ url_for('dashboard') }}"><i class="bi bi-speedometer2"></i> لوحة التحكم</a>
      <a href="{{ url_for('alerts') }}"><i class="bi bi-bell"></i> التنبيهات
        {% set ac = get_alerts_count() %}
        {% if ac > 0 %}<span class="badge-alert">{{ ac }}</span>{% endif %}
      </a>
      <a href="{{ url_for('help_page') }}"><i class="bi bi-question-circle"></i> دليل الاستخدام</a>
    </div>
  </div>

  <div class="menu-group">
    <div class="group-header" onclick="toggleGroup(this)">
      <span><i class="bi bi-building"></i> العقارات</span>
      <i class="bi bi-chevron-down arrow"></i>
    </div>
    <div class="group-body">
      <a href="{{ url_for('units_list') }}"><i class="bi bi-door-closed"></i> الشقق</a>
      <a href="{{ url_for('tenants_list') }}"><i class="bi bi-people"></i> المستأجرين</a>
      <a href="{{ url_for('contracts_list') }}"><i class="bi bi-file-text"></i> العقود</a>
    </div>
  </div>

  <div class="menu-group">
    <div class="group-header" onclick="toggleGroup(this)">
      <span><i class="bi bi-cash-stack"></i> المالية</span>
      <i class="bi bi-chevron-down arrow"></i>
    </div>
    <div class="group-body">
      <a href="{{ url_for('rents_list') }}"><i class="bi bi-cash-coin"></i> الإيجارات</a>
      <a href="{{ url_for('utilities_list') }}"><i class="bi bi-lightning-charge"></i> الخدمات</a>
      <a href="{{ url_for('expenses_list') }}"><i class="bi bi-wallet2"></i> المصروفات</a>
    </div>
  </div>

  <div class="menu-group">
    <div class="group-header" onclick="toggleGroup(this)">
      <span><i class="bi bi-tools"></i> العمليات</span>
      <i class="bi bi-chevron-down arrow"></i>
    </div>
    <div class="group-body">
      <a href="{{ url_for('maintenance_list') }}"><i class="bi bi-wrench"></i> الصيانة</a>
      <a href="{{ url_for('staff_list') }}"><i class="bi bi-person-badge"></i> الموظفين</a>
      <a href="{{ url_for('reports') }}"><i class="bi bi-graph-up-arrow"></i> التقارير</a>
    </div>
  </div>

  <div class="menu-group">
    <div class="group-header" onclick="toggleGroup(this)">
      <span><i class="bi bi-gear"></i> النظام</span>
      <i class="bi bi-chevron-down arrow"></i>
    </div>
    <div class="group-body">
      <a href="{{ url_for('profile') }}"><i class="bi bi-person-circle"></i> الملف الشخصي</a>
      {% if current_user() and current_user().role in ['admin','manager'] %}
      <a href="{{ url_for('users_list') }}"><i class="bi bi-shield-lock"></i> المستخدمين</a>
      <a href="{{ url_for('activity_log') }}"><i class="bi bi-clock-history"></i> سجل النشاط</a>
      {% endif %}
      <a href="{{ url_for('settings') }}"><i class="bi bi-gear-wide-connected"></i> الإعدادات</a>
      <a href="{{ url_for('logout') }}" style="color:#ff6b6b;"><i class="bi bi-box-arrow-right"></i> خروج</a>
    </div>
  </div>

  <div style="padding:14px 18px; color:#6b8aa8; font-size:11px; text-align:center;">
    الإصدار 1.0<br>© HAYAL TOWER 2026
  </div>
</aside>
{% endif %}

<main class="{% if session.get('user_id') %}main{% else %}container mt-5{% endif %}">
  {% if session.get('user_id') %}
  <div class="topbar no-print">
    <div style="display:flex; align-items:center; gap:15px; flex:1;">
      <button class="menu-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
      <form action="{{ url_for('global_search') }}" method="get" style="flex:1; max-width:400px;">
        <input name="q" class="form-control form-control-sm"
               placeholder="🔍 بحث سريع (شقة، مستأجر، عقد...)" required>
      </form>
    </div>
    <div class="user-info">
      <button class="theme-toggle" onclick="toggleTheme()" title="الوضع الليلي">🌙</button>
      <div>
        <div style="font-weight:bold; font-size:14px;">{{ current_user().full_name or current_user().username }}</div>
        <div style="font-size:11px; color:#6c757d;">{{ current_user().role }}</div>
      </div>
      <div class="avatar">{{ (current_user().full_name or current_user().username)[0]|upper }}</div>
    </div>
  </div>
  {% endif %}

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show">{{ msg }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}

  {% block content %}{% endblock %}
</main>

<script src="{{ url_for('static', filename='js/bootstrap.bundle.min.js') }}"></script>
<script>
function toggleGroup(el) {
  const body = el.nextElementSibling;
  if (body.classList.contains('collapsed')) {
    body.classList.remove('collapsed');
    el.classList.remove('collapsed');
  } else {
    body.classList.add('collapsed');
    el.classList.add('collapsed');
  }
}

function toggleTheme() {
  document.body.classList.toggle('dark-mode');
  const isDark = document.body.classList.contains('dark-mode');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  document.querySelector('.theme-toggle').textContent = isDark ? '☀️' : '🌙';
}

function playNotification() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.frequency.value = 800; osc.type = 'sine';
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.5);
  } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
  if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = '☀️';
  }
  const currentPath = window.location.pathname;
  document.querySelectorAll('.menu-group').forEach(function(group) {
    group.querySelectorAll('a').forEach(function(link) {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
        const body = group.querySelector('.group-body');
        if (body) body.classList.remove('collapsed');
        const header = group.querySelector('.group-header');
        if (header) header.classList.remove('collapsed');
      }
    });
  });
  {% if session.get('user_id') %}
    const alertCount = {{ get_alerts_count() }};
    if (alertCount > 0 && !sessionStorage.getItem('alertPlayed')) {
      setTimeout(playNotification, 1500);
      sessionStorage.setItem('alertPlayed', '1');
    }
  {% endif %}
});
</script>
{% block scripts %}{% endblock %}
</body>
</html>
"""


def render(template, **kwargs):
    full = BASE_TEMPLATE.replace(
        '{% block content %}{% endblock %}',
        '{% block content %}' + template + '{% endblock %}'
    )
    return render_template_string(full, **kwargs)


# ============================================================
#                     المصادقة
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.active and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id
            session['role'] = u.role
            log_activity('login', f'تسجيل دخول: {u.username}')
            flash('✅ مرحباً بك في نظام عمارة هيال', 'success')
            return redirect(url_for('dashboard'))
        flash('❌ بيانات الدخول خاطئة', 'danger')
    return render('''
    <div class="row justify-content-center" style="margin-top:60px;">
      <div class="col-md-4">
        <div class="card p-4" style="background:#fff;">
          <div class="text-center mb-4">
            <div style="font-size:42px;">🏢</div>
            <h3 style="color:#1a3a5c; font-weight:bold;">عمارة هيال</h3>
            <p style="color:#6c757d; letter-spacing:3px; font-size:12px;">HAYAL TOWER</p>
            <p style="color:#999; font-size:12px;">نظام إدارة العمارة السكنية</p>
          </div>
          <form method="post">
            <div class="mb-3"><label>اسم المستخدم</label>
              <input name="username" class="form-control form-control-lg" required autofocus
                     placeholder="مثال: admin"></div>
            <div class="mb-3"><label>كلمة المرور</label>
              <input name="password" type="password" class="form-control form-control-lg" required
                     placeholder="••••••••"></div>
            <button class="btn btn-warning w-100 btn-lg">🔐 دخول</button>
          </form>
          <hr>
          <small class="text-muted text-center d-block">
            افتراضي: <b>admin / admin123</b>
          </small>
        </div>
      </div>
    </div>
    ''')


@app.route('/logout')
def logout():
    log_activity('logout', 'تسجيل خروج')
    session.clear()
    return redirect(url_for('login'))
# ============================================================
#                     لوحة التحكم
# ============================================================

@app.route('/')
@login_required
def dashboard():
    today = date.today()
    month_str = today.strftime('%Y-%m')

    total_units = Unit.query.count()
    occupied_units = Unit.query.filter_by(status='مسكونة').count()
    empty_units = Unit.query.filter_by(status='فارغة').count()
    maintenance_units = Unit.query.filter_by(status='صيانة').count()
    occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0

    month_collected = db.session.query(func.coalesce(func.sum(RentPayment.amount_paid), 0))\
        .filter(RentPayment.month == month_str).scalar()
    month_due = db.session.query(func.coalesce(func.sum(RentPayment.amount_due), 0))\
        .filter(RentPayment.month == month_str).scalar()
    month_remaining = month_due - month_collected

    total_debts = db.session.query(
        func.coalesce(func.sum(RentPayment.amount_due - RentPayment.amount_paid), 0)
    ).scalar()

    active_contracts = Contract.query.filter_by(status='ساري').count()
    total_tenants = Tenant.query.filter_by(active=True).count()
    open_maintenance = MaintenanceRequest.query.filter(
        MaintenanceRequest.status != 'مكتمل').count()

    future_date = date.fromordinal(today.toordinal() + 30)
    expiring_contracts = Contract.query.filter(
        Contract.status == 'ساري',
        Contract.end_date <= future_date,
        Contract.end_date >= today
    ).order_by(Contract.end_date).all()

    late_rents = RentPayment.query.filter(
        RentPayment.amount_paid < RentPayment.amount_due
    ).order_by(RentPayment.month.desc()).limit(5).all()

    labels, values = [], []
    for i in range(5, -1, -1):
        m = today.replace(day=1)
        for _ in range(i):
            prev = m - timedelta(days=1)
            m = prev.replace(day=1)
        m_str = m.strftime('%Y-%m')
        collected = db.session.query(func.coalesce(func.sum(RentPayment.amount_paid), 0))\
            .filter(RentPayment.month == m_str).scalar()
        labels.append(m.strftime('%Y-%m'))
        values.append(float(collected))

    return render('''
    <h3 class="mb-3">🏠 لوحة التحكم</h3>

    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="stat-card green">
          <p>🏢 إجمالي الشقق</p>
          <h3>{{ total_units }}</h3>
          <small class="text-muted">{{ occupied_units }} مسكونة • {{ empty_units }} فارغة</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card cyan">
          <p>📊 نسبة الإشغال</p>
          <h3>{{ "%.0f"|format(occupancy_rate) }}%</h3>
          <small class="text-muted">من {{ total_units }} شقة</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card purple">
          <p>👥 المستأجرين</p>
          <h3>{{ total_tenants }}</h3>
          <small class="text-muted">{{ active_contracts }} عقد ساري</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card red">
          <p>💸 إجمالي المتأخرات</p>
          <h3>{{ "{:,.0f}".format(total_debts) }}</h3>
          <small class="text-muted">{{ get_setting('currency', 'ر.ي') }}</small>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="stat-card green">
          <p>💰 محصّل هذا الشهر</p>
          <h3>{{ "{:,.0f}".format(month_collected) }}</h3>
          <small class="text-muted">من {{ "{:,.0f}".format(month_due) }} مطلوب</small>
        </div>
      </div>
      <div class="col-md-4">
        <div class="stat-card {{ 'green' if month_remaining <= 0 else 'red' }}">
          <p>⏳ متبقي هذا الشهر</p>
          <h3>{{ "{:,.0f}".format(month_remaining) }}</h3>
          <small class="text-muted">{{ month_str }}</small>
        </div>
      </div>
      <div class="col-md-4">
        <div class="stat-card orange">
          <p>🔧 صيانة مفتوحة</p>
          <h3>{{ open_maintenance }}</h3>
          <small class="text-muted">طلبات بحاجة متابعة</small>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-8">
        <div class="card">
          <div class="card-header">📈 التحصيل الشهري (آخر 6 أشهر)</div>
          <div class="card-body"><canvas id="chart" height="80"></canvas></div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-header">🏠 حالة الشقق</div>
          <div class="card-body">
            <div style="padding:10px; border-bottom:1px solid #eee;">
              <span class="badge bg-success">{{ occupied_units }}</span> مسكونة
            </div>
            <div style="padding:10px; border-bottom:1px solid #eee;">
              <span class="badge bg-secondary">{{ empty_units }}</span> فارغة
            </div>
            <div style="padding:10px; border-bottom:1px solid #eee;">
              <span class="badge bg-warning">{{ maintenance_units }}</span> صيانة
            </div>
            <div style="padding:10px;">
              <a href="{{ url_for('units_list') }}" class="btn btn-sm btn-outline-primary w-100">
                عرض كل الشقق
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="row g-3">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header bg-warning">⚠️ عقود تنتهي قريباً ({{ expiring_contracts|length }})</div>
          <table class="table mb-0">
            <thead><tr><th>الشقة</th><th>المستأجر</th><th>تاريخ الانتهاء</th></tr></thead>
            <tbody>
            {% for c in expiring_contracts %}
              <tr>
                <td><b>{{ c.unit.number if c.unit else '-' }}</b></td>
                <td>{{ c.tenant.name if c.tenant else '-' }}</td>
                <td class="text-danger">{{ c.end_date.strftime('%Y-%m-%d') if c.end_date else '-' }}</td>
              </tr>
            {% else %}
              <tr><td colspan="3" class="empty-state">
                <div class="icon">✅</div>
                <h5>لا توجد عقود تنتهي قريباً</h5>
              </td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card">
          <div class="card-header bg-danger text-white">💸 إيجارات متأخرة ({{ late_rents|length }})</div>
          <table class="table mb-0">
            <thead><tr><th>الشقة</th><th>المستأجر</th><th>المتبقي</th></tr></thead>
            <tbody>
            {% for r in late_rents %}
              <tr>
                <td><b>{{ r.unit.number if r.unit else '-' }}</b></td>
                <td>{{ r.tenant.name if r.tenant else '-' }}</td>
                <td class="text-danger"><b>{{ "{:,.0f}".format(r.amount_due - r.amount_paid) }}</b></td>
              </tr>
            {% else %}
              <tr><td colspan="3" class="empty-state">
                <div class="icon">✅</div>
                <h5>لا توجد متأخرات</h5>
              </td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    ''',
    total_units=total_units, occupied_units=occupied_units, empty_units=empty_units,
    maintenance_units=maintenance_units, occupancy_rate=occupancy_rate,
    month_collected=month_collected, month_due=month_due, month_remaining=month_remaining,
    month_str=month_str, total_debts=total_debts, active_contracts=active_contracts,
    total_tenants=total_tenants, open_maintenance=open_maintenance,
    expiring_contracts=expiring_contracts, late_rents=late_rents,
    labels=labels, values=values) + '''
    <script src="''' + url_for('static', filename='js/chart.js') + '''"></script>
    <script>
      new Chart(document.getElementById('chart'), {
        type: 'line',
        data: {
          labels: ''' + labels.__str__().replace("'", '"') + ''',
          datasets: [{
            label: 'التحصيل',
            data: ''' + values.__str__() + ''',
            borderColor: '#4a9eff',
            backgroundColor: 'rgba(74,158,255,.15)',
            fill: true, tension: .35, borderWidth: 3,
            pointBackgroundColor: '#1a3a5c', pointRadius: 5
          }]
        },
        options: { plugins: { legend: { display: false } } }
      });
    </script>'''


# ============================================================
#                     الشقق (Units) - مُصلحة
# ============================================================

@app.route('/units')
@login_required
def units_list():
    q = request.args.get('q', '').strip()
    floor = request.args.get('floor', '').strip()
    status = request.args.get('status', '').strip()
    query = Unit.query
    if q:
        query = query.filter(Unit.number.contains(q))
    if floor:
        try:
            query = query.filter(Unit.floor == int(floor))
        except:
            pass
    if status:
        query = query.filter(Unit.status == status)
    items = query.order_by(Unit.floor, Unit.number).all()

    # ✅ الإصلاح: جلب العقود النشطة في Python بدلاً من Jinja
    active_contracts = {}
    for c in Contract.query.filter_by(status='ساري').all():
        active_contracts[c.unit_id] = c

    total_units = Unit.query.count()
    occupied = Unit.query.filter_by(status='مسكونة').count()
    empty = Unit.query.filter_by(status='فارغة').count()
    maintenance = Unit.query.filter_by(status='صيانة').count()

    floors = sorted(set([u.floor for u in Unit.query.all() if u.floor]))

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>🏢 الشقق ({{ items|length }})</h3>
      <div>
        <a href="{{ url_for('export_units_csv') }}" class="btn btn-outline-success">📊 CSV</a>
        <a href="{{ url_for('unit_form') }}" class="btn btn-success">+ شقة جديدة</a>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-3"><div class="stat-card"><p>🏢 الإجمالي</p><h3>{{ total_units }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card green"><p>✅ مسكونة</p><h3>{{ occupied }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card orange"><p>🔓 فارغة</p><h3>{{ empty }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card red"><p>🔧 صيانة</p><h3>{{ maintenance }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-4">
          <input name="q" value="{{ q }}" class="form-control"
                 placeholder="🔍 ابحث برقم الشقة...">
        </div>
        <div class="col-md-3">
          <select name="floor" class="form-select">
            <option value="">كل الطوابق</option>
            {% for f in floors %}
            <option value="{{ f }}" {{ 'selected' if floor==f|string }}>الطابق {{ f }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <select name="status" class="form-select">
            <option value="">كل الحالات</option>
            <option value="مسكونة" {{ 'selected' if status=='مسكونة' }}>مسكونة</option>
            <option value="فارغة" {{ 'selected' if status=='فارغة' }}>فارغة</option>
            <option value="صيانة" {{ 'selected' if status=='صيانة' }}>صيانة</option>
          </select>
        </div>
        <div class="col-md-2"><button class="btn btn-primary w-100">🔍 بحث</button></div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>الشقة</th><th>الطابق</th><th>الغرف</th><th>المساحة</th>
          <th>الإيجار</th><th>الحالة</th><th>المستأجر الحالي</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for u in items %}
        <tr class="{{ 'table-success' if u.status=='مسكونة' else ('table-warning' if u.status=='صيانة' else '') }}">
          <td><b style="font-size:16px;">{{ u.number }}</b>
            {% if u.future %}<span class="badge bg-secondary">مستقبلية</span>{% endif %}
          </td>
          <td>{{ u.floor }}</td>
          <td>{{ u.rooms }}</td>
          <td>{{ u.area_sqm }} م²</td>
          <td><b>{{ "{:,.0f}".format(u.monthly_rent) }}</b> {{ u.currency }}</td>
          <td>
            {% if u.status == 'مسكونة' %}
              <span class="badge bg-success">✅ مسكونة</span>
            {% elif u.status == 'فارغة' %}
              <span class="badge bg-secondary">🔓 فارغة</span>
            {% else %}
              <span class="badge bg-warning">🔧 صيانة</span>
            {% endif %}
          </td>
          <td>
            {% set ac = active_contracts.get(u.id) %}
            {% if ac %}
              <a href="{{ url_for('tenant_profile', id=ac.tenant_id) }}">
                {{ ac.tenant.name if ac.tenant else '-' }}
              </a>
            {% else %}
              <span class="text-muted">-</span>
            {% endif %}
          </td>
          <td>
            <a href="{{ url_for('unit_profile', id=u.id) }}" class="btn btn-sm btn-info" title="عرض"><i class="bi bi-eye"></i></a>
            <a href="{{ url_for('unit_form', id=u.id) }}" class="btn btn-sm btn-primary" title="تعديل"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('unit_delete', id=u.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف الشقة؟')" title="حذف"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="8" class="empty-state">
          <div class="icon">🏢</div>
          <h5>لا توجد شقق</h5>
          <p>ابدأ بإضافة شقق العمارة</p>
          <a href="{{ url_for('unit_form') }}" class="btn btn-success">+ إضافة أول شقة</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, floor=floor, status=status,
        total_units=total_units, occupied=occupied, empty=empty,
        maintenance=maintenance, floors=floors,
        active_contracts=active_contracts)


@app.route('/units/new', methods=['GET', 'POST'])
@app.route('/units/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def unit_form(id=None):
    u = Unit.query.get(id) if id else None
    if request.method == 'POST':
        if not u:
            u = Unit()
            db.session.add(u)
        u.number = request.form['number'].strip()
        u.floor = int(request.form.get('floor') or 1)
        u.rooms = int(request.form.get('rooms') or 3)
        u.area_sqm = float(request.form.get('area_sqm') or 0)
        u.monthly_rent = float(request.form.get('monthly_rent') or 0)
        u.currency = request.form.get('currency', 'ر.ي')
        u.status = request.form.get('status', 'فارغة')
        u.future = request.form.get('future') == 'on'
        u.notes = request.form.get('notes', '').strip()
        db.session.commit()
        log_activity('save_unit', f'حفظ شقة: {u.number}')
        flash('✅ تم حفظ الشقة', 'success')
        return redirect(url_for('units_list'))
    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل شقة' if u else '➕ إضافة شقة جديدة' }}</h3>
      <a href="{{ url_for('units_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-3">
          <label>رقم الشقة <span class="text-danger">*</span></label>
          <input name="number" value="{{ u.number if u else '' }}" class="form-control" required
                 placeholder="101">
          <small class="help-text">مثال: 101، 102، 201</small>
        </div>
        <div class="col-md-3">
          <label>الطابق</label>
          <input name="floor" type="number" value="{{ u.floor if u else 1 }}" class="form-control"
                 min="1" max="20">
          <small class="help-text">رقم الطابق (1، 2، 3...)</small>
        </div>
        <div class="col-md-3">
          <label>عدد الغرف</label>
          <input name="rooms" type="number" value="{{ u.rooms if u else 3 }}" class="form-control"
                 min="1" max="10">
          <small class="help-text">مثال: 2، 3، 4</small>
        </div>
        <div class="col-md-3">
          <label>المساحة (م²)</label>
          <input name="area_sqm" type="number" step="0.01" value="{{ u.area_sqm if u else 0 }}"
                 class="form-control" placeholder="120">
          <small class="help-text">مساحة الشقة</small>
        </div>
        <div class="col-md-4">
          <label>الإيجار الشهري</label>
          <input name="monthly_rent" type="number" step="0.01" value="{{ u.monthly_rent if u else 0 }}"
                 class="form-control" placeholder="50000">
          <small class="help-text">قيمة الإيجار المتفق عليها</small>
        </div>
        <div class="col-md-4">
          <label>العملة</label>
          <select name="currency" class="form-select">
            {% for cur in ['ر.ي', 'ر.س', 'د.إ', '$'] %}
            <option {{ 'selected' if u and u.currency==cur }}>{{ cur }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>حالة الشقة</label>
          <select name="status" class="form-select">
            {% for st in ['فارغة', 'مسكونة', 'صيانة'] %}
            <option {{ 'selected' if u and u.status==st }}>{{ st }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-12">
          <label class="form-check">
            <input type="checkbox" name="future" class="form-check-input"
                   {{ 'checked' if u and u.future }}>
            شقة مستقبلية (غير جاهزة بعد)
          </label>
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" rows="2" class="form-control">{{ u.notes if u else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('units_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>''', u=u)


@app.route('/units/<int:id>')
@login_required
def unit_profile(id):
    u = Unit.query.get_or_404(id)
    contracts = Contract.query.filter_by(unit_id=id).order_by(Contract.id.desc()).all()
    utilities = UtilityBill.query.filter_by(unit_id=id).order_by(UtilityBill.id.desc()).limit(20).all()
    maintenance = MaintenanceRequest.query.filter_by(unit_id=id).order_by(MaintenanceRequest.id.desc()).limit(10).all()
    active_contract = Contract.query.filter_by(unit_id=id, status='ساري').first()

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h3 style="margin:0;">🏠 شقة {{ u.number }}</h3>
        <small class="text-muted">الطابق {{ u.floor }} - {{ u.rooms }} غرف - {{ u.area_sqm }} م²</small>
      </div>
      <div>
        <a href="{{ url_for('unit_form', id=u.id) }}" class="btn btn-primary">✏️ تعديل</a>
        <a href="{{ url_for('units_list') }}" class="btn btn-secondary">← رجوع</a>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-3"><div class="stat-card"><p>الحالة</p><h5>{{ u.status }}</h5></div></div>
      <div class="col-md-3"><div class="stat-card green"><p>الإيجار الشهري</p><h5>{{ "{:,.0f}".format(u.monthly_rent) }} {{ u.currency }}</h5></div></div>
      <div class="col-md-3"><div class="stat-card purple"><p>عدد العقود</p><h3>{{ contracts|length }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card cyan"><p>المستأجر الحالي</p><h5>{{ active_contract.tenant.name if active_contract and active_contract.tenant else '-' }}</h5></div></div>
    </div>

    <div class="card mb-3">
      <div class="card-header">📝 العقود ({{ contracts|length }})</div>
      <table class="table mb-0">
        <thead><tr><th>الرقم</th><th>المستأجر</th><th>من</th><th>إلى</th><th>الإيجار</th><th>الحالة</th><th></th></tr></thead>
        <tbody>
        {% for c in contracts %}
        <tr>
          <td>{{ c.number }}</td>
          <td>{{ c.tenant.name if c.tenant else '-' }}</td>
          <td>{{ c.start_date }}</td>
          <td>{{ c.end_date }}</td>
          <td>{{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }}</td>
          <td><span class="badge bg-{{ 'success' if c.status=='ساري' else 'secondary' }}">{{ c.status }}</span></td>
          <td><a href="{{ url_for('contract_view', id=c.id) }}" class="btn btn-sm btn-info">عرض</a></td>
        </tr>
        {% else %}
        <tr><td colspan="7" class="text-center text-muted py-3">لا توجد عقود</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card mb-3">
      <div class="card-header">💡 الخدمات (آخر 20)</div>
      <table class="table mb-0">
        <thead><tr><th>الشهر</th><th>النوع</th><th>الاستهلاك</th><th>الإجمالي</th><th>الحالة</th></tr></thead>
        <tbody>
        {% for b in utilities %}
        <tr>
          <td>{{ b.month }}</td>
          <td><span class="badge bg-{{ 'warning' if b.service_type=='كهرباء' else 'info' }}">{{ b.service_type }}</span></td>
          <td>{{ b.consumption }}</td>
          <td>{{ "{:,.0f}".format(b.total) }}</td>
          <td><span class="badge bg-{{ 'success' if b.status=='مدفوع' else 'danger' }}">{{ b.status }}</span></td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="text-center text-muted py-3">لا توجد فواتير</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-header">🔧 طلبات الصيانة ({{ maintenance|length }})</div>
      <table class="table mb-0">
        <thead><tr><th>الرقم</th><th>النوع</th><th>الحالة</th><th>التكلفة</th><th>التاريخ</th></tr></thead>
        <tbody>
        {% for m in maintenance %}
        <tr>
          <td>{{ m.number }}</td>
          <td>{{ m.category }}</td>
          <td><span class="badge bg-{{ 'success' if m.status=='مكتمل' else ('warning' if m.status=='قيد التنفيذ' else 'secondary') }}">{{ m.status }}</span></td>
          <td>{{ "{:,.0f}".format(m.cost) }}</td>
          <td>{{ m.request_date }}</td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="text-center text-muted py-3">لا توجد طلبات</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', u=u, contracts=contracts, utilities=utilities,
        maintenance=maintenance, active_contract=active_contract)


@app.route('/units/<int:id>/delete')
@login_required
def unit_delete(id):
    u = Unit.query.get_or_404(id)
    active = Contract.query.filter_by(unit_id=id, status='ساري').first()
    if active:
        flash('❌ لا يمكن حذف شقة لها عقد ساري', 'danger')
        return redirect(url_for('units_list'))
    db.session.delete(u)
    db.session.commit()
    log_activity('delete_unit', f'حذف شقة: {u.number}')
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('units_list'))


@app.route('/export/units.csv')
@login_required
def export_units_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['الشقة', 'الطابق', 'الغرف', 'المساحة', 'الإيجار', 'العملة', 'الحالة'])
    for u in Unit.query.order_by(Unit.floor, Unit.number).all():
        w.writerow([u.number, u.floor, u.rooms, u.area_sqm, u.monthly_rent,
                    u.currency, u.status])
    return Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=units.csv'})


# ============================================================
#                     المستأجرين (Tenants)
# ============================================================

@app.route('/tenants')
@login_required
def tenants_list():
    q = request.args.get('q', '').strip()
    active = request.args.get('active', '')
    query = Tenant.query
    if q:
        query = query.filter(or_(
            Tenant.name.contains(q), Tenant.phone.contains(q),
            Tenant.national_id.contains(q)))
    if active == '1':
        query = query.filter_by(active=True)
    items = query.order_by(Tenant.id.desc()).all()

    total = Tenant.query.count()
    active_count = Tenant.query.filter_by(active=True).count()

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>👥 المستأجرين ({{ items|length }})</h3>
      <div>
        <a href="{{ url_for('export_tenants_csv') }}" class="btn btn-outline-success">📊 CSV</a>
        <a href="{{ url_for('tenant_form') }}" class="btn btn-success">+ مستأجر جديد</a>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-6"><div class="stat-card"><p>إجمالي المستأجرين</p><h3>{{ total }}</h3></div></div>
      <div class="col-md-6"><div class="stat-card green"><p>النشطين حالياً</p><h3>{{ active_count }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-6">
          <input name="q" value="{{ q }}" class="form-control"
                 placeholder="🔍 ابحث بالاسم أو الهاتف أو رقم الهوية...">
        </div>
        <div class="col-md-3">
          <label class="form-check mt-2">
            <input type="checkbox" name="active" value="1" {{ 'checked' if active=='1' }}>
            النشطين فقط
          </label>
        </div>
        <div class="col-md-3"><button class="btn btn-primary w-100">🔍 بحث</button></div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>#</th><th>الاسم</th><th>الهوية</th><th>الهاتف</th>
          <th>الحالة</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for t in items %}
        <tr class="{{ '' if t.active else 'table-secondary' }}">
          <td>{{ t.id }}</td>
          <td><b>{{ t.name }}</b></td>
          <td>{{ t.national_id or '-' }}</td>
          <td>{{ t.phone or '-' }}</td>
          <td>
            {% if t.active %}
              <span class="badge bg-success">نشط</span>
            {% else %}
              <span class="badge bg-secondary">غير نشط</span>
            {% endif %}
          </td>
          <td>
            <a href="{{ url_for('tenant_profile', id=t.id) }}" class="btn btn-sm btn-info"><i class="bi bi-eye"></i></a>
            <a href="{{ url_for('tenant_form', id=t.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('tenant_delete', id=t.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف المستأجر؟')"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="6" class="empty-state">
          <div class="icon">👥</div>
          <h5>لا يوجد مستأجرين</h5>
          <a href="{{ url_for('tenant_form') }}" class="btn btn-success">+ إضافة مستأجر</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, active=active, total=total, active_count=active_count)


@app.route('/tenants/new', methods=['GET', 'POST'])
@app.route('/tenants/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def tenant_form(id=None):
    t = Tenant.query.get(id) if id else None
    if request.method == 'POST':
        if not t:
            t = Tenant()
            db.session.add(t)
        t.name = request.form['name'].strip()
        t.national_id = request.form.get('national_id', '').strip()
        t.phone = request.form.get('phone', '').strip()
        t.phone2 = request.form.get('phone2', '').strip()
        t.job = request.form.get('job', '').strip()
        t.family_size = int(request.form.get('family_size') or 1)
        t.emergency_contact = request.form.get('emergency_contact', '').strip()
        t.emergency_phone = request.form.get('emergency_phone', '').strip()
        t.address_prev = request.form.get('address_prev', '').strip()
        t.notes = request.form.get('notes', '').strip()
        t.active = request.form.get('active') == 'on'
        db.session.commit()
        log_activity('save_tenant', f'حفظ مستأجر: {t.name}')
        flash('✅ تم حفظ المستأجر', 'success')
        return redirect(url_for('tenants_list'))
    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل مستأجر' if t else '➕ إضافة مستأجر جديد' }}</h3>
      <a href="{{ url_for('tenants_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6">
          <label>الاسم الكامل <span class="text-danger">*</span></label>
          <input name="name" value="{{ t.name if t else '' }}" class="form-control form-control-lg"
                 required autofocus placeholder="الاسم الكامل">
          <small class="help-text">مثال: محمد أحمد علي</small>
        </div>
        <div class="col-md-6">
          <label>رقم الهوية</label>
          <input name="national_id" value="{{ t.national_id if t else '' }}" class="form-control"
                 placeholder="01234567">
          <small class="help-text">رقم البطاقة أو جواز السفر</small>
        </div>
        <div class="col-md-4">
          <label>الهاتف</label>
          <input name="phone" value="{{ t.phone if t else '' }}" class="form-control"
                 placeholder="777777777">
        </div>
        <div class="col-md-4">
          <label>هاتف إضافي</label>
          <input name="phone2" value="{{ t.phone2 if t else '' }}" class="form-control"
                 placeholder="733333333">
        </div>
        <div class="col-md-4">
          <label>الوظيفة</label>
          <input name="job" value="{{ t.job if t else '' }}" class="form-control"
                 placeholder="موظف / تاجر / طالب">
        </div>
        <div class="col-md-4">
          <label>عدد أفراد الأسرة</label>
          <input name="family_size" type="number" value="{{ t.family_size if t else 1 }}"
                 class="form-control" min="1" max="20">
        </div>
        <div class="col-md-4">
          <label>جهة اتصال للطوارئ</label>
          <input name="emergency_contact" value="{{ t.emergency_contact if t else '' }}"
                 class="form-control" placeholder="اسم شخص قريب">
        </div>
        <div class="col-md-4">
          <label>هاتف الطوارئ</label>
          <input name="emergency_phone" value="{{ t.emergency_phone if t else '' }}"
                 class="form-control" placeholder="777777777">
        </div>
        <div class="col-12">
          <label>العنوان السابق</label>
          <input name="address_prev" value="{{ t.address_prev if t else '' }}" class="form-control">
        </div>
        <div class="col-12">
          <label class="form-check">
            <input type="checkbox" name="active" class="form-check-input"
                   {{ 'checked' if not t or t.active }}>
            مستأجر نشط
          </label>
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" rows="2" class="form-control">{{ t.notes if t else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('tenants_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>''', t=t)


@app.route('/tenants/<int:id>')
@login_required
def tenant_profile(id):
    t = Tenant.query.get_or_404(id)
    contracts = Contract.query.filter_by(tenant_id=id).order_by(Contract.id.desc()).all()
    payments = RentPayment.query.filter_by(tenant_id=id).order_by(RentPayment.id.desc()).limit(20).all()
    total_paid = sum(p.amount_paid for p in payments)
    total_due = sum(p.amount_due for p in payments)
    total_debt = total_due - total_paid
    active_contract = Contract.query.filter_by(tenant_id=id, status='ساري').first()

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h3 style="margin:0;">👤 {{ t.name }}
          {% if t.active %}<span class="badge bg-success">نشط</span>{% endif %}
        </h3>
        <small class="text-muted">{{ t.job or '' }} {% if t.national_id %}• هوية: {{ t.national_id }}{% endif %}</small>
      </div>
      <div>
        <a href="{{ url_for('tenant_form', id=t.id) }}" class="btn btn-primary">✏️ تعديل</a>
        <a href="{{ url_for('tenants_list') }}" class="btn btn-secondary">← رجوع</a>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-3"><div class="stat-card"><p>📞 الهاتف</p><h5>{{ t.phone or '-' }}</h5></div></div>
      <div class="col-md-3"><div class="stat-card purple"><p>🏠 الشقة الحالية</p><h5>{{ active_contract.unit.number if active_contract and active_contract.unit else '-' }}</h5></div></div>
      <div class="col-md-3"><div class="stat-card green"><p>💰 إجمالي المدفوع</p><h3>{{ "{:,.0f}".format(total_paid) }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card {{ 'red' if total_debt > 0 else 'green' }}"><p>💸 الدين المتبقي</p><h3>{{ "{:,.0f}".format(total_debt) }}</h3></div></div>
    </div>

    <div class="card mb-3">
      <div class="card-header">📝 العقود ({{ contracts|length }})</div>
      <table class="table mb-0">
        <thead><tr><th>الرقم</th><th>الشقة</th><th>من</th><th>إلى</th><th>الإيجار</th><th>الحالة</th><th></th></tr></thead>
        <tbody>
        {% for c in contracts %}
        <tr>
          <td>{{ c.number }}</td>
          <td>{{ c.unit.number if c.unit else '-' }}</td>
          <td>{{ c.start_date }}</td>
          <td>{{ c.end_date }}</td>
          <td>{{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }}</td>
          <td><span class="badge bg-{{ 'success' if c.status=='ساري' else 'secondary' }}">{{ c.status }}</span></td>
          <td><a href="{{ url_for('contract_view', id=c.id) }}" class="btn btn-sm btn-info">عرض</a></td>
        </tr>
        {% else %}
        <tr><td colspan="7" class="text-center text-muted py-3">لا توجد عقود</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-header">💵 دفعات الإيجار - آخر 20</div>
      <table class="table mb-0">
        <thead><tr><th>الشهر</th><th>المطلوب</th><th>المدفوع</th><th>المتبقي</th><th>تاريخ الدفع</th></tr></thead>
        <tbody>
        {% for p in payments %}
        <tr>
          <td>{{ p.month }}</td>
          <td>{{ "{:,.0f}".format(p.amount_due) }}</td>
          <td class="text-success">{{ "{:,.0f}".format(p.amount_paid) }}</td>
          <td class="text-danger">{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }}</td>
          <td>{{ p.payment_date }}</td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="text-center text-muted py-3">لا توجد دفعات</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', t=t, contracts=contracts, payments=payments,
        total_paid=total_paid, total_due=total_due, total_debt=total_debt,
        active_contract=active_contract)


@app.route('/tenants/<int:id>/delete')
@login_required
def tenant_delete(id):
    t = Tenant.query.get_or_404(id)
    active = Contract.query.filter_by(tenant_id=id, status='ساري').first()
    if active:
        flash('❌ لا يمكن حذف مستأجر له عقد ساري', 'danger')
        return redirect(url_for('tenants_list'))
    db.session.delete(t)
    db.session.commit()
    log_activity('delete_tenant', f'حذف مستأجر: {t.name}')
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('tenants_list'))


@app.route('/export/tenants.csv')
@login_required
def export_tenants_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['#', 'الاسم', 'الهوية', 'الهاتف', 'الهاتف2', 'الوظيفة', 'عدد الأسرة', 'الحالة'])
    for t in Tenant.query.all():
        w.writerow([t.id, t.name, t.national_id, t.phone, t.phone2, t.job,
                    t.family_size, 'نشط' if t.active else 'غير نشط'])
    return Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=tenants.csv'})


# ============================================================
#                     العقود (Contracts)
# ============================================================

@app.route('/contracts')
@login_required
def contracts_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    query = Contract.query
    if q:
        query = query.filter(Contract.number.contains(q))
    if status:
        query = query.filter(Contract.status == status)
    items = query.order_by(Contract.id.desc()).all()

    active_count = Contract.query.filter_by(status='ساري').count()
    expired_count = Contract.query.filter_by(status='منتهي').count()

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>📝 العقود ({{ items|length }})</h3>
      <div>
        <a href="{{ url_for('export_contracts_csv') }}" class="btn btn-outline-success">📊 CSV</a>
        <a href="{{ url_for('contract_form') }}" class="btn btn-success">+ عقد جديد</a>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="stat-card green"><p>عقود سارية</p><h3>{{ active_count }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card orange"><p>عقود منتهية</p><h3>{{ expired_count }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card"><p>الإجمالي</p><h3>{{ items|length }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-6">
          <input name="q" value="{{ q }}" class="form-control" placeholder="🔍 بحث برقم العقد...">
        </div>
        <div class="col-md-4">
          <select name="status" class="form-select">
            <option value="">كل الحالات</option>
            <option value="ساري" {{ 'selected' if status=='ساري' }}>ساري</option>
            <option value="منتهي" {{ 'selected' if status=='منتهي' }}>منتهي</option>
            <option value="ملغي" {{ 'selected' if status=='ملغي' }}>ملغي</option>
          </select>
        </div>
        <div class="col-md-2"><button class="btn btn-primary w-100">🔍</button></div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>الرقم</th><th>الشقة</th><th>المستأجر</th><th>من</th><th>إلى</th>
          <th>الإيجار</th><th>طريقة الدفع</th><th>الحالة</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for c in items %}
        <tr>
          <td><b>{{ c.number }}</b></td>
          <td><b>{{ c.unit.number if c.unit else '-' }}</b></td>
          <td>{{ c.tenant.name if c.tenant else '-' }}</td>
          <td>{{ c.start_date }}</td>
          <td>{{ c.end_date }}</td>
          <td>{{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }}</td>
          <td><span class="badge bg-secondary">{{ c.payment_method }}</span></td>
          <td>
            <span class="badge bg-{{ 'success' if c.status=='ساري' else ('warning' if c.status=='منتهي' else 'danger') }}">
              {{ c.status }}
            </span>
          </td>
          <td>
            <a href="{{ url_for('contract_view', id=c.id) }}" class="btn btn-sm btn-info"><i class="bi bi-eye"></i></a>
            <a href="{{ url_for('contract_print', id=c.id) }}" class="btn btn-sm btn-secondary"
               target="_blank"><i class="bi bi-printer"></i></a>
            <a href="{{ url_for('contract_form', id=c.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('contract_delete', id=c.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف العقد؟')"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="9" class="empty-state">
          <div class="icon">📝</div>
          <h5>لا توجد عقود</h5>
          <a href="{{ url_for('contract_form') }}" class="btn btn-success">+ إضافة عقد</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, status=status,
        active_count=active_count, expired_count=expired_count)


@app.route('/contracts/new', methods=['GET', 'POST'])
@app.route('/contracts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def contract_form(id=None):
    c = Contract.query.get(id) if id else None
    tenants = Tenant.query.filter_by(active=True).order_by(Tenant.name).all()
    units = Unit.query.filter(Unit.status.in_(['فارغة', 'مسكونة'])).order_by(Unit.number).all()

    if request.method == 'POST':
        if not c:
            c = Contract(number=next_number(Contract, 'CON'))
            db.session.add(c)
        c.tenant_id = int(request.form['tenant_id'])
        c.unit_id = int(request.form['unit_id'])
        c.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        c.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        c.monthly_rent = float(request.form.get('monthly_rent') or 0)
        c.deposit = float(request.form.get('deposit') or 0)
        c.payment_method = request.form.get('payment_method', 'شهري')
        c.currency = request.form.get('currency', 'ر.ي')
        c.status = request.form.get('status', 'ساري')
        c.notes = request.form.get('notes', '').strip()
        unit = Unit.query.get(c.unit_id)
        if unit and c.status == 'ساري':
            unit.status = 'مسكونة'
        db.session.commit()
        log_activity('save_contract', f'حفظ عقد: {c.number}')
        flash('✅ تم حفظ العقد', 'success')
        return redirect(url_for('contracts_list'))

    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل عقد' if c else '➕ عقد جديد' }}</h3>
      <a href="{{ url_for('contracts_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6">
          <label>المستأجر <span class="text-danger">*</span></label>
          <select name="tenant_id" class="form-select" required>
            <option value="">-- اختر المستأجر --</option>
            {% for t in tenants %}
            <option value="{{ t.id }}" {{ 'selected' if c and c.tenant_id==t.id }}>{{ t.name }} - {{ t.phone or '' }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>الشقة <span class="text-danger">*</span></label>
          <select name="unit_id" class="form-select" required>
            <option value="">-- اختر الشقة --</option>
            {% for u in units %}
            <option value="{{ u.id }}" {{ 'selected' if c and c.unit_id==u.id }}>
              {{ u.number }} - الطابق {{ u.floor }} - {{ u.status }}
            </option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>تاريخ البداية <span class="text-danger">*</span></label>
          <input name="start_date" type="date" value="{{ c.start_date if c else '' }}"
                 class="form-control" required>
        </div>
        <div class="col-md-6">
          <label>تاريخ النهاية <span class="text-danger">*</span></label>
          <input name="end_date" type="date" value="{{ c.end_date if c else '' }}"
                 class="form-control" required>
        </div>
        <div class="col-md-4">
          <label>الإيجار الشهري</label>
          <input name="monthly_rent" type="number" step="0.01"
                 value="{{ c.monthly_rent if c else 0 }}" class="form-control" placeholder="50000">
        </div>
        <div class="col-md-4">
          <label>مبلغ الضمان</label>
          <input name="deposit" type="number" step="0.01"
                 value="{{ c.deposit if c else 0 }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>العملة</label>
          <select name="currency" class="form-select">
            {% for cur in ['ر.ي', 'ر.س', 'د.إ', '$'] %}
            <option {{ 'selected' if c and c.currency==cur }}>{{ cur }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>طريقة الدفع</label>
          <select name="payment_method" class="form-select">
            {% for pm in ['شهري', 'ربع سنوي', 'نصف سنوي', 'سنوي'] %}
            <option {{ 'selected' if c and c.payment_method==pm }}>{{ pm }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>حالة العقد</label>
          <select name="status" class="form-select">
            {% for st in ['ساري', 'منتهي', 'ملغي'] %}
            <option {{ 'selected' if c and c.status==st }}>{{ st }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" rows="2" class="form-control">{{ c.notes if c else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('contracts_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>''', c=c, tenants=tenants, units=units)


@app.route('/contracts/<int:id>')
@login_required
def contract_view(id):
    c = Contract.query.get_or_404(id)
    payments = RentPayment.query.filter_by(contract_id=id).order_by(RentPayment.id.desc()).all()
    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>📝 عقد {{ c.number }}</h3>
      <div>
        <a href="{{ url_for('contract_print', id=c.id) }}" class="btn btn-secondary" target="_blank">🖨️ طباعة</a>
        <a href="{{ url_for('contract_form', id=c.id) }}" class="btn btn-primary">✏️ تعديل</a>
        <a href="{{ url_for('contracts_list') }}" class="btn btn-outline-secondary">← رجوع</a>
      </div>
    </div>

    <div class="card p-4 mb-3">
      <div class="row g-3">
        <div class="col-md-6">
          <p><b>المستأجر:</b> {{ c.tenant.name if c.tenant else '-' }}</p>
          <p><b>الهاتف:</b> {{ c.tenant.phone if c.tenant else '-' }}</p>
          <p><b>الشقة:</b> {{ c.unit.number if c.unit else '-' }} (الطابق {{ c.unit.floor if c.unit else '-' }})</p>
        </div>
        <div class="col-md-6">
          <p><b>من:</b> {{ c.start_date }}</p>
          <p><b>إلى:</b> {{ c.end_date }}</p>
          <p><b>طريقة الدفع:</b> {{ c.payment_method }}</p>
        </div>
        <div class="col-md-4"><div class="stat-card green"><p>الإيجار الشهري</p><h3>{{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }}</h3></div></div>
        <div class="col-md-4"><div class="stat-card purple"><p>الضمان</p><h3>{{ "{:,.0f}".format(c.deposit) }}</h3></div></div>
        <div class="col-md-4"><div class="stat-card {{ 'green' if c.status=='ساري' else 'orange' }}"><p>الحالة</p><h3>{{ c.status }}</h3></div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header d-flex justify-content-between">
        <span>💵 دفعات هذا العقد ({{ payments|length }})</span>
        <a href="{{ url_for('rent_form') }}?contract_id={{ c.id }}" class="btn btn-sm btn-success">+ دفعة جديدة</a>
      </div>
      <table class="table mb-0">
        <thead><tr><th>الشهر</th><th>المطلوب</th><th>المدفوع</th><th>المتبقي</th><th>التاريخ</th><th></th></tr></thead>
        <tbody>
        {% for p in payments %}
        <tr>
          <td>{{ p.month }}</td>
          <td>{{ "{:,.0f}".format(p.amount_due) }}</td>
          <td class="text-success">{{ "{:,.0f}".format(p.amount_paid) }}</td>
          <td class="text-danger">{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }}</td>
          <td>{{ p.payment_date }}</td>
          <td><a href="{{ url_for('rent_print', id=p.id) }}" class="btn btn-sm btn-secondary" target="_blank"><i class="bi bi-printer"></i></a></td>
        </tr>
        {% else %}
        <tr><td colspan="6" class="text-center text-muted py-3">لا توجد دفعات</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', c=c, payments=payments)


@app.route('/contracts/<int:id>/print')
@login_required
def contract_print(id):
    c = Contract.query.get_or_404(id)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>عقد {{ c.number }}</title>
      <link rel="stylesheet" href="''' + url_for('static', filename='css/bootstrap.rtl.min.css') + '''">
      <style>body { font-family: Tahoma, sans-serif; padding: 30px; line-height: 1.8; }
        h1, h2 { text-align: center; }
        .section { margin: 20px 0; }
        .signature { margin-top: 60px; display: flex; justify-content: space-between; }
        @media print { .no-print { display: none !important; } }</style>
    </head>
    <body onload="window.print()">
      <div class="no-print text-center mb-3">
        <button onclick="window.print()" class="btn btn-primary">🖨️ طباعة</button>
        <button onclick="window.close()" class="btn btn-secondary">إغلاق</button>
      </div>

      <div style="text-align:center; border-bottom: 3px double #333; padding-bottom: 15px; margin-bottom: 25px;">
        <h1 style="color:#1a3a5c;">{{ get_setting('tower_name', 'عمارة هيال') }}</h1>
        <p style="font-size: 12px; color: #666;">{{ get_setting('tower_address', '') }} | {{ get_setting('tower_phone', '') }}</p>
        <h2>عقد إيجار وحدة سكنية</h2>
      </div>

      <p><b>رقم العقد:</b> {{ c.number }} &nbsp;&nbsp; <b>التاريخ:</b> {{ c.created_at.strftime('%Y-%m-%d') }}</p>

      <div class="section">
        <h4>الطرف الأول (المالك / الوكيل):</h4>
        <p>{{ get_setting('tower_name', 'عمارة هيال') }} - {{ get_setting('tower_address', '') }}</p>
      </div>

      <div class="section">
        <h4>الطرف الثاني (المستأجر):</h4>
        <p>الاسم: <b>{{ c.tenant.name if c.tenant else '-' }}</b></p>
        <p>رقم الهوية: {{ c.tenant.national_id if c.tenant else '-' }}</p>
        <p>الهاتف: {{ c.tenant.phone if c.tenant else '-' }}</p>
        <p>العمل: {{ c.tenant.job if c.tenant else '-' }}</p>
      </div>

      <div class="section">
        <h4>تفاصيل الوحدة السكنية:</h4>
        <p>رقم الشقة: <b>{{ c.unit.number if c.unit else '-' }}</b></p>
        <p>الطابق: {{ c.unit.floor if c.unit else '-' }}</p>
        <p>عدد الغرف: {{ c.unit.rooms if c.unit else '-' }}</p>
        <p>المساحة: {{ c.unit.area_sqm if c.unit else '-' }} م²</p>
      </div>

      <div class="section">
        <h4>تفاصيل العقد:</h4>
        <p>مدة العقد: من <b>{{ c.start_date }}</b> إلى <b>{{ c.end_date }}</b></p>
        <p>قيمة الإيجار الشهري: <b>{{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }}</b></p>
        <p>طريقة الدفع: <b>{{ c.payment_method }}</b></p>
        <p>مبلغ الضمان: <b>{{ "{:,.0f}".format(c.deposit) }} {{ c.currency }}</b></p>
      </div>

      <div class="section">
        <h4>شروط عامة:</h4>
        <ol>
          <li>يلتزم الطرف الثاني بدفع الإيجار في الوقت المتفق عليه.</li>
          <li>في حال التأخر عن الدفع أكثر من 15 يوماً يحق للطرف الأول اتخاذ الإجراءات القانونية.</li>
          <li>يُستخدم العقار للسكن فقط ولا يجوز تغيير النشاط دون إذن كتابي.</li>
          <li>يُعاد الضمان عند انتهاء العقد وتسليم الشقة بحالة جيدة.</li>
          <li>يلتزم المستأجر بالمحافظة على الوحدة السكنية والمرافق المشتركة.</li>
        </ol>
      </div>

      <div class="signature">
        <div style="text-align:center;">
          <p><b>الطرف الأول</b></p>
          <p>_______________________</p>
          <p>التوقيع</p>
        </div>
        <div style="text-align:center;">
          <p><b>الطرف الثاني</b></p>
          <p>_______________________</p>
          <p>التوقيع</p>
        </div>
      </div>
    </body></html>''', c=c)


@app.route('/contracts/<int:id>/delete')
@login_required
def contract_delete(id):
    c = Contract.query.get_or_404(id)
    unit = Unit.query.get(c.unit_id)
    if unit and unit.status == 'مسكونة':
        unit.status = 'فارغة'
    db.session.delete(c)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('contracts_list'))


@app.route('/export/contracts.csv')
@login_required
def export_contracts_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['الرقم', 'الشقة', 'المستأجر', 'من', 'إلى', 'الإيجار', 'العملة', 'طريقة الدفع', 'الحالة'])
    for c in Contract.query.all():
        w.writerow([c.number, c.unit.number if c.unit else '',
                    c.tenant.name if c.tenant else '', c.start_date, c.end_date,
                    c.monthly_rent, c.currency, c.payment_method, c.status])
    return Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=contracts.csv'})


# ============================================================
#                     الإيجارات (Rents)
# ============================================================

@app.route('/rents')
@login_required
def rents_list():
    q = request.args.get('q', '').strip()
    month = request.args.get('month', '').strip()
    status = request.args.get('status', '').strip()
    query = RentPayment.query
    if q:
        query = query.filter(RentPayment.number.contains(q))
    if month:
        query = query.filter(RentPayment.month == month)
    if status == 'paid':
        query = query.filter(RentPayment.amount_paid >= RentPayment.amount_due)
    elif status == 'unpaid':
        query = query.filter(RentPayment.amount_paid < RentPayment.amount_due)
    items = query.order_by(RentPayment.month.desc(), RentPayment.id.desc()).all()

    total_due = sum(p.amount_due for p in items)
    total_paid = sum(p.amount_paid for p in items)
    total_remaining = total_due - total_paid
    months = sorted(set([p.month for p in RentPayment.query.all()]), reverse=True)

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>💵 الإيجارات ({{ items|length }})</h3>
      <div>
        <a href="{{ url_for('export_rents_csv') }}" class="btn btn-outline-success">📊 CSV</a>
        <a href="{{ url_for('rent_form') }}" class="btn btn-success">+ دفعة جديدة</a>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="stat-card"><p>إجمالي المطلوب</p><h3>{{ "{:,.0f}".format(total_due) }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card green"><p>المحصّل</p><h3>{{ "{:,.0f}".format(total_paid) }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card red"><p>المتبقي</p><h3>{{ "{:,.0f}".format(total_remaining) }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-4">
          <input name="q" value="{{ q }}" class="form-control" placeholder="🔍 ابحث برقم الإيصال...">
        </div>
        <div class="col-md-3">
          <select name="month" class="form-select">
            <option value="">كل الأشهر</option>
            {% for m in months %}<option value="{{ m }}" {{ 'selected' if month==m }}>{{ m }}</option>{% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <select name="status" class="form-select">
            <option value="">الكل</option>
            <option value="paid" {{ 'selected' if status=='paid' }}>مدفوع</option>
            <option value="unpaid" {{ 'selected' if status=='unpaid' }}>غير مكتمل</option>
          </select>
        </div>
        <div class="col-md-2"><button class="btn btn-primary w-100">🔍</button></div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>الإيصال</th><th>الشهر</th><th>الشقة</th><th>المستأجر</th>
          <th>المطلوب</th><th>المدفوع</th><th>المتبقي</th><th>التاريخ</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for p in items %}
        <tr class="{{ 'table-success' if p.amount_paid >= p.amount_due else 'table-danger' }}">
          <td><b>{{ p.number }}</b></td>
          <td>{{ p.month }}</td>
          <td><b>{{ p.unit.number if p.unit else '-' }}</b></td>
          <td>{{ p.tenant.name if p.tenant else '-' }}</td>
          <td>{{ "{:,.0f}".format(p.amount_due) }}</td>
          <td class="text-success">{{ "{:,.0f}".format(p.amount_paid) }}</td>
          <td class="text-danger"><b>{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }}</b></td>
          <td>{{ p.payment_date or '-' }}</td>
          <td>
            <a href="{{ url_for('rent_print', id=p.id) }}" class="btn btn-sm btn-secondary"
               target="_blank"><i class="bi bi-printer"></i></a>
            <a href="{{ url_for('rent_form', id=p.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('rent_delete', id=p.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف الدفعة؟')"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="9" class="empty-state">
          <div class="icon">💵</div>
          <h5>لا توجد دفعات</h5>
          <a href="{{ url_for('rent_form') }}" class="btn btn-success">+ إضافة دفعة</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, month=month, status=status,
        total_due=total_due, total_paid=total_paid,
        total_remaining=total_remaining, months=months)


@app.route('/rents/new', methods=['GET', 'POST'])
@app.route('/rents/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def rent_form(id=None):
    p = RentPayment.query.get(id) if id else None
    contracts = Contract.query.filter_by(status='ساري').all()
    preselected_contract = request.args.get('contract_id')

    if request.method == 'POST':
        if not p:
            p = RentPayment(number=next_number(RentPayment, 'REC'))
            db.session.add(p)
        contract_id = int(request.form['contract_id'])
        c = Contract.query.get(contract_id)
        p.contract_id = contract_id
        p.tenant_id = c.tenant_id
        p.unit_id = c.unit_id
        p.month = request.form['month']
        p.amount_due = float(request.form.get('amount_due') or 0)
        p.amount_paid = float(request.form.get('amount_paid') or 0)
        if request.form.get('payment_date'):
            p.payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d').date()
        p.method = request.form.get('method', 'نقد')
        p.currency = c.currency
        p.notes = request.form.get('notes', '').strip()
        db.session.commit()
        log_activity('save_rent', f'دفعة: {p.number}')
        flash('✅ تم حفظ الدفعة', 'success')
        return redirect(url_for('rents_list'))

    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل دفعة' if p else '➕ دفعة إيجار جديدة' }}</h3>
      <a href="{{ url_for('rents_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-12">
          <label>العقد <span class="text-danger">*</span></label>
          <select name="contract_id" class="form-select" required id="contractSel">
            <option value="">-- اختر العقد --</option>
            {% for c in contracts %}
            <option value="{{ c.id }}"
                    data-rent="{{ c.monthly_rent }}"
                    data-currency="{{ c.currency }}"
                    {{ 'selected' if (p and p.contract_id==c.id) or (not p and preselected_contract==c.id|string) }}>
              {{ c.number }} - شقة {{ c.unit.number if c.unit else '' }} - {{ c.tenant.name if c.tenant else '' }}
              ({{ "{:,.0f}".format(c.monthly_rent) }} {{ c.currency }})
            </option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>الشهر <span class="text-danger">*</span></label>
          <input name="month" type="month" value="{{ p.month if p else '' }}" class="form-control" required>
        </div>
        <div class="col-md-4">
          <label>المبلغ المطلوب</label>
          <input name="amount_due" type="number" step="0.01"
                 value="{{ p.amount_due if p else 0 }}" class="form-control" id="dueInput">
        </div>
        <div class="col-md-4">
          <label>المبلغ المدفوع</label>
          <input name="amount_paid" type="number" step="0.01"
                 value="{{ p.amount_paid if p else 0 }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>تاريخ الدفع</label>
          <input name="payment_date" type="date"
                 value="{{ p.payment_date if p and p.payment_date else '' }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>طريقة الدفع</label>
          <select name="method" class="form-select">
            {% for m in ['نقد', 'تحويل بنكي', 'شيك'] %}
            <option {{ 'selected' if p and p.method==m }}>{{ m }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" class="form-control">{{ p.notes if p else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('rents_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>
    <script>
      document.getElementById('contractSel').addEventListener('change', function(e) {
        const opt = e.target.selectedOptions[0];
        const rent = opt.dataset.rent;
        if (rent) document.getElementById('dueInput').value = rent;
      });
    </script>''', p=p, contracts=contracts, preselected_contract=preselected_contract)


@app.route('/rents/<int:id>/print')
@login_required
def rent_print(id):
    p = RentPayment.query.get_or_404(id)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>إيصال {{ p.number }}</title>
      <link rel="stylesheet" href="''' + url_for('static', filename='css/bootstrap.rtl.min.css') + '''">
      <style>
        body { font-family: Tahoma, sans-serif; padding: 20px; }
        .receipt { max-width: 500px; margin: auto; border: 2px solid #1a3a5c; padding: 25px; border-radius: 10px; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px; }
        .row-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #ddd; }
        @media print { .no-print { display: none !important; } body { padding: 0; } }
      </style>
    </head>
    <body onload="window.print()">
      <div class="no-print text-center mb-3">
        <button onclick="window.print()" class="btn btn-primary">🖨️ طباعة</button>
        <button onclick="window.close()" class="btn btn-secondary">إغلاق</button>
      </div>
      <div class="receipt">
        <div class="header">
          <h2>🏢 {{ get_setting('tower_name', 'عمارة هيال') }}</h2>
          <p style="font-size:12px; margin: 4px 0;">{{ get_setting('tower_address', '') }}</p>
          <h4 style="margin-top: 15px;">إيصال استلام إيجار</h4>
        </div>
        <div class="row-item"><b>رقم الإيصال:</b> <span>{{ p.number }}</span></div>
        <div class="row-item"><b>التاريخ:</b> <span>{{ p.payment_date or p.created_at.strftime('%Y-%m-%d') }}</span></div>
        <div class="row-item"><b>الشهر:</b> <span>{{ p.month }}</span></div>
        <hr>
        <div class="row-item"><b>الشقة:</b> <span>{{ p.unit.number if p.unit else '-' }}</span></div>
        <div class="row-item"><b>المستأجر:</b> <span>{{ p.tenant.name if p.tenant else '-' }}</span></div>
        <div class="row-item"><b>الهاتف:</b> <span>{{ p.tenant.phone if p.tenant else '-' }}</span></div>
        <hr>
        <div class="row-item"><b>المبلغ المطلوب:</b> <span>{{ "{:,.0f}".format(p.amount_due) }} {{ p.currency }}</span></div>
        <div class="row-item" style="background: #d4edda; padding: 12px; border-radius: 6px;">
          <b style="color: #155724;">المبلغ المدفوع:</b>
          <span style="color: #155724; font-size: 20px; font-weight: bold;">{{ "{:,.0f}".format(p.amount_paid) }} {{ p.currency }}</span>
        </div>
        {% if p.amount_due - p.amount_paid > 0 %}
        <div class="row-item" style="background: #f8d7da; padding: 12px; border-radius: 6px;">
          <b style="color: #721c24;">المتبقي:</b>
          <span style="color: #721c24;">{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }} {{ p.currency }}</span>
        </div>
        {% endif %}
        <div class="row-item"><b>طريقة الدفع:</b> <span>{{ p.method }}</span></div>
        <div style="margin-top: 40px; text-align: center;">
          <p>شكراً لتعاملكم معنا 🌹</p>
        </div>
      </div>
    </body></html>''', p=p)


@app.route('/rents/<int:id>/delete')
@login_required
def rent_delete(id):
    p = RentPayment.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('rents_list'))


@app.route('/export/rents.csv')
@login_required
def export_rents_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['الرقم', 'الشهر', 'الشقة', 'المستأجر', 'المطلوب', 'المدفوع', 'المتبقي', 'التاريخ'])
    for p in RentPayment.query.all():
        w.writerow([p.number, p.month,
                    p.unit.number if p.unit else '',
                    p.tenant.name if p.tenant else '',
                    p.amount_due, p.amount_paid,
                    p.amount_due - p.amount_paid,
                    p.payment_date or ''])
    return Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=rents.csv'})


# ============================================================
#                     الخدمات (كهرباء/ماء)
# ============================================================

@app.route('/utilities')
@login_required
def utilities_list():
    q = request.args.get('q', '').strip()
    month = request.args.get('month', '').strip()
    stype = request.args.get('type', '').strip()
    status = request.args.get('status', '').strip()
    query = UtilityBill.query
    if q:
        query = query.filter(UtilityBill.number.contains(q))
    if month:
        query = query.filter(UtilityBill.month == month)
    if stype:
        query = query.filter(UtilityBill.service_type == stype)
    if status:
        query = query.filter(UtilityBill.status == status)
    items = query.order_by(UtilityBill.month.desc(), UtilityBill.id.desc()).all()

    total_electric = sum(b.total for b in items if b.service_type == 'كهرباء')
    total_water = sum(b.total for b in items if b.service_type == 'ماء')
    unpaid_total = sum(b.total for b in items if b.status != 'مدفوع')
    months = sorted(set([b.month for b in UtilityBill.query.all()]), reverse=True)

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>💡 فواتير الخدمات (كهرباء / ماء)</h3>
      <div>
        <a href="{{ url_for('export_utilities_csv') }}" class="btn btn-outline-success">📊 CSV</a>
        <a href="{{ url_for('utility_form') }}" class="btn btn-success">+ فاتورة جديدة</a>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="stat-card orange"><p>⚡ إجمالي الكهرباء</p><h3>{{ "{:,.0f}".format(total_electric) }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card cyan"><p>💧 إجمالي الماء</p><h3>{{ "{:,.0f}".format(total_water) }}</h3></div></div>
      <div class="col-md-4"><div class="stat-card red"><p>💰 غير مدفوع</p><h3>{{ "{:,.0f}".format(unpaid_total) }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-4"><input name="q" value="{{ q }}" class="form-control" placeholder="🔍 بحث..."></div>
        <div class="col-md-2"><select name="month" class="form-select">
          <option value="">كل الأشهر</option>
          {% for m in months %}<option value="{{ m }}" {{ 'selected' if month==m }}>{{ m }}</option>{% endfor %}
        </select></div>
        <div class="col-md-2"><select name="type" class="form-select">
          <option value="">النوع</option>
          <option value="كهرباء" {{ 'selected' if stype=='كهرباء' }}>⚡ كهرباء</option>
          <option value="ماء" {{ 'selected' if stype=='ماء' }}>💧 ماء</option>
        </select></div>
        <div class="col-md-2"><select name="status" class="form-select">
          <option value="">الحالة</option>
          <option value="مدفوع" {{ 'selected' if status=='مدفوع' }}>مدفوع</option>
          <option value="غير مدفوع" {{ 'selected' if status=='غير مدفوع' }}>غير مدفوع</option>
        </select></div>
        <div class="col-md-2"><button class="btn btn-primary w-100">🔍</button></div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>الرقم</th><th>الشقة</th><th>النوع</th><th>الشهر</th>
          <th>الاستهلاك</th><th>الإجمالي</th><th>الحالة</th><th>الصورة</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for b in items %}
        <tr class="{{ 'table-success' if b.status=='مدفوع' else '' }}">
          <td><b>{{ b.number }}</b></td>
          <td><b>{{ b.unit.number if b.unit else '-' }}</b></td>
          <td>{% if b.service_type == 'كهرباء' %}<span class="badge bg-warning">⚡ كهرباء</span>{% else %}<span class="badge bg-info">💧 ماء</span>{% endif %}</td>
          <td>{{ b.month }}</td>
          <td>{{ b.consumption }}</td>
          <td><b>{{ "{:,.0f}".format(b.total) }}</b></td>
          <td>{% if b.status == 'مدفوع' %}<span class="badge bg-success">مدفوع</span>{% else %}<span class="badge bg-danger">غير مدفوع</span>{% endif %}</td>
          <td>
            {% if b.image %}
              <a href="{{ url_for('uploaded_file', filename=b.image) }}" target="_blank">
                <img src="{{ url_for('uploaded_file', filename=b.image) }}"
                     style="width:40px;height:40px;object-fit:cover;border-radius:4px;">
              </a>
            {% else %}<span class="text-muted">-</span>{% endif %}
          </td>
          <td>
            <a href="{{ url_for('utility_print', id=b.id) }}" class="btn btn-sm btn-secondary" target="_blank"><i class="bi bi-printer"></i></a>
            <a href="{{ url_for('utility_form', id=b.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('utility_delete', id=b.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف الفاتورة؟')"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="9" class="empty-state">
          <div class="icon">💡</div>
          <h5>لا توجد فواتير</h5>
          <a href="{{ url_for('utility_form') }}" class="btn btn-success">+ إضافة فاتورة</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, month=month, stype=stype, status=status,
        total_electric=total_electric, total_water=total_water,
        unpaid_total=unpaid_total, months=months)


@app.route('/utilities/new', methods=['GET', 'POST'])
@app.route('/utilities/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def utility_form(id=None):
    b = UtilityBill.query.get(id) if id else None
    units = Unit.query.order_by(Unit.number).all()

    if request.method == 'POST':
        if not b:
            b = UtilityBill(number=next_number(UtilityBill, 'UTL'))
            db.session.add(b)
        b.unit_id = int(request.form['unit_id'])
        b.service_type = request.form['service_type']
        b.month = request.form['month']
        b.prev_reading = float(request.form.get('prev_reading') or 0)
        b.curr_reading = float(request.form.get('curr_reading') or 0)
        b.consumption = b.curr_reading - b.prev_reading
        b.unit_price = float(request.form.get('unit_price') or 0)
        b.total = b.consumption * b.unit_price
        b.status = request.form.get('status', 'غير مدفوع')
        if request.form.get('paid_date'):
            b.paid_date = datetime.strptime(request.form['paid_date'], '%Y-%m-%d').date()
        b.notes = request.form.get('notes', '').strip()

        file = request.files.get('image')
        if file and file.filename:
            filename = f"bill_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            b.image = filename

        db.session.commit()
        log_activity('save_utility', f'فاتورة: {b.number}')
        flash('✅ تم حفظ الفاتورة', 'success')
        return redirect(url_for('utilities_list'))

    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل فاتورة' if b else '➕ فاتورة خدمة جديدة' }}</h3>
      <a href="{{ url_for('utilities_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post" enctype="multipart/form-data">
      <div class="row g-3">
        <div class="col-md-4">
          <label>الشقة <span class="text-danger">*</span></label>
          <select name="unit_id" class="form-select" required>
            <option value="">-- اختر الشقة --</option>
            {% for u in units %}
            <option value="{{ u.id }}" {{ 'selected' if b and b.unit_id==u.id }}>شقة {{ u.number }} - طابق {{ u.floor }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>نوع الخدمة <span class="text-danger">*</span></label>
          <select name="service_type" class="form-select" required>
            <option value="كهرباء" {{ 'selected' if b and b.service_type=='كهرباء' }}>⚡ كهرباء</option>
            <option value="ماء" {{ 'selected' if b and b.service_type=='ماء' }}>💧 ماء</option>
          </select>
        </div>
        <div class="col-md-4">
          <label>الشهر <span class="text-danger">*</span></label>
          <input name="month" type="month" value="{{ b.month if b else '' }}" class="form-control" required>
        </div>
        <div class="col-md-3">
          <label>القراءة السابقة</label>
          <input name="prev_reading" type="number" step="0.01"
                 value="{{ b.prev_reading if b else 0 }}" class="form-control" id="prevR">
        </div>
        <div class="col-md-3">
          <label>القراءة الحالية</label>
          <input name="curr_reading" type="number" step="0.01"
                 value="{{ b.curr_reading if b else 0 }}" class="form-control" id="currR">
        </div>
        <div class="col-md-3">
          <label>سعر الوحدة</label>
          <input name="unit_price" type="number" step="0.01"
                 value="{{ b.unit_price if b else 0 }}" class="form-control" id="unitP">
        </div>
        <div class="col-md-3">
          <label>الإجمالي</label>
          <input name="total" type="number" step="0.01" value="{{ b.total if b else 0 }}"
                 class="form-control" id="totalInp" readonly style="background:#f0f0f0;">
          <small class="help-text">يُحسب = استهلاك × سعر</small>
        </div>
        <div class="col-md-6">
          <label>الحالة</label>
          <select name="status" class="form-select">
            <option value="غير مدفوع" {{ 'selected' if b and b.status=='غير مدفوع' }}>غير مدفوع</option>
            <option value="مدفوع" {{ 'selected' if b and b.status=='مدفوع' }}>مدفوع</option>
          </select>
        </div>
        <div class="col-md-6">
          <label>تاريخ الدفع (إن مدفوع)</label>
          <input name="paid_date" type="date" value="{{ b.paid_date if b and b.paid_date else '' }}" class="form-control">
        </div>
        <div class="col-12">
          <label>صورة الفاتورة</label>
          <input name="image" type="file" class="form-control" accept="image/*">
          {% if b and b.image %}
          <small class="text-muted">
            الصورة الحالية:
            <a href="{{ url_for('uploaded_file', filename=b.image) }}" target="_blank">عرض</a>
          </small>
          {% endif %}
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" class="form-control">{{ b.notes if b else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('utilities_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>
    <script>
      function calcTotal() {
        const p = parseFloat(document.getElementById('prevR').value) || 0;
        const c = parseFloat(document.getElementById('currR').value) || 0;
        const u = parseFloat(document.getElementById('unitP').value) || 0;
        const total = (c - p) * u;
        document.getElementById('totalInp').value = total > 0 ? total.toFixed(2) : 0;
      }
      document.getElementById('prevR').addEventListener('input', calcTotal);
      document.getElementById('currR').addEventListener('input', calcTotal);
      document.getElementById('unitP').addEventListener('input', calcTotal);
    </script>''', b=b, units=units)


@app.route('/utilities/<int:id>/print')
@login_required
def utility_print(id):
    b = UtilityBill.query.get_or_404(id)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>فاتورة {{ b.number }}</title>
      <link rel="stylesheet" href="''' + url_for('static', filename='css/bootstrap.rtl.min.css') + '''">
      <style>
        body { font-family: Tahoma, sans-serif; padding: 20px; }
        .bill { max-width: 550px; margin: auto; border: 2px solid #1a3a5c; padding: 25px; border-radius: 10px; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px; }
        .row-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #ddd; }
        @media print { .no-print { display: none !important; } body { padding: 0; } }
      </style>
    </head>
    <body onload="window.print()">
      <div class="no-print text-center mb-3">
        <button onclick="window.print()" class="btn btn-primary">🖨️ طباعة</button>
        <button onclick="window.close()" class="btn btn-secondary">إغلاق</button>
      </div>
      <div class="bill">
        <div class="header">
          <h2>🏢 {{ get_setting('tower_name', 'عمارة هيال') }}</h2>
          <h4>فاتورة {{ b.service_type }}</h4>
        </div>
        <div class="row-item"><b>رقم الفاتورة:</b> <span>{{ b.number }}</span></div>
        <div class="row-item"><b>الشهر:</b> <span>{{ b.month }}</span></div>
        <div class="row-item"><b>الشقة:</b> <span>{{ b.unit.number if b.unit else '-' }}</span></div>
        <hr>
        <div class="row-item"><b>القراءة السابقة:</b> <span>{{ b.prev_reading }}</span></div>
        <div class="row-item"><b>القراءة الحالية:</b> <span>{{ b.curr_reading }}</span></div>
        <div class="row-item"><b>الاستهلاك:</b> <span>{{ b.consumption }}</span></div>
        <div class="row-item"><b>سعر الوحدة:</b> <span>{{ "{:,.2f}".format(b.unit_price) }}</span></div>
        <div class="row-item" style="background:#fff3cd; padding:12px; border-radius:6px;">
          <b>الإجمالي:</b>
          <span style="font-size:22px; font-weight:bold;">{{ "{:,.0f}".format(b.total) }}</span>
        </div>
        <div class="row-item"><b>الحالة:</b>
          <span class="badge bg-{{ 'success' if b.status=='مدفوع' else 'danger' }}">{{ b.status }}</span>
        </div>
        {% if b.image %}
        <div style="margin-top:20px; text-align:center;">
          <img src="{{ url_for('uploaded_file', filename=b.image) }}" style="max-width:100%; border-radius:8px;">
        </div>
        {% endif %}
        <div style="margin-top:30px; text-align:center; color:#666;">
          <p>شكراً لتعاملكم معنا 🌹</p>
        </div>
      </div>
    </body></html>''', b=b)


@app.route('/utilities/<int:id>/delete')
@login_required
def utility_delete(id):
    b = UtilityBill.query.get_or_404(id)
    try:
        if b.image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], b.image))
    except:
        pass
    db.session.delete(b)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('utilities_list'))


@app.route('/export/utilities.csv')
@login_required
def export_utilities_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['الرقم', 'الشقة', 'النوع', 'الشهر', 'الاستهلاك', 'السعر', 'الإجمالي', 'الحالة'])
    for b in UtilityBill.query.all():
        w.writerow([b.number, b.unit.number if b.unit else '',
                    b.service_type, b.month, b.consumption,
                    b.unit_price, b.total, b.status])
    return Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=utilities.csv'})


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# ============================================================
#                     الصيانة (Maintenance)
# ============================================================

@app.route('/maintenance')
@login_required
def maintenance_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    priority = request.args.get('priority', '').strip()
    query = MaintenanceRequest.query
    if q:
        query = query.filter(MaintenanceRequest.number.contains(q))
    if status:
        query = query.filter(MaintenanceRequest.status == status)
    if priority:
        query = query.filter(MaintenanceRequest.priority == priority)
    items = query.order_by(MaintenanceRequest.id.desc()).all()

    new_count = MaintenanceRequest.query.filter_by(status='جديد').count()
    inprogress = MaintenanceRequest.query.filter_by(status='قيد التنفيذ').count()
    done_count = MaintenanceRequest.query.filter_by(status='مكتمل').count()
    total_cost = db.session.query(func.coalesce(func.sum(MaintenanceRequest.cost), 0)).scalar()

    return render('''
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>🔧 الصيانة ({{ items|length }})</h3>
      <a href="{{ url_for('maintenance_form') }}" class="btn btn-success">+ طلب صيانة جديد</a>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-3"><div class="stat-card orange"><p>جديدة</p><h3>{{ new_count }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card purple"><p>قيد التنفيذ</p><h3>{{ inprogress }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card green"><p>مكتملة</p><h3>{{ done_count }}</h3></div></div>
      <div class="col-md-3"><div class="stat-card red"><p>إجمالي التكلفة</p><h3>{{ "{:,.0f}".format(total_cost) }}</h3></div></div>
    </div>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-6">
          <input name="q" value="{{ q }}" class="form-control" placeholder="🔍 بحث برقم الطلب...">
        </div>
        <div class="col-md-3">
          <select name="status" class="form-select">
            <option value="">كل الحالات</option>
            {% for s in ['جديد', 'قيد التنفيذ', 'مكتمل'] %}
            <option value="{{ s }}" {{ 'selected' if status==s }}>{{ s }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <select name="priority" class="form-select">
            <option value="">كل الأولويات</option>
            {% for p in ['عادي', 'مستعجل', 'طارئ'] %}
            <option value="{{ p }}" {{ 'selected' if priority==p }}>{{ p }}</option>
            {% endfor %}
          </select>
        </div>
      </form>
    </div></div>

    <div class="card">
      <table class="table mb-0">
        <thead><tr>
          <th>الرقم</th><th>الشقة</th><th>النوع</th><th>الأولوية</th>
          <th>الحالة</th><th>التكلفة</th><th>تاريخ الطلب</th><th>إجراءات</th>
        </tr></thead>
        <tbody>
        {% for m in items %}
        <tr>
          <td><b>{{ m.number }}</b></td>
          <td><b>{{ m.unit.number if m.unit else '-' }}</b></td>
          <td>{{ m.category }}</td>
          <td>
            <span class="badge bg-{{ 'danger' if m.priority=='طارئ' else ('warning' if m.priority=='مستعجل' else 'secondary') }}">
              {{ m.priority }}
            </span>
          </td>
          <td>
            <span class="badge bg-{{ 'success' if m.status=='مكتمل' else ('warning' if m.status=='قيد التنفيذ' else 'secondary') }}">
              {{ m.status }}
            </span>
          </td>
          <td>{{ "{:,.0f}".format(m.cost) }}</td>
          <td>{{ m.request_date }}</td>
          <td>
            <a href="{{ url_for('maintenance_form', id=m.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
            <a href="{{ url_for('maintenance_delete', id=m.id) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('حذف الطلب؟')"><i class="bi bi-trash"></i></a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="8" class="empty-state">
          <div class="icon">🔧</div>
          <h5>لا توجد طلبات صيانة</h5>
          <a href="{{ url_for('maintenance_form') }}" class="btn btn-success">+ طلب جديد</a>
        </td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    ''', items=items, q=q, status=status, priority=priority,
        new_count=new_count, inprogress=inprogress, done_count=done_count,
        total_cost=total_cost)


@app.route('/maintenance/new', methods=['GET', 'POST'])
@app.route('/maintenance/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def maintenance_form(id=None):
    m = MaintenanceRequest.query.get(id) if id else None
    units = Unit.query.order_by(Unit.number).all()
    tenants = Tenant.query.filter_by(active=True).all()

    if request.method == 'POST':
        if not m:
            m = MaintenanceRequest(number=next_number(MaintenanceRequest, 'MNT'))
            db.session.add(m)
        m.unit_id = int(request.form['unit_id'])
        m.tenant_id = int(request.form['tenant_id']) if request.form.get('tenant_id') else None
        m.category = request.form['category']
        m.description = request.form.get('description', '').strip()
        m.priority = request.form.get('priority', 'عادي')
        m.technician = request.form.get('technician', '').strip()
        m.cost = float(request.form.get('cost') or 0)
        m.status = request.form.get('status', 'جديد')
        if request.form.get('request_date'):
            m.request_date = datetime.strptime(request.form['request_date'], '%Y-%m-%d').date()
        if request.form.get('done_date'):
            m.done_date = datetime.strptime(request.form['done_date'], '%Y-%m-%d').date()
        m.notes = request.form.get('notes', '').strip()
        db.session.commit()
        log_activity('save_maintenance', f'طلب صيانة: {m.number}')
        flash('✅ تم الحفظ', 'success')
        return redirect(url_for('maintenance_list'))

    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>{{ '✏️ تعديل طلب صيانة' if m else '➕ طلب صيانة جديد' }}</h3>
      <a href="{{ url_for('maintenance_list') }}" class="btn btn-secondary">← رجوع</a>
    </div>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6">
          <label>الشقة <span class="text-danger">*</span></label>
          <select name="unit_id" class="form-select" required>
            <option value="">-- اختر الشقة --</option>
            {% for u in units %}
            <option value="{{ u.id }}" {{ 'selected' if m and m.unit_id==u.id }}>
              شقة {{ u.number }} - الطابق {{ u.floor }}
            </option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>المستأجر (اختياري)</label>
          <select name="tenant_id" class="form-select">
            <option value="">-- بدون --</option>
            {% for t in tenants %}
            <option value="{{ t.id }}" {{ 'selected' if m and m.tenant_id==t.id }}>{{ t.name }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>نوع المشكلة <span class="text-danger">*</span></label>
          <select name="category" class="form-select" required>
            {% for cat in ['كهرباء', 'سباكة', 'تكييف', 'نجارة', 'دهان', 'أقفال', 'مصعد', 'نظافة', 'أخرى'] %}
            <option {{ 'selected' if m and m.category==cat }}>{{ cat }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>الأولوية</label>
          <select name="priority" class="form-select">
            {% for p in ['عادي', 'مستعجل', 'طارئ'] %}
            <option {{ 'selected' if m and m.priority==p }}>{{ p }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4">
          <label>الحالة</label>
          <select name="status" class="form-select">
            {% for s in ['جديد', 'قيد التنفيذ', 'مكتمل'] %}
            <option {{ 'selected' if m and m.status==s }}>{{ s }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-12">
          <label>وصف المشكلة</label>
          <textarea name="description" rows="3" class="form-control">{{ m.description if m else '' }}</textarea>
        </div>
        <div class="col-md-4">
          <label>الفني / المُصلح</label>
          <input name="technician" value="{{ m.technician if m else '' }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>التكلفة</label>
          <input name="cost" type="number" step="0.01" value="{{ m.cost if m else 0 }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>تاريخ الطلب</label>
          <input name="request_date" type="date"
                 value="{{ m.request_date if m and m.request_date else '' }}" class="form-control">
        </div>
        <div class="col-md-4">
          <label>تاريخ الإنجاز</label>
          <input name="done_date" type="date"
                 value="{{ m.done_date if m and m.done_date else '' }}" class="form-control">
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" class="form-control">{{ m.notes if m else '' }}</textarea>
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-success btn-lg">💾 حفظ</button>
        <a href="{{ url_for('maintenance_list') }}" class="btn btn-secondary btn-lg">إلغاء</a>
      </div>
    </form></div>''', m=m, units=units, tenants=tenants)


@app.route('/maintenance/<int:id>/delete')
@login_required
def maintenance_delete(id):
    m = MaintenanceRequest.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('maintenance_list'))


# ============================================================
#                     الموظفين (Staff)
# ============================================================

@app.route('/staff')
@login_required
def staff_list():
    items = Staff.query.order_by(Staff.name).all()
    total_salary = sum(s.salary for s in items if s.active)
    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>👷 الموظفين ({{ items|length }})</h3>
      <a href="{{ url_for('staff_form') }}" class="btn btn-success">+ موظف جديد</a>
    </div>
    <div class="row g-3 mb-3">
      <div class="col-md-6"><div class="stat-card"><p>إجمالي الموظفين</p><h3>{{ items|length }}</h3></div></div>
      <div class="col-md-6"><div class="stat-card green"><p>إجمالي الرواتب</p><h3>{{ "{:,.0f}".format(total_salary) }}</h3></div></div>
    </div>
    <div class="card"><table class="table mb-0">
      <thead><tr><th>#</th><th>الاسم</th><th>الوظيفة</th><th>الهاتف</th><th>الراتب</th><th>الحالة</th><th>إجراءات</th></tr></thead>
      <tbody>
      {% for s in items %}
      <tr class="{{ '' if s.active else 'table-secondary' }}">
        <td>{{ s.id }}</td>
        <td><b>{{ s.name }}</b></td>
        <td><span class="badge bg-info">{{ s.job }}</span></td>
        <td>{{ s.phone or '-' }}</td>
        <td>{{ "{:,.0f}".format(s.salary) }}</td>
        <td>{% if s.active %}<span class="badge bg-success">نشط</span>{% else %}<span class="badge bg-secondary">غير نشط</span>{% endif %}</td>
        <td>
          <a href="{{ url_for('staff_form', id=s.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
          <a href="{{ url_for('staff_delete', id=s.id) }}" class="btn btn-sm btn-danger"
             onclick="return confirm('حذف الموظف؟')"><i class="bi bi-trash"></i></a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="7" class="empty-state">
        <div class="icon">👷</div>
        <h5>لا يوجد موظفين</h5>
        <a href="{{ url_for('staff_form') }}" class="btn btn-success">+ إضافة موظف</a>
      </td></tr>
      {% endfor %}
      </tbody>
    </table></div>''', items=items, total_salary=total_salary)


@app.route('/staff/new', methods=['GET', 'POST'])
@app.route('/staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def staff_form(id=None):
    s = Staff.query.get(id) if id else None
    if request.method == 'POST':
        if not s:
            s = Staff()
            db.session.add(s)
        s.name = request.form['name'].strip()
        s.job = request.form.get('job', '').strip()
        s.phone = request.form.get('phone', '').strip()
        s.salary = float(request.form.get('salary') or 0)
        if request.form.get('hire_date'):
            s.hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date()
        s.active = request.form.get('active') == 'on'
        s.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('✅ تم الحفظ', 'success')
        return redirect(url_for('staff_list'))
    return render('''
    <h3>{{ '✏️ تعديل موظف' if s else '➕ موظف جديد' }}</h3>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6">
          <label>الاسم *</label>
          <input name="name" value="{{ s.name if s else '' }}" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label>الوظيفة</label>
          <select name="job" class="form-select">
            {% for j in ['حارس', 'عامل نظافة', 'فني كهرباء', 'فني سباكة', 'فني مصعد', 'أخرى'] %}
            <option {{ 'selected' if s and s.job==j }}>{{ j }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label>الهاتف</label>
          <input name="phone" value="{{ s.phone if s else '' }}" class="form-control" placeholder="777777777">
        </div>
        <div class="col-md-6">
          <label>الراتب الشهري</label>
          <input name="salary" type="number" step="0.01" value="{{ s.salary if s else 0 }}" class="form-control">
        </div>
        <div class="col-md-6">
          <label>تاريخ التعيين</label>
          <input name="hire_date" type="date" value="{{ s.hire_date if s and s.hire_date else '' }}" class="form-control">
        </div>
        <div class="col-md-6">
          <label class="form-check mt-4">
            <input type="checkbox" name="active" class="form-check-input" {{ 'checked' if not s or s.active }}>
            موظف نشط
          </label>
        </div>
        <div class="col-12">
          <label>ملاحظات</label>
          <textarea name="notes" class="form-control">{{ s.notes if s else '' }}</textarea>
        </div>
      </div>
      <div class="mt-3">
        <button class="btn btn-success">💾 حفظ</button>
        <a href="{{ url_for('staff_list') }}" class="btn btn-secondary">إلغاء</a>
      </div>
    </form></div>''', s=s)


@app.route('/staff/<int:id>/delete')
@login_required
def staff_delete(id):
    s = Staff.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('staff_list'))


# ============================================================
#                     المصروفات (Expenses)
# ============================================================

@app.route('/expenses')
@login_required
def expenses_list():
    q = request.args.get('q', '').strip()
    cat = request.args.get('cat', '').strip()
    query = Expense.query
    if q:
        query = query.filter(Expense.description.contains(q))
    if cat:
        query = query.filter(Expense.category == cat)
    items = query.order_by(Expense.id.desc()).all()
    total = sum(e.amount for e in items)
    categories = [c[0] for c in db.session.query(Expense.category).distinct().all() if c[0]]

    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>💸 المصروفات - الإجمالي: {{ "{:,.0f}".format(total) }}</h3>
      <a href="{{ url_for('expense_form') }}" class="btn btn-success">+ مصروف جديد</a>
    </div>
    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-6"><input name="q" value="{{ q }}" class="form-control" placeholder="🔍 بحث..."></div>
        <div class="col-md-4"><select name="cat" class="form-select">
          <option value="">كل الفئات</option>
          {% for c in categories %}<option value="{{ c }}" {{ 'selected' if cat==c }}>{{ c }}</option>{% endfor %}
        </select></div>
        <div class="col-md-2"><button class="btn btn-primary w-100">🔍</button></div>
      </form>
    </div></div>
    <div class="card"><table class="table mb-0">
      <thead><tr><th>#</th><th>التاريخ</th><th>الفئة</th><th>الوصف</th><th>المبلغ</th><th>إجراءات</th></tr></thead>
      <tbody>
      {% for e in items %}
      <tr>
        <td>{{ e.id }}</td>
        <td>{{ e.date.strftime('%Y-%m-%d') }}</td>
        <td><span class="badge bg-secondary">{{ e.category }}</span></td>
        <td>{{ e.description or '-' }}</td>
        <td class="text-danger"><b>{{ "{:,.0f}".format(e.amount) }}</b> {{ e.currency }}</td>
        <td>
          <a href="{{ url_for('expense_delete', id=e.id) }}" class="btn btn-sm btn-danger"
             onclick="return confirm('حذف؟')"><i class="bi bi-trash"></i></a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="6" class="empty-state">
        <div class="icon">💸</div>
        <h5>لا توجد مصروفات</h5>
        <a href="{{ url_for('expense_form') }}" class="btn btn-success">+ إضافة</a>
      </td></tr>
      {% endfor %}
      </tbody>
    </table></div>''', items=items, q=q, cat=cat, total=total, categories=categories)


@app.route('/expenses/new', methods=['GET', 'POST'])
@login_required
def expense_form():
    if request.method == 'POST':
        e = Expense(category=request.form['category'],
                    description=request.form.get('description', ''),
                    amount=float(request.form.get('amount') or 0),
                    currency=request.form.get('currency', 'ر.ي'))
        db.session.add(e)
        db.session.commit()
        log_activity('create_expense', f'مصروف: {e.amount}')
        flash('💸 تم التسجيل', 'success')
        return redirect(url_for('expenses_list'))
    return render('''
    <h3>💸 مصروف جديد</h3>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6"><label>الفئة *</label>
          <select name="category" class="form-select" required>
            <option>كهرباء عامة</option>
            <option>ماء عام</option>
            <option>نظافة</option>
            <option>رواتب</option>
            <option>صيانة عامة</option>
            <option>مصعد</option>
            <option>أخرى</option>
          </select></div>
        <div class="col-md-4"><label>المبلغ *</label>
          <input name="amount" type="number" step="0.01" class="form-control" required></div>
        <div class="col-md-2"><label>العملة</label>
          <select name="currency" class="form-select">
            {% for cur in ['ر.ي', 'ر.س', 'د.إ', '$'] %}<option>{{ cur }}</option>{% endfor %}
          </select></div>
        <div class="col-12"><label>الوصف</label>
          <textarea name="description" class="form-control"></textarea></div>
      </div>
      <div class="mt-3">
        <button class="btn btn-success">💾 حفظ</button>
        <a href="{{ url_for('expenses_list') }}" class="btn btn-secondary">إلغاء</a>
      </div>
    </form></div>''')


@app.route('/expenses/<int:id>/delete')
@login_required
def expense_delete(id):
    e = Expense.query.get_or_404(id)
    db.session.delete(e)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('expenses_list'))


# ============================================================
#                     التقارير (Reports)
# ============================================================

@app.route('/reports')
@login_required
def reports():
    from_date = request.args.get('from', (date.today().replace(day=1)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to', date.today().strftime('%Y-%m-%d'))
    try:
        fd = datetime.strptime(from_date, '%Y-%m-%d')
        td = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        fd = datetime.combine(date.today().replace(day=1), datetime.min.time())
        td = datetime.now()

    rents = RentPayment.query.filter(RentPayment.payment_date.between(fd.date(), td.date())).all()
    total_rent = sum(r.amount_paid for r in rents)

    utilities = UtilityBill.query.filter(UtilityBill.status == 'مدفوع').all()
    total_utilities = sum(u.total for u in utilities)

    expenses_total = db.session.query(func.coalesce(func.sum(Expense.amount), 0))\
        .filter(Expense.date.between(fd, td)).scalar()

    profit = total_rent - expenses_total

    total_units = Unit.query.count()
    occupied = Unit.query.filter_by(status='مسكونة').count()
    occupancy_rate = (occupied / total_units * 100) if total_units > 0 else 0

    top_units = db.session.query(
        Unit.number, func.sum(RentPayment.amount_paid)
    ).join(RentPayment, RentPayment.unit_id == Unit.id)\
        .filter(RentPayment.payment_date.between(fd.date(), td.date()))\
        .group_by(Unit.id).order_by(func.sum(RentPayment.amount_paid).desc()).limit(10).all()

    unpaid_list = RentPayment.query.filter(RentPayment.amount_paid < RentPayment.amount_due).all()
    total_unpaid = sum(p.amount_due - p.amount_paid for p in unpaid_list)

    return render('''
    <h3 class="mb-3">📊 التقارير والإحصائيات</h3>

    <div class="card mb-3"><div class="card-body">
      <form class="row g-2">
        <div class="col-md-4"><label>من تاريخ</label>
          <input type="date" name="from" value="{{ from_date }}" class="form-control"></div>
        <div class="col-md-4"><label>إلى تاريخ</label>
          <input type="date" name="to" value="{{ to_date }}" class="form-control"></div>
        <div class="col-md-4 d-flex align-items-end">
          <button class="btn btn-primary w-100">🔄 تحديث</button>
        </div>
      </form>
    </div></div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="stat-card green">
        <p>💰 إجمالي الإيرادات</p><h3>{{ "{:,.0f}".format(total_rent) }}</h3>
        <small>من {{ rents|length }} دفعة</small>
      </div></div>
      <div class="col-md-4"><div class="stat-card red">
        <p>💸 إجمالي المصروفات</p><h3>{{ "{:,.0f}".format(expenses_total) }}</h3>
      </div></div>
      <div class="col-md-4"><div class="stat-card {{ 'green' if profit >= 0 else 'red' }}">
        <p>📈 صافي الربح</p><h3>{{ "{:,.0f}".format(profit) }}</h3>
      </div></div>
      <div class="col-md-4"><div class="stat-card cyan">
        <p>📊 نسبة الإشغال</p><h3>{{ "%.0f"|format(occupancy_rate) }}%</h3>
        <small>{{ occupied }} من {{ total_units }} شقة</small>
      </div></div>
      <div class="col-md-4"><div class="stat-card orange">
        <p>⚠️ المتأخرات</p><h3>{{ "{:,.0f}".format(total_unpaid) }}</h3>
        <small>{{ unpaid_list|length }} دفعة متأخرة</small>
      </div></div>
      <div class="col-md-4"><div class="stat-card purple">
        <p>💡 خدمات مدفوعة</p><h3>{{ "{:,.0f}".format(total_utilities) }}</h3>
      </div></div>
    </div>

    <div class="card mb-3">
      <div class="card-header">🏆 أفضل 10 شقق تحصيلاً</div>
      <table class="table mb-0">
        <thead><tr><th>الشقة</th><th>إجمالي التحصيل</th></tr></thead>
        <tbody>
        {% for number, total in top_units %}
        <tr><td><b>شقة {{ number }}</b></td><td class="text-success">{{ "{:,.0f}".format(total) }}</td></tr>
        {% else %}
        <tr><td colspan="2" class="text-center text-muted py-3">لا توجد بيانات</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card mb-3">
      <div class="card-header bg-danger text-white">💸 المتأخرات ({{ unpaid_list|length }})</div>
      <table class="table mb-0">
        <thead><tr><th>الشهر</th><th>الشقة</th><th>المستأجر</th><th>المطلوب</th><th>المدفوع</th><th>المتبقي</th></tr></thead>
        <tbody>
        {% for p in unpaid_list %}
        <tr>
          <td>{{ p.month }}</td>
          <td>{{ p.unit.number if p.unit else '-' }}</td>
          <td>{{ p.tenant.name if p.tenant else '-' }}</td>
          <td>{{ "{:,.0f}".format(p.amount_due) }}</td>
          <td class="text-success">{{ "{:,.0f}".format(p.amount_paid) }}</td>
          <td class="text-danger"><b>{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }}</b></td>
        </tr>
        {% else %}
        <tr><td colspan="6" class="text-center text-muted py-3">✅ لا توجد متأخرات</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-header">📤 التصدير والنسخ الاحتياطي</div>
      <div class="card-body">
        <a href="{{ url_for('export_units_csv') }}" class="btn btn-success">🏢 الشقق</a>
        <a href="{{ url_for('export_tenants_csv') }}" class="btn btn-success">👥 المستأجرين</a>
        <a href="{{ url_for('export_contracts_csv') }}" class="btn btn-success">📝 العقود</a>
        <a href="{{ url_for('export_rents_csv') }}" class="btn btn-success">💵 الإيجارات</a>
        <a href="{{ url_for('export_utilities_csv') }}" class="btn btn-success">💡 الخدمات</a>
        <a href="{{ url_for('download_backup') }}" class="btn btn-primary">💾 نسخة احتياطية</a>
      </div>
    </div>
    ''', from_date=from_date, to_date=to_date,
        total_rent=total_rent, expenses_total=expenses_total, profit=profit,
        total_units=total_units, occupied=occupied, occupancy_rate=occupancy_rate,
        top_units=top_units, unpaid_list=unpaid_list, total_unpaid=total_unpaid,
        total_utilities=total_utilities, rents=rents)


# ============================================================
#                     التنبيهات (Alerts)
# ============================================================

@app.route('/alerts')
@login_required
def alerts():
    today = date.today()
    future = date.fromordinal(today.toordinal() + 30)

    expiring = Contract.query.filter(
        Contract.status == 'ساري',
        Contract.end_date <= future,
        Contract.end_date >= today
    ).order_by(Contract.end_date).all()

    late_rents = RentPayment.query.filter(
        RentPayment.amount_paid < RentPayment.amount_due).all()

    open_maintenance = MaintenanceRequest.query.filter(
        MaintenanceRequest.status != 'مكتمل').all()

    unpaid_utilities = UtilityBill.query.filter_by(status='غير مدفوع').all()

    empty_units = Unit.query.filter_by(status='فارغة').all()

    return render('''
    <h3 class="mb-3">🔔 التنبيهات الذكية</h3>
    <p class="text-muted">افتح هذه الصفحة كل صباح لمعرفة ما يحتاج انتباهك</p>

    <div class="row g-3">
      <div class="col-md-6"><div class="card">
        <div class="card-header bg-warning">⚠️ عقود تنتهي قريباً ({{ expiring|length }})</div>
        <table class="table mb-0">
          <thead><tr><th>الشقة</th><th>المستأجر</th><th>تاريخ الانتهاء</th></tr></thead>
          <tbody>
          {% for c in expiring %}
          <tr>
            <td><b>{{ c.unit.number if c.unit else '-' }}</b></td>
            <td>{{ c.tenant.name if c.tenant else '-' }}</td>
            <td class="text-danger">{{ c.end_date }}</td>
          </tr>
          {% else %}<tr><td colspan="3" class="text-center text-muted py-3">✅ لا توجد</td></tr>{% endfor %}
          </tbody>
        </table>
      </div></div>

      <div class="col-md-6"><div class="card">
        <div class="card-header bg-danger text-white">💸 إيجارات متأخرة ({{ late_rents|length }})</div>
        <table class="table mb-0">
          <thead><tr><th>الشقة</th><th>المستأجر</th><th>المتبقي</th></tr></thead>
          <tbody>
          {% for p in late_rents %}
          <tr>
            <td><b>{{ p.unit.number if p.unit else '-' }}</b></td>
            <td>{{ p.tenant.name if p.tenant else '-' }}</td>
            <td class="text-danger"><b>{{ "{:,.0f}".format(p.amount_due - p.amount_paid) }}</b></td>
          </tr>
          {% else %}<tr><td colspan="3" class="text-center text-muted py-3">✅ لا توجد</td></tr>{% endfor %}
          </tbody>
        </table>
      </div></div>

      <div class="col-md-6"><div class="card">
        <div class="card-header bg-info text-white">🔧 صيانة مفتوحة ({{ open_maintenance|length }})</div>
        <table class="table mb-0">
          <thead><tr><th>الرقم</th><th>الشقة</th><th>النوع</th><th>الحالة</th></tr></thead>
          <tbody>
          {% for m in open_maintenance %}
          <tr>
            <td><a href="{{ url_for('maintenance_form', id=m.id) }}">{{ m.number }}</a></td>
            <td>{{ m.unit.number if m.unit else '-' }}</td>
            <td>{{ m.category }}</td>
            <td><span class="badge bg-warning">{{ m.status }}</span></td>
          </tr>
          {% else %}<tr><td colspan="4" class="text-center text-muted py-3">✅ لا توجد</td></tr>{% endfor %}
          </tbody>
        </table>
      </div></div>

      <div class="col-md-6"><div class="card">
        <div class="card-header bg-warning">⚡ فواتير غير مدفوعة ({{ unpaid_utilities|length }})</div>
        <table class="table mb-0">
          <thead><tr><th>الشقة</th><th>النوع</th><th>الشهر</th><th>المبلغ</th></tr></thead>
          <tbody>
          {% for b in unpaid_utilities %}
          <tr>
            <td><b>{{ b.unit.number if b.unit else '-' }}</b></td>
            <td>{{ b.service_type }}</td>
            <td>{{ b.month }}</td>
            <td class="text-danger">{{ "{:,.0f}".format(b.total) }}</td>
          </tr>
          {% else %}<tr><td colspan="4" class="text-center text-muted py-3">✅ لا توجد</td></tr>{% endfor %}
          </tbody>
        </table>
      </div></div>

      <div class="col-md-12"><div class="card">
        <div class="card-header bg-secondary text-white">🏢 شقق فارغة ({{ empty_units|length }})</div>
        <table class="table mb-0">
          <thead><tr><th>الشقة</th><th>الطابق</th><th>الغرف</th><th>الإيجار</th></tr></thead>
          <tbody>
          {% for u in empty_units %}
          <tr>
            <td><b>{{ u.number }}</b></td>
            <td>{{ u.floor }}</td>
            <td>{{ u.rooms }}</td>
            <td>{{ "{:,.0f}".format(u.monthly_rent) }} {{ u.currency }}</td>
          </tr>
          {% else %}<tr><td colspan="4" class="text-center text-muted py-3">✅ لا توجد شقق فارغة</td></tr>{% endfor %}
          </tbody>
        </table>
      </div></div>
    </div>
    ''', expiring=expiring, late_rents=late_rents,
        open_maintenance=open_maintenance, unpaid_utilities=unpaid_utilities,
        empty_units=empty_units)


# ============================================================
#                     الإعدادات (Settings)
# ============================================================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        for k in ['tower_name', 'tower_address', 'tower_phone',
                  'manager_name', 'manager_phone', 'currency']:
            set_setting(k, request.form.get(k, ''))
        flash('⚙️ تم حفظ الإعدادات', 'success')
        return redirect(url_for('settings'))
    return render('''
    <h3>⚙️ الإعدادات</h3>
    <div class="card p-4 mb-3"><form method="post">
      <h5>🏢 بيانات العمارة</h5><hr>
      <div class="row g-3">
        <div class="col-md-6"><label>اسم العمارة</label>
          <input name="tower_name" value="{{ get_setting('tower_name', 'عمارة هيال') }}" class="form-control"></div>
        <div class="col-md-6"><label>رقم الهاتف</label>
          <input name="tower_phone" value="{{ get_setting('tower_phone', '') }}" class="form-control"></div>
        <div class="col-12"><label>العنوان</label>
          <input name="tower_address" value="{{ get_setting('tower_address', '') }}" class="form-control"></div>
        <div class="col-md-6"><label>اسم الوكيل / المدير</label>
          <input name="manager_name" value="{{ get_setting('manager_name', '') }}" class="form-control"></div>
        <div class="col-md-6"><label>هاتف الوكيل</label>
          <input name="manager_phone" value="{{ get_setting('manager_phone', '') }}" class="form-control"></div>
        <div class="col-md-3"><label>العملة الافتراضية</label>
          <select name="currency" class="form-select">
            {% for cur in ['ر.ي', 'ر.س', 'د.إ', '$'] %}
            <option {{ 'selected' if get_setting('currency')==cur }}>{{ cur }}</option>
            {% endfor %}
          </select></div>
      </div>
      <div class="mt-3"><button class="btn btn-success btn-lg">💾 حفظ</button></div>
    </form></div>
    <div class="card p-4 mb-3"><h5>💾 النسخ الاحتياطي</h5><hr>
      <a href="{{ url_for('download_backup') }}" class="btn btn-primary">📥 تنزيل نسخة احتياطية</a>
    </div>
    <div class="card p-4"><h5>ℹ️ معلومات النظام</h5><hr>
      <p><b>الإصدار:</b> 1.0</p>
      <p><b>قاعدة البيانات:</b> <code>hayal_tower.db</code></p>
      <p><b>مجلد الصور:</b> <code>uploads/</code></p>
    </div>''')


@app.route('/backup')
@login_required
@admin_required
def download_backup():
    db_path = os.path.join(BASE_DIR, 'hayal_tower.db')
    if not os.path.exists(db_path):
        flash('❌ قاعدة البيانات غير موجودة', 'danger')
        return redirect(url_for('settings'))
    return send_from_directory(BASE_DIR, 'hayal_tower.db', as_attachment=True,
                                download_name=f'hayal_tower_{date.today()}.db')


# ============================================================
#                     الملف الشخصي
# ============================================================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    u = current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')
            if not check_password_hash(u.password, old):
                flash('❌ كلمة المرور الحالية خاطئة', 'danger')
            elif len(new) < 4:
                flash('❌ كلمة المرور الجديدة قصيرة', 'danger')
            elif new != confirm:
                flash('❌ كلمتا المرور غير متطابقتين', 'danger')
            else:
                u.password = generate_password_hash(new)
                db.session.commit()
                log_activity('change_password', 'تغيير كلمة المرور')
                flash('✅ تم تغيير كلمة المرور', 'success')
        elif action == 'update_info':
            u.full_name = request.form.get('full_name', '').strip()
            db.session.commit()
            flash('✅ تم التحديث', 'success')
        return redirect(url_for('profile'))
    return render('''
    <h3>👤 الملف الشخصي</h3>
    <div class="row g-3">
      <div class="col-md-6">
        <div class="card p-4"><h5>🔐 تغيير كلمة المرور</h5><hr>
          <form method="post"><input type="hidden" name="action" value="change_password">
            <div class="mb-3"><label>كلمة المرور الحالية</label>
              <input name="old_password" type="password" class="form-control" required></div>
            <div class="mb-3"><label>كلمة المرور الجديدة</label>
              <input name="new_password" type="password" class="form-control" required minlength="4"></div>
            <div class="mb-3"><label>تأكيد كلمة المرور</label>
              <input name="confirm_password" type="password" class="form-control" required minlength="4"></div>
            <button class="btn btn-warning w-100">🔐 تغيير</button>
          </form>
        </div>
        <div class="card p-4 mt-3"><h5>✏️ تعديل البيانات</h5><hr>
          <form method="post"><input type="hidden" name="action" value="update_info">
            <div class="mb-3"><label>الاسم الكامل</label>
              <input name="full_name" value="{{ u.full_name or '' }}" class="form-control"></div>
            <button class="btn btn-primary w-100">💾 حفظ</button>
          </form>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card p-4"><h5>ℹ️ معلومات الحساب</h5><hr>
          <p><b>اسم المستخدم:</b> {{ u.username }}</p>
          <p><b>الاسم الكامل:</b> {{ u.full_name or '-' }}</p>
          <p><b>الصلاحية:</b> <span class="badge bg-{{ 'danger' if u.role=='admin' else 'info' }}">{{ u.role }}</span></p>
          <p><b>معرف المستخدم:</b> #{{ u.id }}</p>
          <p><b>تاريخ الإنشاء:</b> {{ u.created_at.strftime('%Y-%m-%d') }}</p>
        </div>
      </div>
    </div>''', u=u)


# ============================================================
#                     إدارة المستخدمين
# ============================================================

@app.route('/users')
@login_required
@admin_required
def users_list():
    items = User.query.order_by(User.id).all()
    return render('''
    <div class="d-flex justify-content-between mb-3">
      <h3>👥 المستخدمين ({{ items|length }})</h3>
      <a href="{{ url_for('user_form') }}" class="btn btn-success">+ مستخدم جديد</a>
    </div>
    <div class="card"><table class="table mb-0">
      <thead><tr><th>#</th><th>اسم المستخدم</th><th>الاسم الكامل</th><th>الصلاحية</th><th>الحالة</th><th>إجراءات</th></tr></thead>
      <tbody>
      {% for u in items %}
      <tr>
        <td>{{ u.id }}</td><td><b>{{ u.username }}</b></td><td>{{ u.full_name or '-' }}</td>
        <td><span class="badge bg-{{ 'danger' if u.role=='admin' else 'info' }}">{{ u.role }}</span></td>
        <td>{% if u.active %}<span class="badge bg-success">نشط</span>{% else %}<span class="badge bg-secondary">معطل</span>{% endif %}</td>
        <td>
          <a href="{{ url_for('user_form', id=u.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-pencil"></i></a>
          {% if u.username != 'admin' %}
          <a href="{{ url_for('user_delete', id=u.id) }}" class="btn btn-sm btn-danger"
             onclick="return confirm('حذف؟')"><i class="bi bi-trash"></i></a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table></div>''')


@app.route('/users/new', methods=['GET', 'POST'])
@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_form(id=None):
    u = User.query.get(id) if id else None
    if request.method == 'POST':
        username = request.form['username'].strip()
        existing = User.query.filter(User.username == username).first()
        if existing and (not u or existing.id != u.id):
            flash('❌ اسم المستخدم موجود مسبقاً', 'danger')
            return redirect(url_for('user_form', id=id) if id else url_for('user_form'))
        if not u:
            u = User(username=username)
            db.session.add(u)
        u.username = username
        u.full_name = request.form.get('full_name', '').strip()
        u.role = request.form.get('role', 'manager')
        u.active = request.form.get('active') == 'on'
        pwd = request.form.get('password', '')
        if pwd:
            u.password = generate_password_hash(pwd)
        elif not id:
            flash('❌ كلمة المرور مطلوبة', 'danger')
            return redirect(url_for('user_form'))
        db.session.commit()
        flash('✅ تم الحفظ', 'success')
        return redirect(url_for('users_list'))
    return render('''
    <h3>{{ '✏️ تعديل مستخدم' if u else '➕ مستخدم جديد' }}</h3>
    <div class="card p-4"><form method="post">
      <div class="row g-3">
        <div class="col-md-6"><label>اسم المستخدم *</label>
          <input name="username" value="{{ u.username if u else '' }}" class="form-control" required></div>
        <div class="col-md-6"><label>الاسم الكامل</label>
          <input name="full_name" value="{{ u.full_name if u else '' }}" class="form-control"></div>
        <div class="col-md-6"><label>الصلاحية</label>
          <select name="role" class="form-select">
            <option value="admin" {{ 'selected' if u and u.role=='admin' }}>مدير عام</option>
            <option value="manager" {{ 'selected' if u and u.role=='manager' }}>مدير / وكيل</option>
            <option value="viewer" {{ 'selected' if u and u.role=='viewer' }}>مشاهدة فقط</option>
          </select></div>
        <div class="col-md-6">
          <label class="form-check mt-4">
            <input type="checkbox" name="active" class="form-check-input" {{ 'checked' if not u or u.active }}>
            نشط
          </label></div>
        <div class="col-12"><label>كلمة المرور {{ '(اتركها فارغة لعدم التغيير)' if u else '*' }}</label>
          <input name="password" type="password" class="form-control" {{ '' if u else 'required' }}></div>
      </div>
      <div class="mt-3"><button class="btn btn-success">💾 حفظ</button>
        <a href="{{ url_for('users_list') }}" class="btn btn-secondary">إلغاء</a></div>
    </form></div>''', u=u)


@app.route('/users/<int:id>/delete')
@login_required
@admin_required
def user_delete(id):
    u = User.query.get_or_404(id)
    if u.username == 'admin':
        flash('❌ لا يمكن حذف المدير الرئيسي', 'danger')
        return redirect(url_for('users_list'))
    if u.id == current_user().id:
        flash('❌ لا يمكنك حذف حسابك', 'danger')
        return redirect(url_for('users_list'))
    db.session.delete(u)
    db.session.commit()
    flash('🗑️ تم الحذف', 'warning')
    return redirect(url_for('users_list'))


# ============================================================
#                     سجل النشاط
# ============================================================

@app.route('/activity')
@login_required
@admin_required
def activity_log():
    items = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(500).all()
    return render('''
    <h3>📋 سجل النشاط (آخر 500)</h3>
    <div class="card"><table class="table mb-0">
      <thead><tr><th>#</th><th>التاريخ</th><th>المستخدم</th><th>الحركة</th><th>التفاصيل</th></tr></thead>
      <tbody>
      {% for a in items %}
      <tr>
        <td>{{ a.id }}</td>
        <td>{{ a.date.strftime('%Y-%m-%d %H:%M') }}</td>
        <td>{{ a.user.username if a.user else '-' }}</td>
        <td><span class="badge bg-secondary">{{ a.action }}</span></td>
        <td>{{ a.details or '-' }}</td>
      </tr>
      {% else %}
      <tr><td colspan="5" class="text-center text-muted py-4">لا يوجد سجل</td></tr>
      {% endfor %}
      </tbody>
    </table></div>''')


# ============================================================
#                     البحث العام
# ============================================================

@app.route('/search')
@login_required
def global_search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('dashboard'))

    units = Unit.query.filter(Unit.number.contains(q)).limit(10).all()
    tenants = Tenant.query.filter(or_(
        Tenant.name.contains(q), Tenant.phone.contains(q),
        Tenant.national_id.contains(q))).limit(10).all()
    contracts = Contract.query.filter(Contract.number.contains(q)).limit(10).all()
    rents = RentPayment.query.filter(RentPayment.number.contains(q)).limit(10).all()

    return render('''
    <h3>🔍 نتائج البحث عن: "<span class="text-warning">{{ q }}</span>"</h3>
    <hr>
    <div class="row g-3">
      <div class="col-md-6"><div class="card">
        <div class="card-header">🏢 الشقق ({{ units|length }})</div>
        <table class="table mb-0"><tbody>
          {% for u in units %}
          <tr><td>شقة {{ u.number }} - طابق {{ u.floor }}</td>
              <td><a href="{{ url_for('unit_profile', id=u.id) }}" class="btn btn-sm btn-info">عرض</a></td></tr>
          {% else %}<tr><td class="text-center text-muted py-3">لا نتائج</td></tr>{% endfor %}
        </tbody></table></div>
      </div>
      <div class="col-md-6"><div class="card">
        <div class="card-header">👥 المستأجرين ({{ tenants|length }})</div>
        <table class="table mb-0"><tbody>
          {% for t in tenants %}
          <tr><td>{{ t.name }} - {{ t.phone or '' }}</td>
              <td><a href="{{ url_for('tenant_profile', id=t.id) }}" class="btn btn-sm btn-info">عرض</a></td></tr>
          {% else %}<tr><td class="text-center text-muted py-3">لا نتائج</td></tr>{% endfor %}
        </tbody></table></div>
      </div>
      <div class="col-md-6"><div class="card">
        <div class="card-header">📝 العقود ({{ contracts|length }})</div>
        <table class="table mb-0"><tbody>
          {% for c in contracts %}
          <tr><td>{{ c.number }} - {{ c.tenant.name if c.tenant else '' }}</td>
              <td><a href="{{ url_for('contract_view', id=c.id) }}" class="btn btn-sm btn-info">عرض</a></td></tr>
          {% else %}<tr><td class="text-center text-muted py-3">لا نتائج</td></tr>{% endfor %}
        </tbody></table></div>
      </div>
      <div class="col-md-6"><div class="card">
        <div class="card-header">💵 الإيجارات ({{ rents|length }})</div>
        <table class="table mb-0"><tbody>
          {% for r in rents %}
          <tr><td>{{ r.number }} - {{ r.month }}</td>
              <td><a href="{{ url_for('rent_print', id=r.id) }}" class="btn btn-sm btn-info">عرض</a></td></tr>
          {% else %}<tr><td class="text-center text-muted py-3">لا نتائج</td></tr>{% endfor %}
        </tbody></table></div>
      </div>
    </div>''', q=q, units=units, tenants=tenants,
        contracts=contracts, rents=rents)


# ============================================================
#                     دليل الاستخدام
# ============================================================

@app.route('/help')
@login_required
def help_page():
    return render('''
    <h3>📖 دليل الاستخدام</h3>
    <p class="text-muted">تعليمات سريعة لكل واجهة</p>

    <div class="accordion mt-3" id="helpAcc">
      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button" data-bs-toggle="collapse" data-bs-target="#h1">
          🏢 الشقق - كيف أضيف الشقق؟
        </button>
      </h2><div id="h1" class="accordion-collapse collapse show" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ul>
            <li><b>رقم الشقة:</b> مثال: 101، 201، 301</li>
            <li><b>الطابق:</b> رقم الطابق (1-7)</li>
            <li><b>عدد الغرف:</b> 2، 3، 4</li>
            <li><b>المساحة:</b> بالمتر المربع</li>
            <li><b>الإيجار الشهري:</b> مثال: 50,000</li>
            <li><b>العملة:</b> ر.ي / ر.س / د.إ / $</li>
            <li><b>الحالة:</b> فارغة / مسكونة / صيانة</li>
            <li><b>شقة مستقبلية:</b> ضع علامة للشقق قيد الإنشاء</li>
          </ul>
        </div>
      </div></div>

      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#h2">
          👥 المستأجرين - ماذا أكتب؟
        </button>
      </h2><div id="h2" class="accordion-collapse collapse" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ul>
            <li><b>الاسم:</b> كامل الاسم</li>
            <li><b>رقم الهوية:</b> رقم البطاقة</li>
            <li><b>الهاتف:</b> 9 أرقام</li>
            <li><b>الوظيفة:</b> موظف / تاجر / طالب</li>
            <li><b>عدد الأسرة:</b> عدد السكان</li>
            <li><b>جهة الطوارئ:</b> اسم وهاتف شخص قريب</li>
          </ul>
        </div>
      </div></div>

      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#h3">
          📝 العقود - كيف أنشئ عقداً؟
        </button>
      </h2><div id="h3" class="accordion-collapse collapse" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ol>
            <li>اختر <b>المستأجر</b></li>
            <li>اختر <b>الشقة</b> (ستظهر الفارغة فقط)</li>
            <li>أدخل <b>تاريخ البداية والنهاية</b></li>
            <li>أدخل <b>الإيجار الشهري</b></li>
            <li>أدخل <b>الضمان</b></li>
            <li>اختر <b>طريقة الدفع</b></li>
            <li>احفظ → ستتحول حالة الشقة تلقائياً إلى "مسكونة"</li>
          </ol>
        </div>
      </div></div>

      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#h4">
          💵 الإيجارات - كيف أسجل دفعة؟
        </button>
      </h2><div id="h4" class="accordion-collapse collapse" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ol>
            <li>اختر <b>العقد</b></li>
            <li>اختر <b>الشهر</b> (مثال: 2026-01)</li>
            <li>المبلغ المطلوب <b>يُملأ تلقائياً</b></li>
            <li>أدخل <b>المبلغ المدفوع</b></li>
            <li>احفظ → يمكنك طباعة إيصال</li>
          </ol>
        </div>
      </div></div>

      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#h5">
          💡 الخدمات - فواتير الكهرباء والماء
        </button>
      </h2><div id="h5" class="accordion-collapse collapse" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ol>
            <li>اختر <b>الشقة</b></li>
            <li>اختر <b>النوع</b> (كهرباء / ماء)</li>
            <li>اختر <b>الشهر</b></li>
            <li>أدخل <b>القراءة السابقة والحالية</b></li>
            <li>أدخل <b>سعر الوحدة</b></li>
            <li>الإجمالي <b>يُحسب تلقائياً</b></li>
            <li>ارفع <b>صورة الفاتورة</b> (اختياري)</li>
            <li>احفظ → يمكنك طباعة الفاتورة</li>
          </ol>
        </div>
      </div></div>

      <div class="accordion-item"><h2 class="accordion-header">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#h6">
          💡 نصائح عامة
        </button>
      </h2><div id="h6" class="accordion-collapse collapse" data-bs-parent="#helpAcc">
        <div class="accordion-body">
          <ul>
            <li>استخدم <b>🔍 البحث السريع</b> في الأعلى</li>
            <li>اضغط <b>🌙</b> لتبديل الوضع الليلي</li>
            <li>خُذ <b>نسخة احتياطية</b> كل أسبوع</li>
            <li>افتح <b>التنبيهات</b> كل صباح</li>
            <li>اطبع <b>العقود والإيصالات</b> بضغطة واحدة</li>
          </ul>
        </div>
      </div></div>
    </div>''')


# ============================================================
#                     معالج الأخطاء
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render('''
    <div class="text-center" style="padding:60px;">
      <div style="font-size:80px;">🔍</div>
      <h2>الصفحة غير موجودة</h2>
      <a href="{{ url_for('dashboard') }}" class="btn btn-primary">← لوحة التحكم</a>
    </div>'''), 404


@app.errorhandler(500)
def server_error(e):
    return render('''
    <div class="text-center" style="padding:60px;">
      <div style="font-size:80px;">⚠️</div>
      <h2>حدث خطأ في السيرفر</h2>
      <a href="{{ url_for('dashboard') }}" class="btn btn-primary">← لوحة التحكم</a>
    </div>'''), 500


# ============================================================
#                     التشغيل + البيانات الأولية
# ============================================================

def create_initial_data():
    """إنشاء البيانات الأولية (مستخدمين + إعدادات + 22 شقة + موظفين)"""

    # المستخدمون
    if not User.query.filter_by(username='admin').first():
        db.session.add_all([
            User(username='admin', password=generate_password_hash('admin123'),
                 full_name='المدير العام', role='admin'),
            User(username='manager', password=generate_password_hash('123'),
                 full_name='الوكيل', role='manager'),
            User(username='viewer', password=generate_password_hash('123'),
                 full_name='مشاهد', role='viewer'),
        ])
        db.session.commit()

    # الإعدادات
    defaults = {
        'tower_name': 'عمارة هيال',
        'tower_address': '',
        'tower_phone': '',
        'manager_name': '',
        'manager_phone': '',
        'currency': 'ر.ي',
    }
    for k, v in defaults.items():
        if not Setting.query.filter_by(key=k).first():
            db.session.add(Setting(key=k, value=v))
    db.session.commit()

    # 22 شقة
    if Unit.query.count() == 0:
        units_data = [
            ('101', 1, 3, 120, 50000, False),
            ('102', 1, 3, 120, 50000, False),
            ('201', 2, 3, 130, 55000, False),
            ('202', 2, 3, 130, 55000, False),
            ('203', 2, 2, 100, 45000, False),
            ('204', 2, 2, 100, 45000, False),
            ('301', 3, 3, 130, 55000, False),
            ('302', 3, 3, 130, 55000, False),
            ('303', 3, 2, 100, 45000, False),
            ('304', 3, 2, 100, 45000, False),
            ('401', 4, 3, 130, 55000, False),
            ('402', 4, 3, 130, 55000, False),
            ('403', 4, 2, 100, 45000, False),
            ('404', 4, 2, 100, 45000, False),
            ('501', 5, 3, 130, 55000, False),
            ('502', 5, 3, 130, 55000, False),
            ('503', 5, 2, 100, 45000, False),
            ('504', 5, 2, 100, 45000, False),
            ('601', 6, 3, 130, 55000, True),
            ('602', 6, 3, 130, 55000, True),
            ('701', 7, 3, 130, 55000, True),
            ('702', 7, 3, 130, 55000, True),
        ]
        for number, floor, rooms, area, rent, future in units_data:
            db.session.add(Unit(
                number=number, floor=floor, rooms=rooms,
                area_sqm=area, monthly_rent=rent, currency='ر.ي',
                status='فارغة', future=future
            ))
        db.session.commit()

    # موظفين افتراضيين
    if Staff.query.count() == 0:
        db.session.add_all([
            Staff(name='حارس العمارة', job='حارس', salary=40000, active=True),
            Staff(name='عامل النظافة', job='عامل نظافة', salary=30000, active=True),
        ])
        db.session.commit()


with app.app_context():
    db.create_all()
    create_initial_data()


if __name__ == '__main__':
    print("=" * 60)
    print("  🏢 عمارة هيال - HAYAL TOWER")
    print("=" * 60)
    print("  النظام يعمل على: http://127.0.0.1:5000")
    print("  المستخدم: admin | كلمة المرور: admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)