"""
语音识别配置文件
支持多个语音识别服务提供商
"""

import os
from enum import Enum

class SpeechProvider(Enum):
    """语音识别服务提供商"""
    ALIYUN = "aliyun"      # 阿里云
    BAIDU = "baidu"        # 百度
    TENCENT = "tencent"    # 腾讯云
    BROWSER = "browser"    # 浏览器 Web Speech API（需要 VPN）

# 当前使用的提供商
CURRENT_PROVIDER = SpeechProvider.ALIYUN

# ===== 阿里云配置 =====
# 方式1: 传统语音识别服务（需要 AccessKey + AppKey）
# 获取方法：https://ram.console.aliyun.com/manage/ak
ALIYUN_ACCESS_KEY_ID = os.getenv('ALIYUN_ACCESS_KEY_ID', '')
ALIYUN_ACCESS_KEY_SECRET = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '')
ALIYUN_APP_KEY = os.getenv('ALIYUN_APP_KEY', '')  # 语音识别应用的 AppKey

# 方式2: DashScope API（推荐，配置更简单）
# 获取方法：https://dashscope.console.aliyun.com/apiKey
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', 'sk-ef6f244b67a645ecb21e4641170f05cd')

# ===== 百度配置 =====
# 获取方法：https://console.bce.baidu.com/ai/#/ai/speech/app/list
BAIDU_APP_ID = os.getenv('BAIDU_APP_ID', '120363220')
BAIDU_API_KEY = os.getenv('BAIDU_API_KEY', 'toFLcCsRz4UaIlW6hzj0UFIu')
BAIDU_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY', 'CgOpRrQRkTOpQZl6G5wwbA8OmdNtDtST')

# ===== 腾讯云配置 =====
# 获取方法：https://console.cloud.tencent.com/cam/capi
TENCENT_SECRET_ID = os.getenv('TENCENT_SECRET_ID', '')
TENCENT_SECRET_KEY = os.getenv('TENCENT_SECRET_KEY', '')

# ===== 通用配置 =====
LANGUAGE = 'zh-CN'  # 识别语言
SAMPLE_RATE = 16000  # 采样率
ENCODING = 'pcm'     # 音频编码格式

# 识别参数
ENABLE_PUNCTUATION = False  # 是否添加标点符号
ENABLE_INTERMEDIATE_RESULT = True  # 是否返回中间结果
MAX_SINGLE_SEGMENT_TIME = 60000  # 单次识别最大时长（毫秒）

