from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from extensions import db
from models import User, ActivationCode, GuideContent, Category, Tag
import uuid
from functools import wraps
import google.generativeai as genai
import json
# 定义蓝图
admin_bp = Blueprint('admin', __name__)

# 配置 API Key
genai.configure(api_key="AIzaSyAlM1VnwDZ2h_8AuoGAtBGK0Ya-ht0Sv2k") 
model = genai.GenerativeModel('gemini-flash-latest')

# --- 1. 先定义自定义装饰器 ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 确保用户已登录且是管理员
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('您没有权限访问管理后台', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- 新增：AI 润色接口 ---
@admin_bp.route('/ai-polish', methods=['POST'])
@login_required
@admin_required
def ai_polish():
    data = request.json
    title = data.get('title')
    
    if not title:
        return {"status": "error", "message": "请先输入标题"}, 400

    prompt = f"""
    你是一名资深的心理学编辑。请根据标题《{title}》创作一篇专业的心理指南。
    要求：
    1. 风格：治愈、专业、易懂。
    2. 输出格式必须为 JSON，包含：
       - summary: 100字以内的摘要。
       - content: Markdown格式的正文，包含背景、建议和练习。
    请直接输出 JSON，不要包含 ```json 标签。
    """
    
    try:
        response = model.generate_content(prompt)
        # 清理并解析 AI 返回的内容
        print("AI响应：", response.text)
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw_text)

        return {"status": "success", "summary": result['summary'], "content": result['content']}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# --- 2. 定义路由函数 ---

# 1、后台主页：展示统计数据
@admin_bp.route('/')
@login_required
@admin_required
def admin_index():
    user_count = User.query.filter_by(is_admin=False).count()
    guide_count = GuideContent.query.count()
    # 注意：这里你可以决定是使用 dashboard.html 还是 admin.html
    return render_template('admin/dashboard.html', user_count=user_count, guide_count=guide_count)

# 2、用户与激活码管理
@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter_by(is_admin=False).all()
    codes = ActivationCode.query.order_by(ActivationCode.created_at.desc()).all()
    return render_template('admin/users.html', users=users, codes=codes)

# 3、心理指南管理列表
@admin_bp.route('/guides')
@login_required
@admin_required
def manage_guides():
    guides = GuideContent.query.order_by(GuideContent.updated_at.desc()).all()
    return render_template('admin/guides.html', guides=guides)

# 4、审批用户权限
@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_paid = not user.is_paid 
    db.session.commit()
    flash(f'已成功更新用户 {user.username} 的权限', 'success')
    # AJAX 要求返回 JSON 而不是 redirect
    return {
        "status": "success", 
        "is_paid": user.is_paid,
        "username": user.username
    }

# 2. 新增：发布新指南逻辑
@admin_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_guide():
    if request.method == 'POST':
        new_guide = GuideContent(
            title=request.form.get('title'),
            summary=request.form.get('summary'),
            content=request.form.get('content'),
            cover_image_url=request.form.get('cover_image_url'),
            category_id=request.form.get('category_id'),
            is_published=True # 默认发布
        )
        # 处理标签
        tag_ids = request.form.getlist('tags')
        new_guide.tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        
        db.session.add(new_guide)
        db.session.commit()
        flash('✨ 新指南已成功发布！', 'success')
        return redirect(url_for('admin.manage_guides'))
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/add.html', categories=categories, tags=tags)

# 5、批量生成激活码
@admin_bp.route('/generate-codes', methods=['POST'])
@login_required
@admin_required
def generate_codes():
    for _ in range(10):
        random_code = str(uuid.uuid4())[:8].upper()
        if not ActivationCode.query.filter_by(code=random_code).first():
            db.session.add(ActivationCode(code=random_code))
    db.session.commit()
    flash('成功生成 10 个新激活码！', 'success')
    return redirect(url_for('admin.manage_users'))

# 编辑指南内容
@admin_bp.route('/edit/<int:guide_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_guide(guide_id):
    guide = GuideContent.query.get_or_404(guide_id)
    if request.method == 'POST':
        guide.title = request.form.get('title')
        guide.summary = request.form.get('summary')
        guide.content = request.form.get('content')
        guide.cover_image_url = request.form.get('cover_image_url')
        guide.category_id = request.form.get('category_id')
        
        tag_ids = request.form.getlist('tags')
        guide.tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        
        db.session.commit()
        flash(f'指南《{guide.title}》已更新！', 'success')
        return redirect(url_for('admin.manage_guides'))
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/edit.html', guide=guide, categories=categories, tags=tags)