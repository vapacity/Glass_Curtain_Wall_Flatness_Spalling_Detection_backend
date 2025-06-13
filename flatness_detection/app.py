import os
import time
import uuid
from datetime import datetime
import numpy as np
import cv2
import torch
from PIL import Image, ImageDraw
from flask import request, jsonify, Flask, send_from_directory
from flask_cors import CORS
from torch.autograd import Variable
from torchvision import transforms
# 你项目环境下的自定义工具和config
from config import gdd_testing_root, gdd_results_root
from misc import check_mkdir, crf_refine
from gdnet import GDNet
from segment import extract_white_regions, segment_from_original_image, save_segments
from flatnessDetectStrategy import detect_glass_flatness
from drawFlatnessResult import draw_flatness_results
import requests
import shutil
app = Flask(__name__)
CORS(app)
# ===== 设备自动适配，兼容M1/M2/M3/CPU/NVIDIA =====
def get_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device('mps')
    else:
        return torch.device('cpu')
device = get_device()
print("Using device:", device)
gdd_results_root = './results'
# 加载模型相关参数
ckpt_path = './ckpt'
exp_name = 'GDNet'
args = {
    'snapshot': '200',
    'scale': 416,
    'crf': False,
}
upload_user_name = "flatness-detection"
upload_user_password = "tongji-icw-3455"
oss_url = "http://110.42.214.164:9000"
segments_dir = "./temp_segments"
# 图像预处理
img_transform = transforms.Compose([
    transforms.Resize((args['scale'], args['scale'])),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# download and store to ./imgs/
def downloadImage(url):
    # 使用 requests 发送 GET 请求
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        # 保存图片到本地
        check_mkdir("./imgs")
        temp_image_path = './imgs/temp_image.jpg'
        with open(temp_image_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
            print(temp_image_path)

        # 返回图片的路径
        return temp_image_path
    else:
        return jsonify({'error': 'Failed to fetch image'}), 500


import os
import subprocess


# 检查目录是否存在，不存在则创建
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")


# 使用 curl 命令下载文件
def download_file_with_curl(url, target_path):
    try:
        command = ['curl', '-o', target_path, url]
        subprocess.run(command, check=True)
        print(f"File downloaded successfully to {target_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while downloading {url}: {e}")


def check_and_download_model(model_url, model_filename, model_dir):
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    model_path = os.path.join(model_dir, model_filename)
    if os.path.exists(model_path):
        print(f"Model {model_filename} already exists at {model_path}. Skipping download.")
        return model_path
    else:
        import subprocess
        print(f"Downloading {model_filename} from {model_url} ...")
        subprocess.run(['curl', '-o', model_path, model_url], check=True)
        return model_path
other_model_url = 'http://110.42.214.164:9000/oss/download/flatness-detection/sys/models/resnext101.pth'
other_model_filename = 'resnext_101_32x4d.pth'
other_model_dir = '.'
other_model_path = check_and_download_model(other_model_url, other_model_filename, other_model_dir)

#test1

# # 检查并下载第一个模型
# gdd_model_path = check_and_download_model(gdd_model_url, gdd_model_filename, gdd_model_dir)

# 检查并下载第二个模型
other_model_path = check_and_download_model(other_model_url, other_model_filename, other_model_dir)


def upload_image(file_path, target_path, oss_url, upload_user_name, upload_password):
    try:
        print("upload_image inside:",file_path)
        # 打开本地图片文件
        with open(file_path, 'rb') as file:
            # 构建请求的文件字段和用户身份信息
            files = {'file': file}
            data = {
                'userName': upload_user_name,
                'password': upload_password
            }

            # 构建上传的URL路径
            upload_url = f"{oss_url}/oss/upload/{target_path}"

            print(f"Uploading to: {upload_url}")
            # 发送 POST 请求上传文件
            response = requests.post(upload_url, files=files, data=data)

            # 检查响应状态码
            if response.status_code != 200:
                print(f"Failed to upload {file_path}. Status code: {response.status_code}, Error: {response.text}")
                return f"Failed to upload image. Status code: {response.status_code}, Error: {response.text}"

            # 如果响应内容是JSON，尝试解析
            try:
                response_json = response.json()
                download_url = response_json.get('downloadUrl', None)
                if download_url:
                    print(f"Uploaded {os.path.basename(file_path)} to OSS. Download URL: {download_url}")
                    return download_url
                else:
                    print(f"Error: 'downloadUrl' not found in response for {file_path}")
                    return "Error: 'downloadUrl' not found in response"
            except ValueError:
                # 如果返回不是JSON格式，直接返回响应文本（应该是URL）
                print(f"Uploaded {os.path.basename(file_path)} to OSS. Response: {response.text}")
                return response.text  # 返回URL字符串

    except Exception as e:
        print(f"Error uploading image {file_path}: {str(e)}")
        return f"Error uploading image: {str(e)}"


######以下为具体分割功能######
to_test = {'GDD': './imgs'}

to_pil = transforms.ToPILImage()

def extract_boundary(segmented_image):
    """
    提取分割图像的边界点。
    使用阈值分割，找到图像中的边界
    """
    # 将图像转为二值图像
    binary_image = np.where(segmented_image > 0.5, 255, 0).astype(np.uint8)  # 假设分割值大于0.5是目标区域

    # 使用Canny边缘检测
    edges = cv2.Canny(binary_image, 100, 200)

    # 获取边界点的坐标
    boundary_points = np.column_stack(np.where(edges > 0))  # 获取所有边缘点的坐标

    return boundary_points, binary_image

def draw_boundary_on_image(image, boundary_points):
    """
    在图像上绘制边界点。
    """
    image_with_boundary = image.copy()  # 创建图像副本，避免修改原图
    draw = ImageDraw.Draw(image_with_boundary)

    # 在图像上绘制边界点
    for point in boundary_points:
        draw.point((point[1], point[0]), fill='red')  # 绘制红色边界点

    return image_with_boundary
def save_boundary_points(boundary_points, img_name, output_dir):
    """
    保存边界点坐标为.npy文件。
    """
    # 保存为NumPy文件
    np.save(os.path.join(output_dir, img_name + "_boundary.npy"), boundary_points)

def save_image_with_boundary(image, file_path):
    """
    保存带有边界的图像。
    """
    image.save(file_path)

# 生成唯一的 output_id
def generate_output_id():
    return str(uuid.uuid4())

######以上为具体分割功能######

######数据库连接相关######
import pymysql

# 数据库连接函数 - 每次执行时创建连接，操作完后关闭连接
def get_db_connection():
    return pymysql.connect(
        host='1.117.69.116',  # 替换为实际的数据库主机地址
        user='flatness',  # 替换为实际的数据库用户名
        password='TXaRZbA4mHwPsPch',  # 替换为实际的数据库密码
        database='flatness',  # 替换为实际的数据库名称
        cursorclass=pymysql.cursors.DictCursor  # 查询返回字典
    )

# 插入数据库的函数
def insert_into_output_info(output_id, output_url, result,
                            edge_image_url,line_image_url,gradient_image_url,frequency_image_url,
                            edge_analysis,line_analysis,gradient_analysis,frequency_analysis,
                            edge_result,line_result,gradient_result,frequency_result):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """INSERT INTO outputInfo (output_id, output_url, result,
            edge_image_url,line_image_url,gradient_image_url,frequency_image_url,
            edge_analysis,line_analysis,gradient_analysis,frequency_analysis,
            edge_result,line_result,gradient_result,frequency_result) 
                       VALUES (%s, %s, %s,%s, %s, %s,%s, %s, %s,%s, %s, %s,%s, %s, %s)"""
            cursor.execute(query, (output_id, output_url, result,
                                   edge_image_url, line_image_url, gradient_image_url, frequency_image_url,
                                   edge_analysis, line_analysis, gradient_analysis, frequency_analysis,
                                   edge_result, line_result, gradient_result, frequency_result
                                   ))
            connection.commit()
            print(f"Inserted output info for {output_url}")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        if connection:
            connection.close()  # 关闭连接

# 插入历史数据的函数
def insert_into_historydata(userName, input_url, output_id, result,output_result_url):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """INSERT INTO historyData (user_name, input_url, output_id, timestamp, result,output_result_url)
                        VALUES (%s, %s, %s, %s, %s,%s)"""
            cursor.execute(query, (userName, input_url, output_id, timestamp, result,output_result_url))
            connection.commit()
            print(f"Inserted history data for {input_url}")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        if connection:
            connection.close()  # 关闭连接

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
######具体api######


def clean_directory(directory):
    """
    清理指定的目录，删除其中的所有文件。
    """
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # 删除目录及其中的所有内容
                else:
                    os.remove(file_path)  # 删除文件
            except Exception as e:
                print(f"Error cleaning {file_path}: {e}")
        print(f"Cleaned directory: {directory}")
    else:
        print(f"Directory {directory} does not exist.")
# 分割玻璃
@app.route('/flatness/detect', methods=['POST'])
def divide():
    data = request.get_json()
    print(data)
    url = data.get('url')
    username = data.get('username')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    if not username:
        return jsonify({'error': 'No username provided'}), 400
    try:
        input_path = downloadImage(url)
        # === 兼容M1/M2/M3/CPU/NVIDIA，统一用 .to(device) ===
        net = GDNet().to(device)
        if len(args['snapshot']) > 0:
            print('Load snapshot {} for testing'.format(args['snapshot']))
            # === 加 map_location，保证权重文件能跨平台加载 ===
            net.load_state_dict(torch.load('./model/200.pth', map_location=device))
        net.eval()
        with torch.no_grad():
            for name, root in {'GDD': './imgs'}.items():
                img_list = [img_name for img_name in os.listdir(root)]
                for idx, img_name in enumerate(img_list):
                    print(f'predicting for {name}: {idx + 1} / {len(img_list)}')
                    check_mkdir(os.path.join(gdd_results_root, f'{exp_name}_{args["snapshot"]}'))
                    img = Image.open(os.path.join(root, img_name))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        print(f"{name} is a gray image.")
                    w, h = img.size
                    img_var = Variable(img_transform(img).unsqueeze(0)).to(device)
                    f1, f2, f3 = net(img_var)
                    f3 = f3.data.squeeze(0).cpu()
                    from torchvision import transforms as T
                    to_pil = T.ToPILImage()
                    f3_pil = to_pil(f3)
                    f3_resized = T.Resize((h, w))(f3_pil)
                    f3 = np.array(f3_resized)
                    binary_path = os.path.join(gdd_results_root, f'{exp_name}_{args["snapshot"]}',
                                               img_name[:-4] + ".png")
                    Image.fromarray(f3).save(binary_path)
                    current_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
                    binary_url = upload_image(binary_path, f"sys/boundary/{current_datetime}.jpg", oss_url, upload_user_name,
                                              upload_user_password)
                    # 后处理、区域分割与上传等操作...
                    black_white_image = np.array(Image.open(binary_path))
                    original_image = np.array(Image.open(input_path))
                    contours = extract_white_regions(black_white_image)
                    segments = segment_from_original_image(original_image, contours)
                    check_mkdir(segments_dir)
                    save_segments(segments, segments_dir)
                    segment_urls = []
                    flat_results = []
                    img_list2 = os.listdir(segments_dir)
                    output_id = str(uuid.uuid4())
                    for seg_name in img_list2:
                        img_path = segments_dir + '/' + seg_name
                        target_path = f"sys/boundary/{current_datetime}/{seg_name}"
                        segment_url = upload_image(img_path, target_path, oss_url, upload_user_name, upload_user_password)
                        segment_urls.append(segment_url)
                        result = detect_glass_flatness(img_path, seg_name.replace('.png',''))
                        edge_url = upload_image(result['edge_image_path'],f"{target_path.replace('.png','')}-edge.jpg",
                                                oss_url, upload_user_name, upload_user_password)
                        line_url = upload_image(result['line_image_path'], f"{target_path.replace('.png','')}-line.jpg", oss_url,
                                                upload_user_name, upload_user_password)
                        gradient_url = upload_image(result['gradient_image_path'], f"{target_path.replace('.png','')}-gradient.jpg",
                                                    oss_url, upload_user_name, upload_user_password)
                        frequency_url = upload_image(result['frequency_image_path'], f"{target_path.replace('.png','')}-frequency.jpg",
                                                     oss_url, upload_user_name, upload_user_password)
                        flat_results.append(result['flatness_result'])
                        insert_into_output_info(output_id, segment_url, result['flatness_result'],
                                               edge_url, line_url, gradient_url, frequency_url,
                                               result['edge_analysis'], result['line_analysis'], result['gradient_analysis'], result['frequency_analysis'],
                                               result['edge_result'], result['line_result'], result['gradient_result'], result['frequency_result'])
                    result_image_path = draw_flatness_results(input_path, segments, flat_results)
                    result_image_url = upload_image(result_image_path, f"{target_path.replace('.png','')}-flatnessResult.jpg", oss_url,
                                                    upload_user_name, upload_user_password)
                    
                    clean_directory('./imgs')  
                    clean_directory('./output')
                    clean_directory('./temp_segments')  
                    if False in flat_results:
                        insert_into_historydata(username, url, output_id, 0, result_image_url)
                        return jsonify({"result": "不平整",
                                        "output_image": result_image_url,
                                        "output_id": output_id}), 200
                    else:
                        insert_into_historydata(username, url, output_id, 1, result_image_url)
                        return jsonify({"result": "平整",
                                        "output_image": result_image_url,
                                        "output_id": output_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
