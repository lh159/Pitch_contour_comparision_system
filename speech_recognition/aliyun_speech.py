"""
阿里云实时语音识别 SDK 封装
使用阿里云语音服务 NLS SDK
"""

import json
import threading
import time
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import nls
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False
    logger.warning("阿里云 NLS SDK 未安装，请运行: pip install aliyun-python-sdk-core aliyun-nls-python3-sdk")


class AliyunRealtimeSpeech:
    """阿里云实时语音识别"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        """
        初始化阿里云语音识别
        
        Args:
            access_key_id: 阿里云 AccessKey ID
            access_key_secret: 阿里云 AccessKey Secret
            app_key: 语音识别应用的 AppKey
        """
        if not ALIYUN_SDK_AVAILABLE:
            raise ImportError("阿里云 NLS SDK 未安装")
        
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.transcriber = None
        self.on_result_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        self.is_running = False
        
    def on_sentence_begin(self, message, *args):
        """句子开始回调"""
        logger.debug(f"句子开始: {message}")
        
    def on_sentence_end(self, message, *args):
        """句子结束回调（最终结果）"""
        try:
            result = json.loads(message)
            text = result.get('payload', {}).get('result', '')
            if text and self.on_result_callback:
                logger.info(f"识别结果: {text}")
                self.on_result_callback(text, is_final=True)
        except Exception as e:
            logger.error(f"解析结果失败: {e}")
            
    def on_result_changed(self, message, *args):
        """中间结果回调"""
        try:
            result = json.loads(message)
            text = result.get('payload', {}).get('result', '')
            if text and self.on_result_callback:
                logger.debug(f"中间结果: {text}")
                self.on_result_callback(text, is_final=False)
        except Exception as e:
            logger.error(f"解析中间结果失败: {e}")
            
    def on_start(self, message, *args):
        """开始回调"""
        logger.info("语音识别已启动")
        
    def on_error(self, message, *args):
        """错误回调"""
        logger.error(f"识别错误: {message}")
        if self.on_error_callback:
            self.on_error_callback(message)
            
    def on_close(self, *args):
        """关闭回调"""
        logger.info("语音识别已关闭")
        self.is_running = False
        
    def start(self, on_result: Callable, on_error: Optional[Callable] = None):
        """
        开始实时语音识别
        
        Args:
            on_result: 结果回调函数 callback(text: str, is_final: bool)
            on_error: 错误回调函数 callback(error: str)
        """
        if self.is_running:
            logger.warning("识别已在运行中")
            return
            
        self.on_result_callback = on_result
        self.on_error_callback = on_error
        
        try:
            # 创建实时语音识别对象
            self.transcriber = nls.NlsSpeechTranscriber(
                token=self._get_token(),
                appkey=self.app_key,
                on_sentence_begin=self.on_sentence_begin,
                on_sentence_end=self.on_sentence_end,
                on_result_changed=self.on_result_changed,
                on_start=self.on_start,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            
            # 配置参数
            self.transcriber.start(
                ex={'enable_intermediate_result': True}  # 启用中间结果
            )
            
            self.is_running = True
            logger.info("阿里云语音识别启动成功")
            
        except Exception as e:
            error_msg = f"启动识别失败: {str(e)}"
            logger.error(error_msg)
            if self.on_error_callback:
                self.on_error_callback(error_msg)
                
    def send_audio(self, audio_data: bytes):
        """
        发送音频数据
        
        Args:
            audio_data: PCM 格式的音频数据（16000Hz, 16bit, 单声道）
        """
        if not self.is_running or not self.transcriber:
            logger.warning("识别未运行，无法发送音频")
            return
            
        try:
            self.transcriber.send_audio(audio_data)
        except Exception as e:
            logger.error(f"发送音频失败: {e}")
            
    def stop(self):
        """停止语音识别"""
        if not self.is_running or not self.transcriber:
            return
            
        try:
            self.transcriber.stop()
            self.is_running = False
            logger.info("已停止语音识别")
        except Exception as e:
            logger.error(f"停止识别失败: {e}")
            
    def _get_token(self) -> str:
        """
        获取阿里云 Token
        Token 有效期为 24 小时
        """
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest
            
            client = AcsClient(self.access_key_id, self.access_key_secret, 'cn-shanghai')
            
            request = CommonRequest()
            request.set_method('POST')
            request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
            request.set_version('2019-02-28')
            request.set_action_name('CreateToken')
            
            response = client.do_action_with_exception(request)
            token_info = json.loads(response)
            
            token = token_info['Token']['Id']
            expire_time = token_info['Token']['ExpireTime']
            
            logger.info(f"Token 获取成功，有效期至: {expire_time}")
            return token
            
        except Exception as e:
            logger.error(f"获取 Token 失败: {e}")
            raise


class AliyunSpeechSimple:
    """
    简化版阿里云语音识别（使用 HTTP API）
    不需要安装 SDK，只需要 requests
    适合快速测试
    """
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        
    def recognize_file(self, audio_file_path: str) -> str:
        """
        识别音频文件（一句话识别）
        
        Args:
            audio_file_path: 音频文件路径（支持 WAV, MP3 等）
            
        Returns:
            识别结果文本
        """
        import requests
        import base64
        import hmac
        import hashlib
        from datetime import datetime
        
        # 读取音频文件
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
            
        # Base64 编码
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # API 地址
        url = 'https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr'
        
        # 请求参数
        params = {
            'appkey': self.app_key,
            'format': 'wav',
            'sample_rate': 16000,
        }
        
        # 请求体
        data = {
            'audio_data': audio_base64
        }
        
        # 发送请求
        try:
            response = requests.post(
                url,
                params=params,
                json=data,
                headers={
                    'Content-Type': 'application/json',
                },
                timeout=10
            )
            
            result = response.json()
            
            if result.get('status') == 20000000:  # 成功
                return result.get('result', '')
            else:
                error_msg = result.get('message', '未知错误')
                logger.error(f"识别失败: {error_msg}")
                return ''
                
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return ''

