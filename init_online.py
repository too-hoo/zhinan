from extensions import db
from models import User, ActivationCode
import uuid
from werkzeug.security import generate_password_hash

# 1. 创建管理员 (使用你的真实手机号)
admin = User(
    phone='18888888888', 
    username='toohoo', 
    password_hash=generate_password_hash('你的强密码'), 
    is_admin=True, 
    is_paid=True
)
db.session.add(admin)

# 2. 生成 10 个激活码
for _ in range(10):
    db.session.add(ActivationCode(code=str(uuid.uuid4())[:8].upper()))

db.session.commit()
exit()