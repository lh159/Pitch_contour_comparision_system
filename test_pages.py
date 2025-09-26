#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多页面应用的脚本
"""

import requests
import sys
import time

def test_page(url, page_name):
    """测试单个页面"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ {page_name} - 状态码: {response.status_code}")
            return True
        else:
            print(f"❌ {page_name} - 状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {page_name} - 连接错误: {e}")
        return False

def main():
    """主测试函数"""
    base_url = "http://localhost:9999"
    
    pages = [
        ("/", "首页（重定向到home）"),
        ("/home", "首页 - 选择练习模式"),
        ("/standard-audio", "标准发音播放页面"),
        ("/recording", "录音界面页面"),
        ("/results", "结果分析页面"),
        ("/legacy", "原有单页面应用")
    ]
    
    print("🚀 开始测试多页面应用...")
    print(f"测试基础URL: {base_url}")
    print("-" * 50)
    
    success_count = 0
    total_count = len(pages)
    
    for path, name in pages:
        url = f"{base_url}{path}"
        if test_page(url, name):
            success_count += 1
        time.sleep(0.5)  # 避免请求过快
    
    print("-" * 50)
    print(f"测试完成: {success_count}/{total_count} 页面正常")
    
    if success_count == total_count:
        print("🎉 所有页面测试通过！")
        return 0
    else:
        print("⚠️  部分页面测试失败，请检查服务器状态")
        return 1

if __name__ == "__main__":
    sys.exit(main())
