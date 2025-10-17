"""
百度语音识别 REST API 封装
使用百度极速版语音识别服务（推荐 PCM 格式）
"""

import json
import logging
import base64
import requests
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 百度 SDK 可用性标志（REST API 模式始终可用）
BAIDU_SDK_AVAILABLE = True


class BaiduSpeech:
    """百度语音识别（使用 REST API）"""
    
    # API 端点
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    ASR_URL_PRO = "https://vop.baidu.com/pro_api"  # 极速版（推荐）
    ASR_URL_STANDARD = "https://vop.baidu.com/server_api"  # 标准版
    
    def __init__(self, app_id: str, api_key: str, secret_key: str):
        """
        初始化百度语音识别
        
        Args:
            app_id: 百度 App ID
            api_key: 百度 API Key
            secret_key: 百度 Secret Key
        """
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        
        # 获取 Access Token
        self._get_access_token()
    
    def _get_access_token(self):
        """获取百度 API Access Token"""
        try:
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }
            response = requests.post(self.TOKEN_URL, params=params)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                logger.info("百度 Access Token 获取成功")
            else:
                logger.error(f"获取 Access Token 失败: {result}")
                raise Exception("无法获取 Access Token")
                
        except Exception as e:
            logger.error(f"获取 Access Token 异常: {e}")
            raise
    
    def _refresh_token(self):
        """刷新 Access Token"""
        logger.info("刷新 Access Token...")
        self._get_access_token()
    
    def _recognize_api(self, audio_data: bytes, format: str, rate: int, channel: int = 1) -> str:
        """
        调用百度语音识别 API
        
        Args:
            audio_data: 音频数据（PCM 或其他格式）
            format: 音频格式 ('pcm', 'wav', 'amr', 'mp3')
            rate: 采样率 (8000 或 16000)
            channel: 声道数 (1 或 2)
            
        Returns:
            识别结果文本
        """
        try:
            # 检查音频数据大小
            if len(audio_data) == 0:
                logger.error("⚠️ 音频数据为空，无法识别")
                return ''
            
            if len(audio_data) < 1000:
                logger.warning(f"⚠️ 音频数据过小 ({len(audio_data)} bytes)，可能导致识别失败")
            
            # Base64 编码音频数据
            speech = base64.b64encode(audio_data).decode('utf-8')
            
            # 构造请求数据
            data = {
                'format': format,
                'rate': rate,
                'channel': channel,
                'cuid': 'python_client',
                'token': self.access_token,
                'speech': speech,
                'len': len(audio_data),
                'dev_pid': 80001  # 极速版（推荐 PCM 格式）
            }
            
            logger.info(f"📤 发送识别请求: format={format}, rate={rate}, len={len(audio_data)}, token={self.access_token[:20]}...")
            
            # 调用 API
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.ASR_URL_PRO,  # 使用极速版端点
                data=json.dumps(data),
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            # 如果 Token 过期，刷新后重试一次
            if result.get('err_no') == 110:  # Token 过期
                logger.warning("Token 过期，正在刷新...")
                self._refresh_token()
                data['token'] = self.access_token
                response = requests.post(
                    self.ASR_URL_PRO,
                    data=json.dumps(data),
                    headers=headers,
                    timeout=10
                )
                result = response.json()
            
            err_no = result.get('err_no')
            if err_no == 0:
                # 识别成功
                results = result.get('result', [])
                text = ''.join(results) if results else ''
                logger.info(f"✅ 识别成功: {text}")
                return text
            else:
                # 识别失败
                err_msg = result.get('err_msg', '未知错误')
                sn = result.get('sn', 'N/A')
                logger.error(f"❌ 识别失败: 错误码 {err_no}: {err_msg}")
                logger.error(f"   请求 SN: {sn}")
                logger.error(f"   完整响应: {json.dumps(result, ensure_ascii=False)}")
                
                # 错误码 6 通常表示权限问题或配置问题
                if err_no == 6:
                    logger.error("⚠️ 错误码 6 可能的原因：")
                    logger.error("   1. AppID/API Key/Secret Key 配置不匹配")
                    logger.error("   2. 该 AppID 未开通极速版服务权限")
                    logger.error("   3. Token 已过期或无效")
                    logger.error(f"   4. 音频格式或参数错误 (format={format}, rate={rate}, len={len(audio_data)})")
                    logger.error("💡 建议：请检查百度控制台的服务开通状态和密钥配置")
                    logger.error(f"💡 当前使用 Token: {self.access_token[:30]}...")
                
                return ''
                
        except Exception as e:
            logger.error(f"识别异常: {e}")
            return ''
        
    def recognize_file(self, audio_file_path: str, format: str = 'wav', rate: int = 16000, channel: int = 1) -> str:
        """
        识别音频文件
        
        Args:
            audio_file_path: 音频文件路径
            format: 音频格式 ('wav', 'pcm', 'amr', 'mp3')
            rate: 采样率 (8000 或 16000)
            channel: 声道数 (1 或 2)
            
        Returns:
            识别结果文本
        """
        try:
            # 读取音频文件
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            # 调用内部 API 方法
            return self._recognize_api(audio_data, format, rate, channel)
                
        except Exception as e:
            logger.error(f"读取文件异常: {e}")
            return ''
            
    def recognize_bytes(self, audio_data: bytes, format: str = 'pcm', rate: int = 16000) -> str:
        """
        识别音频数据（字节流）
        
        Args:
            audio_data: PCM 格式的音频数据
            format: 音频格式
            rate: 采样率
            
        Returns:
            识别结果文本
        """
        return self._recognize_api(audio_data, format, rate)

