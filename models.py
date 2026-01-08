# models.py
from extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone
from extensions import login_manager
import uuid

# 定义收藏中间表
user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('guide_id', db.Integer, db.ForeignKey('guide_content.id'), primary_key=True)
)

# --- 1. 用户模型 (包含 CRUD 基础) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 核心修改：手机号作为主登录凭证，必须唯一且不能为空
    phone = db.Column(db.String(11), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=False, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # 扩展信息
    email = db.Column(db.String(120), unique=True, nullable=True)
    gender = db.Column(db.String(10), nullable=True) # 如：男、女、保密
    identity = db.Column(db.String(50), nullable=True) # 如：学生、职场人

    is_paid = db.Column(db.Boolean, default=False) # 是否为付费用户
    is_admin = db.Column(db.Boolean, default=False) # 新增：标记是否为管理员
    # 时间追踪字段 使用 default=datetime.utcnow，系统会自动填充当前 UTC 时间
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # PM 建议：记录最后登录时间，帮你判断用户活跃度
    last_login = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))
    favorite_guides = db.relationship('GuideContent', 
                                      secondary=user_favorites, 
                                      backref=db.backref('favorited_by', lazy='dynamic'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 新增激活码模型
class ActivationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # 激活码内容
    is_used = db.Column(db.Boolean, default=False) # 是否已被使用
    used_by_username = db.Column(db.String(80), nullable=True) # 被哪个用户使用了（方便追溯）
    created_at = db.Column(db.DateTime, default=db.func.now()) # 创建时间：方便你管理库存

# 分类模型：用于导航和内容过滤
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # 分类名称
    icon_url = db.Column(db.String(255)) # 分类图标，如：图标库链接或本地路径
    description = db.Column(db.String(200)) # 分类简介（PM建议：利于SEO和用户理解）
    sort_order = db.Column(db.Integer, default=0) # 排序权重（PM建议：方便你手动调整分类的前后顺序）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立一对多关联：一个分类下可以有多个指导内容
    guides = db.relationship('GuideContent', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

# 关联表：连接指导内容和标签 (多对多)
guide_tags = db.Table('guide_tags',
    db.Column('guide_id', db.Integer, db.ForeignKey('guide_content.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# 标签模型
class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # 标签名，如“焦虑”
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
# 指导内容模型：核心知识库
class GuideContent(db.Model):
    __tablename__ = 'guide_content'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False) # 所属分类ID
    
    title = db.Column(db.String(100), nullable=False) # 标题
    summary = db.Column(db.String(255)) # 列表显示的简介
    content = db.Column(db.Text, nullable=False) # 核心长文本（建议存储 Markdown 格式）
    
    # 核心升级：增加标签关联
    tags = db.relationship('Tag', secondary=guide_tags, backref=db.backref('guides', lazy='dynamic'))

    # 多媒体资源
    icon_url = db.Column(db.String(255)) # 缩略图
    cover_image_url = db.Column(db.String(255)) # 内容详情页顶部大图
    audio_url = db.Column(db.String(255)) # 冥想音频/语音导读链接
    video_url = db.Column(db.String(255)) # 心理科普或练习视频链接
    
    # 互动数据
    view_count = db.Column(db.Integer, default=0) # 阅读数
    like_count = db.Column(db.Integer, default=0) # 点赞数
    
    # 运营字段（PM建议：增加灵活性）
    is_published = db.Column(db.Boolean, default=True) # 是否发布（方便你写草稿）
    is_featured = db.Column(db.Boolean, default=False) # 是否精华/置顶（方便在首页做推荐位）
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # 最后更新时间

    def __repr__(self):
        return f'<GuideContent {self.title}>'

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 反馈内容
    content = db.Column(db.Text, nullable=False)
    # 用户联系方式（可选，方便回访）
    contact = db.Column(db.String(100), nullable=True)
    # 反馈时间
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # 关联用户
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))

    # 状态：0-未处理，1-已采纳，2-已回复
    status = db.Column(db.Integer, default=0)