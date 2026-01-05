# blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User, ActivationCode
from datetime import datetime, timezone

# 定义蓝图
auth_bp = Blueprint('auth', __name__)


# --- 2. 路由：系统功能（登录/退出/注册） ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # 简单的“创建”逻辑
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('auth.register'))
        
        new_user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit() # --- 新增逻辑：更新最后登录时间 ---
            return redirect(url_for('content.index'))
        flash('登录失败，请检查用户名或密码', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('content.index'))

# ---验证激活码 ---
@auth_bp.route('/activate', methods=['GET', 'POST'])
def activate():
    if request.method == 'POST':
        input_code = request.form.get('activation_code')
        # 查询数据库中是否存在该激活码且未被使用
        code_entry = ActivationCode.query.filter_by(code=input_code, is_used=False).first()
        
        if code_entry:
            # 验证成功，将激活码存入 session，并跳转到下一步
            session['valid_code'] = input_code
            return redirect(url_for('auth.register_account'))
        else:
            flash('激活码无效或已被使用', 'danger')
    return render_template('activate.html') # 对应 image_57fa65.jpg 的样式

# --- 创建账户 ---
@auth_bp.route('/register-account', methods=['GET', 'POST'])
def register_account():
    # 安全检查：如果没有经过激活码验证，不准访问此页面
    valid_code = session.get('valid_code')
    if not valid_code:
        return redirect(url_for('auth.activate'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 创建付费用户逻辑
        new_user = User(
            username=username, 
            password_hash=generate_password_hash(password),
            is_paid=True # 拿到码注册的直接就是付费用户
        )
        
        # 标记激活码为已使用
        code_entry = ActivationCode.query.filter_by(code=valid_code).first()
        code_entry.is_used = True
        code_entry.used_by_username = username
        
        db.session.add(new_user)
        db.session.commit()
        
        session.pop('valid_code') # 注册完清除 session
        flash('账号激活并注册成功！请登录。', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register_account.html')
