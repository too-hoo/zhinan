# 个人主页内容控制逻辑文件
from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user
from models import Feedback
from extensions import db

# 定义蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/profile')
@login_required
def profile():
    # 获取用户收藏的指南（SQLAlchemy 会自动处理中间表查询）
    favorites = current_user.favorite_guides
    return render_template('profile.html', favorites=favorites)

@main_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback():
    if request.method == 'POST':
        content = request.form.get('content')
        contact = request.form.get('contact')
        
        if not content:
            flash('请输入您的反馈内容', 'danger')
            return redirect(url_for('main.submit_feedback'))
            
        new_feedback = Feedback(
            content=content,
            contact=contact,
            user_id=current_user.id
        )
        db.session.add(new_feedback)
        db.session.commit()
        
        flash('🎉 反馈提交成功！感谢您的宝贵建议。', 'success')
        return redirect(url_for('main.profile'))
        
    return render_template('main/feedback.html')
