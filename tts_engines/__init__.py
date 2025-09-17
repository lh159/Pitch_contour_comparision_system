# -*- coding: utf-8 -*-
"""
TTS引擎模块
支持多种TTS引擎的统一管理
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import os

class TTSEngineBase(ABC):
    """TTS引擎基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False
        self.supported_features = {
            'emotion_control': False,
            'voice_cloning': False,
            'speed_control': False,
            'volume_control': False,
            'multilingual': False
        }
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化引擎"""
        pass
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径
            **kwargs: 其他参数
        
        Returns:
            bool: 合成是否成功
        """
        pass
    
    def get_supported_features(self) -> Dict[str, bool]:
        """获取支持的功能特性"""
        return self.supported_features.copy()
    
    def is_feature_supported(self, feature: str) -> bool:
        """检查是否支持特定功能"""
        return self.supported_features.get(feature, False)
    
    def cleanup(self):
        """清理资源"""
        pass

class DialogueTTSEngine(ABC):
    """场景对话TTS引擎接口"""
    
    @abstractmethod
    def synthesize_dialogue(self, text: str, character: str = 'default', 
                          emotion: str = 'calm', output_path: str = None, **kwargs) -> bool:
        """
        为场景对话合成语音
        
        Args:
            text: 对话文本
            character: 角色类型
            emotion: 情感类型
            output_path: 输出文件路径
            **kwargs: 其他参数
        
        Returns:
            bool: 合成是否成功
        """
        pass
    
    @abstractmethod
    def get_available_characters(self) -> List[str]:
        """获取可用的角色类型"""
        pass
    
    @abstractmethod
    def get_available_emotions(self) -> List[str]:
        """获取可用的情感类型"""
        pass

class VoiceCloningEngine(ABC):
    """语音克隆引擎接口"""
    
    @abstractmethod
    def clone_voice(self, text: str, reference_audio: str, 
                   output_path: str, **kwargs) -> bool:
        """
        语音克隆
        
        Args:
            text: 要合成的文本
            reference_audio: 参考音频文件路径
            output_path: 输出文件路径
            **kwargs: 其他参数
        
        Returns:
            bool: 克隆是否成功
        """
        pass
