# blueprints/admin/guides.py 管理后台指南内容管理控制
import os, re, json
import google.generativeai as genai
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from extensions import db
from models import GuideContent, Category, Tag
from utils.oss_helper import OssHelper
from . import admin_required

# 定义子蓝图
guides_bp = Blueprint('admin_guides', __name__, url_prefix='/guides')
oss_helper = OssHelper()

# 配置 Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY")) 
model = genai.GenerativeModel('gemini-flash-latest')

@guides_bp.route('/')
@login_required
@admin_required
def manage_guides():
    # 增加分页逻辑，每页显示 10 条指南
    page = request.args.get('page', 1, type=int)
    pagination = GuideContent.query.order_by(GuideContent.updated_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/guides.html', guides=pagination.items, pagination=pagination)

@guides_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_guide():
    if request.method == 'POST':
        title = request.form.get('title')
        summary = request.form.get('summary')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        
        cover_url = request.form.get('cover_image_url')
        file = request.files.get('cover_file')
        
        if file and file.filename != '':
            cover_url = oss_helper.upload_file(file, folder='images', is_private=False)

        # 核心改进：如果没有上传也没有填链接，给一个系统默认图
        if not cover_url:
            cover_url = "https://my-media-system.oss-cn-beijing.aliyuncs.com/images/default_cover.jpg"
            

        new_guide = GuideContent(
            title=title, summary=summary, content=content,
            cover_image_url=cover_url, category_id=category_id
        )
        db.session.add(new_guide)
        db.session.commit()
        flash('🎉 指南已成功发布！', 'success')
        return redirect(url_for('admin.admin_guides.manage_guides')) # 注意路径
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/add.html', categories=categories, tags=tags)

# 编辑指南内容
@guides_bp.route('/edit/<int:guide_id>', methods=['GET', 'POST'])
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
        
        return redirect(url_for('admin.admin_guides.manage_guides'))
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/edit.html', guide=guide, categories=categories, tags=tags)

@guides_bp.route('/ai-polish', methods=['POST'])
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