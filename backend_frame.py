# -*- coding: utf-8 -*-
import pymysql
from flask import Flask, request, jsonify
from flask_cors import CORS

#数据库连接
db = pymysql.connect(host="127.0.0.1",user="root",password="",database="")
cursor = db.cursor()

#后端服务启动
app = Flask(__name__)
CORS(app, resources=r'/*')

@app.route('/URL', methods=['POST'])
def fun():
    if request.method == "POST":
        
        try:

            return "1"
        except Exception as e:
            print("failed:",e)
            db.rollback()
            return "-1"

# 判断文件后缀是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#上传图片接口
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'status': 'fail', 'msg': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'fail', 'msg': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # ====== 检测逻辑（此处为占位） ======
        # 检测图片是否合格，比如 crack_detect(save_path)
        detection_passed = True  # 模拟检测通过
        # ====================================

        if detection_passed:
            try:
                sql = "INSERT INTO images (filename, filepath) VALUES (%s, %s)"
                cursor.execute(sql, (filename, save_path))
                db.commit()
                return jsonify({'status': 'success', 'msg': 'Image uploaded and passed detection'}), 200
            except Exception as e:
                db.rollback()
                return jsonify({'status': 'fail', 'msg': f'Database error: {e}'}), 500
        else:
            return jsonify({'status': 'fail', 'msg': 'Image failed detection'}), 400

    return jsonify({'status': 'fail', 'msg': 'Invalid file type'}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8899)
    db.close()
    print("Good bye!")
