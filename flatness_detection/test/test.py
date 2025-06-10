"""
平整度检测服务的集成测试模块

本模块包含了对玻璃幕墙平整度检测服务的完整API测试，包括：
- 图片上传功能测试
- 图像分割功能测试  
- 平整度检测功能测试
- 历史记录查询功能测试

测试前提条件：
1. 平整度检测服务必须在 http://localhost:8002/flatness 运行
2. 测试目录下必须存在 test.jpg 文件作为测试图片
"""

import os
import pytest
import requests

# 平整度检测服务的基础URL地址
BASE_URL = "http://localhost:8002/flatness"

# 测试用的图片文件路径
TEST_IMAGE_PATH = "test.jpg"

# 测试用的用户名常量
USERNAME = "zwj"

@pytest.fixture(scope="session", autouse=True)
def ensure_service_up():
    """
    会话级别的自动运行fixture，用于确保服务可用
    
    在所有测试开始前自动运行，通过调用历史记录接口来检查服务是否正常运行。
    如果服务不可达，则跳过所有测试。
    
    Raises:
        pytest.skip: 当服务不可达时跳过测试
    """
    try:
        # 尝试调用历史记录接口来检查服务状态
        r = requests.get(
            f"{BASE_URL}/history",
            params={"username": USERNAME},
            timeout=5
        )
        r.raise_for_status()
    except Exception as e:
        # 服务不可达时跳过所有测试
        pytest.skip(f"跳过：平整度检测服务不可达 → {e}")

@pytest.fixture(scope="session")
def upload_url():
    """
    会话级别的fixture，用于上传测试图片并返回下载URL
    
    该fixture会在第一次使用时执行，上传test.jpg文件到服务器，
    并返回可用于后续测试的图片下载URL。同一测试会话中多次调用
    会返回相同的URL，避免重复上传。
    
    Returns:
        str: 上传后的图片下载URL
        
    Raises:
        AssertionError: 当测试图片不存在或上传失败时
    """
    # 确保测试图片存在
    assert os.path.exists(TEST_IMAGE_PATH), "请在项目根目录放一张 test.jpg 用来测试上传"
    
    # 上传图片到服务器
    with open(TEST_IMAGE_PATH, "rb") as f:
        files = {"file": f}
        data = {"username": USERNAME}
        r = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data,
            timeout=10
        )
    
    # 验证上传成功
    assert r.status_code == 200, f"【/upload】返回 {r.status_code}"
    resp = r.json()
    assert "downloadUrl" in resp, f"返回体中缺少 downloadUrl → {resp}"
    
    # 返回图片的下载URL供后续测试使用
    return resp["downloadUrl"]

def test_segment(upload_url):
    """
    测试图像分割接口 POST /segment
    
    该接口用于对上传的玻璃幕墙图片进行分割处理，识别出各个玻璃面板区域。
    
    请求参数:
        - url: String - 图片的下载URL
        - username: String - 用户名
    
    返回格式:
        - result: String[] - 分割后的图片URL列表
        
    Args:
        upload_url (str): 由fixture提供的已上传图片的URL
    """
    # 构造请求参数
    payload = {
        "url": upload_url,
        "username": USERNAME,
    }
    
    # 调用分割接口
    r = requests.post(
        f"{BASE_URL}/segment",
        data=payload,
        timeout=15  # 图像处理可能需要较长时间
    )
    
    # 验证响应
    assert r.status_code == 200, f"【/segment】返回 {r.status_code}"
    data = r.json()
    
    # 验证返回数据结构
    assert "result" in data, data
    assert isinstance(data["result"], list), f"result 应为数组 → {data}"

def test_detect(upload_url):
    """
    测试平整度检测接口 POST /detect
    
    该接口是核心功能接口，用于检测玻璃幕墙的平整度问题。
    会对图片中的玻璃面板进行分析，识别可能存在的不平整区域。
    
    请求参数:
        - url: String - 图片的下载URL
        - username: String - 用户名
    
    返回格式:
        - result: String[] - 检测结果图片URL列表，包含标注的不平整区域
        
    Args:
        upload_url (str): 由fixture提供的已上传图片的URL
    """
    # 构造请求参数
    payload = {
        "url": upload_url,
        "username": USERNAME,
    }
    
    # 调用检测接口
    r = requests.post(
        f"{BASE_URL}/detect",
        data=payload,
        timeout=15  # 检测算法可能需要较长时间
    )
    
    # 验证响应
    assert r.status_code == 200, f"【/detect】返回 {r.status_code}"
    data = r.json()
    
    # 验证返回数据结构
    assert "result" in data, data
    assert isinstance(data["result"], list), f"result 应为数组 → {data}"

def test_history():
    """
    测试历史记录查询接口 GET /history
    
    该接口用于查询指定用户的平整度检测历史记录。
    可以查看用户之前上传和检测的所有图片记录。
    
    请求参数:
        - username: String - 用户名（通过URL参数传递）
    
    返回格式:
        - history: flatnessHistoryDto[] - 历史记录列表
          每条记录包含：检测时间、原图URL、检测结果等信息
    """
    # 发送GET请求查询历史记录
    r = requests.get(
        f"{BASE_URL}/history",
        params={"username": USERNAME},
        timeout=5
    )
    
    # 验证响应
    assert r.status_code == 200, f"【/history】返回 {r.status_code}"
    data = r.json()
    
    # 验证返回数据结构
    assert "history" in data, data
    assert isinstance(data["history"], list), f"history 应为列表 → {data}"
    
    # 历史记录可能为空列表，这是正常的
    # 如果有历史记录，每条记录应该包含必要的字段
    if data["history"]:
        # 可以进一步验证历史记录的结构
        for record in data["history"]:
            # 这里可以根据实际的flatnessHistoryDto结构添加更多验证
            assert isinstance(record, dict), f"历史记录项应为字典 → {record}"
