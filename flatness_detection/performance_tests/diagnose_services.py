"""
诊断服务状态和接口可用性
"""

import requests
import json

def check_service_status():
    """检查服务运行状态"""
    print("=== 检查服务状态 ===\n")
    
    # 检查平整度检测服务
    print("1. 平整度检测服务 (端口 8080):")
    try:
        # 尝试访问历史记录接口（通常是最简单的接口）
        response = requests.get("http://localhost:8080/flatness/history?username=zwj", timeout=5)
        print(f"   状态: 运行中")
        print(f"   响应状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应内容: {response.text[:100]}...")
    except requests.exceptions.ConnectionError:
        print("   状态: 未运行或无法连接")
    except Exception as e:
        print(f"   错误: {e}")
    
    print("\n2. 爆裂检测服务 (端口 9090):")
    try:
        response = requests.get("http://localhost:9090/defect/history?username=zwj", timeout=5)
        print(f"   状态: 运行中")
        print(f"   响应状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应内容: {response.text[:100]}...")
    except requests.exceptions.ConnectionError:
        print("   状态: 未运行或无法连接")
    except Exception as e:
        print(f"   错误: {e}")

def test_image_urls():
    """测试图片URL的可访问性"""
    print("\n\n=== 测试图片URL可访问性 ===\n")
    
    test_urls = [
        "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",
        "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107155845.jpg",
        "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250601181315.jpg",
    ]
    
    valid_urls = []
    
    for url in test_urls:
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {url} - 可访问")
                valid_urls.append(url)
            else:
                print(f"✗ {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"✗ {url} - 错误: {e}")
    
    return valid_urls

def test_api_endpoints():
    """测试API端点"""
    print("\n\n=== 测试API端点 ===\n")
    
    # 测试平整度检测接口
    print("1. 测试平整度检测接口:")
    test_data = {
        "url": "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",
        "username": "zwj"
    }
    
    try:
        response = requests.post("http://localhost:8080/flatness/detect", json=test_data, timeout=30)
        print(f"   状态码: {response.status_code}")
        print(f"   响应时间: {response.elapsed.total_seconds():.2f}秒")
        if response.status_code == 200:
            result = response.json()
            print(f"   响应内容: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"   错误响应: {response.text[:200]}...")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试爆裂检测接口
    print("\n2. 测试爆裂检测接口:")
    test_data = {
        'url': 'http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg',
        'username': 'zwj'
    }
    
    try:
        response = requests.post("http://localhost:9090/defect/classify", data=test_data, timeout=30)
        print(f"   状态码: {response.status_code}")
        print(f"   响应时间: {response.elapsed.total_seconds():.2f}秒")
        if response.status_code == 200:
            result = response.json()
            print(f"   响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"   错误响应: {response.text[:200]}...")
    except Exception as e:
        print(f"   错误: {e}")

def suggest_fixes():
    """提供修复建议"""
    print("\n\n=== 修复建议 ===\n")
    
    print("如果服务未运行:")
    print("1. 启动平整度检测服务:")
    print("   cd ICW_FlatnessDetection_Backend")
    print("   python app.py")
    print("")
    print("2. 启动爆裂检测服务:")
    print("   cd ICW_SpallingDetection_Backend")
    print("   python app.py")
    print("")
    print("如果测试失败:")
    print("1. 检查服务日志中的错误信息")
    print("2. 确保数据库连接正常")
    print("3. 确保模型文件已下载")
    print("4. 检查OSS服务是否可访问")

def main():
    print("开始诊断服务...\n")
    
    # 1. 检查服务状态
    check_service_status()
    
    # 2. 测试图片URL
    valid_urls = test_image_urls()
    
    # 3. 测试API端点
    test_api_endpoints()
    
    # 4. 提供修复建议
    suggest_fixes()
    
    print("\n诊断完成!")

if __name__ == "__main__":
    main()