# 玻璃幕墙检测系统性能测试方案

## 系统概述

### 1. ICW_FlatnessDetection_Backend (平整度检测系统)
- **端口**: 8080
- **主要功能**: 玻璃幕墙平整度检测
- **核心模型**: GDNet (使用PyTorch)
- **主要接口**:
  - `POST /flatness/detect` - 平整度检测接口
  - `GET /flatness/history` - 历史记录查询
  - `GET /flatness/getDetail` - 检测详情查询

### 2. ICW_SpallingDetection_Backend (爆裂检测系统)
- **端口**: 9090  
- **主要功能**: 玻璃幕墙爆裂缺陷检测
- **核心模型**: ResNet34 (使用PyTorch)
- **主要接口**:
  - `POST /defect/upload` - 图片上传
  - `POST /defect/classify` - 缺陷分类检测
  - `POST /defect/showDefect` - 显示缺陷标注
  - `GET /defect/history` - 历史记录查询

## 性能测试方案

### 1. 测试环境准备
```yaml
测试工具:
  - Apache JMeter (GUI界面，适合复杂场景)
  - Locust (Python编写，适合代码化测试)
  - wrk (命令行工具，适合简单压测)
  
测试数据:
  - 准备不同尺寸的测试图片（小：<1MB，中：1-5MB，大：>5MB）
  - 准备正常和异常的测试用例
```

### 2. 测试指标
- **响应时间**: 平均响应时间、P95、P99
- **吞吐量**: QPS (每秒请求数)
- **并发能力**: 最大并发用户数
- **资源使用**: CPU、内存、GPU使用率
- **错误率**: 请求失败率、超时率
- **稳定性**: 长时间运行的性能表现

### 3. 测试场景设计

#### 3.1 平整度检测系统测试

**场景1: 单用户基准测试**
```python
# 测试脚本示例 (使用Locust)
from locust import HttpUser, task, between
import base64

class FlatnessDetectionUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def detect_flatness(self):
        test_data = {
            "url": "http://110.42.214.164:9000/test/sample.jpg",
            "username": "test_user"
        }
        response = self.client.post("/flatness/detect", json=test_data)
        
    @task(2)
    def get_history(self):
        self.client.get("/flatness/history?username=test_user")
```

**场景2: 并发压力测试**
- 并发用户数：10, 20, 50, 100
- 测试时长：每个阶段10分钟
- 记录各并发级别下的性能指标

**场景3: 大文件处理测试**
- 测试不同尺寸图片的处理性能
- 监控内存使用情况
- 测试GPU利用率

#### 3.2 爆裂检测系统测试

**场景1: 图片上传性能测试**
```python
class SpallingDetectionUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def upload_image(self):
        with open('test_image.jpg', 'rb') as f:
            files = {'file': f}
            self.client.post("/defect/upload", files=files)
    
    @task(2) 
    def classify_defect(self):
        data = {
            'url': 'http://110.42.214.164:9000/test/sample.jpg',
            'username': 'test_user'
        }
        self.client.post("/defect/classify", data=data)
```

**场景2: 混合负载测试**
- 30% 上传请求
- 50% 分类检测请求
- 20% 历史查询请求

### 4. 性能优化建议

#### 4.1 代码层面优化
1. **模型推理优化**
   - 使用批处理进行推理
   - 启用模型量化或剪枝
   - 使用TorchScript优化模型

2. **图片处理优化**
   - 实现图片预处理缓存
   - 使用多进程处理图片
   - 优化图片大小和格式

3. **数据库优化**
   - 添加适当的索引
   - 使用连接池管理数据库连接
   - 考虑读写分离

#### 4.2 系统架构优化
1. **负载均衡**
   - 部署多个实例
   - 使用Nginx进行负载均衡

2. **缓存策略**
   - 使用Redis缓存热点数据
   - 实现结果缓存机制

3. **异步处理**
   - 使用消息队列处理耗时任务
   - 实现异步API响应

### 5. 测试执行计划

```bash
# 第一阶段：基准测试
# 获取单个请求的基准性能
wrk -t2 -c1 -d30s --latency http://localhost:8080/flatness/detect

# 第二阶段：压力测试
# 使用Locust进行渐进式压力测试
locust -f performance_test.py --host=http://localhost:8080

# 第三阶段：稳定性测试
# 24小时持续压力测试
locust -f performance_test.py --host=http://localhost:8080 \
       --users 50 --spawn-rate 5 --run-time 24h

# 第四阶段：极限测试
# 测试系统的极限承载能力
```

### 6. 监控指标收集

```python
# 监控脚本示例
import psutil
import GPUtil
import time

def monitor_system():
    while True:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        
        # GPU使用率（如果有）
        gpus = GPUtil.getGPUs()
        gpu_usage = gpus[0].load * 100 if gpus else 0
        
        print(f"CPU: {cpu_percent}%, Memory: {memory.percent}%, GPU: {gpu_usage}%")
        time.sleep(5)
```

### 7. 测试报告模板

```markdown
## 性能测试报告

### 测试环境
- 硬件配置：[CPU/内存/GPU]
- 操作系统：[OS版本]
- Python版本：[版本号]
- PyTorch版本：[版本号]

### 测试结果汇总
| 接口 | 并发数 | 平均响应时间(ms) | P95(ms) | P99(ms) | QPS | 错误率 |
|------|--------|------------------|---------|---------|-----|---------|
| /flatness/detect | 10 | - | - | - | - | - |
| /flatness/detect | 50 | - | - | - | - | - |
| /defect/classify | 10 | - | - | - | - | - |
| /defect/classify | 50 | - | - | - | - | - |

### 性能瓶颈分析
1. 主要瓶颈：[CPU/内存/GPU/网络/数据库]
2. 优化建议：[具体建议]

### 结论与建议
[测试总结和改进建议]
```

### 8. 自动化测试脚本

创建一个完整的性能测试脚本 `run_performance_test.sh`:

```bash
#!/bin/bash

# 性能测试自动化脚本

# 1. 检查服务是否运行
echo "检查服务状态..."
curl -f http://localhost:8080/test || echo "平整度检测服务未运行"
curl -f http://localhost:9090/test || echo "爆裂检测服务未运行"

# 2. 运行基准测试
echo "运行基准测试..."
python benchmark_test.py

# 3. 运行压力测试
echo "运行压力测试..."
locust -f performance_test.py --headless \
       --users 100 --spawn-rate 10 \
       --run-time 30m --html report.html

# 4. 生成测试报告
echo "生成测试报告..."
python generate_report.py

echo "性能测试完成！"
```

## 总结

这个性能测试方案涵盖了：
1. 两个系统的接口功能分析
2. 详细的性能测试场景设计
3. 具体的测试脚本示例
4. 性能优化建议
5. 监控和报告方案

您可以根据实际需求调整测试参数和场景，确保测试覆盖系统的关键性能指标。