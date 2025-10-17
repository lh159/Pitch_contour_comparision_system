"""
阿里云 DashScope 语音识别服务封装
使用 DashScope API (sk-xxx 格式的密钥)
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional

class DashScopeSpeechRecognizer:
    """DashScope 语音识别服务"""
    
    def __init__(self, api_key: str):
        """
        初始化 DashScope 语音识别
        
        Args:
            api_key: DashScope API Key (格式: sk-xxxx)
        """
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr"
        
    def recognize(self, audio_file_path: str) -> Optional[str]:
        """
        识别音频文件
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            识别的文本，失败返回 None
        """
        try:
            # DashScope 语音识别 API
            # 参考: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-qianwen-audio-api
            
            # 方式1: 使用文件上传
            with open(audio_file_path, 'rb') as f:
                files = {
                    'audio': (os.path.basename(audio_file_path), f, 'audio/wav')
                }
                
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'X-DashScope-Async': 'false'  # 同步调用
                }
                
                data = {
                    'model': 'paraformer-v1',  # 使用通用识别模型
                    'language_hints': ['zh'],   # 中文识别
                }
                
                response = requests.post(
                    f"{self.base_url}/recognition",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 解析结果
                    if result.get('output') and result['output'].get('text'):
                        text = result['output']['text']
                        print(f"✓ DashScope 识别成功: {text}")
                        return text
                    else:
                        print(f"⚠️ DashScope 识别无结果: {result}")
                        return None
                else:
                    print(f"❌ DashScope 识别失败: HTTP {response.status_code}")
                    print(f"响应: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ DashScope 识别异常: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.api_key or not self.api_key.startswith('sk-'):
            return False
        
        try:
            # 简单测试 API key 是否有效
            # 400 错误表示请求方法不对，但 API key 是有效的
            # 401 错误才表示 API key 无效
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            response = requests.get(
                "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/models",
                headers=headers,
                timeout=5
            )
            # 200: 成功, 400: 方法不对但key有效, 404: 端点不存在但key有效
            return response.status_code in [200, 400, 404]
        except:
            return False


def test_dashscope_recognition():
    """测试 DashScope 语音识别"""
    from config.speech_config import DASHSCOPE_API_KEY
    
    if not DASHSCOPE_API_KEY:
        print("❌ 未配置 DASHSCOPE_API_KEY")
        return
    
    print(f"✓ API Key: {DASHSCOPE_API_KEY[:10]}...")
    
    recognizer = DashScopeSpeechRecognizer(DASHSCOPE_API_KEY)
    
    # 检查可用性
    if recognizer.is_available():
        print("✓ DashScope 服务可用")
    else:
        print("❌ DashScope 服务不可用，请检查 API Key")
        return
    
    # 测试识别（需要提供测试音频文件）
    test_audio = "uploads/test.wav"
    if os.path.exists(test_audio):
        result = recognizer.recognize(test_audio)
        print(f"识别结果: {result}")
    else:
        print(f"⚠️ 测试音频文件不存在: {test_audio}")


if __name__ == "__main__":
    test_dashscope_recognition()

