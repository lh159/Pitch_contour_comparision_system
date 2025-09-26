#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录音API测试脚本
用于验证新添加的录音功能是否正常工作
"""

import requests
import json
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_recording_api(base_url="http://localhost:5000"):
    """测试录音API功能"""
    
    print("🎙️ 开始测试录音API功能...")
    
    # 测试1: 开始录音会话
    print("\n1. 测试开始录音会话...")
    try:
        response = requests.post(f"{base_url}/api/recording/start", 
                               json={}, 
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                session_id = data.get('session_id')
                print(f"✅ 录音会话创建成功，会话ID: {session_id}")
            else:
                print(f"❌ 录音会话创建失败: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return False
    
    # 测试2: 检查录音状态
    print("\n2. 测试录音状态查询...")
    try:
        response = requests.get(f"{base_url}/api/recording/status/{session_id}", 
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ 录音状态查询成功: 录音中={data.get('is_recording')}")
            else:
                print(f"❌ 录音状态查询失败: {data.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    
    # 测试3: 模拟录音一段时间
    print("\n3. 模拟录音过程...")
    print("   (在实际使用中，这里会通过 /api/recording/data 上传音频数据)")
    time.sleep(2)  # 模拟录音2秒
    
    # 测试4: 停止录音会话
    print("\n4. 测试停止录音会话...")
    try:
        response = requests.post(f"{base_url}/api/recording/stop", 
                               json={"session_id": session_id}, 
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ 录音会话停止成功")
                print(f"   文件ID: {data.get('file_id')}")
                print(f"   文件名: {data.get('filename')}")
                print(f"   时长: {data.get('duration', 0):.2f}秒")
            else:
                print(f"❌ 录音会话停止失败: {data.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    
    print("\n🎙️ 录音API测试完成!")
    return True

def test_file_upload_api(base_url="http://localhost:5000"):
    """测试文件上传API功能"""
    
    print("\n📁 测试文件上传API功能...")
    
    # 创建一个测试音频文件（空文件用于测试）
    test_file_path = "/tmp/test_audio.wav"
    try:
        with open(test_file_path, 'wb') as f:
            # 写入WAV文件头（最小有效WAV文件）
            f.write(b'RIFF')
            f.write((36).to_bytes(4, 'little'))  # 文件大小-8
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write((16).to_bytes(4, 'little'))  # fmt块大小
            f.write((1).to_bytes(2, 'little'))   # 音频格式
            f.write((1).to_bytes(2, 'little'))   # 声道数
            f.write((44100).to_bytes(4, 'little'))  # 采样率
            f.write((88200).to_bytes(4, 'little'))  # 字节率
            f.write((2).to_bytes(2, 'little'))   # 块对齐
            f.write((16).to_bytes(2, 'little'))  # 位深度
            f.write(b'data')
            f.write((0).to_bytes(4, 'little'))   # 数据大小
        
        # 上传测试文件
        with open(test_file_path, 'rb') as f:
            files = {'audio': ('test_audio.wav', f, 'audio/wav')}
            response = requests.post(f"{base_url}/api/audio/upload", 
                                   files=files, 
                                   timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ 文件上传成功")
                print(f"   文件ID: {data.get('file_id')}")
                print(f"   文件名: {data.get('filename')}")
            else:
                print(f"❌ 文件上传失败: {data.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ 文件上传测试失败: {e}")
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def main():
    """主函数"""
    print("🚀 录音功能测试开始...")
    
    # 检查服务器是否运行
    base_url = "http://localhost:5000"
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ 服务器运行正常: {base_url}")
        else:
            print(f"⚠️ 服务器响应异常: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器 {base_url}")
        print(f"   错误: {e}")
        print("   请确保服务器正在运行 (python web_interface.py)")
        return False
    
    # 运行测试
    success = True
    success &= test_recording_api(base_url)
    test_file_upload_api(base_url)
    
    if success:
        print("\n🎉 所有测试通过！录音功能已准备就绪。")
        print("\n📝 使用说明:")
        print("1. 在电脑浏览器上，系统会自动使用浏览器录音功能")
        print("2. 在移动端或云服务器上，系统会自动切换到服务器录音模式")
        print("3. 前端会根据环境自动选择最佳的录音方式")
    else:
        print("\n⚠️ 部分测试失败，请检查服务器配置和依赖项。")
    
    return success

if __name__ == "__main__":
    main()
