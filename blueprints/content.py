# blueprints/content.py
from flask import Blueprint, render_template, request
from models import Category, Tag, GuideContent
from extensions import db
from flask import Blueprint, render_template
# 定义蓝图
content_bp = Blueprint('content', __name__)

# --- 路由：资料权限鉴定 ---
@content_bp.route('/')
def index():
    return render_template('index.html') # 或者创建一个简单的 index.html

@content_bp.route('/guides')
def list_guides():
    cat_id = request.args.get('category_id', type=int)
    tag_id = request.args.get('tag_id', type=int)
    search_q = request.args.get('q', '') # 新增：搜索关键字

    query = GuideContent.query.filter_by(is_published=True)

    # 逻辑过滤
    if search_q:
        query = query.filter(GuideContent.title.contains(search_q) | GuideContent.summary.contains(search_q))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if tag_id:
        query = query.join(GuideContent.tags).filter(Tag.id == tag_id)

    guides = query.order_by(GuideContent.created_at.desc()).all()
    categories = Category.query.order_by(Category.sort_order.asc()).all()
    tags = Tag.query.all()

    return render_template('content/list.html', 
                           guides=guides, 
                           categories=categories, 
                           tags=tags,
                           current_cat=cat_id,
                           current_tag=tag_id,
                           search_q=search_q)

@content_bp.route('/guide/<int:guide_id>')
def show_guide(guide_id):
    # 1. 查询文章，如果不存在则返回 404
    guide = GuideContent.query.get_or_404(guide_id)
    
    # 2. 增加阅读数
    guide.view_count += 1
    db.session.commit()
    
    # 3. 获取相关推荐：同分类下的其他 3 篇文章
    # 逻辑：过滤掉当前文章 ID，按随机排序取 3 个
    related_guides = GuideContent.query.filter(
        GuideContent.category_id == guide.category_id,
        GuideContent.id != guide_id,
        GuideContent.is_published == True
    ).order_by(db.func.random()).limit(3).all()
    
    return render_template('content/detail.html', 
                           guide=guide, 
                           related_guides=related_guides)

@content_bp.route('/like/<int:guide_id>', methods=['POST'])
def like_guide(guide_id):
    guide = GuideContent.query.get_or_404(guide_id)
    guide.like_count += 1
    db.session.commit()
    return {"status": "success", "new_count": guide.like_count} # 返回 JSON 给前端