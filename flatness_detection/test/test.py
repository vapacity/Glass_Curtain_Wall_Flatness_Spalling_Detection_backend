import os
import pytest
import requests

# BASE_URL = "http://localhost:8002/flatness"
TEST_IMAGE_PATH = "test.jpg"
USERNAME = "zwj"   # ← 把用户名设成常量

@pytest.fixture(scope="session", autouse=True)
def ensure_service_up():
    try:
        r = requests.get(
            f"{BASE_URL}/history",
            params={"username": USERNAME},
            timeout=5
        )
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f"跳过：平整度检测服务不可达 → {e}")

@pytest.fixture(scope="session")
def upload_url():
    assert os.path.exists(TEST_IMAGE_PATH), "请在项目根目录放一张 test.jpg 用来测试上传"
    with open(TEST_IMAGE_PATH, "rb") as f:
        files = {"file": f}
        data = {"username": USERNAME}
        r = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data,
            timeout=10
        )
    assert r.status_code == 200, f"【/upload】返回 {r.status_code}"
    resp = r.json()
    assert "downloadUrl" in resp, f"返回体中缺少 downloadUrl → {resp}"
    return resp["downloadUrl"]

def test_segment(upload_url):
    """
    POST /segment
    请求参数: url: String, username: String
    返回: result: String[]
    """
    payload = {
        "url": upload_url,
        "username": USERNAME,
    }
    r = requests.post(
        f"{BASE_URL}/segment",
        data=payload,
        timeout=15
    )
    assert r.status_code == 200, f"【/segment】返回 {r.status_code}"
    data = r.json()
    assert "result" in data, data
    assert isinstance(data["result"], list), f"result 应为数组 → {data}"

def test_detect(upload_url):
    """
    POST /detect
    请求参数: url: String, username: String
    返回: result: String[]
    """
    payload = {
        "url": upload_url,
        "username": USERNAME,
    }
    r = requests.post(
        f"{BASE_URL}/detect",
        data=payload,
        timeout=15
    )
    assert r.status_code == 200, f"【/detect】返回 {r.status_code}"
    data = r.json()
    assert "result" in data, data
    assert isinstance(data["result"], list), f"result 应为数组 → {data}"

def test_history():
    """
    GET /history
    请求参数: username: String
    返回: history: flatnessHistoryDto (list)
    """
    r = requests.get(
        f"{BASE_URL}/history",
        params={"username": USERNAME},
        timeout=5
    )
    assert r.status_code == 200, f"【/history】返回 {r.status_code}"
    data = r.json()
    assert "history" in data, data
    assert isinstance(data["history"], list), f"history 应为列表 → {data}"
