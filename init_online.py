from app import app, db, User, ActivationCode
from werkzeug.security import generate_password_hash
import uuid

def init_system():
    with app.app_context():
        # 1. 创建所有数据表
        print("正在创建数据库表...")
        db.create_all()

        # 2. 初始化管理员账号 (toohoo)
        admin_user = User.query.filter_by(username='toohoo').first()
        if not admin_user:
            print("正在创建管理员账号: toohoo...")
            admin_user = User(
                username='toohoo',
                password_hash=generate_password_hash('123'), # 建议改一个复杂的
                is_admin=True,
                is_paid=True
            )
            db.session.add(admin_user)
        else:
            print("管理员账号已存在，跳过创建。")

        # 3. 预生成第一批小红书激活码 (20个)
        existing_codes = ActivationCode.query.count()
        if existing_codes == 0:
            print("正在预生成第一批激活码...")
            for _ in range(20):
                code = str(uuid.uuid4())[:8].upper()
                new_code = ActivationCode(code=code)
                db.session.add(new_code)
            print("20个激活码已就绪。")
        
        db.session.commit()
        print("🎉 线上系统初始化完成！")

if __name__ == "__main__":
    init_system()