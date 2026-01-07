# blueprints/admin/codes.py
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from extensions import db
from models import ActivationCode
from . import admin_required

codes_bp = Blueprint('admin_codes', __name__, url_prefix='/codes')

@codes_bp.route('/')
@login_required
@admin_required
def list_codes():
    page = request.args.get('page', 1, type=int)
    # 分页显示激活码
    pagination = ActivationCode.query.order_by(ActivationCode.id.desc()).paginate(page=page, per_page=20)
    return render_template('admin/codes/list.html', codes=pagination.items, pagination=pagination)

@codes_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate_codes():
    for _ in range(10):
        random_code = str(uuid.uuid4())[:8].upper()
        # 确保激活码不重复
        if not ActivationCode.query.filter_by(code=random_code).first():
            # 修正点：使用 is_used=False 替代 status='可用'
            db.session.add(ActivationCode(code=random_code, is_used=False))
    db.session.commit()
    flash('成功生成 10 个新激活码！', 'success')
    return redirect(url_for('admin.admin_codes.list_codes'))

@codes_bp.route('/api/copy-available')
@login_required
@admin_required
def get_available_codes():
    # 查询所有未被使用的激活码
    available = ActivationCode.query.filter_by(is_used=False).all()
    code_text = "\n".join([c.code for c in available])
    return jsonify({"success": True, "data": code_text})