from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
# from flask_cors import CORS  # 导入 CORS

import torch
import torch.nn as nn
from torchvision import transforms
import torchvision.models as models
from PIL import Image
from io import BytesIO
import os
import requests
import shutil
from werkzeug.utils import secure_filename
import script
import pymysql
import re

app = Flask(__name__)
# 加载模型
model = models.resnet34(pretrained=False)
num_features = model.fc.in_features
model.fc = nn.Linear(num_features, 2)
model.load_state_dict(torch.load('resnet34_model.pth'))
model.eval()

# 设备设置
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

upload_user_name = "flatness-detection"
upload_user_password = "tongji-icw-3455"
oss_url = "http://110.42.214.164:9000"

# 配置 MySQL 数据库连接
def get_db_connection():
    return pymysql.connect(
        host="1.117.69.116",  # MySQL 主机地址
        user="spalling",  # MySQL 用户名
        password="ELEwGjNKEiWtbym5",  # MySQL 密码
        database="spalling",  # 使用的数据库
        cursorclass=pymysql.cursors.DictCursor  # 查询返回字典
    )

# 清理文件名
def clean_filename(filename):
    return re.sub(r'[^A-Za-z0-9\.\-]', '_', filename)

def clean_path(path):
    path_parts = path.split('/')
    clean_parts = [clean_filename(part) for part in path_parts]
    return '/'.join(clean_parts)

# 下载图片
def downloadImage(url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            temp_image_path = "tmp_image.jpg"
            with open(temp_image_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            return temp_image_path
        else:
            print(f"Failed to download {url}")
            return None
    except Exception as e:
        print(f"Failed to download image: {e}")
        return None

# 上传图片
def upload_image(file_path, target_path, oss_url, user_name, password):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {
                'userName': user_name,
                'password': password
            }
            upload_url = f"{oss_url}/oss/upload/{target_path}"
            print(upload_url)
            response = requests.post(upload_url, files=files, data=data)

            if response.status_code != 200:
                return f"Failed to upload image. Status code: {response.status_code}, Error: {response.text}"

            try:
                response_json = response.json()
                download_url = response_json.get('downloadUrl', None)
                if download_url:
                    return download_url
                else:
                    return "Error: 'downloadUrl' not found in response"
            except ValueError:
                return response.text

    except Exception as e:
        return f"Error uploading image: {str(e)}"

# 插入历史记录
def sql_insert_history(input_image_url, output_image_url, result, user_name):
    try:
        timestamp = datetime.now()
        connection = get_db_connection()
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO historydata (origin_url, process_url, is_spalling, user_name, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (input_image_url, output_image_url, result, user_name, timestamp))
        connection.commit()
        print("Image data inserted successfully!")

    except pymysql.MySQLError as err:
        print(f"Error: {err}")
    finally:
        connection.close()
        cursor.close()

# 查找历史记录
def sql_find_history(user_name: str):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT user_name, origin_url, process_url, is_spalling, timestamp
            FROM historydata
            WHERE user_name = %s
            """
            cursor.execute(sql, (user_name,))
            results = cursor.fetchall()

            defect_history_dto = []
            for row in results:
                dto = {
                    'userName': row['user_name'],
                    'inputImg': row['origin_url'],
                    'outputImg': row['process_url'],
                    'result': row['is_spalling'],
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else None
                }
                defect_history_dto.append(dto)

            return defect_history_dto

    except Exception as e:
        print(f"Error occurred: {e}")
        return []
    finally:
        connection.close()

# 图片上传接口
@app.route('/defect/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    temp_file_path = os.path.join('temp', filename)
    os.makedirs('temp', exist_ok=True)
    file.save(temp_file_path)
    time = datetime.now().strftime('%Y%m%d%H%M%S')
    download_url = upload_image(temp_file_path, f"user/upload/{time}.jpg", oss_url,upload_user_name, upload_user_password)
    os.remove(temp_file_path)

    if download_url.startswith('http'):
        return jsonify({'downloadUrl': download_url})
    else:
        return jsonify({'error': download_url}), 500

# 图片分类接口
@app.route('/defect/classify', methods=['POST'])
def classify():
    if 'url' not in request.form or 'username' not in request.form:
        return jsonify({'error': 'No image URL or username provided'}), 400

    image_url = request.form['url']
    user_name = request.form['username']

    image_path = downloadImage(image_url)
    if image_path is None:
        return jsonify({'error': 'Failed to download image from the URL'}), 400

    try:
        image = Image.open(image_path).convert('RGB')
        image = transforms.ToTensor()(image).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(image)
            _, predicted = torch.max(outputs, 1)

        result = ['defect', 'undefect'][predicted.item()]
        if result == 'undefect':
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            target_url = f"user/result/{timestamp}.jpg"
            upload_image(image_path, target_url, oss_url, user_name, upload_user_password)
            sql_insert_history(image_url, image_url, 0, user_name)

        return jsonify({'result': result})

    except Exception as e:
        return jsonify({'error': f"Error in processing the image: {e}"}), 500

    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

# 显示缺陷
@app.route('/defect/showDefect', methods=['POST'])
def show_defect():
    if 'url' not in request.form or 'username' not in request.form:
        return jsonify({'error': 'No image URL or username provided'}), 400

    user_name = request.form['username']
    image_url = request.form['url']

    image_path = downloadImage(image_url)
    if image_path is None:
        return jsonify({'error': 'Failed to download image from the URL'}), 400

    try:
        processed_image_path = script.process_image(image_path)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        target_url = f"user/result/{timestamp}.jpg"
        upload_url = upload_image(processed_image_path, target_url, oss_url, upload_user_name, upload_user_password)
        sql_insert_history(image_url, upload_url, 1, user_name)

        if upload_url:
            return jsonify({"downloadUrl": upload_url}), 200
        else:
            return jsonify({"error": "Image processing failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 查询历史记录
@app.route('/defect/history', methods=['GET'])
def history():
    user_name = request.args.get('username')
    if not user_name:
        return jsonify({'error': 'No username provided'}), 400

    historyDto = sql_find_history(user_name)
    if historyDto:
        return jsonify({"history": historyDto}), 200
    else:
        return jsonify({"error": "History not found"}), 404

# 测试
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Hello, World!'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
