from flask import Blueprint, render_template
from flask_login import login_required, current_user

# 定义蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/guide')
@login_required
def guide():
    if not current_user.is_paid:
        # 如果不是付费用户，跳转回首页并提示
        return render_template('no_permission.html')
    return render_template('guide.html')