#!/bin/bash
# PaddleOCR-VL 自定义产线服务启动脚本
# 此产线通过一个 API 调用完成版面分析 + OCR-VL 两步业务

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 配置
CONFIG_FILE="${SCRIPT_DIR}/paddleocr_vl_server_config.yaml"
HOST="0.0.0.0"
PORT="58811"

# 检查 vLLM 服务是否运行 (OCR-VL 模型后端)
VLLM_URL="http://127.0.0.1:58810/v1/models"
echo "检查 vLLM 服务状态..."
if curl -s --connect-timeout 5 "$VLLM_URL" > /dev/null 2>&1; then
    echo "✓ vLLM 服务已运行"
else
    echo "⚠ 警告: vLLM 服务未运行在 http://127.0.0.1:58810"
    echo "  请先启动 vLLM 服务以支持 PaddleOCR-VL-0.9B 模型"
    echo "  示例: vllm serve PaddleOCR-VL-0.9B --port 58810"
    echo ""
fi

# 激活 conda 环境
echo "激活 paddleocr conda 环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate paddleocr

# 启动服务
echo "=========================================="
echo "启动 PaddleOCR-VL 自定义产线服务"
echo "=========================================="
echo "配置文件: $CONFIG_FILE"
echo "服务地址: http://${HOST}:${PORT}"
echo "API 端点: http://${HOST}:${PORT}/layout-parsing"
echo "健康检查: http://${HOST}:${PORT}/health"
echo "=========================================="
echo ""

# 设置环境变量跳过模型源检查（可选，加速启动）
export DISABLE_MODEL_SOURCE_CHECK=True

paddlex --serve --pipeline "$CONFIG_FILE" --host "$HOST" --port "$PORT"
