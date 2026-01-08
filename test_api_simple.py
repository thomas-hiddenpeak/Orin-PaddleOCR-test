#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 产线 API 简单测试脚本

纯 API 调用，无需安装 PaddleOCR 相关框架
仅依赖: requests, pathlib (标准库)

使用方法:
    python test_api_simple.py
    python test_api_simple.py --image /path/to/image.jpg
    python test_api_simple.py --url https://example.com/image.png
"""

import argparse
import base64
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)


# API 配置
API_HOST = "http://127.0.0.1:58811"
API_ENDPOINT = "/layout-parsing"


def test_with_url(image_url: str):
    """使用远程 URL 测试"""
    print(f"测试模式: 远程 URL")
    print(f"图片 URL: {image_url}")
    
    payload = {
        "file": image_url,
        "fileType": 1,  # 1=图像, 0=PDF
        "visualize": True,
    }
    return call_api(payload)


def test_with_local_file(file_path: str):
    """使用本地文件测试"""
    path = Path(file_path)
    if not path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)
    
    print(f"测试模式: 本地文件")
    print(f"文件路径: {path.absolute()}")
    print(f"文件大小: {path.stat().st_size} 字节")
    
    # 读取并 Base64 编码
    with open(path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("ascii")
    
    # 判断文件类型
    suffix = path.suffix.lower()
    file_type = 0 if suffix == ".pdf" else 1
    
    payload = {
        "file": file_data,
        "fileType": file_type,
        "visualize": True,
    }
    return call_api(payload)


def call_api(payload: dict):
    """调用 API"""
    url = f"{API_HOST}{API_ENDPOINT}"
    print(f"\nAPI 地址: {url}")
    print("正在调用 API...")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=300)
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {API_HOST}")
        print("请确保产线服务已启动:")
        print("  ./start_paddleocr_vl_server.sh")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("错误: 请求超时 (>300秒)")
        sys.exit(1)
    
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code != 200:
        print(f"错误: {response.text}")
        sys.exit(1)
    
    # 解析响应
    result = response.json()
    
    error_code = result.get("errorCode", -1)
    error_msg = result.get("errorMsg", "")
    log_id = result.get("logId", "N/A")
    
    print(f"日志 ID: {log_id}")
    print(f"错误码: {error_code}")
    
    if error_code != 0:
        print(f"API 错误: {error_msg}")
        sys.exit(1)
    
    print("✓ API 调用成功!")
    print("-" * 50)
    
    return result


def save_results(result: dict, output_dir: str = "api_output"):
    """保存结果"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    data = result.get("result", {})
    layout_results = data.get("layoutParsingResults", [])
    
    print(f"\n解析结果: {len(layout_results)} 页")
    
    for i, page_result in enumerate(layout_results):
        print(f"\n=== 第 {i + 1} 页 ===")
        
        # 保存 Markdown
        markdown = page_result.get("markdown", {})
        md_text = markdown.get("text", "")
        
        if md_text:
            md_file = output_path / f"page_{i}_result.md"
            md_file.write_text(md_text, encoding="utf-8")
            print(f"Markdown 已保存: {md_file}")
            
            # 预览内容
            print("\n--- Markdown 预览 ---")
            preview = md_text[:1500]
            print(preview)
            if len(md_text) > 1500:
                print(f"... (共 {len(md_text)} 字符，已截断)")
            print("--- 预览结束 ---")
        
        # 保存 Markdown 中的图片
        md_images = markdown.get("images", {})
        if md_images:
            print(f"\nMarkdown 图片: {len(md_images)} 张")
            for img_name, img_b64 in md_images.items():
                img_path = output_path / f"page_{i}_{img_name}"
                img_path.parent.mkdir(parents=True, exist_ok=True)
                img_path.write_bytes(base64.b64decode(img_b64))
                print(f"  - {img_path}")
        
        # 保存可视化图片
        output_images = page_result.get("outputImages", {})
        if output_images:
            print(f"\n可视化图片: {len(output_images)} 张")
            for img_name, img_b64 in output_images.items():
                img_path = output_path / f"page_{i}_{img_name}.jpg"
                img_path.write_bytes(base64.b64decode(img_b64))
                print(f"  - {img_path}")
        
        # 保存结构化结果
        pruned_result = page_result.get("prunedResult", {})
        if pruned_result:
            json_file = output_path / f"page_{i}_structure.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(pruned_result, f, ensure_ascii=False, indent=2)
            print(f"\n结构化结果已保存: {json_file}")
    
    # 保存完整响应
    full_response_file = output_path / "full_response.json"
    with open(full_response_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n完整响应已保存: {full_response_file}")
    
    print(f"\n{'=' * 50}")
    print(f"所有结果已保存到: {output_path.absolute()}")
    print(f"{'=' * 50}")


def main():
    parser = argparse.ArgumentParser(
        description="PaddleOCR-VL API 测试脚本 (纯 API 调用)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--image",
        type=str,
        help="本地图片/PDF 文件路径",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="远程图片 URL",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="api_output",
        help="输出目录 (默认: api_output)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://127.0.0.1:58811",
        help="API 服务地址 (默认: http://127.0.0.1:58811)",
    )
    
    args = parser.parse_args()
    
    global API_HOST
    API_HOST = args.host
    
    print("=" * 50)
    print("PaddleOCR-VL 产线 API 测试")
    print("=" * 50)
    
    # 确定测试方式
    if args.url:
        result = test_with_url(args.url)
    elif args.image:
        result = test_with_local_file(args.image)
    else:
        # 默认使用官方示例图片
        default_url = "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png"
        print(f"未指定输入，使用默认测试图片:")
        result = test_with_url(default_url)
    
    # 保存结果
    save_results(result, args.output)


if __name__ == "__main__":
    main()
