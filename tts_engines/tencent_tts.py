# -*- coding: utf-8 -*-
"""
腾讯云TTS引擎
官方文档: https://cloud.tencent.com/document/product/1073
"""
import json
import base64
import hmac
import hashlib
import time
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TencentTTS:
    """腾讯云TTS引擎"""
    
    def __init__(self, secret_id: str, secret_key: str):
        """
        初始化腾讯云TTS
        
        Args:
            secret_id: 腾讯云SecretId
            secret_key: 腾讯云SecretKey
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        
        # API配置
        self.endpoint = "https://tts.tencentcloudapi.com"
        self.service = "tts"
        self.version = "2019-08-23"
        self.action = "TextToVoice"
        self.region = "ap-beijing"
        
        # 默认参数
        self.default_params = {
            'VoiceType': 101001,  # 音色 101001=智逍遥
            'Speed': 0,           # 语速 -2到6
            'Volume': 0,          # 音量 -10到10
            'PrimaryLanguage': 1,  # 主语言 1=中文
            'SampleRate': 16000,   # 采样率
            'Codec': 'wav'         # 编码格式
        }
    
    def _sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 1. 拼接规范请求串
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        # 2. 拼接待签名字符串
        timestamp = str(int(time.time()))
        date = time.strftime("%Y-%m-%d", time.gmtime(int(timestamp)))
        
        canonical_request = f"POST\n/\n\n{query_string}\n"
        string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{date}/{self.service}/tc3_request\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # 3. 计算签名
        secret_date = hmac.new(f"TC3{self.secret_key}".encode(), date.encode(), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, self.service.encode(), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode(), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        
        # 4. 拼接 Authorization
        authorization = f"TC3-HMAC-SHA256 " \
                       f"Credential={self.secret_id}/{date}/{self.service}/tc3_request, " \
                       f"SignedHeaders=content-type;host, " \
                       f"Signature={signature}"
        
        return authorization, timestamp
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            **kwargs: 额外参数
                - VoiceType: 音色
                - Speed: 语速
                - Volume: 音量
        
        Returns:
            bool: 成功返回True
        """
        try:
            # 准备参数
            params = self.default_params.copy()
            params.update(kwargs)
            params['Text'] = text
            
            # 请求体
            body = json.dumps(params)
            
            # 生成签名
            authorization, timestamp = self._sign(params)
            
            # 请求头
            headers = {
                'Authorization': authorization,
                'Content-Type': 'application/json; charset=utf-8',
                'Host': 'tts.tencentcloudapi.com',
                'X-TC-Action': self.action,
                'X-TC-Timestamp': timestamp,
                'X-TC-Version': self.version,
                'X-TC-Region': self.region
            }
            
            # 发送请求
            response = requests.post(
                self.endpoint,
                headers=headers,
                data=body,
                timeout=30
            )
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            if 'Response' in result and 'Audio' in result['Response']:
                # 成功，解码并保存音频
                audio_data = base64.b64decode(result['Response']['Audio'])
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"腾讯云TTS合成成功: {text} -> {output_path}")
                return True
            else:
                # 错误
                response = result.get('Response', {}) or {}
                error = response.get('Error', {})
                logger.error(f"腾讯云TTS合成失败: {error}")
                return False
                
        except Exception as e:
            logger.error(f"腾讯云TTS合成异常: {e}")
            return False
    
    def get_voice_list(self) -> Dict[str, str]:
        """获取可用的音色列表"""
        return {
            '101001': '智逍遥(男声)',
            '101002': '智聆(女声)',
            '101003': '智美(女声)',
            '101004': '智云(男声)',
            '101005': '智莉(女声)',
            '101006': '智言(男声)',
            '101007': '智娜(女声)',
            '101008': '智琪(女声)',
            '101009': '智芸(女声)',
            '101010': '智华(男声)',
            '101011': '智燕(女声)',
            '101012': '智丹(女声)',
            '101013': '智辉(男声)',
            '101014': '智宁(女声)',
            '101015': '智萌(女声)',
            '101016': '智甜(女声)',
            '101017': '智蓉(女声)',
            '101018': '智靖(男声)',
            '101019': '智彤(女声)'
        }
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            # 简单测试请求
            test_text = "测试"
            temp_file = "temp_test.wav"
            result = self.synthesize(test_text, temp_file)
            if result:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            return result
        except:
            return False

# 测试函数
def test_tencent_tts():
    """测试腾讯云TTS功能"""
    import os
    
    # 从环境变量获取密钥
    secret_id = os.getenv('TENCENT_SECRET_ID')
    secret_key = os.getenv('TENCENT_SECRET_KEY')
    
    if not secret_id or not secret_key:
        print("请设置环境变量 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")
        return False
    
    tts = TencentTTS(secret_id, secret_key)
    
    # 测试合成
    test_text = "你好，这是腾讯云TTS测试。"
    output_file = "test_tencent_tts.wav"
    
    if tts.synthesize(test_text, output_file):
        print(f"✓ 腾讯云TTS测试成功，文件保存为: {output_file}")
        return True
    else:
        print("✗ 腾讯云TTS测试失败")
        return False

if __name__ == "__main__":
    test_tencent_tts()
