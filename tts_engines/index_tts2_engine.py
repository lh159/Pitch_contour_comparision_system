# -*- coding: utf-8 -*-
"""
IndexTTS2引擎封装
"""

import os
import sys
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple
from . import TTSEngineBase, DialogueTTSEngine, VoiceCloningEngine

class IndexTTS2Engine(TTSEngineBase, DialogueTTSEngine, VoiceCloningEngine):
    """IndexTTS2引擎"""
    
    def __init__(self, model_dir: str = "third_party/index-tts/checkpoints", 
                 use_fp16: bool = True, use_cuda_kernel: bool = True):
        super().__init__("IndexTTS2")
        self.model_dir = model_dir
        self.use_fp16 = use_fp16
        self.use_cuda_kernel = use_cuda_kernel
        self.tts = None
        
        # 支持的功能特性
        self.supported_features = {
            'emotion_control': True,
            'voice_cloning': True,
            'speed_control': False,  # 当前版本未启用
            'volume_control': False,
            'multilingual': True
        }
        
        # 预定义角色语音配置
        self.voice_profiles = {
            'child': {
                'voice_sample': 'examples/voice_01.wav',
                'description': '儿童角色',
                'emotions': {
                    'happy': [0.8, 0, 0, 0, 0, 0, 0.3, 0.2],
                    'surprised': [0.2, 0, 0, 0, 0, 0, 0.9, 0.1],
                    'calm': [0, 0, 0, 0, 0, 0, 0, 1.0]
                }
            },
            'adult_female': {
                'voice_sample': 'examples/voice_07.wav',
                'description': '成年女性',
                'emotions': {
                    'calm': [0, 0, 0, 0, 0, 0, 0, 1.0],
                    'happy': [0.7, 0, 0, 0, 0, 0, 0.2, 0.3],
                    'sad': [0, 0, 0.8, 0, 0, 0.3, 0, 0.1]
                }
            },
            'adult_male': {
                'voice_sample': 'examples/voice_10.wav',
                'description': '成年男性',
                'emotions': {
                    'calm': [0, 0, 0, 0, 0, 0, 0, 1.0],
                    'angry': [0, 0.8, 0, 0, 0, 0, 0, 0.2],
                    'surprised': [0.3, 0, 0, 0, 0, 0, 0.7, 0.2]
                }
            },
            'elderly': {
                'voice_sample': 'examples/voice_04.wav',
                'description': '老年角色',
                'emotions': {
                    'calm': [0, 0, 0, 0, 0, 0, 0, 1.0],
                    'gentle': [0, 0, 0, 0, 0, 0, 0.2, 0.8]
                }
            }
        }
        
        # 情感向量映射 [happy, angry, sad, fear, disgust, melancholy, surprised, calm]
        self.emotion_vectors = {
            'happy': [0.8, 0, 0, 0, 0, 0, 0.2, 0.3],
            'angry': [0, 0.9, 0, 0, 0, 0, 0.1, 0],
            'sad': [0, 0, 0.8, 0, 0, 0.3, 0, 0.1],
            'fear': [0, 0, 0, 0.8, 0, 0.2, 0.3, 0],
            'disgust': [0, 0, 0, 0, 0.8, 0, 0, 0.2],
            'melancholy': [0, 0, 0.3, 0, 0, 0.8, 0, 0.2],
            'surprised': [0.3, 0, 0, 0, 0, 0, 0.8, 0.1],
            'calm': [0, 0, 0, 0, 0, 0, 0, 1.0],
            'gentle': [0, 0, 0, 0, 0, 0, 0.2, 0.8]
        }
    
    def initialize(self) -> bool:
        """初始化IndexTTS2引擎"""
        try:
            # 检查Python版本兼容性
            python_version = sys.version_info
            if not (python_version.major == 3 and 8 <= python_version.minor <= 12):
                print(f"✗ {self.name} 不支持Python {python_version.major}.{python_version.minor}")
                print("IndexTTS2推荐Python 3.8-3.11版本")
                print("当前系统将使用其他TTS引擎")
                return False
            elif python_version.minor == 12:
                print(f"⚠ {self.name} 在Python 3.12上可能存在兼容性问题，但将尝试运行")
                print("如遇到问题，建议使用Python 3.8-3.11版本")
            
            # 添加IndexTTS2到Python路径
            index_tts_path = os.path.abspath("third_party/index-tts")
            if index_tts_path not in sys.path:
                sys.path.insert(0, index_tts_path)
            
            # 检查模型文件
            config_path = os.path.join(self.model_dir, "config.yaml")
            if not os.path.exists(config_path):
                print(f"✗ {self.name} 配置文件不存在: {config_path}")
                print("请先下载模型文件：")
                print("cd third_party/index-tts")
                print("pip install huggingface_hub")
                print("huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=checkpoints")
                return False
            
            # 检查关键模型文件是否存在
            required_files = ["gpt.pth", "s2mel.pth"]
            missing_files = []
            for file in required_files:
                if not os.path.exists(os.path.join(self.model_dir, file)):
                    missing_files.append(file)
            
            # 检查qwen模型文件
            qwen_model_dir = os.path.join(self.model_dir, "qwen0.6bemo4-merge")
            qwen_files = ["pytorch_model.bin", "model.safetensors"]
            qwen_exists = any(os.path.exists(os.path.join(qwen_model_dir, f)) for f in qwen_files)
            
            if missing_files or not qwen_exists:
                print(f"✗ {self.name} 缺少关键模型文件:")
                if missing_files:
                    print(f"  - 缺少: {missing_files}")
                if not qwen_exists:
                    print(f"  - qwen模型文件不完整")
                print("请先下载模型文件：")
                print("cd third_party/index-tts")
                print("pip install huggingface_hub")
                print("huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=checkpoints")
                return False
            
            # 导入IndexTTS2
            try:
                from indextts.infer_v2 import IndexTTS2
                
                self.tts = IndexTTS2(
                    cfg_path=config_path,
                    model_dir=self.model_dir,
                    use_fp16=self.use_fp16,
                    use_cuda_kernel=self.use_cuda_kernel,
                    use_deepspeed=False
                )
                
                self.is_initialized = True
                print(f"✓ {self.name} 初始化成功")
                return True
                
            except ImportError as e:
                print(f"✗ {self.name} 导入失败: {e}")
                print("请安装IndexTTS2依赖：")
                print("cd third_party/index-tts")
                print("pip install -e .")
                return False
            
        except Exception as e:
            print(f"✗ {self.name} 初始化失败: {e}")
            return False
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """标准语音合成"""
        character = kwargs.get('character', 'adult_female')
        emotion = kwargs.get('emotion', 'calm')
        return self.synthesize_dialogue(text, character, emotion, output_path, **kwargs)
    
    def synthesize_dialogue(self, text: str, character: str = 'adult_female', 
                          emotion: str = 'calm', output_path: str = None, **kwargs) -> bool:
        """为场景对话合成语音"""
        if not self.is_initialized or not self.tts:
            print(f"{self.name} 未初始化")
            return False
        
        try:
            # 检查角色配置
            if character not in self.voice_profiles:
                print(f"不支持的角色类型: {character}，使用默认角色")
                character = 'adult_female'
            
            profile = self.voice_profiles[character]
            voice_sample_path = os.path.join("third_party/index-tts", profile['voice_sample'])
            
            # 检查语音样本文件
            if not os.path.exists(voice_sample_path):
                print(f"语音样本文件不存在: {voice_sample_path}")
                return False
            
            # 生成输出路径
            if output_path is None:
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                output_path = f"cache/indextts2/dialogue_{character}_{emotion}_{text_hash}.wav"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 获取情感参数
            emo_alpha = kwargs.get('emo_alpha', 0.8)
            
            if emotion in profile.get('emotions', {}):
                # 使用预定义的情感向量
                emo_vector = profile['emotions'][emotion]
                
                self.tts.infer(
                    spk_audio_prompt=voice_sample_path,
                    text=text,
                    output_path=output_path,
                    emo_vector=emo_vector,
                    emo_alpha=emo_alpha,
                    use_random=False,
                    verbose=False
                )
            elif emotion in self.emotion_vectors:
                # 使用通用情感向量
                emo_vector = self.emotion_vectors[emotion]
                
                self.tts.infer(
                    spk_audio_prompt=voice_sample_path,
                    text=text,
                    output_path=output_path,
                    emo_vector=emo_vector,
                    emo_alpha=emo_alpha,
                    use_random=False,
                    verbose=False
                )
            else:
                # 使用文本情感分析
                self.tts.infer(
                    spk_audio_prompt=voice_sample_path,
                    text=text,
                    output_path=output_path,
                    emo_alpha=emo_alpha,
                    use_emo_text=True,
                    use_random=False,
                    verbose=False
                )
            
            # 检查输出文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✓ {self.name} 成功合成: {text} -> {output_path}")
                return True
            else:
                print(f"✗ {self.name} 合成失败：输出文件无效")
                return False
            
        except Exception as e:
            print(f"✗ {self.name} 合成失败: {e}")
            return False
    
    def clone_voice(self, text: str, reference_audio: str, 
                   output_path: str = None, emotion_audio: str = None, 
                   emo_alpha: float = 1.0, **kwargs) -> bool:
        """语音克隆功能"""
        if not self.is_initialized or not self.tts:
            print(f"{self.name} 未初始化")
            return False
        
        try:
            # 检查参考音频文件
            if not os.path.exists(reference_audio):
                print(f"参考音频文件不存在: {reference_audio}")
                return False
            
            # 生成输出路径
            if output_path is None:
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                ref_hash = hashlib.md5(reference_audio.encode()).hexdigest()[:8]
                output_path = f"cache/indextts2/cloned_{ref_hash}_{text_hash}.wav"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 执行语音克隆
            if emotion_audio and os.path.exists(emotion_audio):
                # 使用情感参考音频
                self.tts.infer(
                    spk_audio_prompt=reference_audio,
                    text=text,
                    output_path=output_path,
                    emo_audio_prompt=emotion_audio,
                    emo_alpha=emo_alpha,
                    verbose=False
                )
            else:
                # 仅使用语音克隆
                self.tts.infer(
                    spk_audio_prompt=reference_audio,
                    text=text,
                    output_path=output_path,
                    verbose=False
                )
            
            # 检查输出文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✓ {self.name} 语音克隆成功: {text} -> {output_path}")
                return True
            else:
                print(f"✗ {self.name} 语音克隆失败：输出文件无效")
                return False
            
        except Exception as e:
            print(f"✗ {self.name} 语音克隆失败: {e}")
            return False
    
    def get_available_characters(self) -> List[str]:
        """获取可用的角色类型"""
        return list(self.voice_profiles.keys())
    
    def get_available_emotions(self) -> List[str]:
        """获取可用的情感类型"""
        return list(self.emotion_vectors.keys())
    
    def get_voice_sample_path(self, character: str) -> Optional[str]:
        """获取角色语音样本路径"""
        if character in self.voice_profiles:
            return os.path.join("third_party/index-tts", 
                              self.voice_profiles[character]['voice_sample'])
        return None
    
    def add_custom_character(self, name: str, voice_sample: str, 
                           emotions: Dict[str, List[float]] = None):
        """添加自定义角色"""
        self.voice_profiles[name] = {
            'voice_sample': voice_sample,
            'description': f'自定义角色: {name}',
            'emotions': emotions or {'calm': [0, 0, 0, 0, 0, 0, 0, 1.0]}
        }
    
    def cleanup(self):
        """清理资源"""
        if self.tts:
            # IndexTTS2可能需要特定的清理操作
            try:
                # 这里可以添加模型清理代码
                pass
            except:
                pass
            self.tts = None
        
        self.is_initialized = False
