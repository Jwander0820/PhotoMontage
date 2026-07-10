import os
import sys
import uuid
import numpy as np
import cv2
from flask import Flask, request, jsonify, render_template, send_from_directory

from core.processing_img import ProcessingImg
from core.rt_input_img_data import InputImgData
from core.get_dir_data import GetDirImg
from utils.split_txt_data import SpiltTxtData
from utils.img_tools import ImgTools
import random

import hashlib

app = Flask(__name__)

TARGET_IMG_DIR = "./target_img"
ELEMENT_IMG_DIR = "./element_img"
MONTAGE_IMG_DIR = "./montage_img"
ELEMENT_DATA_DIR = "./element_img_data"

for d in [TARGET_IMG_DIR, MONTAGE_IMG_DIR, ELEMENT_DATA_DIR, ELEMENT_IMG_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# If element_img is empty, auto-generate 128 test color blocks
has_images = False
if os.path.exists(ELEMENT_IMG_DIR):
    for f in os.listdir(ELEMENT_IMG_DIR):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            has_images = True
            break

if not has_images:
    print("Auto-generating 128 test color blocks for startup...")
    try:
        from generate_test_elements import generate_color_blocks
        generate_color_blocks(ELEMENT_IMG_DIR, 128)
        print("Success: Generated 128 test color blocks.")
    except Exception as e:
        print(f"Warning: Could not auto-generate test elements: {e}")

def get_element_data_file(element_dir):
    # 根據資料夾路徑計算 MD5，產生唯一的快取檔名
    abs_path = os.path.abspath(element_dir)
    dir_hash = hashlib.md5(abs_path.encode('utf-8')).hexdigest()[:8]
    folder_name = "".join([c for c in os.path.basename(abs_path) if c.isalnum() or c in ('_', '-')])
    if not folder_name:
        folder_name = "dir"
    return os.path.join(ELEMENT_DATA_DIR, f"cache_{folder_name}_{dir_hash}.txt")


@app.route('/')
def index():
    # Provide predefined target images
    target_images = []
    if os.path.exists(TARGET_IMG_DIR):
        target_images = [f for f in os.listdir(TARGET_IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return render_template('index.html', target_images=target_images)

@app.route('/api/update_elements', methods=['POST'])
def update_elements():
    try:
        element_dir = request.form.get('element_dir', ELEMENT_IMG_DIR)
        if not os.path.exists(element_dir):
            return jsonify({'error': f'資料夾不存在: {element_dir}'}), 400
            
        element_data_file = get_element_data_file(element_dir)
        cache_filename = os.path.basename(element_data_file)
        
        # 刪除舊的資料清單以重新產生
        if os.path.exists(element_data_file):
            os.remove(element_data_file)
            
        GetDirImg.get_specified_dir_img_data(element_dir, cache_filename)
        
        # 計算成功讀取了幾張圖片
        count = 0
        if os.path.exists(element_data_file):
            with open(element_data_file, 'r') as f:
                lines = f.readlines()
                count = len(lines)
                
        return jsonify({
            'success': True,
            'count': count,
            'message': f'成功更新素材庫，共讀取了 {count} 張圖片。'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/montage', methods=['POST'])
def run_montage():
    try:
        org_img_pixel = int(request.form.get('org_img_pixel', 100))
        element_img_pixel = int(request.form.get('element_img_pixel', 200))
        cal_color_method = request.form.get('cal_color_method', 'average')
        element_dir = request.form.get('element_dir', ELEMENT_IMG_DIR)
        
        # Handle file upload or predefined selection
        target_img_path = None
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            target_img_path = os.path.join(TARGET_IMG_DIR, filename)
            file.save(target_img_path)
        else:
            predefined_img = request.form.get('predefined_img')
            if predefined_img:
                target_img_path = os.path.join(TARGET_IMG_DIR, predefined_img)
        
        if not target_img_path or not os.path.exists(target_img_path):
            return jsonify({'error': 'No valid target image provided'}), 400

        element_data_file = get_element_data_file(element_dir)
        cache_filename = os.path.basename(element_data_file)

        # If data file doesn't exist, generate it now using the element_dir
        if not os.path.exists(element_data_file):
            if not os.path.exists(element_dir):
                return jsonify({'error': f'素材資料夾不存在: {element_dir}。請確認路徑或將圖片放入該資料夾。'}), 400
            print(f"Generating element image data from {element_dir}...")
            GetDirImg.get_specified_dir_img_data(element_dir, cache_filename)

        # Double check if any elements exist in index
        if not os.path.exists(element_data_file) or os.path.getsize(element_data_file) == 0:
            return jsonify({'error': '素材資料庫為空，請放入圖片後點擊「更新素材資料庫」'}), 400

        mask_img, montage_img, img_height_num, img_width_num = InputImgData.rt_input_img_data(
            target_img_path, org_img_pixel, element_img_pixel)
            
        element_img_list = InputImgData.rt_element_img_list(element_data_file)
        
        color_set = ProcessingImg.cal_img_block_color_set(
            mask_img, org_img_pixel, img_width_num, img_height_num, cal_color_method=cal_color_method)
            
        block_color_dict = ProcessingImg.cal_img_block_color_dict(
            color_set, element_img_list, cal_color_method=cal_color_method)
            
        for i in range(img_width_num):
            for j in range(img_height_num):
                mask_img_tmp, color = ProcessingImg.cal_img_block_color(
                    mask_img, org_img_pixel, i, j, cal_color_method=cal_color_method)
                
                matched_elements = block_color_dict.get(tuple(color))
                if not matched_elements:
                    # fallback if dictionary fails somehow
                    continue
                    
                selected_element_idx = random.choice(matched_elements)
                selected_element = element_img_list[selected_element_idx]
                file_path, crop_data, _, _ = SpiltTxtData.split_img_resize_data(selected_element)
                
                montage_img = ProcessingImg.crop_element_img_paste_montage_img(
                    file_path, crop_data, montage_img, element_img_pixel, i, j)

        mask_img_resize = cv2.resize(mask_img, (montage_img.shape[1], montage_img.shape[0]))
        merge_img = cv2.addWeighted(mask_img_resize, 0.3, montage_img, 0.7, 0)
        
        save_img_name = f"web_{uuid.uuid4().hex[:8]}"
        ImgTools.save_img(save_img_name, merge_img, org_img_pixel, element_img_pixel, cal_color_method)
        
        zoom_ratio = element_img_pixel // org_img_pixel
        output_filename = f'Montage_{save_img_name}_ZoomRatio-{zoom_ratio}_ElementImgSize-{element_img_pixel}_Method-{cal_color_method}.png'
        
        return jsonify({
            'success': True,
            'result_url': f'/montage_img/{output_filename}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/montage_img/<filename>')
def serve_montage_img(filename):
    return send_from_directory(MONTAGE_IMG_DIR, filename)
    
@app.route('/target_img/<filename>')
def serve_target_img(filename):
    return send_from_directory(TARGET_IMG_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
