#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试阿里云TTS API的正确格式
"""
import json
import requests
import logging

logging.basicConfig(level=logging.DEBUG)

def test_different_api_formats():
    """测试不同的API请求格式"""
    api_key = "sk-26cd7fe2661444f2804896a590bdbbc0"
    base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 测试格式1: 标准格式
    print("=== 测试格式1: 标准格式 ===")
    payload1 = {
        'model': 'cosyvoice-v1',
        'input': {
            'text': '你好'
        },
        'parameters': {
            'voice': 'zhimiao_emo'
        }
    }
    
    test_request(base_url, headers, payload1, "标准格式")
    
    # 测试格式2: 添加task_group
    print("\n=== 测试格式2: 添加task_group ===")
    payload2 = {
        'model': 'cosyvoice-v1',
        'task_group': 'audio',
        'input': {
            'text': '你好'
        },
        'parameters': {
            'voice': 'zhimiao_emo'
        }
    }
    
    test_request(base_url, headers, payload2, "添加task_group")
    
    # 测试格式3: 使用老版本格式
    print("\n=== 测试格式3: 老版本格式 ===")
    payload3 = {
        'model': 'sambert-zhimiao-emo-v1',
        'input': {
            'text': '你好'
        },
        'parameters': {
            'voice': 'zhimiao_emo'
        }
    }
    
    test_request(base_url, headers, payload3, "老版本格式")
    
    # 测试格式4: 完整参数
    print("\n=== 测试格式4: 完整参数 ===")
    payload4 = {
        'model': 'cosyvoice-v1',
        'input': {
            'text': '你好，欢迎使用音高曲线比对系统'
        },
        'parameters': {
            'voice': 'zhimiao_emo',
            'format': 'mp3',
            'sample_rate': 22050,
            'volume': 50,
            'speech_rate': 0,
            'pitch_rate': 0
        }
    }
    
    test_request(base_url, headers, payload4, "完整参数")

def test_request(url, headers, payload, description):
    """测试单个请求"""
    print(f"测试: {description}")
    print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ 错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

if __name__ == "__main__":
    test_different_api_formats()
