# -*- coding: utf-8 -*-
"""
百度智能云TTS引擎
官方文档: https://cloud.baidu.com/doc/SPEECH/s/Jk38y8him
"""
import json
import base64
import requests
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaiduTTS:
    """百度智能云TTS引擎"""
    
    def __init__(self, api_key: str, secret_key: str):
        """
        初始化百度TTS
        
        Args:
            api_key: 百度云API Key
            secret_key: 百度云Secret Key
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expires_at = 0
        
        # API配置
        self.token_url = "https://aip.baidubce.com/oauth/2.0/token"
        self.tts_url = "https://tsn.baidu.com/text2audio"
        
        # 默认参数
        self.default_params = {
            'spd': 5,    # 语速 0-15，默认5
            'pit': 5,    # 音调 0-15，默认5  
            'vol': 8,    # 音量 0-15，默认5
            'per': 4,    # 发音人 0女声,1男声,3度逍遥,4度丫丫,5度小娇
            'lan': 'zh'  # 语言
        }
    
    def _get_access_token(self) -> bool:
        """获取access_token"""
        try:
            # 检查token是否还有效
            if self.access_token and time.time() < self.token_expires_at:
                return True
            
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }
            
            response = requests.post(self.token_url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if 'access_token' in result:
                self.access_token = result['access_token']
                # token有效期约30天，这里设置为25天后过期
                self.token_expires_at = time.time() + (25 * 24 * 3600)
                logger.info("百度TTS access_token获取成功")
                return True
            else:
                logger.error(f"获取access_token失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"获取百度TTS access_token异常: {e}")
            return False
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            **kwargs: 额外参数
                - spd: 语速 0-15
                - pit: 音调 0-15
                - vol: 音量 0-15
                - per: 发音人
        
        Returns:
            bool: 成功返回True
        """
        try:
            # 获取access_token
            if not self._get_access_token():
                return False
            
            # 准备参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 请求数据
            data = {
                'tex': text,
                'tok': self.access_token,
                'cuid': 'python_client',
                'ctp': 1,  # 客户端类型
                **params
            }
            
            # 发送请求
            response = requests.post(
                self.tts_url, 
                data=data, 
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()
            
            # 检查响应
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                # 成功，保存音频文件
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"百度TTS合成成功: {text} -> {output_path}")
                return True
            else:
                # 错误响应，通常是JSON格式
                try:
                    error_info = json.loads(response.content.decode('utf-8'))
                    logger.error(f"百度TTS合成失败: {error_info}")
                except:
                    logger.error(f"百度TTS合成失败，响应内容: {response.content}")
                return False
                
        except Exception as e:
            logger.error(f"百度TTS合成异常: {e}")
            return False
    
    def get_voice_list(self) -> Dict[str, str]:
        """获取可用的发音人列表"""
        return {
            '0': '度小美(女声)',
            '1': '度小宇(男声)', 
            '3': '度逍遥(情感男声)',
            '4': '度丫丫(萝莉女声)',
            '5': '度小娇(情感女声)',
            '103': '度米朵(情感童声)',
            '106': '度博文(情感男声)',
            '110': '度小童(萌娃童声)',
            '111': '度小萌(萌娃童声)',
            '5003': '度小鹿(温暖女声)',
            '5004': '度小博(磁性男声)'
        }
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._get_access_token()

# 测试函数
def test_baidu_tts():
    """测试百度TTS功能"""
    import os
    
    # 从环境变量获取密钥
    api_key = os.getenv('BAIDU_API_KEY')
    secret_key = os.getenv('BAIDU_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("请设置环境变量 BAIDU_API_KEY 和 BAIDU_SECRET_KEY")
        return False
    
    tts = BaiduTTS(api_key, secret_key)
    
    # 测试合成
    test_text = "你好，这是百度TTS测试。"
    output_file = "test_baidu_tts.wav"
    
    if tts.synthesize(test_text, output_file):
        print(f"✓ 百度TTS测试成功，文件保存为: {output_file}")
        return True
    else:
        print("✗ 百度TTS测试失败")
        return False

if __name__ == "__main__":
    test_baidu_tts()
