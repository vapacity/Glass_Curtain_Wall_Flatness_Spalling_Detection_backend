"""
增强版性能测试脚本 - 包含OSS上传下载测试
"""

from locust import HttpUser, task, between, events
import json
import time
import random
from datetime import datetime
import os
import requests
from PIL import Image
import io
import base64

# 创建测试图片
def create_test_images():
    """创建不同大小的测试图片"""
    sizes = {
        'small': (800, 600),
        'medium': (1920, 1080),
        'large': (3840, 2160)
    }
    
    for name, size in sizes.items():
        filename = f'test_image_{name}.jpg'
        if not os.path.exists(filename):
            img = Image.new('RGB', size, color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            # 添加一些随机线条使图片更真实
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            for _ in range(100):
                x1, y1 = random.randint(0, size[0]), random.randint(0, size[1])
                x2, y2 = random.randint(0, size[0]), random.randint(0, size[1])
                draw.line((x1, y1, x2, y2), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), width=2)
            img.save(filename, quality=85)
            print(f"Created test image: {filename} ({os.path.getsize(filename)/1024:.1f}KB)")

# 创建测试图片
create_test_images()

# 测试数据 - 使用实际可访问的图片URL
TEST_IMAGES = [
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107155845.jpg",
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250601181315.jpg",
]

TEST_USERS = ["test_user1", "test_user2", "test_user3", "performance_test", "locust_test"]

# OSS配置
OSS_CONFIG = {
    "url": "http://110.42.214.164:9000",
    "userName": "flatness-detection",
    "password": "tongji-icw-3455"
}

class OSSPerformanceTest(HttpUser):
    """OSS上传下载性能测试"""
    
    wait_time = between(1, 3)
    host = OSS_CONFIG["url"]
    
    def on_start(self):
        """初始化"""
        self.test_files = [
            'test_image_small.jpg',
            'test_image_medium.jpg',
            'test_image_large.jpg'
        ]
    
    @task(3)
    def upload_to_oss(self):
        """测试OSS上传性能"""
        test_file = random.choice(self.test_files)
        if not os.path.exists(test_file):
            return
            
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        target_path = f"performance_test/{timestamp}_{test_file}"
        
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'image/jpeg')}
            data = {
                'userName': OSS_CONFIG['userName'],
                'password': OSS_CONFIG['password']
            }
            
            with self.client.post(
                f"/oss/upload/{target_path}",
                files=files,
                data=data,
                catch_response=True,
                name=f"/oss/upload ({os.path.getsize(test_file)/1024:.0f}KB)"
            ) as response:
                if response.status_code == 200:
                    try:
                        # 尝试解析JSON响应
                        result = response.json()
                        if 'downloadUrl' in result:
                            response.success()
                            # 保存URL供下载测试使用
                            if not hasattr(self, 'uploaded_urls'):
                                self.uploaded_urls = []
                            self.uploaded_urls.append(result['downloadUrl'])
                        else:
                            # 如果响应是纯文本URL
                            response.success()
                            if not hasattr(self, 'uploaded_urls'):
                                self.uploaded_urls = []
                            self.uploaded_urls.append(response.text.strip())
                    except:
                        # 如果不是JSON，可能是直接返回的URL
                        if response.text.startswith('http'):
                            response.success()
                            if not hasattr(self, 'uploaded_urls'):
                                self.uploaded_urls = []
                            self.uploaded_urls.append(response.text.strip())
                        else:
                            response.failure("响应格式错误")
                else:
                    response.failure(f"上传失败: {response.status_code}")
    
    @task(2)
    def download_from_oss(self):
        """测试OSS下载性能"""
        # 使用预设的测试图片URL或已上传的URL
        if hasattr(self, 'uploaded_urls') and self.uploaded_urls:
            url = random.choice(self.uploaded_urls)
        else:
            url = random.choice(TEST_IMAGES)
        
        # 提取路径部分
        path = url.replace(f"{OSS_CONFIG['url']}/oss/download/", "")
        
        with self.client.get(
            f"/oss/download/{path}",
            catch_response=True,
            name="/oss/download"
        ) as response:
            if response.status_code == 200:
                # 验证是否为图片
                try:
                    Image.open(io.BytesIO(response.content))
                    response.success()
                except:
                    response.failure("下载的内容不是有效图片")
            else:
                response.failure(f"下载失败: {response.status_code}")


class FlatnessDetectionUser(HttpUser):
    """平整度检测系统性能测试（优化版）"""
    
    wait_time = between(2, 5)
    host = "http://localhost:8080"
    
    def on_start(self):
        """初始化用户数据"""
        self.username = random.choice(TEST_USERS)
        self.test_images = TEST_IMAGES.copy()
        random.shuffle(self.test_images)
        # 初始化一个空的output_ids列表
        self.output_ids = []
    
    @task(3)
    def detect_flatness(self):
        """测试平整度检测接口"""
        image_url = random.choice(self.test_images)
        
        test_data = {
            "url": image_url,
            "username": self.username
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/flatness/detect", 
            json=test_data,
            catch_response=True,
            name="/flatness/detect",
            timeout=120  # 增加超时时间，因为图像处理可能需要较长时间
        ) as response:
            total_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "result" in result and "output_id" in result:
                        response.success()
                        self.output_ids.append(result["output_id"])
                        print(f"检测成功: {result['result']}, 耗时: {total_time:.0f}ms")
                    else:
                        response.failure(f"响应格式错误: {result}")
                except Exception as e:
                    response.failure(f"JSON解析失败: {str(e)}")
            elif response.status_code == 500:
                response.failure(f"服务器错误: {response.text}")
            else:
                response.failure(f"状态码: {response.status_code}, 响应: {response.text[:100]}")
    
    @task(2)
    def get_history(self):
        """测试历史记录查询接口"""
        with self.client.get(
            f"/flatness/history?username={self.username}",
            catch_response=True,
            name="/flatness/history"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "history" in result:
                        response.success()
                    else:
                        response.failure(f"响应格式错误: {result}")
                except Exception as e:
                    response.failure(f"JSON解析失败: {str(e)}")
            else:
                response.failure(f"状态码: {response.status_code}")
    
    @task(1)
    def get_detail(self):
        """测试详情查询接口"""
        if self.output_ids:
            output_id = random.choice(self.output_ids)
            with self.client.get(
                f"/flatness/getDetail?username={self.username}&outputId={output_id}",
                catch_response=True,
                name="/flatness/getDetail"
            ) as response:
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if "result" in result:
                            response.success()
                        else:
                            response.failure(f"响应格式错误: {result}")
                    except Exception as e:
                        response.failure(f"JSON解析失败: {str(e)}")
                else:
                    response.failure(f"状态码: {response.status_code}")


class SpallingDetectionUser(HttpUser):
    """爆裂检测系统性能测试（优化版）"""
    
    wait_time = between(2, 5)
    host = "http://localhost:9090"
    
    def on_start(self):
        """初始化用户数据"""
        self.username = random.choice(TEST_USERS)
        self.test_images = TEST_IMAGES.copy()
        random.shuffle(self.test_images)
        self.uploaded_urls = []
    
    @task(1)
    def upload_image(self):
        """测试图片上传接口"""
        test_file = 'test_image_small.jpg'
        if not os.path.exists(test_file):
            create_test_images()
            
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'image/jpeg')}
            
            with self.client.post(
                "/defect/upload",
                files=files,
                catch_response=True,
                name="/defect/upload"
            ) as response:
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if "downloadUrl" in result:
                            response.success()
                            self.uploaded_urls.append(result["downloadUrl"])
                        else:
                            response.failure(f"响应格式错误: {result}")
                    except Exception as e:
                        response.failure(f"JSON解析失败: {str(e)}")
                else:
                    response.failure(f"状态码: {response.status_code}")
    
    @task(3)
    def classify_defect(self):
        """测试缺陷分类接口"""
        image_url = random.choice(self.test_images)
        
        data = {
            'url': image_url,
            'username': self.username
        }
        
        with self.client.post(
            "/defect/classify",
            data=data,
            catch_response=True,
            name="/defect/classify",
            timeout=60
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "result" in result:
                        response.success()
                        print(f"分类结果: {result['result']}")
                    else:
                        response.failure(f"响应格式错误: {result}")
                except Exception as e:
                    response.failure(f"JSON解析失败: {str(e)}")
            else:
                response.failure(f"状态码: {response.status_code}, 响应: {response.text[:100]}")
    
    @task(2)
    def show_defect(self):
        """测试缺陷显示接口"""
        image_url = random.choice(self.test_images)
        
        data = {
            'url': image_url,
            'username': self.username
        }
        
        with self.client.post(
            "/defect/showDefect",
            data=data,
            catch_response=True,
            name="/defect/showDefect",
            timeout=60
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "downloadUrl" in result:
                        response.success()
                    else:
                        response.failure(f"响应格式错误: {result}")
                except Exception as e:
                    response.failure(f"JSON解析失败: {str(e)}")
            else:
                response.failure(f"状态码: {response.status_code}")


# 统计信息收集
performance_stats = {
    "start_time": None,
    "requests": [],
    "errors": [],
    "oss_upload_times": [],
    "oss_download_times": [],
    "detection_times": []
}

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """记录每个请求的详细信息"""
    req_data = {
        "timestamp": datetime.now().isoformat(),
        "type": request_type,
        "name": name,
        "response_time": response_time,
        "response_length": response_length,
        "status_code": response.status_code if response else None
    }
    
    performance_stats["requests"].append(req_data)
    
    # 分类记录不同类型请求的响应时间
    if "oss/upload" in name:
        performance_stats["oss_upload_times"].append(response_time)
    elif "oss/download" in name:
        performance_stats["oss_download_times"].append(response_time)
    elif "detect" in name or "classify" in name:
        performance_stats["detection_times"].append(response_time)

@events.request_failure.add_listener
def on_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """记录失败的请求"""
    performance_stats["errors"].append({
        "timestamp": datetime.now().isoformat(),
        "type": request_type,
        "name": name,
        "response_time": response_time,
        "exception": str(exception)
    })

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的初始化"""
    performance_stats["start_time"] = datetime.now().isoformat()
    print(f"性能测试开始时间: {performance_stats['start_time']}")
    print(f"目标主机: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时生成报告"""
    print(f"\n性能测试结束，共完成 {len(performance_stats['requests'])} 个请求")
    print(f"失败请求数: {len(performance_stats['errors'])}")
    
    # 计算统计信息
    if performance_stats["oss_upload_times"]:
        avg_upload = sum(performance_stats["oss_upload_times"]) / len(performance_stats["oss_upload_times"])
        print(f"OSS上传平均耗时: {avg_upload:.0f}ms")
    
    if performance_stats["oss_download_times"]:
        avg_download = sum(performance_stats["oss_download_times"]) / len(performance_stats["oss_download_times"])
        print(f"OSS下载平均耗时: {avg_download:.0f}ms")
    
    if performance_stats["detection_times"]:
        avg_detection = sum(performance_stats["detection_times"]) / len(performance_stats["detection_times"])
        print(f"检测接口平均耗时: {avg_detection:.0f}ms")
    
    # 保存详细的性能数据
    with open('performance_results_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(performance_stats, f, indent=2, ensure_ascii=False)
    
    print("\n详细测试结果已保存到 performance_results_enhanced.json")


if __name__ == "__main__":
    print("增强版性能测试脚本")
    print("\n可用的测试类:")
    print("1. OSSPerformanceTest - OSS上传下载性能测试")
    print("2. FlatnessDetectionUser - 平整度检测系统测试")
    print("3. SpallingDetectionUser - 爆裂检测系统测试")
    print("\n运行示例:")
    print("OSS测试: locust -f performance_test_enhanced.py OSSPerformanceTest --host=http://110.42.214.164:9000")
    print("平整度检测: locust -f performance_test_enhanced.py FlatnessDetectionUser --host=http://localhost:8080")
    print("爆裂检测: locust -f performance_test_enhanced.py SpallingDetectionUser --host=http://localhost:9090")
    print("\n无界面运行:")
    print("locust -f performance_test_enhanced.py OSSPerformanceTest --host=http://110.42.214.164:9000 --headless -u 10 -r 2 -t 5m")