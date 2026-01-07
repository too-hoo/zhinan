# blueprints/content.py
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
    pagination = query.order_by(GuideContent.created_at.desc()).paginate(page=page, per_page=6)
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
    guide = GuideContent.query.get_or_404(guide_id)
    
    # 权限检查（虽然 list 页面有拦截，但详情页入口也要守住）
    if not current_user.is_paid:
        return render_template('no_permission.html')

    # 1. 阅读数自增
    guide.view_count += 1
    db.session.commit()

    # 2. 核心改进：处理正文中的私有链接
    # 逻辑：查找 Markdown 中符合 OSS 域名的链接并生成签名
    content = guide.content
    
    # 这是一个匹配 OSS 完整链接的正则
    oss_pattern = rf"https://{oss_helper.bucket_name}\.{oss_helper.endpoint.replace('https://', '')}/[^\s\)\?]+"
    
    def sign_match(match):
        raw_url = match.group(0)
        # 调用新写的签名方法
        return oss_helper.get_signed_url(raw_url)

    # 动态替换所有匹配到的原始链接为签名链接
    signed_content = re.sub(oss_pattern, sign_match, content)

    # 3. 处理封面图签名（如果是私有的话）
    signed_cover = oss_helper.get_signed_url(guide.cover_image_url)
    
    # 3. 获取相关推荐：同分类下的其他 3 篇文章
    # 逻辑：过滤掉当前文章 ID，按随机排序取 3 个
    related_guides = GuideContent.query.filter(
        GuideContent.category_id == guide.category_id,
        GuideContent.id != guide_id,
        GuideContent.is_published == True
    ).order_by(db.func.random()).limit(3).all()
    
    return render_template('content/detail.html', 
                            guide=guide, 
                            content=signed_content, # 传出带有签名的正文
                            cover=signed_cover,
                            related_guides=related_guides)

@content_bp.route('/like/<int:guide_id>', methods=['POST'])
@login_required
def like_guide(guide_id):
    guide = GuideContent.query.get_or_404(guide_id)
    guide.like_count += 1
    db.session.commit()
    return {"status": "success", "new_count": guide.like_count} # 返回 JSON 给前端