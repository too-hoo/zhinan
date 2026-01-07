# blueprints/admin/__init__.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import current_user
from functools import wraps

# 1. 定义总的 admin 蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理员权限装饰器 (提取为公共组件)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('您没有权限访问管理后台', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# 2. 导入子模块 (注意：此时先确保文件已存在，见下文)
from .users import users_bp
from .codes import codes_bp
from .guides import guides_bp
from .materials import materials_bp
from .taxonomy import taxonomy_bp

# 3. 注册子蓝图，实现 URL 嵌套
# 这样访问路径会自动变为 /admin/users, /admin/codes 等
admin_bp.register_blueprint(users_bp)
admin_bp.register_blueprint(codes_bp)
admin_bp.register_blueprint(guides_bp)
admin_bp.register_blueprint(materials_bp)
admin_bp.register_blueprint(taxonomy_bp)

# 保留仪表盘主页路由
@admin_bp.route('/')
@admin_required
def admin_index():
    from models import User, GuideContent
    user_count = User.query.filter_by(is_admin=False).count()
    guide_count = GuideContent.query.count()
    return render_template('admin/dashboard.html', user_count=user_count, guide_count=guide_count)