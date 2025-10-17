"""
语音识别模块
支持多个服务提供商
"""

from .aliyun_speech import AliyunRealtimeSpeech, AliyunSpeechSimple, ALIYUN_SDK_AVAILABLE

__all__ = [
    'AliyunRealtimeSpeech',
    'AliyunSpeechSimple', 
    'ALIYUN_SDK_AVAILABLE'
]

