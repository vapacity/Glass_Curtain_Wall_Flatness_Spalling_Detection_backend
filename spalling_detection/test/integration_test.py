import unittest
import requests
import os
from datetime import datetime, timedelta
import random
import string

class SpallingDetectionSystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """测试类初始化设置"""
        cls.base_url = "http://localhost:8080"
        cls.test_username = "testuser_" + ''.join(random.choices(string.ascii_lowercase, k=5))
        cls.valid_image_url = "http://110.42.214.164:9000/user/upload/test.jpg"
        cls.invalid_image_url = "http://invalid.url/nonexistent.jpg"
        
        # 创建一个临时测试图片
        cls.test_image_path = "test_file.jpg"

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        if os.path.exists(cls.test_image_path):
            os.remove(cls.test_image_path)

    def test_1_test_endpoint(self):
        """测试基础/test接口"""
        response = requests.get(f"{self.base_url}/test")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "Hello, World!")

    def test_2_upload_image(self):
        """测试图片上传功能"""
        # 正常上传测试
        with open(self.test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/defect/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("downloadUrl", json_data)
        self.assertTrue(json_data["downloadUrl"].startswith("http"))
        
        # 保存上传的URL供后续测试使用
        self.__class__.uploaded_image_url = json_data["downloadUrl"]
        
        # 异常测试 - 无文件上传
        response = requests.post(f"{self.base_url}/defect/upload")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        
        # 异常测试 - 空文件名
        files = {'file': ('', open(self.test_image_path, 'rb'))}
        response = requests.post(f"{self.base_url}/defect/upload", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_3_classify_image(self):
        """测试图片分类功能"""
        # 使用之前上传的图片URL进行测试
        test_url = getattr(self, 'uploaded_image_url', self.valid_image_url)
        
        # 正常分类测试
        data = {
            'url': test_url,
            'username': self.test_username
        }
        response = requests.post(f"{self.base_url}/defect/classify", data=data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("result", json_data)
        self.assertIn(json_data["result"], ['defect', 'undefect'])
        
        # 保存分类结果供后续测试使用
        self.__class__.classification_result = json_data["result"]
        
        # 异常测试 - 缺少参数
        response = requests.post(f"{self.base_url}/defect/classify", data={'url': test_url})
        self.assertEqual(response.status_code, 400)
        
        response = requests.post(f"{self.base_url}/defect/classify", data={'username': self.test_username})
        self.assertEqual(response.status_code, 400)
        
        # 异常测试 - 无效图片URL
        data = {
            'url': self.invalid_image_url,
            'username': self.test_username
        }
        response = requests.post(f"{self.base_url}/defect/classify", data=data)
        self.assertEqual(response.status_code, 400)

    def test_4_show_defect(self):
        """测试显示缺陷功能"""
        # 只有当分类结果为defect时才测试此功能
        if getattr(self, 'classification_result', None) != 'defect':
            self.skipTest("Classification result is not 'defect', skipping showDefect test")
        
        test_url = getattr(self, 'uploaded_image_url', self.valid_image_url)
        
        # 正常显示缺陷测试
        data = {
            'url': test_url,
            'username': self.test_username
        }
        response = requests.post(f"{self.base_url}/defect/showDefect", data=data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("downloadUrl", json_data)
        self.assertTrue(json_data["downloadUrl"].startswith("http"))
        
        # 保存处理后的URL供历史记录测试使用
        self.__class__.processed_image_url = json_data["downloadUrl"]
        
        # 异常测试 - 无效图片URL
        data = {
            'url': self.invalid_image_url,
            'username': self.test_username
        }
        response = requests.post(f"{self.base_url}/defect/showDefect", data=data)
        self.assertEqual(response.status_code, 400)

    def test_5_history_query(self):
        """测试历史记录查询功能"""
        # 等待1秒确保记录已写入数据库
        import time
        time.sleep(1)
        
        # 正常查询测试
        params = {'username': self.test_username}
        response = requests.get(f"{self.base_url}/defect/history", params=params)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("history", json_data)
        self.assertIsInstance(json_data["history"], list)
        
        # 验证历史记录内容
        if json_data["history"]:
            history_item = json_data["history"][0]
            self.assertEqual(history_item["userName"], self.test_username)
            self.assertIn("inputImg", history_item)
            self.assertIn("outputImg", history_item)
            self.assertIn("result", history_item)
            self.assertIn("timestamp", history_item)
            
            # 验证时间戳是最近的时间
            timestamp = datetime.strptime(history_item["timestamp"], '%Y-%m-%d %H:%M:%S')
            self.assertLess(datetime.now() - timestamp, timedelta(minutes=5))
        
        # 异常测试 - 缺少username参数
        response = requests.get(f"{self.base_url}/defect/history")
        self.assertEqual(response.status_code, 400)
        
        # 异常测试 - 不存在的用户
        params = {'username': 'nonexistent_user_123'}
        response = requests.get(f"{self.base_url}/defect/history", params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["history"]), 0)

    def test_6_full_workflow(self):
        """测试完整工作流程: 上传->分类->显示缺陷->查询历史"""
        # 1. 上传图片
        with open(self.test_image_path, 'rb') as f:
            files = {'file': f}
            upload_response = requests.post(f"{self.base_url}/defect/upload", files=files)
        self.assertEqual(upload_response.status_code, 200)
        uploaded_url = upload_response.json()["downloadUrl"]
        
        # 2. 分类图片
        data = {
            'url': uploaded_url,
            'username': self.test_username
        }
        classify_response = requests.post(f"{self.base_url}/defect/classify", data=data)
        self.assertEqual(classify_response.status_code, 200)
        classification_result = classify_response.json()["result"]
        
        # 3. 如果是缺陷，显示缺陷
        if classification_result == 'defect':
            show_defect_response = requests.post(f"{self.base_url}/defect/showDefect", data=data)
            self.assertEqual(show_defect_response.status_code, 200)
            processed_url = show_defect_response.json()["downloadUrl"]
        else:
            processed_url = uploaded_url
        
        # 4. 查询历史记录
        params = {'username': self.test_username}
        history_response = requests.get(f"{self.base_url}/defect/history", params=params)
        self.assertEqual(history_response.status_code, 200)
        
        # 验证历史记录中包含我们刚刚的操作
        history_items = history_response.json()["history"]
        self.assertTrue(any(
            item["origin_url"] == uploaded_url and 
            item["process_url"] == processed_url and 
            item["user_name"] == self.test_username
            for item in history_items
        ))

if __name__ == '__main__':
    unittest.main(verbosity=2)