import os
from flask import Flask
from extensions import db, login_manager
from models import User
# 导入蓝图
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.admin import admin_bp
from blueprints.content import content_bp

app = Flask(__name__)
# 基础配置
app.config['SECRET_KEY'] = 'zhinan-secret-key-123'
# 这里的逻辑是：如果系统里有 DATABASE_URL 这个环境变量，就用它（连接云库）
# 如果没有（比如你在本地开发），就默认用回 instance/zhinan.db
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///zhinan.db'
).replace('postgres://', 'postgresql://') # 这是一个兼容性小修复
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 1. 初始化扩展
db.init_app(app)
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 2. 注册蓝图
app.register_blueprint(auth_bp) # 默认前缀
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(content_bp)

# --- 启动前初始化数据库 ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # 自动创建 zhinan.db 文件
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)