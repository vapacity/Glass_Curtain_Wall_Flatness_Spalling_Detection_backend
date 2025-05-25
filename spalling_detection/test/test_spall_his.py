import pytest
from unittest.mock import patch
from flask import json

# 被测试模块路径为 spalling.service.app
from spalling.service.app import app, get_spalling_history

upload_user_name = "spalling-detection"

# 创建测试客户端
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 测试 get_spalling_history 函数
def test_get_spalling_history():
    # 模拟返回历史记录
    result = get_spalling_history(upload_user_name)
    assert isinstance(result, list)
    for item in result:
        assert 'filename' in item
        assert 'result' in item
        assert 'timestamp' in item

# 测试 /spalling/history 接口
def test_spalling_history_api(client):
    # 缺少用户名参数
    response = client.post('/spalling/history')
    assert response.status_code == 400
    assert b'No username provided' in response.data

    # 模拟数据库返回记录
    mock_data = [
        {
            "filename": "upload/20250501.jpg",
            "result": "defect",
            "timestamp": "2025-05-25 10:00:00"
        },
        {
            "filename": "upload/20250502.jpg",
            "result": "undefect",
            "timestamp": "2025-05-24 11:00:00"
        }
    ]

    with patch('spalling.service.app.get_spalling_history') as mock_func:
        mock_func.return_value = mock_data
        response = client.post('/spalling/history', data={'username': upload_user_name})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['result'] == 'defect'
