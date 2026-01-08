from app import app, db, User, ActivationCode
from werkzeug.security import generate_password_hash
from flask_migrate import upgrade
import uuid

def init_system():
    with app.app_context():
        # 1. 结构同步：优先使用 Flask-Migrate 提供的 upgrade()
        # 这比直接 db.create_all() 更专业，能确保线上数据库拥有 Alembic 版本记录
        print("🔄 正在同步数据库结构 (Migrations)...")
        try:
            upgrade() 
            print("✅ 数据库结构已更新至最新版本。")
        except Exception as e:
            print(f"⚠️ 自动迁移过程中出现提示（可能已是最新版本）: {e}")
            # 如果迁移工具未就绪，则使用 create_all 作为兜底方案
            db.create_all()

        # 2. 初始化管理员账号 (必须包含手机号)
        # 注意：现在 phone 是主登录凭证，且必须唯一
        admin_phone = '18888888888' # 请在此处设置你的真实管理员手机号
        admin_user = User.query.filter_by(phone=admin_phone).first()
        
        if not admin_user:
            print(f"👤 正在创建管理员账号 (手机号: {admin_phone})...")
            admin_user = User(
                phone=admin_phone,      # 必须字段
                username='toohoo',
                # 建议在上线前将 'AdminPassword123' 改为复杂的强密码
                password_hash=generate_password_hash('AdminPassword123'),
                is_admin=True,          # 标记管理员权限
                is_paid=True            # 标记为已付费核心成员
            )
            db.session.add(admin_user)
        else:
            print(f"ℹ️ 管理员账号 ({admin_phone}) 已存在，跳过创建。")

        # 3. 预生成第一批激活码 (20个)
        if ActivationCode.query.count() == 0:
            print("🔑 正在预生成第一批注册激活码...")
            for _ in range(20):
                # 生成 8 位短码
                code = str(uuid.uuid4())[:8].upper()
                new_code = ActivationCode(code=code)
                db.session.add(new_code)
            print("✅ 20个激活码已就绪。")
        
        db.session.commit()
        print("🎉 线上系统初始化流程全部完成！")

if __name__ == "__main__":
    init_system()