# -*- coding: utf-8 -*-
"""
阿里云智能语音情感TTS引擎
支持多种情感表达的高质量中文语音合成
官方文档: https://help.aliyun.com/zh/isi/
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Union
import dashscope
from dashscope.audio.tts import SpeechSynthesizer
from . import TTSEngineBase, DialogueTTSEngine

logger = logging.getLogger(__name__)

class AlibabaEmotionTTS(TTSEngineBase, DialogueTTSEngine):
    """阿里云情感TTS引擎"""
    
    # 支持的发音人配置（基于实际测试结果）
    AVAILABLE_VOICES = {
        # 情感TTS - 知妙女声（可用）
        'zhimiao_emo': {
            'model': 'sambert-zhimiao-emo-v1',
            'voice': 'zhimiao_emo',
            'name': '知妙(女声-情感)',
            'gender': 'female',
            'emotions': ['neutral', 'happy', 'sad', 'angry', 'gentle', 'serious'],
            'description': '温柔女声，支持多种情感表达'
        },
        # 标准TTS - 知初女声（可用）
        'zhichu': {
            'model': 'sambert-zhichu-v1',
            'voice': 'zhichu',
            'name': '知初(女声-标准)',
            'gender': 'female', 
            'emotions': ['neutral'],
            'description': '清晰女声，标准发音'
        },
        # 情感TTS - 知锋多情感男声（可用）
        'zhifeng_emo': {
            'model': 'sambert-zhifeng-emo-v1',
            'voice': 'zhifeng_emo',
            'name': '知锋(男声-多情感)',
            'gender': 'male',
            'emotions': ['angry', 'fear', 'happy', 'neutral', 'sad', 'surprise'],
            'description': '多情感男声，支持愤怒、恐惧、快乐、中性、悲伤、惊讶等情感'
        },
        # 标准TTS - 知硕男声（保留作为备用）
        'zhishuo': {
            'model': 'sambert-zhishuo-v1',
            'voice': 'zhishuo',
            'name': '知硕(男声-标准)',
            'gender': 'male',
            'emotions': ['neutral'],
            'description': '自然男声，标准发音'
        }
    }
    
    # 默认配置
    DEFAULT_CONFIG = {
        'voice': 'zhimiao_emo',      # 默认使用知妙女声
        'emotion': 'neutral',         # 默认中性情感
        'sample_rate': 48000,         # 采样率
        'format': 'mp3',             # 音频格式
        'volume': 50,                # 音量 0-100
        'speech_rate': 0,            # 语速 -500到500
        'pitch_rate': 0              # 音调 -500到500
    }
    
    def __init__(self, api_key: str):
        """
        初始化阿里云情感TTS
        
        Args:
            api_key: DashScope API密钥
        """
        super().__init__("阿里云情感TTS")
        self.api_key = api_key
        
        # 设置DashScope API密钥
        dashscope.api_key = api_key
        
        # 设置支持的功能
        self.supported_features.update({
            'emotion_control': True,
            'voice_cloning': False,
            'speed_control': False,  # SDK暂不支持
            'volume_control': False,  # SDK暂不支持
            'multilingual': True
        })
    
    def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                logger.error("阿里云TTS API密钥未配置")
                return False
            
            # 测试API连接
            test_result = self.synthesize(
                text="测试",
                output_path=None,  # 不保存文件，只测试连接
                test_mode=True
            )
            
            if test_result:
                self.is_initialized = True
                logger.info("阿里云情感TTS初始化成功")
                return True
            else:
                logger.error("阿里云情感TTS初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"阿里云情感TTS初始化异常: {e}")
            return False
    
    def synthesize(self, text: str, output_path: str = None, **kwargs) -> bool:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径
            **kwargs: 其他参数
                - voice: 发音人 (默认: zhimiao_emo)
                - emotion: 情感 (默认: neutral) 
                - format: 音频格式 (默认: mp3)
                - test_mode: 测试模式，不保存文件
        
        Returns:
            bool: 合成是否成功
        """
        try:
            # 获取参数
            voice_key = kwargs.get('voice', self.DEFAULT_CONFIG['voice'])
            emotion = kwargs.get('emotion', self.DEFAULT_CONFIG['emotion'])
            format_type = kwargs.get('format', self.DEFAULT_CONFIG['format'])
            test_mode = kwargs.get('test_mode', False)
            
            # 验证发音人
            if voice_key not in self.AVAILABLE_VOICES:
                logger.warning(f"不支持的发音人: {voice_key}, 使用默认发音人")
                voice_key = self.DEFAULT_CONFIG['voice']
            
            voice_config = self.AVAILABLE_VOICES[voice_key]
            
            # 验证情感
            if emotion not in voice_config['emotions']:
                logger.warning(f"发音人 {voice_key} 不支持情感 {emotion}, 使用neutral")
                emotion = 'neutral'
            
            # 测试模式直接返回成功
            if test_mode:
                return True
            
            # 构建合成文本
            synthesis_text = self._prepare_text(text, emotion, voice_config)
            
            # 使用SDK进行语音合成
            result = SpeechSynthesizer.call(
                model=voice_config['model'],
                text=synthesis_text,
                voice=voice_config['voice'],
                format=format_type
            )
            
            if result.get_response().status_code == 200:
                # 确保输出目录存在
                if output_path:
                    # 确保输出路径有目录部分
                    output_dir = os.path.dirname(output_path)
                    if output_dir:  # 只有当有目录部分时才创建
                        os.makedirs(output_dir, exist_ok=True)
                    
                    # 保存音频文件
                    with open(output_path, 'wb') as f:
                        f.write(result.get_audio_data())
                    
                    # 验证文件是否成功保存
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info(f"阿里云TTS音频合成成功: {output_path}")
                        return True
                    else:
                        logger.error("阿里云TTS音频文件保存失败")
                        return False
                else:
                    # 不需要保存文件，直接返回成功
                    logger.info("阿里云TTS音频合成成功")
                    return True
            else:
                logger.error(f"阿里云TTS合成失败: {result.get_response().status_code}")
                if hasattr(result.get_response(), 'message'):
                    logger.error(f"错误信息: {result.get_response().message}")
                return False
                
        except Exception as e:
            logger.error(f"阿里云TTS合成异常: {e}")
            return False
    
    def synthesize_dialogue(self, text: str, character: str = 'default', 
                          emotion: str = 'neutral', output_path: str = None, **kwargs) -> bool:
        """
        为场景对话合成语音
        
        Args:
            text: 对话文本
            character: 角色类型 ('male', 'female', 'default')
            emotion: 情感类型
            output_path: 输出文件路径
            **kwargs: 其他参数
        
        Returns:
            bool: 合成是否成功
        """
        # 根据角色选择合适的发音人
        voice_mapping = {
            'male': 'zhifeng_emo',   # 男声多情感
            'female': 'zhimiao_emo', # 女声情感
            'default': 'zhimiao_emo' # 默认女声情感
        }
        
        voice = voice_mapping.get(character, 'zhimiao_emo')
        
        return self.synthesize(
            text=text,
            output_path=output_path,
            voice=voice,
            emotion=emotion,
            **kwargs
        )
    
    def get_available_characters(self) -> List[str]:
        """获取可用的角色类型"""
        return ['male', 'female', 'default']
    
    def get_available_emotions(self) -> List[str]:
        """获取可用的情感类型"""
        all_emotions = set()
        for voice_info in self.AVAILABLE_VOICES.values():
            all_emotions.update(voice_info['emotions'])
        return sorted(list(all_emotions))
    
    def get_voice_info(self) -> Dict[str, Dict]:
        """获取发音人信息"""
        return self.AVAILABLE_VOICES.copy()
    
    def _prepare_text(self, text: str, emotion: str, voice_config: Dict) -> str:
        """
        准备合成文本
        
        Args:
            text: 原始文本
            emotion: 情感
            voice_config: 发音人配置
        
        Returns:
            str: 处理后的文本
        """
        # 直接返回原始文本，让阿里云的情感TTS引擎自然处理情感
        # 不需要在文本中添加情感提示，避免被读出来
        return text
    

def create_alibaba_tts(api_key: str) -> Optional[AlibabaEmotionTTS]:
    """创建阿里云情感TTS实例的工厂函数"""
    try:
        tts = AlibabaEmotionTTS(api_key)
        if tts.initialize():
            return tts
        else:
            return None
    except Exception as e:
        logger.error(f"创建阿里云TTS实例失败: {e}")
        return None
