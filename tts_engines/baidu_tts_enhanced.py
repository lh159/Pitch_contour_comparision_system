# -*- coding: utf-8 -*-
"""
增强的百度TTS引擎，支持时间戳生成
"""
import os
import json
import time
import hashlib
import requests
import base64
from typing import Dict, List, Optional
from urllib.parse import urlencode

class BaiduTTSWithTimestamp:
    """增强的百度TTS，支持时间戳生成"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expires_at = 0
        
        # API 端点
        self.token_url = "https://aip.baidubce.com/oauth/2.0/token"
        self.tts_url = "https://tsn.baidu.com/text2audio"
        # 注意：百度TTS实际上不直接提供字级时间戳API
        # 这里提供的是一个兼容的实现框架
        
    def _get_access_token(self) -> bool:
        """获取访问令牌"""
        if self.access_token and time.time() < self.token_expires_at:
            return True
        
        try:
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }
            
            response = requests.post(self.token_url, data=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                # 提前5分钟刷新token
                self.token_expires_at = time.time() + result.get('expires_in', 3600) - 300
                print("✓ 百度TTS访问令牌获取成功")
                return True
            else:
                print(f"✗ 获取访问令牌失败: {result}")
                return False
                
        except Exception as e:
            print(f"✗ 获取百度TTS访问令牌异常: {e}")
            return False
    
    def synthesize_with_timestamps(self, text: str, output_path: str) -> Dict:
        """
        使用百度TTS生成音频并尝试获取时间戳
        注意：百度TTS标准API不提供字级时间戳，这里提供兼容实现
        """
        try:
            # 1. 先生成标准TTS音频
            audio_success = self._synthesize_standard_audio(text, output_path)
            
            if not audio_success:
                return {'success': False, 'error': 'TTS音频生成失败'}
            
            # 2. 由于百度TTS标准API不提供时间戳，使用通用时间戳生成器
            from timestamp_generator import UniversalTimestampGenerator
            
            timestamp_generator = UniversalTimestampGenerator()
            timestamp_result = timestamp_generator.generate_timestamps(text, output_path, 'auto')
            
            if timestamp_result['success']:
                return {
                    'success': True,
                    'audio_path': output_path,
                    'char_timestamps': timestamp_result['char_timestamps'],
                    'duration': timestamp_result['duration'],
                    'method': f"baidu_tts + {timestamp_result['method']}",
                    'tts_engine': 'baidu'
                }
            else:
                # 即使时间戳生成失败，也返回音频
                return {
                    'success': True,
                    'audio_path': output_path,
                    'char_timestamps': [],
                    'duration': 0,
                    'method': 'baidu_tts_only',
                    'tts_engine': 'baidu',
                    'warning': '时间戳生成失败'
                }
                
        except Exception as e:
            print(f"百度TTS增强合成失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _synthesize_standard_audio(self, text: str, output_path: str) -> bool:
        """生成标准TTS音频"""
        try:
            if not self._get_access_token():
                return False
            
            # 准备TTS参数
            params = {
                'tex': text,           # 要合成的文本
                'tok': self.access_token,  # 访问令牌
                'cuid': self._generate_cuid(),  # 用户唯一标识
                'ctp': 1,              # 客户端类型
                'lan': 'zh',           # 语言选择
                'spd': 5,              # 语速 (0-15)
                'pit': 5,              # 音调 (0-15)
                'vol': 5,              # 音量 (0-15)
                'per': 0,              # 发音人选择
                'aue': 6               # 音频编码，6为wav格式
            }
            
            # 发送TTS请求
            response = requests.post(
                self.tts_url,
                data=params,
                timeout=30,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            response.raise_for_status()
            
            # 检查响应类型
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                # 成功获取音频数据
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✓ 百度TTS音频生成成功: {output_path}")
                return True
            else:
                # 可能是错误响应
                try:
                    error_info = response.json()
                    print(f"✗ 百度TTS生成失败: {error_info}")
                except:
                    print(f"✗ 百度TTS生成失败: 响应格式错误")
                return False
                
        except Exception as e:
            print(f"✗ 百度TTS标准音频生成异常: {e}")
            return False
    
    def _generate_cuid(self) -> str:
        """生成用户唯一标识"""
        # 使用API密钥生成一个稳定的CUID
        return hashlib.md5(self.api_key.encode()).hexdigest()[:16]
    
    def synthesize_with_ssml_timestamps(self, text: str, output_path: str) -> Dict:
        """
        使用SSML标记尝试获取更精确的时间戳
        注意：这是一个实验性功能，需要百度TTS高级版本支持
        """
        try:
            # 生成SSML标记的文本
            ssml_text = self._generate_ssml_with_marks(text)
            
            # 调用TTS API
            result = self.synthesize_with_timestamps(ssml_text, output_path)
            
            if result['success']:
                # 解析SSML标记生成的时间戳
                char_timestamps = self._parse_ssml_timestamps(text, result)
                result['char_timestamps'] = char_timestamps
                result['method'] = 'baidu_ssml_timestamps'
            
            return result
            
        except Exception as e:
            print(f"SSML时间戳生成失败: {e}")
            # 降级到标准方法
            return self.synthesize_with_timestamps(text, output_path)
    
    def _generate_ssml_with_marks(self, text: str) -> str:
        """为文本生成SSML标记"""
        ssml_parts = ['<speak>']
        
        for i, char in enumerate(text):
            # 为每个字符添加标记
            ssml_parts.append(f'<mark name="char_{i}"/>{char}')
        
        ssml_parts.append('</speak>')
        return ''.join(ssml_parts)
    
    def _parse_ssml_timestamps(self, original_text: str, tts_result: Dict) -> List[Dict]:
        """解析SSML生成的时间戳"""
        # 这里是示例实现，实际需要根据百度TTS SSML响应格式调整
        char_timestamps = []
        
        # 如果没有SSML时间戳数据，使用现有的时间戳
        if tts_result.get('char_timestamps'):
            return tts_result['char_timestamps']
        
        # 否则生成均匀分布的时间戳
        duration = tts_result.get('duration', 3.0)
        char_count = len(original_text)
        
        if char_count > 0:
            char_duration = duration / char_count
            
            for i, char in enumerate(original_text):
                char_timestamps.append({
                    'char': char,
                    'start_time': i * char_duration,
                    'end_time': (i + 1) * char_duration,
                    'confidence': 0.6,  # SSML方法的置信度
                    'index': i
                })
        
        return char_timestamps

class BaiduTTSEnhancedManager:
    """增强的百度TTS管理器"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.tts_engine = BaiduTTSWithTimestamp(api_key, secret_key)
    
    def generate_audio_with_timestamps(self, text: str, output_path: str, 
                                     method: str = 'auto') -> Dict:
        """
        生成带时间戳的音频
        :param text: 要合成的文本
        :param output_path: 音频输出路径
        :param method: 时间戳生成方法 ('auto', 'ssml', 'standard')
        :return: 生成结果
        """
        try:
            if method == 'ssml':
                return self.tts_engine.synthesize_with_ssml_timestamps(text, output_path)
            else:
                return self.tts_engine.synthesize_with_timestamps(text, output_path)
                
        except Exception as e:
            print(f"增强TTS生成失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def is_available(self) -> bool:
        """检查百度TTS是否可用"""
        return self.tts_engine._get_access_token()

# 使用示例和测试
if __name__ == '__main__':
    import sys
    
    # 从环境变量或配置文件获取密钥
    api_key = os.getenv('BAIDU_API_KEY')
    secret_key = os.getenv('BAIDU_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("请设置BAIDU_API_KEY和BAIDU_SECRET_KEY环境变量")
        sys.exit(1)
    
    # 创建增强的TTS管理器
    tts_manager = BaiduTTSEnhancedManager(api_key, secret_key)
    
    # 测试可用性
    if not tts_manager.is_available():
        print("百度TTS服务不可用")
        sys.exit(1)
    
    # 测试用例
    if len(sys.argv) >= 2:
        test_text = sys.argv[1]
        output_path = f"test_baidu_tts_{int(time.time())}.wav"
        
        print(f"\n=== 测试百度TTS增强功能: {test_text} ===")
        
        # 测试不同方法
        methods = ['auto', 'ssml']
        
        for method in methods:
            print(f"\n--- 方法: {method} ---")
            result = tts_manager.generate_audio_with_timestamps(test_text, output_path, method)
            
            if result['success']:
                print(f"✓ 音频生成成功: {result['audio_path']}")
                print(f"  方法: {result['method']}")
                print(f"  时长: {result.get('duration', 0):.2f}秒")
                
                timestamps = result.get('char_timestamps', [])
                if timestamps:
                    print(f"  时间戳数量: {len(timestamps)}")
                    for i, ts in enumerate(timestamps[:3]):
                        print(f"    {i}: '{ts['char']}' {ts['start_time']:.2f}-{ts['end_time']:.2f}s")
                    if len(timestamps) > 3:
                        print(f"    ... 还有 {len(timestamps) - 3} 个时间戳")
                else:
                    print("  无时间戳数据")
                
                if result.get('warning'):
                    print(f"  警告: {result['warning']}")
            else:
                print(f"✗ 生成失败: {result.get('error')}")
            
            # 清理测试文件
            if os.path.exists(output_path):
                os.remove(output_path)
    else:
        print("使用方法: python baidu_tts_enhanced.py '测试文本'")
        print("请确保设置了BAIDU_API_KEY和BAIDU_SECRET_KEY环境变量")
