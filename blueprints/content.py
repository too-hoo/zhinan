# blueprints/content.py 首页指南内容控制
import re, markdown
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import Category, Tag, GuideContent
from extensions import db
from flask import Blueprint, render_template
from utils.oss_helper import OssHelper

oss_helper = OssHelper()

# 定义蓝图
content_bp = Blueprint('content', __name__)

# --- 路由：资料权限鉴定 ---
@content_bp.route('/')
@login_required
def index():
    return render_template('index.html') # 或者创建一个简单的 index.html

@content_bp.route('/guides')
@login_required
def list_guides():
    # 1. 鉴权逻辑保持不变
    if not current_user.is_paid:
        return render_template('no_permission.html')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    cat_id = request.args.get('category_id', type=int)
    tag_id = request.args.get('tag_id', type=int)
    search_q = request.args.get('q', '')

    query = GuideContent.query.filter_by(is_published=True)

    # 逻辑过滤保持不变
    if search_q:
        query = query.filter(GuideContent.title.contains(search_q) | GuideContent.summary.contains(search_q))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if tag_id:
        query = query.join(GuideContent.tags).filter(Tag.id == tag_id)

    # --- 核心修改：使用 paginate 代替 all() ---
    # per_page 设置为每页显示的条数，例如 6 条（配合瀑布流布局）
    pagination = query.order_by(GuideContent.created_at.desc()).paginate(page=page, per_page=10)
    guides = pagination.items  # 当前页的数据对象列表

    categories = Category.query.order_by(Category.sort_order.asc()).all()
    tags = Tag.query.all()

    return render_template('content/list.html', 
                            guides=guides, 
                            pagination=pagination, # 必须传入分页对象以渲染翻页按钮
                            categories=categories, 
                            tags=tags,
                            current_cat=cat_id,
                            current_tag=tag_id,
                            search_q=search_q)

@content_bp.route('/guide/<int:guide_id>')
@login_required
def show_guide(guide_id):
    # 如果用户未登录，跳转并提醒
    if not current_user.is_authenticated:
        flash('🔑 这是一个深度指南，请登录后继续阅读', 'info')
        return redirect(url_for('auth.login', next=request.path))

    guide = GuideContent.query.get_or_404(guide_id)
    
    # 权限检查（虽然 list 页面有拦截，但详情页入口也要守住）
    if not current_user.is_paid:
        return render_template('no_permission.html', guide=guide)

    # 阅读数自增
    guide.view_count += 1
    db.session.commit()

    # 1. 修复正则匹配 Bug：防止把引号 " 或括号 ) 匹配进 URL
    domain = f"{oss_helper.bucket_name}.{oss_helper.endpoint.replace('https://', '').replace('http://', '')}"
    # 修改点：在 [^...] 中增加了 \" 和 \'，确保匹配到引号就停止
    oss_pattern = rf"https?://{re.escape(domain)}/[^\s\)\?\"']+"
    
    def sign_match(match):
        raw_url = match.group(0)
        return oss_helper.get_signed_url(raw_url)

    # 先进行签名替换
    signed_content = re.sub(oss_pattern, sign_match, guide.content)

    # 2. 将 Markdown 转换为 HTML
    # 增加 extensions 以支持表格、代码块等高级语法
    html_content = markdown.markdown(signed_content, extensions=[
        'fenced_code', 
        'tables', 
        'nl2br',  # 自动换行
        'toc'     # 自动生成目录（可选）
    ])

    # 3. 处理封面签名
    signed_cover = oss_helper.get_signed_url(guide.cover_image_url)

    related_guides = GuideContent.query.filter(
        GuideContent.category_id == guide.category_id,
        GuideContent.id != guide_id,
        GuideContent.is_published == True
    ).order_by(db.func.random()).limit(3).all()
    
    return render_template('content/detail.html', 
                            guide=guide, 
                            content=html_content, # 传出转换后的 HTML
                            cover=signed_cover,
                            related_guides=related_guides)

@content_bp.route('/like/<int:guide_id>', methods=['POST'])
@login_required
def like_guide(guide_id):
    guide = GuideContent.query.get_or_404(guide_id)
    guide.like_count += 1
    db.session.commit()
    return {"status": "success", "new_count": guide.like_count} # 返回 JSON 给前端

@content_bp.route('/favorite/<int:guide_id>', methods=['POST'])
@login_required
def toggle_favorite(guide_id):
    guide = GuideContent.query.get_or_404(guide_id)
    
    # 检查当前用户是否已经收藏过
    if guide in current_user.favorite_guides:
        current_user.favorite_guides.remove(guide)
        status = "unfavorited"
    else:
        current_user.favorite_guides.append(guide)
        status = "favorited"
    
    db.session.commit()
    return {"status": "success", "action": status}

@content_bp.route('/my/favorites')
@login_required
def my_favorites():
    # 获取当前用户的所有收藏，并按时间排序（如果需要更复杂的排序需增加中间表字段）
    guides = current_user.favorite_guides
    return render_template('content/list.html', guides=guides, is_favorite_page=True)