"""
简化的性能测试脚本
可以单独测试各个接口的性能
"""

import requests
import time
import statistics
import json
from datetime import datetime
import argparse

class SimplePerformanceTest:
    def __init__(self):
        self.results = []
        
    def test_endpoint(self, url, method='GET', data=None, json_data=None, headers=None, num_requests=10):
        """测试单个端点的性能"""
        print(f"\n测试端点: {method} {url}")
        print(f"请求数量: {num_requests}")
        
        response_times = []
        success_count = 0
        errors = []
        
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=30)
                elif method == 'POST':
                    if json_data:
                        response = requests.post(url, json=json_data, headers=headers, timeout=30)
                    else:
                        response = requests.post(url, data=data, headers=headers, timeout=30)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # 毫秒
                
                response_times.append(response_time)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"  请求 {i+1}: {response_time:.2f}ms - 成功")
                else:
                    errors.append(f"状态码: {response.status_code}")
                    print(f"  请求 {i+1}: {response_time:.2f}ms - 失败 (状态码: {response.status_code})")
                    
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                errors.append(str(e))
                print(f"  请求 {i+1}: {response_time:.2f}ms - 错误: {str(e)[:50]}...")
            
            time.sleep(0.5)  # 避免请求过于频繁
        
        # 计算统计信息
        if response_times:
            stats = {
                'endpoint': f"{method} {url}",
                'total_requests': num_requests,
                'success_count': success_count,
                'success_rate': (success_count / num_requests) * 100,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'errors': errors[:5]  # 只保留前5个错误
            }
            
            print(f"\n统计结果:")
            print(f"  成功率: {stats['success_rate']:.1f}%")
            print(f"  平均响应时间: {stats['avg_response_time']:.2f}ms")
            print(f"  最小响应时间: {stats['min_response_time']:.2f}ms")
            print(f"  最大响应时间: {stats['max_response_time']:.2f}ms")
            print(f"  标准差: {stats['std_dev']:.2f}ms")
            
            self.results.append(stats)
            return stats
        else:
            print("\n所有请求都失败了!")
            return None

def test_flatness_detection():
    """测试平整度检测系统"""
    print("\n=== 测试平整度检测系统 ===")
    
    tester = SimplePerformanceTest()
    
    # 1. 测试历史记录查询
    tester.test_endpoint(
        "http://localhost:8080/flatness/history?username=test_user",
        method='GET',
        num_requests=5
    )
    
    # 2. 测试平整度检测
    test_data = {
        "url": "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",
        "username": "test_user"
    }
    
    tester.test_endpoint(
        "http://localhost:8080/flatness/detect",
        method='POST',
        json_data=test_data,
        num_requests=3  # 检测接口比较慢，减少测试次数
    )
    
    return tester.results

def test_spalling_detection():
    """测试爆裂检测系统"""
    print("\n=== 测试爆裂检测系统 ===")
    
    tester = SimplePerformanceTest()
    
    # 1. 测试历史记录查询
    tester.test_endpoint(
        "http://localhost:9090/defect/history?username=test_user",
        method='GET',
        num_requests=5
    )
    
    # 2. 测试缺陷分类
    test_data = {
        'url': 'http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg',
        'username': 'test_user'
    }
    
    tester.test_endpoint(
        "http://localhost:9090/defect/classify",
        method='POST',
        data=test_data,
        num_requests=3
    )
    
    return tester.results

def test_oss_performance():
    """测试OSS性能"""
    print("\n=== 测试OSS下载性能 ===")
    
    tester = SimplePerformanceTest()
    
    # 测试图片下载
    test_urls = [
        "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107145947.jpg",
        "http://110.42.214.164:9000/oss/download/flatness-detection/user/upload/20250107155845.jpg",
    ]
    
    for url in test_urls:
        tester.test_endpoint(url, method='GET', num_requests=5)
    
    return tester.results

def generate_report(all_results):
    """生成测试报告"""
    report = {
        'test_time': datetime.now().isoformat(),
        'results': all_results
    }
    
    with open('simple_performance_report.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n\n=== 性能测试总结 ===")
    for result in all_results:
        if result:
            print(f"\n{result['endpoint']}:")
            print(f"  成功率: {result['success_rate']:.1f}%")
            print(f"  平均响应时间: {result['avg_response_time']:.2f}ms")
    
    print("\n详细报告已保存到 simple_performance_report.json")

def main():
    parser = argparse.ArgumentParser(description='简单性能测试工具')
    parser.add_argument('--system', choices=['flatness', 'spalling', 'oss', 'all'], 
                       default='all', help='要测试的系统')
    parser.add_argument('--requests', type=int, default=10, 
                       help='每个端点的请求次数')
    
    args = parser.parse_args()
    
    all_results = []
    
    if args.system in ['flatness', 'all']:
        results = test_flatness_detection()
        all_results.extend(results)
    
    if args.system in ['spalling', 'all']:
        results = test_spalling_detection()
        all_results.extend(results)
    
    if args.system in ['oss', 'all']:
        results = test_oss_performance()
        all_results.extend(results)
    
    generate_report(all_results)

if __name__ == "__main__":
    main()