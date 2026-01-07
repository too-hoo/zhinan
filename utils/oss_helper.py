# utils/oss_helper.py
import os
import uuid
import oss2, mimetypes
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import datetime # 确保导入了 datetime

load_dotenv() # 必须在所有 os.getenv 之前调用

class OssHelper:
    def __init__(self):
        # 从环境变量读取凭证，确保安全
        self.access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
        self.access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
        # 你的 Bucket 信息：华北2 (北京)
        self.endpoint = 'https://oss-cn-beijing.aliyuncs.com'
        self.bucket_name = 'my-media-system'
        
        # 初始化 Auth 和 Bucket
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

    def upload_file(self, file_obj, folder='images', is_private=False):
        """
        上传文件到 OSS
        :param file_obj: Flask request.files 中的文件对象
        :param folder: OSS 上的目录名 (images/videos/audios)
        :param is_private: 是否设为私有文件
        :return: 文件在 OSS 的完整访问路径
        """
        filename = secure_filename(file_obj.filename)
        # 生成唯一文件名，防止覆盖
        ext = filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        oss_path = f"{folder}/{unique_name}"

        # 动态识别 MIME 类型
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            # 根据文件夹兜底
            content_type = 'video/mp4' if folder == 'videos' else 'audio/mpeg'

        headers = {
            'Content-Type': content_type, # 明确告诉浏览器这是图片
            'Cache-Control': 'max-age=31536000', # 重点：设置长久缓存，节省流量
            'Content-Disposition': 'inline' # 尝试告诉浏览器内联显示（但在默认域名下仍受限）
        }
        if is_private:
            headers['x-oss-object-acl'] = oss2.OBJECT_ACL_PRIVATE
        else:
            headers['x-oss-object-acl'] = oss2.OBJECT_ACL_PUBLIC_READ

        # 上传文件流
        self.bucket.put_object(oss_path, file_obj, headers=headers)

        # 返回访问链接
        if is_private:
            # 私有文件返回路径，之后需调用 sign_url 生成带 Token 的链接
            return oss_path 
        else:
            # 公开文件直接返回 CDN/OSS 直链
            return f"https://{self.bucket_name}.oss-cn-beijing.aliyuncs.com/{oss_path}"

    def get_signed_url(self, oss_path, expires=3600):
        """生成私有文件的临时访问链接"""
        return self.bucket.sign_url('GET', oss_path, expires)

    def list_files(self, prefix='material/'):
        """获取 OSS 指定目录下的文件列表"""
        files = []
        try:
            # 遍历指定前缀的文件
            for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
                if obj.key.endswith('/'): 
                    continue 
                
                # 将时间戳或 datetime 转换为人类可读的字符串
                # 如果是整数时间戳：
                last_mod = datetime.datetime.fromtimestamp(obj.last_modified).strftime('%Y-%m-%d %H:%M:%S')
                
                files.append({
                    'name': obj.key.replace(prefix, ""), # 只显示文件名，去掉前缀
                    'url': f"https://{self.bucket_name}.oss-cn-beijing.aliyuncs.com/{obj.key}",
                    'path': obj.key,  # !!! 必须包含这一行，它是删除的唯一凭证
                    'size': obj.size,
                    'last_modified': last_mod # 转换后的字符串
                })
            # 按时间倒序排列
            return sorted(files, key=lambda x: x['last_modified'], reverse=True)
        except Exception as e:
            print(f"OSS 列表获取失败: {e}")
            return []

    def delete_file(self, oss_path):
        """
        从 OSS 中删除指定文件
        :param oss_path: 文件在 OSS 中的完整路径 (如 'video/a61106...mp4')
        """
        try:
            # 执行删除操作
            self.bucket.delete_object(oss_path)
            return True
        except Exception as e:
            print(f"OSS 删除失败: {e}")
            raise e

    def delete_files(self, oss_paths):
        """
        批量删除 OSS 中的文件
        :param oss_paths: 完整路径列表，例如 ['video/1.mp4', 'video/2.mp4']
        """
        if not oss_paths:
            return True
        try:
            # 执行批量删除
            result = self.bucket.batch_delete_objects(oss_paths)
            return True
        except Exception as e:
            print(f"OSS 批量删除失败: {e}")
            raise e
        
    def get_signed_url(self, obj_key, expires=1800):
        """
        根据对象路径生成带签名的访问链接
        :param obj_key: OSS 中的完整路径，例如 'video/demo.mp4'
        :param expires: 签名有效期（秒），默认 30 分钟
        :return: 带有签名的完整 URL
        """
        if not obj_key:
            return ""
        
        # 如果路径本身已经是完整的 http 链接且包含签名，则不重复签名
        if obj_key.startswith('http') and 'OSSAccessKeyId' in obj_key:
            return obj_key
            
        # 提取关键路径（如果存入的是全路径，需要剥离出 key）
        # 假设存的是 'images/3b98ef...png'
        key = obj_key.split('.com/')[-1] if 'http' in obj_key else obj_key

        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        
        # 生成带签名的 GET 请求 URL
        signed_url = bucket.sign_url('GET', key, expires)
        return signed_url