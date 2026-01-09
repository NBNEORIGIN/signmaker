"""Authentication module for SignMaker."""
import os
from datetime import datetime
from functools import wraps

from flask import redirect, url_for, request
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import get_db, dict_cursor, DATABASE_URL

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


class User(UserMixin):
    """User model for authentication."""
    
    def __init__(self, id, email, password_hash, role='user', created_at=None, last_login=None):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at
        self.last_login = last_login
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        cur = dict_cursor(conn)
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        cur.execute(f"SELECT * FROM users WHERE id = {placeholder}", (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            row = dict(row)
            return User(
                id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row.get('role', 'user'),
                created_at=row.get('created_at'),
                last_login=row.get('last_login')
            )
        return None
    
    @staticmethod
    def get_by_email(email):
        conn = get_db()
        cur = dict_cursor(conn)
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        cur.execute(f"SELECT * FROM users WHERE email = {placeholder}", (email,))
        row = cur.fetchone()
        conn.close()
        if row:
            row = dict(row)
            return User(
                id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row.get('role', 'user'),
                created_at=row.get('created_at'),
                last_login=row.get('last_login')
            )
        return None
    
    @staticmethod
    def create(email, password, role='user'):
        conn = get_db()
        cur = conn.cursor()
        password_hash = generate_password_hash(password)
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        
        try:
            cur.execute(f"""
                INSERT INTO users (email, password_hash, role)
                VALUES ({placeholder}, {placeholder}, {placeholder})
            """, (email, password_hash, role))
            conn.commit()
            conn.close()
            return User.get_by_email(email)
        except Exception as e:
            conn.close()
            raise e
    
    @staticmethod
    def update_last_login(user_id):
        conn = get_db()
        cur = conn.cursor()
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        cur.execute(f"""
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = {placeholder}
        """, (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def all():
        conn = get_db()
        cur = dict_cursor(conn)
        cur.execute("SELECT id, email, role, created_at, last_login FROM users ORDER BY email")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def delete(user_id):
        conn = get_db()
        cur = conn.cursor()
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        cur.execute(f"DELETE FROM users WHERE id = {placeholder}", (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_password(user_id, new_password):
        conn = get_db()
        cur = conn.cursor()
        password_hash = generate_password_hash(new_password)
        is_postgres = DATABASE_URL.startswith("postgres")
        placeholder = "%s" if is_postgres else "?"
        cur.execute(f"""
            UPDATE users SET password_hash = {placeholder} WHERE id = {placeholder}
        """, (password_hash, user_id))
        conn.commit()
        conn.close()


def init_users_table():
    """Initialize users table in database."""
    conn = get_db()
    cur = conn.cursor()
    
    is_postgres = DATABASE_URL.startswith("postgres")
    id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def init_admin_user():
    """Create initial admin user if it doesn't exist."""
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not admin_email or not admin_password:
        print("Warning: ADMIN_EMAIL and ADMIN_PASSWORD not set. Skipping admin user creation.")
        return
    
    existing = User.get_by_email(admin_email)
    if not existing:
        try:
            User.create(admin_email, admin_password, role='admin')
            print(f"Admin user created: {admin_email}")
        except Exception as e:
            print(f"Error creating admin user: {e}")
    else:
        print(f"Admin user already exists: {admin_email}")


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
