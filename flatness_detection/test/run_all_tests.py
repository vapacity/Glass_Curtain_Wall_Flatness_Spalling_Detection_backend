#!/usr/bin/env python3
"""
运行所有测试的主脚本
"""

import sys
import os
import unittest
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试模块
from unit_tests.test_flatness_detection import TestFlatnessDetection, TestEdgeCases
from unit_tests.test_methods import TestDetectionMethods
from performance_tests.test_performance import PerformanceTestSuite
from performance_tests.test_stress import StressTest


def run_unit_tests():
    """运行单元测试"""
    print("="*60)
    print("运行单元测试...")
    print("="*60)
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFlatnessDetection))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDetectionMethods))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_performance_tests():
    """运行性能测试"""
    print("\n" + "="*60)
    print("运行性能测试...")
    print("="*60)
    
    suite = PerformanceTestSuite()
    report = suite.run_all_tests()
    
    # 打印关键指标
    print("\n性能测试关键指标:")
    if report['results']['single_image_tests']:
        for test in report['results']['single_image_tests'][:3]:  # 只显示前3个
            print(f"- {test['image_name']}: {test['total_time']:.3f}秒 (FPS: {test['fps']:.2f})")
    
    return True


def run_stress_tests():
    """运行压力测试"""
    print("\n" + "="*60)
    print("运行压力测试...")
    print("="*60)
    
    stress_test = StressTest()
    report = stress_test.run_all_stress_tests()
    
    # 打印关键指标
    print("\n压力测试关键指标:")
    if report['results']['load_tests']:
        max_throughput = max(t['throughput'] for t in report['results']['load_tests'])
        print(f"- 最大吞吐量: {max_throughput:.2f} req/s")
    
    return True


def generate_test_summary():
    """生成测试总结"""
    summary = f"""
    
========================================
测试执行总结
========================================
执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

测试结果:
- 单元测试: 已完成
- 性能测试: 已完成  
- 压力测试: 已完成

生成的报告文件:
- test_reports/test_results_summary.md - 完整测试报告
- test_reports/performance_report.json - 性能测试详细数据
- test_reports/performance_visualization.png - 性能可视化图表
- test_reports/stress_test_report.json - 压力测试详细数据
- test_reports/stress_test_visualization.png - 压力测试可视化图表

建议查看 test_results_summary.md 获取完整的测试结果分析。
========================================
    """
    
    print(summary)


def main():
    """主函数"""
    print("开始执行玻璃幕墙平整度检测系统测试套件")
    print(f"测试开始时间: {datetime.now()}")
    
    start_time = time.time()
    
    # 确保报告目录存在
    os.makedirs('test_reports', exist_ok=True)
    
    # 运行各类测试
    unit_test_success = run_unit_tests()
    performance_test_success = run_performance_tests()
    stress_test_success = run_stress_tests()
    
    # 生成总结
    generate_test_summary()
    
    total_time = time.time() - start_time
    print(f"\n总测试时间: {total_time:.2f}秒")
    
    # 返回总体成功状态
    return unit_test_success and performance_test_success and stress_test_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)