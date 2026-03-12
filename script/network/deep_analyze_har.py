#!/usr/bin/env python3
"""
深度 HAR 文件分析工具 - 彻底分析教务系统选课机制
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict


def load_har(filepath: str) -> Dict:
    """加载HAR文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_cookies(headers: List[Dict]) -> Dict[str, str]:
    """从请求头中提取 Cookie"""
    cookies = {}
    for header in headers:
        if header['name'].lower() == 'cookie':
            cookie_str = header['value']
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
    return cookies


def analyze_request_deep(entry: Dict) -> Dict[str, Any]:
    """深度分析单个请求"""
    request = entry['request']
    response = entry['response']

    url = request['url']
    parsed_url = urlparse(url)

    # 基本信息
    info = {
        'method': request['method'],
        'url': url,
        'scheme': parsed_url.scheme,
        'host': parsed_url.netloc,
        'path': parsed_url.path,
        'query_string': parsed_url.query,
        'query_params': parse_qs(parsed_url.query) if parsed_url.query else {},
        'status': response['status'],
        'status_text': response['statusText'],
        'time': entry.get('time', 0),  # 请求耗时（毫秒）
        'started_datetime': entry.get('startedDateTime', ''),
    }

    # 请求头分析
    request_headers = {h['name']: h['value'] for h in request['headers']}
    info['headers'] = request_headers
    info['cookies'] = extract_cookies(request['headers'])

    # 重要请求头
    info['content_type'] = request_headers.get('Content-Type', '')
    info['referer'] = request_headers.get('Referer', '')
    info['origin'] = request_headers.get('Origin', '')
    info['user_agent'] = request_headers.get('User-Agent', '')
    info['x_requested_with'] = request_headers.get('X-Requested-With', '')

    # 响应头分析
    response_headers = {h['name']: h['value'] for h in response['headers']}
    info['response_headers'] = response_headers
    info['response_content_type'] = response_headers.get('Content-Type', '')

    # POST 数据分析
    if 'postData' in request:
        post_data = request['postData']
        info['post_content_type'] = post_data.get('mimeType', '')

        if 'text' in post_data:
            text = post_data['text']
            # 尝试解析为 JSON
            try:
                info['post_data'] = json.loads(text)
                info['post_data_type'] = 'json'
            except:
                # 尝试解析为表单数据
                if '&' in text or '=' in text:
                    info['post_data'] = parse_qs(text)
                    info['post_data_type'] = 'form'
                else:
                    info['post_data'] = text
                    info['post_data_type'] = 'text'

        if 'params' in post_data:
            info['post_params'] = {p['name']: p.get('value', '') for p in post_data['params']}

    # 响应数据分析
    if 'content' in response and 'text' in response['content']:
        content_text = response['content']['text']
        info['response_size'] = len(content_text)

        # 尝试解析响应
        try:
            parsed = json.loads(content_text)
            info['response_data'] = parsed
            info['response_data_type'] = 'json'

            # 分析 JSON 结构
            if isinstance(parsed, dict):
                info['response_keys'] = list(parsed.keys())
                if 'success' in parsed:
                    info['api_success'] = parsed['success']
                if 'message' in parsed:
                    info['api_message'] = parsed['message']
        except:
            # HTML 或其他格式
            if content_text.strip().startswith('<!DOCTYPE') or content_text.strip().startswith('<html'):
                info['response_data_type'] = 'html'
                info['response_data'] = content_text[:500]  # 只保留前500字符
            else:
                info['response_data_type'] = 'text'
                info['response_data'] = content_text[:200]

    return info


def categorize_requests(entries: List[Dict]) -> Dict[str, List[Dict]]:
    """将请求按类型分类"""
    categories = defaultdict(list)

    for entry in entries:
        url = entry['request']['url']
        path = urlparse(url).path

        # 静态资源
        if any(ext in url for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.ico', '.woff', '.ttf', '.svg']):
            categories['static'].append(entry)
        # API 请求
        elif 'jwx.dgut.edu.cn' in url:
            # 选课相关
            if 'xsxkkc' in path:
                if 'xsxkGgxxkxk' in path:
                    categories['api_course_list'].append(entry)
                elif 'ggxxkxkOper' in path:
                    categories['api_course_select'].append(entry)
                elif 'getGgxxk' in path:
                    categories['page_course_selection'].append(entry)
                else:
                    categories['api_course_other'].append(entry)
            # 选课结果
            elif 'xsxkjg' in path:
                categories['api_course_result'].append(entry)
            # 认证相关
            elif 'cas' in path or 'login' in path:
                categories['auth'].append(entry)
            # 其他 API
            else:
                categories['api_other'].append(entry)
        else:
            categories['external'].append(entry)

    return dict(categories)


def analyze_api_pattern(requests: List[Dict]) -> Dict[str, Any]:
    """分析 API 调用模式"""
    if not requests:
        return {}

    pattern = {
        'count': len(requests),
        'methods': defaultdict(int),
        'paths': defaultdict(int),
        'avg_time': 0,
        'total_time': 0,
        'status_codes': defaultdict(int),
    }

    total_time = 0
    for req in requests:
        info = analyze_request_deep(req)
        pattern['methods'][info['method']] += 1
        pattern['paths'][info['path']] += 1
        pattern['status_codes'][info['status']] += 1
        total_time += info['time']

    pattern['total_time'] = total_time
    pattern['avg_time'] = total_time / len(requests) if requests else 0

    # 转换为普通字典
    pattern['methods'] = dict(pattern['methods'])
    pattern['paths'] = dict(pattern['paths'])
    pattern['status_codes'] = dict(pattern['status_codes'])

    return pattern


def generate_report(har_files: Dict[str, Path]) -> Dict[str, Any]:
    """生成完整分析报告"""
    report = {
        'summary': {},
        'files': {},
        'api_patterns': {},
        'cookie_analysis': {},
        'request_flow': {},
    }

    all_cookies = set()

    for name, filepath in har_files.items():
        print(f"\n{'='*60}")
        print(f"分析: {name}")
        print('='*60)

        har_data = load_har(filepath)
        entries = har_data['log']['entries']

        # 分类请求
        categorized = categorize_requests(entries)

        # 文件统计
        file_report = {
            'total_requests': len(entries),
            'categories': {k: len(v) for k, v in categorized.items()},
            'requests': {},
        }

        # 分析每个类别
        for category, reqs in categorized.items():
            if category == 'static':
                continue  # 跳过静态资源

            print(f"\n[{category}] {len(reqs)} 个请求")

            category_requests = []
            for i, entry in enumerate(reqs, 1):
                info = analyze_request_deep(entry)
                category_requests.append(info)

                # 收集 Cookie
                all_cookies.update(info['cookies'].keys())

                # 打印关键信息
                print(f"  #{i}: {info['method']} {info['path']}")
                print(f"      状态: {info['status']} | 耗时: {info['time']:.0f}ms")

                if info.get('query_params'):
                    print(f"      查询参数: {list(info['query_params'].keys())}")

                if info.get('post_data_type'):
                    print(f"      POST类型: {info['post_data_type']}")
                    if info['post_data_type'] == 'form':
                        print(f"      POST字段: {list(info['post_data'].keys())}")

                if info.get('api_success') is not None:
                    status = "✓" if info['api_success'] else "✗"
                    msg = info.get('api_message', '')
                    print(f"      结果: {status} {msg}")

            file_report['requests'][category] = category_requests

            # 分析模式
            pattern = analyze_api_pattern(reqs)
            report['api_patterns'][f"{name}_{category}"] = pattern

        report['files'][name] = file_report

    # Cookie 分析
    report['cookie_analysis'] = {
        'unique_cookies': list(all_cookies),
        'count': len(all_cookies),
    }

    return report


def main():
    """主函数"""
    network_dir = Path('developer/network')

    # 所有 HAR 文件
    har_files = {
        '20-20-29_初始加载': network_dir / 'jwx.dgut.edu.cn_Archive [26-03-12 20-20-29].har',
        '20-21-02_小请求': network_dir / 'jwx.dgut.edu.cn_Archive [26-03-12 20-21-02].har',
        '20-22-27_退选界面': network_dir / 'jwx.dgut.edu.cn_Archive [26-03-12 20-22-27].har',
        '20-25-18_页面切换': network_dir / 'jwx.dgut.edu.cn_Archive [26-03-12 20-25-18].har',
        '20-26-26_选课操作': network_dir / 'jwx.dgut.edu.cn_Archive [26-03-12 20-26-26].har',
    }

    # 检查文件存在性
    existing_files = {}
    for name, path in har_files.items():
        if path.exists():
            existing_files[name] = path
        else:
            print(f"⚠️  文件不存在: {path}")

    if not existing_files:
        print("❌ 没有找到任何 HAR 文件")
        return

    # 生成报告
    report = generate_report(existing_files)

    # 保存详细报告
    output_dir = Path('docs/developer/network')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'deep_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*60}")
    print("分析完成！")
    print('='*60)
    print(f"详细报告: {output_file}")

    # 打印摘要
    print(f"\n📊 总体统计:")
    print(f"  分析文件数: {len(existing_files)}")
    print(f"  发现的 Cookie: {', '.join(report['cookie_analysis']['unique_cookies'])}")

    print(f"\n🔍 API 模式:")
    for pattern_name, pattern in report['api_patterns'].items():
        if pattern['count'] > 0:
            print(f"  {pattern_name}:")
            print(f"    请求数: {pattern['count']}")
            print(f"    方法: {pattern['methods']}")
            print(f"    平均耗时: {pattern['avg_time']:.0f}ms")


if __name__ == '__main__':
    main()
