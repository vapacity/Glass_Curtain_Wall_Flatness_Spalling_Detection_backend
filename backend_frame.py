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


if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8899)
    db.close()
    print("Good bye!")
