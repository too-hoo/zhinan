# blueprints/admin/materials.py
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from . import admin_required
from utils.oss_helper import OssHelper

# 这里的第一个参数 'admin_materials' 决定了 url_for 的中间段
materials_bp = Blueprint('admin_materials', __name__, url_prefix='/materials')
oss_helper = OssHelper()

@materials_bp.route('/')
@login_required
@admin_required
def material_center():
    # 之前在 admin.py 中的逻辑
    return render_template('admin/materials.html')

@materials_bp.route('/api/my-media-system/<string:media_type>')
@login_required
@admin_required
def get_materials(media_type):
    folder_map = {'video': 'video/', 'audio': 'audio/', 'material': 'material/', 'image': 'images/'}
    prefix = folder_map.get(media_type, 'images/')
    files = oss_helper.list_files(prefix=prefix)
    return jsonify({'success': True, 'files': files})

@materials_bp.route('/api/upload', methods=['POST'])
@login_required
@admin_required
def upload_material_api():
    file = request.files.get('file')
    media_type = request.form.get('type') # 获取当前所在分类（video/audio/image/material）
    
    if not file:
        return jsonify({'success': False, 'message': '未选择文件'})

    # 这里的 folder_map 必须与你之前修正后的 OSS 目录一致
    folder_map = {
        'video': 'video/',
        'audio': 'audio/',
        'image': 'images/',
        'material': 'material/'
    }
    target_folder = folder_map.get(media_type, 'material/')

    try:
        # 调用你已经完善好的 oss_helper 上传逻辑
        # 它会自动处理 Content-Type 和 Cache-Control
        file_url = oss_helper.upload_file(file, folder=target_folder)
        return jsonify({'success': True, 'url': file_url})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@materials_bp.route('/api/delete', methods=['POST'])
@login_required
@admin_required
def delete_material():
    # 单个删除，获取前端传来的完整路径
    data = request.get_json()
    oss_path = data.get('path')
    
    if not oss_path:
        return jsonify({'success': False, 'message': '缺少文件路径'})

    try:
        # 执行删除
        oss_helper.delete_file(oss_path)
        return jsonify({'success': True, 'message': '文件已永久删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@materials_bp.route('/api/delete_batch', methods=['POST'])
@login_required
@admin_required
def delete_materials():
    # 批量删除
    data = request.get_json()
    oss_paths = data.get('paths', []) # 接收路径列表
    
    if not oss_paths:
        return jsonify({'success': False, 'message': '未选择任何文件'})

    try:
        oss_helper.delete_files(oss_paths)
        return jsonify({'success': True, 'message': f'成功删除 {len(oss_paths)} 个素材'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})