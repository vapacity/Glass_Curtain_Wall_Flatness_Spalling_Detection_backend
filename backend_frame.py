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

        # ======       检测逻辑         ======
        detection_passed = pic_check(filename, save_path);
        
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

#爆裂历史检测
@app.route('/get_crack_records', methods=['POST'])
def get_crack_records():
    try:
        data = request.get_json()
        user_id = data.get('userID')

        if not user_id:
            return jsonify({'status': 'fail', 'msg': 'Missing userID'}), 400

        sql = "SELECT id, image_path, detected_result_path, created_at FROM crack_records WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(sql, (user_id,))
        results = cursor.fetchall()

        # 构造响应数据
        records = []
        for row in results:
            record = {
                'id': row[0],
                'pic': {
                    'base': row[1],
                    'overlay': row[2]
                },
                'created_at': row[3].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row[3], datetime) else str(row[3])
            }
            records.append(record)

        return jsonify({'status': 'success', 'records': records}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({'status': 'fail', 'msg': f'Server error: {e}'}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8899)
    db.close()
    print("Good bye!")
