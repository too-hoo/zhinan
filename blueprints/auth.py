# blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User, ActivationCode
from datetime import datetime, timezone
import re

# 定义蓝图
auth_bp = Blueprint('auth', __name__)


# --- 2. 路由：系统功能（登录/退出/注册） ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # 安全检查：如果没有经过激活码验证，不准访问此页面
    valid_code = session.get('valid_code')
    if not valid_code:
        return redirect(url_for('auth.activate'))
    return render_template('activate.html') # 对应 image_57fa65.jpg 的样式

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        user = User.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit() # --- 新增逻辑：更新最后登录时间 ---
            return redirect(url_for('content.index'))
        flash('登录失败，请检查手机号或密码', 'danger')
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
        phone = request.form.get('phone')
        username = request.form.get('username')
        password = request.form.get('password')

        # 1. 手机号正则验证：必须是国内 11 位手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            flash('请输入有效的 11 位手机号', 'danger')
            return redirect(request.url)
        
        # 2. 检查手机号是否已被注册
        if User.query.filter_by(phone=phone).first():
            # 将用户的is_paid变成true
            User.query.filter_by(phone=phone).first().is_paid = True
            # 标记激活码为已使用
            code_entry = ActivationCode.query.filter_by(code=valid_code).first()
            code_entry.is_used = True
            code_entry.used_by_username = User.query.filter_by(phone=phone).first().username
            db.session.commit()
            session.pop('valid_code') # 注册完清除 session
            flash('该手机号已被注册，账号已激活，请直接登录', 'warning')
            return redirect(url_for('auth.login'))
        
        # 创建付费用户逻辑
        new_user = User(
            phone=phone,
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
