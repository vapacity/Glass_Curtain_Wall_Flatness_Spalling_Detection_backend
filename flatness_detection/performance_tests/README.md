# 性能测试套件

本目录包含玻璃幕墙检测系统的完整性能测试工具集。

## 目录结构

```
performance_tests/
├── README.md                    # 本文档
├── requirements_test.txt        # 测试依赖
├── performance_test_plan.md     # 详细测试计划
├── diagnose_services.py         # 服务诊断工具
├── simple_performance_test.py   # 简单性能测试
├── benchmark_test.py            # 基准性能测试
├── performance_test.py          # Locust压力测试
├── oss_performance_test.py      # OSS性能测试
└── test_image.jpg              # 测试用图片
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_test.txt
```

### 2. 诊断服务状态

首次运行前，建议先诊断服务状态：

```bash
python diagnose_services.py
```

### 3. 运行性能测试

根据需要选择合适的测试工具：

#### 简单性能测试（推荐开始使用）
```bash
# 测试所有系统
python simple_performance_test.py

# 只测试平整度检测
python simple_performance_test.py --system flatness

# 只测试爆裂检测
python simple_performance_test.py --system spalling

# 只测试OSS
python simple_performance_test.py --system oss
```

#### 基准性能测试
```bash
python benchmark_test.py
```

#### OSS专项测试
```bash
python oss_performance_test.py
```

#### Locust压力测试
```bash
# 使用Web界面
locust -f performance_test.py FlatnessDetectionUser --host=http://localhost:8080

# 无界面模式
locust -f performance_test.py FlatnessDetectionUser --host=http://localhost:8080 --headless --users 100 --spawn-rate 10 --run-time 30m
```

## 测试工具说明

### 1. diagnose_services.py
- **功能**：检查服务运行状态和接口可用性
- **用途**：在开始性能测试前诊断问题
- **输出**：服务状态、图片URL可访问性、API响应

### 2. simple_performance_test.py
- **功能**：灵活的单接口性能测试
- **特点**：
  - 支持命令行参数
  - 详细的错误信息
  - JSON格式报告
- **适用场景**：快速验证接口性能

### 3. benchmark_test.py
- **功能**：全面的基准性能测试
- **特点**：
  - 单请求基准测试
  - 并发测试
  - 系统资源监控
- **适用场景**：获取系统基准性能数据

### 4. performance_test.py
- **功能**：基于Locust的压力测试
- **特点**：
  - 模拟真实用户行为
  - 支持大规模并发
  - 实时性能监控
- **适用场景**：压力测试和负载测试

### 5. oss_performance_test.py
- **功能**：OSS上传下载性能测试
- **特点**：
  - 测试不同文件大小
  - 并发上传测试
  - 详细的速度统计
- **适用场景**：评估OSS服务性能

## 测试报告

各测试工具会生成相应的报告文件：

- `simple_performance_report.json` - 简单性能测试报告
- `benchmark_report.json` - 基准测试报告
- `oss_performance_report.json` - OSS性能测试报告
- `performance_results.json` - Locust测试详细数据

## 常见问题

### 1. 服务连接失败
- 确认服务已启动
- 检查端口配置（默认8080和9090）
- 查看服务日志

### 2. 测试超时
- 检查网络连接
- 确认图片URL可访问
- 检查模型文件是否已下载

### 3. 错误率过高
- 降低并发数
- 检查数据库连接
- 确认OSS服务正常

## 性能优化建议

1. **接口层面**
   - 实现请求缓存
   - 优化数据库查询
   - 使用连接池

2. **模型层面**
   - 批量处理请求
   - 模型量化/剪枝
   - GPU加速

3. **系统层面**
   - 负载均衡
   - 水平扩展
   - 异步处理

详细的性能优化方案请参考 `performance_test_plan.md`。