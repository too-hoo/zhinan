# blueprints/admin/users.py
from flask import Blueprint, render_template, request, jsonify
from models import User, db
from flask_login import login_required
from . import admin_required
users_bp = Blueprint('admin_users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@admin_required
def list_users():
    # 实现你要求的分页返回
    page = request.args.get('page', 1, type=int)
    pagination = User.query.filter_by(is_admin=False).order_by(User.id.desc()).paginate(page=page, per_page=10)
    return render_template('admin/users/list.html', users=pagination.items, pagination=pagination)

@users_bp.route('/authorize/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def authorize(user_id):
    # 实现 CRUD 授权逻辑
    user = User.query.get_or_404(user_id)
    user.is_paid = not user.is_paid
    db.session.commit()
    return jsonify({"success": True, "is_paid": user.is_paid})