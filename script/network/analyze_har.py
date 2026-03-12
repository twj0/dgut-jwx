#!/usr/bin/env python3
"""
HAR文件分析工具 - 用于分析教务系统选课网络请求
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs


def load_har(filepath: str) -> Dict:
    """加载HAR文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_request(entry: Dict) -> Dict[str, Any]:
    """分析单个请求"""
    request = entry['request']
    response = entry['response']

    url = request['url']
    parsed_url = urlparse(url)

    # 提取请求信息
    info = {
        'method': request['method'],
        'url': url,
        'path': parsed_url.path,
        'query_params': parse_qs(parsed_url.query) if parsed_url.query else {},
        'status': response['status'],
        'status_text': response['statusText'],
        'headers': {h['name']: h['value'] for h in request['headers']},
        'response_headers': {h['name']: h['value'] for h in response['headers']},
    }

    # 提取POST数据
    if 'postData' in request:
        post_data = request['postData']
        info['content_type'] = post_data.get('mimeType', '')

        if 'text' in post_data:
            text = post_data['text']
            # 尝试解析为JSON
            try:
                info['post_data'] = json.loads(text)
            except:
                # 尝试解析为表单数据
                if '&' in text or '=' in text:
                    info['post_data'] = parse_qs(text)
                else:
                    info['post_data'] = text

    # 提取响应数据
    if 'content' in response and 'text' in response['content']:
        try:
            info['response_data'] = json.loads(response['content']['text'])
        except:
            info['response_data'] = response['content']['text'][:200]  # 只保留前200字符

    return info


def main():
    """主函数"""
    network_dir = Path('developer/network')

    # 重要的HAR文件
    important_hars = {
        'page_switch': 'jwx.dgut.edu.cn_Archive [26-03-12 20-25-18].har',
        'course_selection': 'jwx.dgut.edu.cn_Archive [26-03-12 20-26-26].har',
        'course_deselection': 'jwx.dgut.edu.cn_Archive [26-03-12 20-22-27].har',
    }

    results = {}

    for name, filename in important_hars.items():
        filepath = network_dir / filename
        if not filepath.exists():
            print(f"文件不存在: {filepath}")
            continue

        print(f"\n{'='*60}")
        print(f"分析: {name} ({filename})")
        print('='*60)

        har_data = load_har(filepath)
        entries = har_data['log']['entries']

        # 过滤重要的请求（排除静态资源）
        important_entries = []
        for entry in entries:
            url = entry['request']['url']
            # 排除静态资源
            if any(ext in url for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.ico', '.woff']):
                continue
            # 只关注API请求
            if 'jwx.dgut.edu.cn' in url:
                important_entries.append(entry)

        print(f"\n找到 {len(important_entries)} 个重要请求\n")

        analyzed = []
        for i, entry in enumerate(important_entries, 1):
            info = analyze_request(entry)
            analyzed.append(info)

            print(f"\n请求 #{i}:")
            print(f"  方法: {info['method']}")
            print(f"  路径: {info['path']}")
            print(f"  状态: {info['status']} {info['status_text']}")

            if info['query_params']:
                print(f"  查询参数: {info['query_params']}")

            if 'post_data' in info:
                print(f"  POST数据: {info['post_data']}")

            if 'response_data' in info and isinstance(info['response_data'], dict):
                print(f"  响应数据: {json.dumps(info['response_data'], ensure_ascii=False, indent=2)[:300]}")

        results[name] = analyzed

    # 保存分析结果
    output_dir = Path('docs/developer/network')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'har_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\n分析结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
