import pytest
import torch
import os
from PIL import Image
from io import BytesIO
from datetime import datetime
from unittest.mock import patch, MagicMock

# 导入被测试的应用
from app import app, downloadImage, upload_image

upload_user_name = "spalling-detection"
upload_user_password = "tongji-icw-1805"
oss_url = "http://110.42.214.164:9000"

# 创建测试客户端
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 测试 upload_image 函数
def test_upload_image():
    # 测试上传成功
    time = datetime.now().strftime('%Y%m%d%H%M%S')
    result = upload_image('test_file.jpg', f"user/upload/{time}.jpg", oss_url, upload_user_name, upload_user_password)
    assert result.startswith("http://110.42.214.164:9000/oss/download/spalling-detection/user/upload/")
    
    # 测试上传失败
    result = upload_image("test_file.jpg", f"user/upload/{time}.jpg", oss_url, "user", "pass")
    assert result.startswith("Failed to upload image")

# 测试 downloadImage 函数
def test_downloadImage():
    # 测试下载成功
    url = "http://110.42.214.164:9000/oss/download/spalling-detection/user/upload/20250511184006.jpg"
    result = downloadImage(url)
    assert result == "tmp_image.jpg"
    assert os.path.exists("tmp_image.jpg")
    os.remove("tmp_image.jpg")  # 清理临时文件
    
    # 测试下载失败
    url = "http://example.com/example.jpg"
    result = downloadImage(url)
    assert result is None

# 测试 /defect/upload 接口
def test_upload(client):
    # 测试没有文件的情况
    response = client.post('/defect/upload')
    assert response.status_code == 400
    assert b'No file part' in response.data
    
    # 测试空文件名
    data = {'file': (BytesIO(b"image data"), '')}
    response = client.post('/defect/upload', data=data)
    assert response.status_code == 400
    assert b'No selected file' in response.data
    
    # 测试成功上传（使用模拟的upload_image）
    with patch('app.upload_image') as mock_upload:
        mock_upload.return_value = "http://example.com/uploaded.jpg"
        data = {'file': (BytesIO(b"image data"), 'test.jpg')}
        response = client.post('/defect/upload', data=data)
        assert response.status_code == 200
        assert b'http://example.com/uploaded.jpg' in response.data

# 测试 /defect/classify 接口
def test_classify(client):
    # 测试缺少参数
    response = client.post('/defect/classify')
    assert response.status_code == 400
    assert b'No image URL or username provided' in response.data
    
    # 测试下载失败
    with patch('app.downloadImage') as mock_download:
        mock_download.return_value = None
        data = {'url': 'http://example.com/image.jpg', 'username': upload_user_name}
        response = client.post('/defect/classify', data=data)
        assert response.status_code == 400
        assert b'Failed to download image from the URL' in response.data
    
    # 测试分类成功（使用模拟的模型）
    # 测试defect情况
    data = {'url': 'http://110.42.214.164:9000/oss/download/spalling-detection/user/upload/20250511184006.jpg', 'username': upload_user_name}
    response = client.post('/defect/classify', data=data)
    assert response.status_code == 200
    assert b'"result":"defect"' in response.data
    
    # 测试undefect情况
    data = {'url': 'http://110.42.214.164:9000/oss/download/spalling-detection/user/upload/20250107150325.jpg', 'username': upload_user_name}
    response = client.post('/defect/classify', data=data)
    assert response.status_code == 200
    assert b'"result":"undefect"' in response.data


# 测试 /defect/showDefect 接口
def test_show_defect(client):
    # 测试缺少参数
    response = client.post('/defect/showDefect')
    assert response.status_code == 400
    assert b'No image URL or username provided' in response.data
    
    # 测试下载失败
    with patch('app.downloadImage') as mock_download:
        mock_download.return_value = None
        data = {'url': 'http://example.com/image.jpg', 'username': upload_user_name}
        response = client.post('/defect/showDefect', data=data)
        assert response.status_code == 400
        assert b'Failed to download image from the URL' in response.data
    
    # 测试成功处理（使用模拟的process_image和upload_image）
    with patch('app.downloadImage') as mock_download, \
         patch('script.process_image') as mock_process, \
         patch('app.upload_image') as mock_upload:
        
        mock_download.return_value = "test_image.jpg"
        mock_process.return_value = "processed_image.jpg"
        mock_upload.return_value = "http://example.com/processed.jpg"
        
        data = {'url': 'http://example.com/image.jpg', 'username': upload_user_name}
        response = client.post('/defect/showDefect', data=data)
        assert response.status_code == 200
        assert b'http://example.com/processed.jpg' in response.data
