import os
import json
from extensions import db
from app import app
from models import Category, Tag, GuideContent
import google.generativeai as genai
from datetime import datetime, timezone

# 1. 配置 AI
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# 2. 选择你列表中的可用模型
# 这里使用了你诊断列表中的 gemini-2.0-flash
model = genai.GenerativeModel('gemini-flash-latest')

def generate_psychology_content(category_name, tag_names):
    prompt = f"""
    你是一名资深的心理咨询师。请为我的“心理指南”网站撰写一篇关于“{category_name}”的高质量指南。
    要求如下：
    1. 针对标签：{', '.join(tag_names)}。
    2. 语言风格：专业但通俗易懂，带有疗愈感，适合小红书用户。
    3. 输出格式必须为 JSON，包含以下字段：
       - title: 引人入胜的标题（含表情符号）
       - summary: 100字以内的简介
       - content: 完整的 Markdown 格式文章（包含具体案例、建议、练习方法）
    请直接输出 JSON 内容，不要包含任何 Markdown 格式的包裹符号（如 ```json）。
    """
    
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    
    # 核心修复：清理可能存在的 Markdown 代码块标签
    if raw_text.startswith("```"):
        # 提取第一个 ``` 和最后一个 ``` 之间的内容
        lines = raw_text.splitlines()
        # 去掉第一行 ```json 和最后一行 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
    
    return json.loads(raw_text)

def seed_content():
    with app.app_context():
        # 获取或创建分类
        cat = Category.query.filter_by(name='情绪调节').first()
        if not cat:
            cat = Category(name='情绪调节', description='学习如何与自己的情绪和谐相处')
            db.session.add(cat)
            db.session.commit()

        # 获取或创建标签
        tag_list = []
        for name in ['焦虑', '自我成长']:
            t = Tag.query.filter_by(name=name).first()
            if not t:
                t = Tag(name=name)
                db.session.add(t)
            tag_list.append(t)
        db.session.commit()

        print(f"🚀 正在调用 {model.model_name} 生成 AI 内容...")
        try:
            data = generate_psychology_content(cat.name, [t.name for t in tag_list])
            
            new_guide = GuideContent(
                title=data['title'],
                summary=data['summary'],
                content=data['content'],
                category_id=cat.id,
                tags=tag_list,
                is_published=True
            )
            
            db.session.add(new_guide)
            db.session.commit()
            print(f"✅ 成功导入指南: {data['title']}")
        except Exception as e:
            print(f"❌ 导入失败: {str(e)}")

if __name__ == "__main__":
    seed_content()