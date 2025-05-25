app = Flask(__name__)

# 数据库连接函数 - 每次执行时创建连接，操作完后关闭连接
def get_db_connection():
    return pymysql.connect(
        host='1.117.69.116',  # 替换为实际的数据库主机地址
        user='flatness',  # 替换为实际的数据库用户名
        password='TXaRZbA4mHwPsPch',  # 替换为实际的数据库密码
        database='flatness',  # 替换为实际的数据库名称
        cursorclass=pymysql.cursors.DictCursor  # 查询返回字典
    )

# 查询历史数据的函数
def find_by_userName(userName):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
            SELECT user_name, input_url, output_id, output_result_url,result, timestamp
            FROM historyData 
            WHERE user_name = %s
            ORDER BY timestamp DESC
            """
            cursor.execute(query, (userName,))
            results = cursor.fetchall()

            defect_history_dto = []
            for row in results:
                dto = {
                    'userName': row['user_name'],
                    'inputImg': row['input_url'],
                    'outputId': row['output_id'],
                    'outputImg': row['output_result_url'],
                    'result': row['result'],
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else None
                }
                defect_history_dto.append(dto)

            return defect_history_dto
    except Exception as e:
        print(f"Error querying from database: {e}")
    finally:
        if connection:
            connection.close()  # 关闭连接

def find_by_output_id(output_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
            SELECT 
                output_url, 
                edge_image_url, 
                line_image_url, 
                gradient_image_url, 
                frequency_image_url,
                edge_analysis, 
                line_analysis, 
                gradient_analysis, 
                frequency_analysis
            FROM outputinfo 
            WHERE output_id = %s
            """
            cursor.execute(query, (output_id,))
            results = cursor.fetchall()

            if results:
                # 构建返回的结果列表
                output_data = []

                for result in results:
                    output_url = result['output_url']
                    analyses = [
                        {"url": result['edge_image_url'], "analysis": result['edge_analysis']},
                        {"url": result['line_image_url'], "analysis": result['line_analysis']},
                        {"url": result['gradient_image_url'], "analysis": result['gradient_analysis']},
                        {"url": result['frequency_image_url'], "analysis": result['frequency_analysis']}
                    ]

                    # 将每个output_url与它的相关分析信息添加到结果列表中
                    output_data.append({
                        "outputUrl": output_url,
                        "analyses": analyses
                    })

                return output_data
            else:
                return []

    except Exception as e:
        print(f"Error querying from database: {e}")
        return []
    finally:
        if connection:
            connection.close()  # 关闭连接

@app.route("/flatness/history",methods=['GET'])
def get_history():
    user_name = request.args.get('username')
    if not user_name:
        return jsonify({'error': 'No username provided'}), 400

    historyDto = find_by_userName(user_name)
    if historyDto:
        return jsonify({"history": historyDto}), 200
    else:
        return jsonify({"error": "History not found"}), 404

@app.route("/flatness/getDetail",methods=['GET'])
def get_detail():
    user_name = request.args.get('username')
    output_id = request.args.get('outputId')
    result = find_by_output_id(output_id)
    return jsonify({"result": result}), 200


