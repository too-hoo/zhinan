# from app import app, db, User

# with app.app_context():
#     print("--- 当前数据库中的用户列表 ---")
#     users = User.query.all()
#     if not users:
#         print("数据库中还没有任何用户。")
#     for u in users:
#         print(f"用户名: {u.username} | 是否付费: {u.is_paid}")



# from app import app, db, User
# with app.app_context():
#     u = User.query.filter_by(username='toohoo').first()
#     u.is_paid = False
#     db.session.commit()
#     print(f"用户 {u.username} 现在的付费状态是: {u.is_paid}")


# from app import app, db
# with app.app_context():
#     db.create_all() # 创建数据库
#     print('数据库已按照最新模型重新生成！')

from app import app, db, User
with app.app_context():
    u = User.query.filter_by(username='toohoo').first()
    if u:
        u.is_admin = True
        u.is_paid = True # 顺便给自己开通付费权限
        db.session.commit()
        print("toohoo 已升级为管理员和付费用户！")

# rm instance/zhinan.db
# python -c "from app import app, db; 
# with app.app_context(): db.create_all(); print('数据库已按照最新模型重新生成！')"