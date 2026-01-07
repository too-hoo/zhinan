from flask import Blueprint, render_template
from flask_login import login_required, current_user

# 定义蓝图
main_bp = Blueprint('main', __name__)

