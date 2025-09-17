# -*- coding: utf-8 -*-
"""
百度TTS引擎封装
"""

import os
import requests
import json
import base64
from typing import Dict, List, Optional
from . import TTSEngineBase, DialogueTTSEngine

class BaiduTTSEngine(TTSEngineBase, DialogueTTSEngine):
    """百度TTS引擎"""
    
    def __init__(self, api_key: str, secret_key: str):
        super().__init__("百度TTS")
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        
        # 支持的功能特性
        self.supported_features = {
            'emotion_control': True,
            'voice_cloning': False,
            'speed_control': True,
            'volume_control': True,
            'multilingual': False
        }
        
        # 角色语音配置
        self.voice_profiles = {
            'child': {
                'per': 5,  # 度小娇，可爱童声
                'description': '儿童角色语音'
            },
            'adult_female': {
                'per': 0,  # 度小美，标准女声
                'description': '成年女性角色语音'
            },
            'adult_male': {
                'per': 1,  # 度小宇，标准男声
                'description': '成年男性角色语音'
            },
            'elderly': {
                'per': 4,  # 度丫丫，温和女声
                'description': '老年角色语音'
            }
        }
    
    def initialize(self) -> bool:
        """初始化百度TTS引擎"""
        try:
            # 获取访问令牌
            self.access_token = self._get_access_token()
            if self.access_token:
                self.is_initialized = True
                print(f"✓ {self.name} 初始化成功")
                return True
            else:
                print(f"✗ {self.name} 初始化失败：无法获取访问令牌")
                return False
        except Exception as e:
            print(f"✗ {self.name} 初始化失败: {e}")
            return False
    
    def _get_access_token(self) -> Optional[str]:
        """获取百度API访问令牌"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get("access_token")
            else:
                print(f"获取访问令牌失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"获取访问令牌异常: {e}")
            return None
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """标准语音合成"""
        per = kwargs.get('per', 0)  # 默认度小美
        spd = kwargs.get('spd', 5)  # 语速
        pit = kwargs.get('pit', 5)  # 音调
        vol = kwargs.get('vol', 5)  # 音量
        
        return self._synthesize_with_params(text, output_path, per, spd, pit, vol)
    
    def synthesize_dialogue(self, text: str, character: str = 'adult_female', 
                          emotion: str = 'calm', output_path: str = None, **kwargs) -> bool:
        """为场景对话合成语音"""
        if not self.is_initialized:
            print(f"{self.name} 未初始化")
            return False
        
        # 获取角色配置
        if character not in self.voice_profiles:
            print(f"不支持的角色类型: {character}")
            character = 'adult_female'
        
        profile = self.voice_profiles[character]
        per = profile['per']
        
        # 根据情感调整语音参数
        spd, pit, vol = self._get_emotion_params(emotion)
        
        # 生成输出路径
        if output_path is None:
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_path = f"cache/indextts2/baidu_dialogue_{character}_{emotion}_{text_hash}.wav"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        return self._synthesize_with_params(text, output_path, per, spd, pit, vol)
    
    def _get_emotion_params(self, emotion: str) -> tuple:
        """根据情感获取语音参数"""
        emotion_params = {
            'happy': (6, 6, 6),      # 快乐：较快语速，较高音调，较大音量
            'sad': (4, 4, 4),        # 悲伤：较慢语速，较低音调，较小音量
            'angry': (7, 7, 7),      # 愤怒：快语速，高音调，大音量
            'surprised': (6, 7, 6),  # 惊讶：较快语速，高音调，正常音量
            'afraid': (4, 3, 4),     # 恐惧：慢语速，低音调，小音量
            'calm': (5, 5, 5),       # 平静：正常参数
            'gentle': (4, 4, 5),     # 温和：慢语速，低音调，正常音量
        }
        
        return emotion_params.get(emotion, (5, 5, 5))  # 默认平静
    
    def _synthesize_with_params(self, text: str, output_path: str, 
                              per: int, spd: int, pit: int, vol: int) -> bool:
        """使用指定参数合成语音"""
        if not self.access_token:
            print("访问令牌无效")
            return False
        
        url = "https://tsn.baidu.com/text2audio"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        data = {
            'tex': text,
            'tok': self.access_token,
            'cuid': 'pitch_comparison_system',
            'ctp': 1,
            'lan': 'zh',
            'per': per,
            'spd': spd,
            'pit': pit,
            'vol': vol,
            'aue': 6  # WAV格式
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                # 检查响应内容类型
                content_type = response.headers.get('Content-Type', '')
                
                if 'audio' in content_type:
                    # 保存音频文件
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✓ {self.name} 成功合成: {text} -> {output_path}")
                    return True
                else:
                    # 错误响应
                    try:
                        error_info = response.json()
                        print(f"✗ {self.name} 合成失败: {error_info}")
                    except:
                        print(f"✗ {self.name} 合成失败: 未知错误")
                    return False
            else:
                print(f"✗ {self.name} 请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ {self.name} 合成异常: {e}")
            return False
    
    def get_available_characters(self) -> List[str]:
        """获取可用的角色类型"""
        return list(self.voice_profiles.keys())
    
    def get_available_emotions(self) -> List[str]:
        """获取可用的情感类型"""
        return ['happy', 'sad', 'angry', 'surprised', 'afraid', 'calm', 'gentle']
    
    def cleanup(self):
        """清理资源"""
        self.access_token = None
        self.is_initialized = False
