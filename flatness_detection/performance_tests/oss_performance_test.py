"""
OSS上传下载性能测试脚本
"""

import requests
import time
import os
import statistics
from datetime import datetime
import concurrent.futures
from PIL import Image
import io

class OSSPerformanceTest:
    def __init__(self):
        self.oss_url = "http://110.42.214.164:9000"
        self.upload_user_name = "flatness-detection"
        self.upload_user_password = "tongji-icw-3455"
        
    def create_test_images(self):
        """创建不同大小的测试图片"""
        print("创建测试图片...")
        
        # 小图片 (500KB)
        small_img = Image.new('RGB', (800, 600), color='red')
        small_img.save('test_small.jpg', quality=95)
        
        # 中等图片 (2MB)
        medium_img = Image.new('RGB', (2000, 1500), color='green')
        medium_img.save('test_medium.jpg', quality=95)
        
        # 大图片 (5MB)
        large_img = Image.new('RGB', (4000, 3000), color='blue')
        large_img.save('test_large.jpg', quality=95)
        
        return ['test_small.jpg', 'test_medium.jpg', 'test_large.jpg']
    
    def test_oss_upload(self, file_path):
        """测试OSS上传性能"""
        start_time = time.time()
        
        try:
            with open(file_path, 'rb') as file:
                files = {'file': file}
                data = {
                    'userName': self.upload_user_name,
                    'password': self.upload_user_password
                }
                
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                target_path = f"test/performance/{timestamp}_{os.path.basename(file_path)}"
                upload_url = f"{self.oss_url}/oss/upload/{target_path}"
                
                response = requests.post(upload_url, files=files, data=data)
                
                end_time = time.time()
                upload_time = (end_time - start_time) * 1000  # 转换为毫秒
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        download_url = result.get('downloadUrl', response.text)
                    except:
                        download_url = response.text
                    
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    
                    return {
                        'success': True,
                        'upload_time': upload_time,
                        'file_size': file_size,
                        'download_url': download_url,
                        'speed': file_size / (upload_time / 1000)  # MB/s
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Status code: {response.status_code}",
                        'upload_time': upload_time
                    }
                    
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'error': str(e),
                'upload_time': (end_time - start_time) * 1000
            }
    
    def test_oss_download(self, download_url):
        """测试OSS下载性能"""
        start_time = time.time()
        
        try:
            response = requests.get(download_url, stream=True)
            
            if response.status_code == 200:
                content = response.content
                end_time = time.time()
                download_time = (end_time - start_time) * 1000  # 转换为毫秒
                
                file_size = len(content) / (1024 * 1024)  # MB
                
                return {
                    'success': True,
                    'download_time': download_time,
                    'file_size': file_size,
                    'speed': file_size / (download_time / 1000)  # MB/s
                }
            else:
                end_time = time.time()
                return {
                    'success': False,
                    'error': f"Status code: {response.status_code}",
                    'download_time': (end_time - start_time) * 1000
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'error': str(e),
                'download_time': (end_time - start_time) * 1000
            }
    
    def run_upload_tests(self, test_files):
        """运行上传性能测试"""
        print("\n=== OSS上传性能测试 ===")
        
        upload_results = {}
        
        for file_path in test_files:
            print(f"\n测试文件: {file_path}")
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"文件大小: {file_size:.2f} MB")
            
            results = []
            download_urls = []
            
            # 每个文件测试5次
            for i in range(5):
                result = self.test_oss_upload(file_path)
                results.append(result)
                
                if result['success']:
                    download_urls.append(result['download_url'])
                    print(f"  测试 {i+1}: {result['upload_time']:.2f}ms, 速度: {result['speed']:.2f} MB/s")
                else:
                    print(f"  测试 {i+1}: 失败 - {result['error']}")
                
                time.sleep(1)  # 避免请求过于频繁
            
            # 计算统计信息
            successful_results = [r for r in results if r['success']]
            if successful_results:
                upload_times = [r['upload_time'] for r in successful_results]
                speeds = [r['speed'] for r in successful_results]
                
                upload_results[file_path] = {
                    'avg_time': statistics.mean(upload_times),
                    'min_time': min(upload_times),
                    'max_time': max(upload_times),
                    'avg_speed': statistics.mean(speeds),
                    'success_rate': len(successful_results) / len(results) * 100,
                    'download_urls': download_urls
                }
                
                print(f"\n{file_path} 上传统计:")
                print(f"  平均时间: {upload_results[file_path]['avg_time']:.2f}ms")
                print(f"  平均速度: {upload_results[file_path]['avg_speed']:.2f} MB/s")
                print(f"  成功率: {upload_results[file_path]['success_rate']:.1f}%")
        
        return upload_results
    
    def run_download_tests(self, download_urls):
        """运行下载性能测试"""
        print("\n=== OSS下载性能测试 ===")
        
        download_results = []
        
        for url in download_urls[:3]:  # 测试前3个URL
            print(f"\n测试URL: {url}")
            
            results = []
            
            # 每个URL测试5次
            for i in range(5):
                result = self.test_oss_download(url)
                results.append(result)
                
                if result['success']:
                    print(f"  测试 {i+1}: {result['download_time']:.2f}ms, 速度: {result['speed']:.2f} MB/s")
                else:
                    print(f"  测试 {i+1}: 失败 - {result['error']}")
                
                time.sleep(1)
            
            # 计算统计信息
            successful_results = [r for r in results if r['success']]
            if successful_results:
                download_times = [r['download_time'] for r in successful_results]
                speeds = [r['speed'] for r in successful_results]
                
                download_results.append({
                    'url': url,
                    'avg_time': statistics.mean(download_times),
                    'min_time': min(download_times),
                    'max_time': max(download_times),
                    'avg_speed': statistics.mean(speeds),
                    'success_rate': len(successful_results) / len(results) * 100
                })
        
        return download_results
    
    def test_concurrent_upload(self, file_path, num_concurrent=5):
        """测试并发上传性能"""
        print(f"\n=== 并发上传测试 (并发数: {num_concurrent}) ===")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            start_time = time.time()
            futures = [executor.submit(self.test_oss_upload, file_path) for _ in range(num_concurrent)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = (time.time() - start_time) * 1000
        
        successful_results = [r for r in results if r['success']]
        
        print(f"\n并发上传结果:")
        print(f"  总耗时: {total_time:.2f}ms")
        print(f"  成功数: {len(successful_results)}/{num_concurrent}")
        
        if successful_results:
            avg_time = statistics.mean([r['upload_time'] for r in successful_results])
            print(f"  平均上传时间: {avg_time:.2f}ms")
        
        return results
    
    def generate_report(self, results):
        """生成测试报告"""
        report = {
            'test_time': datetime.now().isoformat(),
            'oss_url': self.oss_url,
            'results': results
        }
        
        with open('oss_performance_report.json', 'w') as f:
            import json
            json.dump(report, f, indent=2)
        
        print("\n测试报告已保存到 oss_performance_report.json")

def main():
    print("开始OSS性能测试...")
    
    tester = OSSPerformanceTest()
    
    # 1. 创建测试图片
    test_files = tester.create_test_images()
    
    # 2. 测试上传性能
    upload_results = tester.run_upload_tests(test_files)
    
    # 3. 测试下载性能
    all_download_urls = []
    for file_result in upload_results.values():
        all_download_urls.extend(file_result.get('download_urls', []))
    
    if all_download_urls:
        download_results = tester.run_download_tests(all_download_urls)
    
    # 4. 测试并发上传
    concurrent_results = tester.test_concurrent_upload(test_files[0], num_concurrent=5)
    
    # 5. 生成报告
    all_results = {
        'upload_results': upload_results,
        'download_results': download_results if 'download_results' in locals() else [],
        'concurrent_results': concurrent_results
    }
    
    tester.generate_report(all_results)
    
    # 清理测试文件
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    print("\nOSS性能测试完成!")

if __name__ == "__main__":
    main()