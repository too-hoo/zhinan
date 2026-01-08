# blueprints/admin/feedback.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import Feedback, db
from . import admin_required

# 定义子蓝图
feedback_bp = Blueprint('admin_feedback', __name__, url_prefix='/feedback')

@feedback_bp.route('/')
@login_required
@admin_required
def list_feedback():
    # 1. 获取当前页码，默认为第 1 页
    page = request.args.get('page', 1, type=int)
    
    # 2. 启用分页查询，每页显示 10 条反馈
    pagination = Feedback.query.order_by(Feedback.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # 3. 将分页对象传给模板
    return render_template('admin/feedback.html', 
                           feedbacks=pagination.items, 
                           pagination=pagination)

@feedback_bp.route('/update/<int:id>/<int:status>', methods=['POST'])
@login_required
@admin_required
def update_status(id, status):
    # 更新反馈处理状态
    item = Feedback.query.get_or_404(id)
    item.status = status
    db.session.commit()
    flash('状态已更新', 'success')
    return redirect(url_for('admin.admin_feedback.list_feedback'))