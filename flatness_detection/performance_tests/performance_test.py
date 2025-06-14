"""
玻璃幕墙检测系统性能测试脚本
使用Locust进行性能测试
"""

from locust import HttpUser, task, between, events
import json
import time
import random
from datetime import datetime

# 测试数据
TEST_IMAGES = [
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",  # 小图片
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107155845.jpg", # 中等图片
    "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250601181315.jpg",  # 大图片
]

TEST_USERS = ["zwj", "zwj", "zwj", "zwj", "zwj"]

class FlatnessDetectionUser(HttpUser):
    """平整度检测系统性能测试"""
    
    wait_time = between(1, 3)
    host = "http://localhost:8080"
    
    def on_start(self):
        """初始化用户数据"""
        self.username = random.choice(TEST_USERS)
        self.test_images = TEST_IMAGES.copy()
        random.shuffle(self.test_images)
    
    @task(3)
    def detect_flatness(self):
        """测试平整度检测接口"""
        image_url = random.choice(self.test_images)
        
        test_data = {
            "url": image_url,
            "username": self.username
        }
        
        with self.client.post(
            "/flatness/detect", 
            json=test_data,
            catch_response=True,
            name="/flatness/detect"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "result" in result and "output_id" in result:
                        response.success()
                        # 保存output_id供后续查询使用
                        if not hasattr(self, 'output_ids'):
                            self.output_ids = []
                        self.output_ids.append(result["output_id"])
                    else:
                        response.failure("响应格式错误")
                except json.JSONDecodeError:
                    response.failure("JSON解析失败")
            else:
                response.failure(f"状态码: {response.status_code}")
    
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
                        response.failure("响应格式错误")
                except json.JSONDecodeError:
                    response.failure("JSON解析失败")
            else:
                response.failure(f"状态码: {response.status_code}")
    
    @task(1)
    def get_detail(self):
        """测试详情查询接口"""
        if hasattr(self, 'output_ids') and self.output_ids:
            output_id = random.choice(self.output_ids)
            with self.client.get(
                f"/flatness/getDetail?username={self.username}&outputId={output_id}",
                catch_response=True,
                name="/flatness/getDetail"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"状态码: {response.status_code}")


class SpallingDetectionUser(HttpUser):
    """爆裂检测系统性能测试"""
    
    wait_time = between(1, 3)
    host = "http://localhost:9090"
    
    def on_start(self):
        """初始化用户数据"""
        self.username = random.choice(TEST_USERS)
        self.test_images = TEST_IMAGES.copy()
        random.shuffle(self.test_images)
    
    @task(1)
    def upload_image(self):
        """测试图片上传接口"""
        # 模拟文件上传（实际测试时需要真实的图片文件）
        with open('test_image.jpg', 'rb') as f:
            files = {'file': ('test.jpg', f, 'image/jpeg')}
            
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
                            # 保存URL供后续使用
                            if not hasattr(self, 'uploaded_urls'):
                                self.uploaded_urls = []
                            self.uploaded_urls.append(result["downloadUrl"])
                        else:
                            response.failure("响应格式错误")
                    except json.JSONDecodeError:
                        response.failure("JSON解析失败")
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
            name="/defect/classify"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "result" in result:
                        response.success()
                    else:
                        response.failure("响应格式错误")
                except json.JSONDecodeError:
                    response.failure("JSON解析失败")
            else:
                response.failure(f"状态码: {response.status_code}")
    
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
            name="/defect/showDefect"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "downloadUrl" in result:
                        response.success()
                    else:
                        response.failure("响应格式错误")
                except json.JSONDecodeError:
                    response.failure("JSON解析失败")
            else:
                response.failure(f"状态码: {response.status_code}")
    
    @task(1)
    def get_history(self):
        """测试历史记录查询接口"""
        with self.client.get(
            f"/defect/history?username={self.username}",
            catch_response=True,
            name="/defect/history"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "history" in result:
                        response.success()
                    else:
                        response.failure("响应格式错误")
                except json.JSONDecodeError:
                    response.failure("JSON解析失败")
            else:
                response.failure(f"状态码: {response.status_code}")


# 自定义统计信息收集
performance_stats = {
    "start_time": None,
    "requests": [],
    "errors": []
}

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """记录每个请求的详细信息"""
    performance_stats["requests"].append({
        "timestamp": datetime.now().isoformat(),
        "type": request_type,
        "name": name,
        "response_time": response_time,
        "response_length": response_length,
        "status_code": response.status_code if response else None
    })

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的初始化"""
    performance_stats["start_time"] = datetime.now().isoformat()
    print(f"性能测试开始时间: {performance_stats['start_time']}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时生成报告"""
    print(f"性能测试结束，共完成 {len(performance_stats['requests'])} 个请求")
    
    # 保存详细的性能数据
    with open('performance_results.json', 'w') as f:
        json.dump(performance_stats, f, indent=2)


if __name__ == "__main__":
    # 可以直接运行此脚本进行测试
    # locust -f performance_test.py --host=http://localhost:8080
    print("请使用以下命令运行性能测试:")
    print("平整度检测系统: locust -f performance_test.py FlatnessDetectionUser --host=http://localhost:8080")
    print("爆裂检测系统: locust -f performance_test.py SpallingDetectionUser --host=http://localhost:9090")