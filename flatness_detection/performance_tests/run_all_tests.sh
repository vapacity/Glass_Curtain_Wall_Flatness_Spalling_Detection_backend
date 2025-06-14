#!/bin/bash

# 性能测试自动化脚本
# 运行所有性能测试并生成综合报告

echo "========================================="
echo "玻璃幕墙检测系统性能测试套件"
echo "========================================="
echo ""

# 创建测试结果目录
mkdir -p test_results
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_DIR="test_results/test_run_${TIMESTAMP}"
mkdir -p ${RESULT_DIR}

# 1. 诊断服务状态
echo "[1/5] 诊断服务状态..."
echo "------------------------"
python diagnose_services.py | tee ${RESULT_DIR}/diagnose.log
echo ""

# 询问是否继续
read -p "服务状态正常吗？是否继续测试？(y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "测试已取消"
    exit 1
fi

# 2. 运行简单性能测试
echo ""
echo "[2/5] 运行简单性能测试..."
echo "------------------------"
python simple_performance_test.py --system all --requests 5
cp simple_performance_report.json ${RESULT_DIR}/
echo ""

# 3. 运行基准测试
echo "[3/5] 运行基准性能测试..."
echo "------------------------"
python benchmark_test.py
cp benchmark_report.json ${RESULT_DIR}/
echo ""

# 4. 运行OSS性能测试
echo "[4/5] 运行OSS性能测试..."
echo "------------------------"
python oss_performance_test.py
cp oss_performance_report.json ${RESULT_DIR}/
echo ""

# 5. 运行Locust压力测试（无界面，30秒）
echo "[5/5] 运行Locust压力测试（30秒）..."
echo "------------------------"
locust -f performance_test.py FlatnessDetectionUser \
    --host=http://localhost:8080 \
    --headless \
    --users 10 \
    --spawn-rate 2 \
    --run-time 30s \
    --html ${RESULT_DIR}/locust_report.html
cp performance_results.json ${RESULT_DIR}/
echo ""

# 生成测试总结
echo "========================================="
echo "测试完成！"
echo "测试结果保存在: ${RESULT_DIR}"
echo "========================================="
echo ""
echo "生成的报告文件："
ls -la ${RESULT_DIR}/
echo ""
echo "请查看各报告文件了解详细测试结果。"