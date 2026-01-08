# Orin-PaddleOCR-test

基于 NVIDIA Jetson AGX Orin 的 PaddleOCR-VL 自定义产线测试项目。

## 概述

本项目实现了一个**一站式文档解析 API**，通过单次 API 调用即可完成：
1. **版面分析** (Layout Detection) - 使用 PP-DocLayoutV2 模型
2. **VL 文字识别** (VL Recognition) - 使用 PaddleOCR-VL-0.9B 模型

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    客户端请求                            │
│              POST /layout-parsing                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           PaddleOCR-VL 产线服务 (端口: 58811)            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  1. 版面分析 (PP-DocLayoutV2)                    │   │
│  │     - 检测 25 种版面元素                         │   │
│  │     - 本地 Paddle 推理                          │   │
│  └─────────────────────┬───────────────────────────┘   │
│                        │                               │
│  ┌─────────────────────▼───────────────────────────┐   │
│  │  2. VL 文字识别 (PaddleOCR-VL-0.9B)              │   │
│  │     - 调用 vLLM 服务                            │   │
│  │     - 后端地址: http://127.0.0.1:58810/v1       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    输出结果                              │
│  - Markdown 文本                                        │
│  - 结构化 JSON                                          │
│  - 可视化图片                                           │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
Orin-PaddleOCR-test/
├── README.md                          # 说明文档
├── paddleocr_vl_server_config.yaml   # 产线配置文件
├── start_paddleocr_vl_server.sh      # 服务启动脚本
├── test_api_simple.py                # API 测试脚本 (纯 requests)
└── paddleocr_vl_demo.png             # 测试图片
```

## 环境要求

- **硬件**: NVIDIA Jetson AGX Orin (或其他支持 CUDA 的设备)
- **软件**:
  - Python 3.10+
  - Conda 环境: `paddleocr`
  - PaddleX 3.3+
  - vLLM (用于 PaddleOCR-VL-0.9B 模型推理)

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| vLLM 服务 | 58810 | PaddleOCR-VL-0.9B 模型后端 |
| 产线服务 | 58811 | 对外提供 API |

## 快速开始

### 1. 启动 vLLM 服务 (前置条件)

确保 vLLM 服务已在端口 58810 运行，加载 PaddleOCR-VL-0.9B 模型：

```bash
# 示例启动命令 (根据实际情况调整)
vllm serve PaddleOCR-VL-0.9B --port 58810
```

### 2. 启动产线服务

```bash
# 使用启动脚本
./start_paddleocr_vl_server.sh

# 或直接使用 paddlex 命令
conda activate paddleocr
paddlex --serve --pipeline paddleocr_vl_server_config.yaml --host 0.0.0.0 --port 58811
```

### 3. 测试 API

```bash
# 使用默认测试图片
python test_api_simple.py

# 使用本地图片
python test_api_simple.py --image paddleocr_vl_demo.png

# 使用远程 URL
python test_api_simple.py --url https://example.com/image.png

# 指定输出目录
python test_api_simple.py --image test.jpg --output my_output
```

## API 说明

### 端点

```
POST http://<host>:58811/layout-parsing
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | string | 是 | 图片 URL 或 Base64 编码的图片数据 |
| fileType | int | 是 | 文件类型: 0=PDF, 1=图像 |
| visualize | bool | 否 | 是否返回可视化结果图片 |

### 请求示例

```bash
curl -X POST "http://127.0.0.1:58811/layout-parsing" \
  -H "Content-Type: application/json" \
  -d '{
    "file": "https://example.com/image.png",
    "fileType": 1,
    "visualize": true
  }'
```

### 响应示例

```json
{
  "logId": "xxx-xxx-xxx",
  "errorCode": 0,
  "errorMsg": "Success",
  "result": {
    "layoutParsingResults": [
      {
        "prunedResult": { ... },
        "markdown": {
          "text": "# 标题\n\n正文内容...",
          "images": { "img_0.jpg": "base64..." }
        },
        "outputImages": {
          "layout_det_res": "base64...",
          "layout_order_res": "base64..."
        }
      }
    ]
  }
}
```

## 配置说明

### paddleocr_vl_server_config.yaml

```yaml
pipeline_name: PaddleOCR-VL       # 产线名称

# 功能开关
use_doc_preprocessor: False       # 文档预处理 (方向矫正等)
use_layout_detection: True        # 版面分析
use_chart_recognition: False      # 图表识别

# 版面分析配置
SubModules:
  LayoutDetection:
    model_name: PP-DocLayoutV2    # 版面分析模型
    threshold: { ... }            # 各类别检测阈值
    
  VLRecognition:
    model_name: PaddleOCR-VL-0.9B # VL识别模型
    genai_config:
      backend: vllm-server        # 后端类型
      server_url: http://127.0.0.1:58810/v1  # vLLM 地址
```

## 版面分析支持的类别

PP-DocLayoutV2 支持检测 25 种版面元素：

| 索引 | 类别 | 索引 | 类别 |
|------|------|------|------|
| 0 | abstract | 13 | header |
| 1 | algorithm | 14 | image |
| 2 | aside_text | 15 | inline_formula |
| 3 | chart | 16 | number |
| 4 | content | 17 | paragraph_title |
| 5 | display_formula | 18 | reference |
| 6 | doc_title | 19 | reference_content |
| 7 | figure_title | 20 | seal |
| 8 | footer | 21 | table |
| 9 | footer_image | 22 | text |
| 10 | footnote | 23 | text |
| 11 | formula_number | 24 | vision_footnote |
| 12 | header_image | | |

## 健康检查

```bash
curl http://127.0.0.1:58811/health
```

响应:
```json
{"logId": "xxx", "errorCode": 0, "errorMsg": "Healthy"}
```

## License

Apache License 2.0

## 相关链接

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleX](https://github.com/PaddlePaddle/PaddleX)
- [vLLM](https://github.com/vllm-project/vllm)
