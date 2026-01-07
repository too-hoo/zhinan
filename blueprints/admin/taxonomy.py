# blueprints/admin/taxonomy.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from extensions import db
from models import Category, Tag, GuideContent
from . import admin_required

taxonomy_bp = Blueprint('admin_taxonomy', __name__, url_prefix='/taxonomy')

@taxonomy_bp.route('/')
@login_required
@admin_required
def list_taxonomy():
    categories = Category.query.order_by(Category.sort_order.asc()).all()
    tags = Tag.query.all()
    return render_template('admin/taxonomy.html', categories=categories, tags=tags)

# --- 分类 CRUD ---
@taxonomy_bp.route('/category/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    name = request.form.get('name')
    if name:
        new_cat = Category(name=name, sort_order=0)
        db.session.add(new_cat)
        db.session.commit()
        flash(f'分类 "{name}" 已创建', 'success')
    return redirect(url_for('admin.admin_taxonomy.list_taxonomy'))

@taxonomy_bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    # 1. 获取要删除的分类
    cat_to_delete = Category.query.get_or_404(id)
    
    # 防止误删“未分类”本身
    if cat_to_delete.name == '未分类':
        flash('系统默认分类“未分类”不能被删除。', 'danger')
        return redirect(url_for('admin.admin_taxonomy.list_taxonomy'))

    # 2. 检查该分类下是否有指南
    associated_guides = GuideContent.query.filter_by(category_id=id).all()
    
    if associated_guides:
        # 3. 寻找或创建“未分类”条目
        uncategorized = Category.query.filter_by(name='未分类').first()
        if not uncategorized:
            uncategorized = Category(name='未分类', sort_order=99)
            db.session.add(uncategorized)
            db.session.flush() # 获取新生成的 ID
        
        # 4. 执行批量迁移
        for guide in associated_guides:
            guide.category_id = uncategorized.id
        
        count = len(associated_guides)
        flash(f'分类已删除。该分类下的 {count} 篇指南已自动移动到“未分类”。', 'info')
    else:
        flash('分类已成功移除。', 'success')

    # 5. 执行物理删除
    db.session.delete(cat_to_delete)
    db.session.commit()
    
    return redirect(url_for('admin.admin_taxonomy.list_taxonomy'))

# --- 标签 CRUD ---
@taxonomy_bp.route('/tag/add', methods=['POST'])
@login_required
@admin_required
def add_tag():
    name = request.form.get('name')
    if name:
        new_tag = Tag(name=name)
        db.session.add(new_tag)
        db.session.commit()
        flash(f'标签 "#{name}" 已创建', 'success')
    return redirect(url_for('admin.admin_taxonomy.list_taxonomy'))

@taxonomy_bp.route('/tag/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_tag(id):
    tag = Tag.query.get_or_404(id)
    db.session.delete(tag)
    db.session.commit()
    flash('标签已移除', 'warning')
    return redirect(url_for('admin.admin_taxonomy.list_taxonomy'))