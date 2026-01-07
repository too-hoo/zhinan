# blueprints/admin.py
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask import current_app
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import User, ActivationCode, GuideContent, Category, Tag
import uuid, re
from functools import wraps
import google.generativeai as genai
import json
from utils.oss_helper import OssHelper

# 定义蓝图
admin_bp = Blueprint('admin', __name__)

# 强制加载 .env 文件
load_dotenv()

# 配置 API Key
api_key = os.getenv("GEMINI_API_KEY")
# 调试打印：在终端看看读到的是不是新 Key
genai.configure(api_key=api_key) 
model = genai.GenerativeModel('gemini-flash-latest')

oss_helper = OssHelper()

# 1--- 先定义自定义装饰器 ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 确保用户已登录且是管理员
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('您没有权限访问管理后台', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# 2--- 新增：AI 润色接口 ---
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
        # 1. 使用正则表达式从 AI 的回答中提取第一个 { 到最后一个 } 之间的内容
        # 这样即使 AI 返回了额外的解释文字，也能准确拿到 JSON 块
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        
        if match:
            raw_text = match.group()
            
            # 2. 关键修复：设置 strict=False
            # 这允许 json 库解析包含原生换行符和制表符的“不规范”JSON 字符串
            result = json.loads(raw_text, strict=False)
            
            return {
                "status": "success", 
                "summary": result.get('summary', ''), 
                "content": result.get('content', '')
            }
        else:
            return {"status": "error", "message": "AI 返回的内容格式不正确"}, 500
            
    except Exception as e:
        # 打印错误到终端方便调试
        print(f"AI 解析错误详情: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


# 3、后台主页：展示统计数据
@admin_bp.route('/')
@login_required
@admin_required
def admin_index():
    user_count = User.query.filter_by(is_admin=False).count()
    guide_count = GuideContent.query.count()
    # 注意：这里你可以决定是使用 dashboard.html 还是 admin.html
    return render_template('admin/dashboard.html', user_count=user_count, guide_count=guide_count)

# 4、用户与激活码管理
@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter_by(is_admin=False).all()
    codes = ActivationCode.query.order_by(ActivationCode.created_at.desc()).all()
    return render_template('admin/users.html', users=users, codes=codes)

# 5、心理指南管理列表
@admin_bp.route('/guides')
@login_required
@admin_required
def manage_guides():
    guides = GuideContent.query.order_by(GuideContent.updated_at.desc()).all()
    return render_template('admin/guides.html', guides=guides)

# 6、审批用户权限
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

# 7 设置允许上传的图片格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 8. 新增：发布新指南逻辑
@admin_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_guide():
    if request.method == 'POST':
        # 获取表单数据
        title = request.form.get('title')
        summary = request.form.get('summary')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        
        # 1. 处理封面图上传 (设为公共读)
        cover_url = request.form.get('cover_image_url') # 手动链接
        file = request.files.get('cover_file') # 本地文件
        
        if file and file.filename != '':
            # 调用助手类上传到 OSS，默认存入 images 目录
            cover_url = oss_helper.upload_file(file, folder='images', is_private=False)

        # 2. 保存到数据库
        new_guide = GuideContent(
            title=title,
            summary=summary,
            content=content,
            cover_image_url=cover_url,
            category_id=category_id
        )
        db.session.add(new_guide)
        db.session.commit()
        
        flash('🎉 指南已成功发布并同步至阿里云 OSS！', 'success')
        return redirect(url_for('admin.manage_guides'))
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/add.html', categories=categories, tags=tags)

# 9、批量生成激活码
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


#10 编辑指南内容
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

# 11
@admin_bp.route('/materials')
@login_required
@admin_required
def material_center():
    # 直接渲染新页面即可，里面的数据由你之前写好的 API 动态加载
    return render_template('admin/materials.html')


# 12 前端可以通过 AJAX 获取不同类型的素材数据
@admin_bp.route('/api/my-media-system/<string:media_type>')
@login_required
def get_materials(media_type):
    # 根据类型映射到 OSS 文件夹
    folder_map = {
        'video': 'video/',
        'audio': 'audio/',
        'material': 'material/',
        'image': 'images/'
    }
    prefix = folder_map.get(media_type, 'my-media-system/')
    files = oss_helper.list_files(prefix=prefix)
    return jsonify({'success': True, 'files': files})

# 13
@admin_bp.route('/api/upload_material', methods=['POST'])
@login_required
def upload_material_api():
    file = request.files.get('file')
    media_type = request.form.get('type') # 获取当前所在分类（video/audio/image/material）
    
    if not file:
        return jsonify({'success': False, 'message': '未选择文件'})

    # 这里的 folder_map 必须与你之前修正后的 OSS 目录一致
    folder_map = {
        'video': 'video/',
        'audio': 'audio/',
        'image': 'images/',
        'material': 'material/'
    }
    target_folder = folder_map.get(media_type, 'material/')

    try:
        # 调用你已经完善好的 oss_helper 上传逻辑
        # 它会自动处理 Content-Type 和 Cache-Control
        file_url = oss_helper.upload_file(file, folder=target_folder)
        return jsonify({'success': True, 'url': file_url})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 14
@admin_bp.route('/api/delete_material', methods=['POST'])
@login_required
def delete_material():
    # 单个删除，获取前端传来的完整路径
    data = request.get_json()
    oss_path = data.get('path')
    
    if not oss_path:
        return jsonify({'success': False, 'message': '缺少文件路径'})

    try:
        # 执行删除
        oss_helper.delete_file(oss_path)
        return jsonify({'success': True, 'message': '文件已永久删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 15
@admin_bp.route('/api/delete_materials', methods=['POST'])
@login_required
def delete_materials():
    # 批量删除
    data = request.get_json()
    oss_paths = data.get('paths', []) # 接收路径列表
    
    if not oss_paths:
        return jsonify({'success': False, 'message': '未选择任何文件'})

    try:
        oss_helper.delete_files(oss_paths)
        return jsonify({'success': True, 'message': f'成功删除 {len(oss_paths)} 个素材'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})