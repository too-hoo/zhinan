# init_online.py
from app import app, db, User
from werkzeug.security import generate_password_hash

def run_init():
    # 核心：必须使用 with 语句进入应用上下文
    with app.app_context():
        print("正在尝试创建管理员账号...")
        
        # 检查是否已存在
        admin = User.query.filter_by(username='toohoo').first()
        
        if not admin:
            # 创建管理员对象
            admin = User(
                phone='18888888888', # 别忘了填上手机号，否则会报 Null 错误
                username='toohoo',
                password_hash=generate_password_hash('你的密码'),
                is_admin=True,
                is_paid=True
            )
            # 这行操作现在在上下文保护下，不会再报错
            db.session.add(admin)
            db.session.commit()
            print("成功：管理员账号已创建！")
        else:
            print("提示：管理员账号已存在，无需重复创建。")

if __name__ == "__main__":
    run_init()