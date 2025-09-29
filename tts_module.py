# -*- coding: utf-8 -*-
"""
TTS模块 - 文本转语音功能
支持阿里云情感TTS、Edge TTS、离线TTS
优先级：阿里云TTS > Edge TTS > 离线TTS
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from config import Config

logger = logging.getLogger(__name__)

# 导入TTS引擎
try:
    from tts_engines.alibaba_emotion_tts import AlibabaEmotionTTS, create_alibaba_tts
    ALIBABA_TTS_AVAILABLE = True
except ImportError:
    ALIBABA_TTS_AVAILABLE = False
    print("⚠️ 阿里云情感TTS不可用，请安装相关依赖")

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("⚠️ Edge TTS不可用，请安装: pip install edge-tts")

class TTSBase(ABC):
    """TTS基类"""
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """
        合成语音
        :param text: 要合成的文本
        :param output_path: 输出音频文件路径
        :param kwargs: 其他参数
        :return: 是否成功
        """
        pass

class EdgeTTS(TTSBase):
    """Edge TTS免费服务"""
    
    def __init__(self):
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("Edge TTS 不可用，请安装: pip install edge-tts")
        
        self.voice = getattr(Config, 'EDGE_TTS_VOICE', 'zh-CN-XiaoxiaoNeural')
        self.rate = getattr(Config, 'EDGE_TTS_RATE', '+0%')
        self.volume = getattr(Config, 'EDGE_TTS_VOLUME', '+0%')
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """使用Edge TTS合成语音"""
        try:
            # 获取可选参数
            voice = kwargs.get('voice', self.voice)
            rate = kwargs.get('rate', self.rate)
            volume = kwargs.get('volume', self.volume)
            
            # 临时文件路径（MP3格式）
            temp_mp3_path = output_path.replace('.wav', '_temp.mp3')
            
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
                await communicate.save(temp_mp3_path)
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_synthesize())
            loop.close()
            
            # 验证临时文件
            if not os.path.exists(temp_mp3_path) or os.path.getsize(temp_mp3_path) == 0:
                logger.error("Edge TTS生成临时文件失败")
                return False
            
            # 转换MP3到WAV格式
            try:
                import subprocess
                # 使用ffmpeg转换格式
                result = subprocess.run([
                    'ffmpeg', '-i', temp_mp3_path, 
                    '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                    '-y', output_path
                ], capture_output=True, text=True)
                
                # 清理临时文件
                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)
                
                if result.returncode == 0:
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info(f"Edge TTS合成成功: {output_path}")
                        return True
                    else:
                        logger.error("Edge TTS格式转换后文件为空")
                        return False
                else:
                    logger.error(f"Edge TTS格式转换失败: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                # 如果没有ffmpeg，尝试使用pydub
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(temp_mp3_path)
                    audio.export(output_path, format="wav")
                    
                    # 清理临时文件
                    if os.path.exists(temp_mp3_path):
                        os.remove(temp_mp3_path)
                    
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info(f"Edge TTS合成成功: {output_path}")
                        return True
                    else:
                        logger.error("Edge TTS格式转换后文件为空")
                        return False
                        
                except ImportError:
                    logger.error("Edge TTS格式转换失败：需要ffmpeg或pydub")
                    # 清理临时文件
                    if os.path.exists(temp_mp3_path):
                        os.remove(temp_mp3_path)
                    return False
                
        except Exception as e:
            logger.error(f"Edge TTS合成失败: {e}")
            return False

class OfflineTTS(TTSBase):
    """离线TTS服务"""
    
    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 200)  # 语速
            self.engine.setProperty('volume', 0.8)  # 音量
        except ImportError:
            raise ImportError("离线TTS不可用，请安装: pip install pyttsx3")
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """使用离线TTS合成语音"""
        try:
            # 设置输出文件
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            # 验证文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"离线TTS合成成功: {output_path}")
                return True
            else:
                logger.error("离线TTS合成失败：文件未生成或为空")
                return False
                
        except Exception as e:
            logger.error(f"离线TTS合成失败: {e}")
            return False

class TTSManager:
    """TTS管理器，优先使用阿里云情感TTS"""
    
    def __init__(self):
        self.tts_engines = []
        self.emotion_engine = None  # 专门的情感TTS引擎
        self.voice_profiles = {}
        self._init_engines()
        self._init_voice_profiles()
    
    def _init_engines(self):
        """初始化可用的TTS引擎 - 优先级：阿里云 > Edge > 离线"""
        
        # 1. 尝试初始化阿里云情感TTS (最高优先级)
        if ALIBABA_TTS_AVAILABLE and hasattr(Config, 'ALIBABA_TTS_CONFIG'):
            alibaba_config = getattr(Config, 'ALIBABA_TTS_CONFIG', {})
            if alibaba_config.get('enabled', False):
                try:
                    api_key = alibaba_config.get('api_key', '')
                    if api_key:
                        alibaba_tts = create_alibaba_tts(api_key)
                        if alibaba_tts:
                            self.emotion_engine = alibaba_tts
                            self.tts_engines.append(("阿里云情感TTS", alibaba_tts))
                            print("✓ 阿里云情感TTS 初始化成功")
                        else:
                            print("✗ 阿里云情感TTS 初始化失败")
                    else:
                        print("✗ 阿里云TTS API密钥未配置")
                except Exception as e:
                    print(f"✗ 阿里云情感TTS 初始化失败: {e}")
        
        # 2. 尝试初始化Edge TTS (备用)
        if EDGE_TTS_AVAILABLE:
            edge_config = getattr(Config, 'EDGE_TTS_CONFIG', {})
            if edge_config.get('enabled', True):
                try:
                    edge_tts = EdgeTTS()
                    self.tts_engines.append(("Edge TTS", edge_tts))
                    print("✓ Edge TTS 初始化成功")
                except Exception as e:
                    print(f"✗ Edge TTS 初始化失败: {e}")
        
        # 3. 尝试初始化离线TTS (最后备用)
        try:
            offline_tts = OfflineTTS()
            self.tts_engines.append(("离线TTS", offline_tts))
            print("✓ 离线TTS 初始化成功")
        except Exception as e:
            print(f"✗ 离线TTS 初始化失败: {e}")
        
        if not self.tts_engines:
            raise RuntimeError("没有可用的TTS引擎，请检查依赖包安装和配置")
        
        print(f"共初始化了 {len(self.tts_engines)} 个TTS引擎")
    
    def _init_voice_profiles(self):
        """初始化不同角色的语音配置"""
        self.voice_profiles = {
            'standard': {
                'description': '标准发音',
                'emotion': 'neutral',
                'voice': 'zhimiao_emo'
            },
            'gentle': {
                'description': '温柔女声',
                'emotion': 'gentle',
                'voice': 'zhimiao_emo'
            },
            'energetic': {
                'description': '活力女声',
                'emotion': 'happy',
                'voice': 'zhimiao_emo'
            },
            'serious': {
                'description': '严肃男声',
                'emotion': 'serious',
                'voice': 'zhifeng_emo'
            }
        }
    
    def generate_standard_audio(self, text: str, output_path: str, voice_gender: str = 'female', voice_emotion: str = 'neutral', **kwargs) -> bool:
        """
        生成标准发音音频
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            voice_gender: 声音性别 ('female', 'male')
            voice_emotion: 情感类型 ('neutral', 'happy', 'sad', etc.)
            **kwargs: 其他参数
                - quality: 音质要求 ('high', 'medium', 'low')
        
        Returns:
            bool: 生成是否成功
        """
        print(f"🎤 开始生成标准发音音频: {text} (性别: {voice_gender}, 情感: {voice_emotion})")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:  # 只有当有目录部分时才创建
            os.makedirs(output_dir, exist_ok=True)
        
        # 优先使用情感TTS
        if self.emotion_engine:
            try:
                # 根据性别和情感选择声音
                emotion = voice_emotion or kwargs.get('emotion', 'neutral')
                
                if voice_gender == 'male':
                    if emotion == 'neutral':
                        voice = 'zhishuo'  # 男声标准（知硕）- 仅支持中性
                        print(f"🎵 使用阿里云男声TTS: voice={voice}, emotion={emotion}")
                    else:
                        # 男声不支持情感，回退到女声情感模型
                        voice = 'zhimiao_emo'
                        print(f"⚠️ 男声暂不支持 {emotion} 情感，使用女声情感模型: voice={voice}, emotion={emotion}")
                else:
                    voice = 'zhimiao_emo'  # 女声（默认，支持情感）
                    print(f"🎵 使用阿里云女声情感TTS: voice={voice}, emotion={emotion}")
                
                success = self.emotion_engine.synthesize(
                    text=text,
                    output_path=output_path,
                    emotion=emotion,
                    voice=voice,
                    **kwargs
                )
                
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"✓ 使用阿里云情感TTS成功生成音频")
                    return True
            except Exception as e:
                print(f"✗ 阿里云情感TTS生成失败: {e}")
        
        # 回退到其他TTS引擎
        for engine_name, engine in self.tts_engines:
            try:
                if engine == self.emotion_engine:
                    continue  # 跳过已经尝试的情感引擎
                
                success = engine.synthesize(text, output_path, **kwargs)
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"✓ 使用 {engine_name} 成功生成音频")
                    return True
                    
            except Exception as e:
                print(f"✗ {engine_name} 生成失败: {e}")
                continue
        
        print("✗ 所有TTS引擎都无法生成音频")
        return False
    
    def generate_emotion_audio(self, text: str, emotion: str, output_path: str, **kwargs) -> bool:
        """
        生成带情感的音频
        
        Args:
            text: 要合成的文本
            emotion: 情感类型
            output_path: 输出文件路径
            **kwargs: 其他参数
        
        Returns:
            bool: 生成是否成功
        """
        if self.emotion_engine:
            return self.emotion_engine.synthesize(
                text=text,
                output_path=output_path,
                emotion=emotion,
                **kwargs
            )
        else:
            # 回退到标准生成
            print("⚠️ 情感TTS不可用，使用标准TTS")
            return self.generate_standard_audio(text, output_path, **kwargs)
    
    def generate_dialogue_audio(self, text: str, output_path: str, 
                               role_type: str = 'standard', emotion: str = 'neutral', **kwargs) -> bool:
        """
        生成对话音频
        
        Args:
            text: 对话文本
            output_path: 输出文件路径
            role_type: 角色类型
            emotion: 情感
            **kwargs: 其他参数
        
        Returns:
            bool: 生成是否成功
        """
        print(f"🎭 生成角色对话音频: {role_type} ({emotion})")
        
        # 获取角色配置
        role_config = self.voice_profiles.get(role_type, self.voice_profiles['standard'])
        
        # 合并配置
        synthesis_params = {
            'emotion': emotion,
            'voice': role_config.get('voice', 'zhimiao_emo'),
            **kwargs
        }
        
        return self.generate_standard_audio(text, output_path, **synthesis_params)
    
    def generate_ai_character_audio(self, text: str, output_path: str, 
                                   character_type: str = 'default', emotion: str = 'neutral', 
                                   scenario_context: str = '', **kwargs) -> bool:
        """
        专门为AI角色生成带情感的对话音频
        
        Args:
            text: AI角色台词文本
            output_path: 输出文件路径
            character_type: AI角色类型 ('adult_male', 'adult_female', 'child', 'elder', etc.)
            emotion: 情感类型 ('neutral', 'happy', 'sad', 'angry', 'gentle', 'serious')
            scenario_context: 场景上下文信息
            **kwargs: 其他参数
        
        Returns:
            bool: 生成是否成功
        """
        print(f"🎭 生成AI角色音频: 角色={character_type}, 情感={emotion}, 文本='{text[:50]}...'")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 优先使用阿里云情感TTS
        if self.emotion_engine:
            try:
                # 根据角色类型映射到具体的发音人
                voice_mapping = {
                    'adult_male': 'zhibing_emo',    # 多情感男声
                    'adult_female': 'zhimiao_emo',  # 多情感女声
                    'young_male': 'zhibing_emo',    # 年轻男性
                    'young_female': 'zhimiao_emo',  # 年轻女性
                    'child': 'zhimiao_emo',         # 儿童（用女声模拟）
                    'elder_male': 'zhishuo',        # 年长男性（标准男声）
                    'elder_female': 'zhichu',       # 年长女性（标准女声）
                    'default': 'zhimiao_emo'        # 默认多情感女声
                }
                
                voice = voice_mapping.get(character_type, 'zhimiao_emo')
                
                # 根据场景上下文调整情感强度
                adjusted_emotion = self._adjust_emotion_for_context(emotion, scenario_context)
                
                print(f"🎵 使用阿里云情感TTS: voice={voice}, emotion={adjusted_emotion}")
                
                success = self.emotion_engine.synthesize(
                    text=text,
                    output_path=output_path,
                    voice=voice,
                    emotion=adjusted_emotion,
                    **kwargs
                )
                
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"✓ AI角色音频生成成功: {output_path}")
                    return True
                else:
                    print(f"✗ 阿里云情感TTS生成失败，尝试备用方案")
                    
            except Exception as e:
                print(f"✗ 阿里云情感TTS生成AI角色音频失败: {e}")
        
        # 回退到标准TTS
        print("🔄 使用标准TTS作为备用方案")
        return self.generate_standard_audio(
            text=text,
            output_path=output_path,
            voice_gender='female' if 'female' in character_type else 'male',
            voice_emotion=emotion,
            **kwargs
        )
    
    def _adjust_emotion_for_context(self, emotion: str, context: str) -> str:
        """
        根据场景上下文调整情感表达
        
        Args:
            emotion: 原始情感
            context: 场景上下文
        
        Returns:
            str: 调整后的情感
        """
        # 简单的上下文情感调整逻辑
        context_lower = context.lower()
        
        # 商务场景 - 更加正式
        if any(word in context_lower for word in ['商务', '工作', '会议', '面试', '办公']):
            if emotion == 'happy':
                return 'gentle'  # 商务场景的开心更温和
            elif emotion in ['angry', 'sad']:
                return 'serious'  # 商务场景不适合强烈情感
        
        # 家庭场景 - 更加亲切
        elif any(word in context_lower for word in ['家庭', '亲子', '家人', '孩子']):
            if emotion == 'neutral':
                return 'gentle'  # 家庭场景更温柔
        
        # 学习场景 - 更加耐心
        elif any(word in context_lower for word in ['学习', '教学', '课堂', '老师', '学生']):
            if emotion == 'neutral':
                return 'gentle'
            elif emotion == 'happy':
                return 'gentle'  # 教学场景的开心应该是鼓励性的
        
        return emotion  # 默认返回原情感
    
    def get_available_emotions(self) -> List[str]:
        """获取可用的情感类型"""
        if self.emotion_engine:
            return self.emotion_engine.get_available_emotions()
        else:
            return ['neutral']  # 默认只有中性
    
    def get_available_voices(self) -> Dict[str, Dict]:
        """获取可用的发音人"""
        if self.emotion_engine:
            return self.emotion_engine.get_voice_info()
        else:
            return {}
    
    def get_available_voice_profiles(self) -> Dict[str, Dict]:
        """获取可用的语音配置文件"""
        return self.voice_profiles.copy()
    
    def get_available_engines(self) -> List[str]:
        """获取可用的TTS引擎列表"""
        return [name for name, _ in self.tts_engines]
    
    def is_emotion_supported(self) -> bool:
        """检查是否支持情感TTS"""
        return self.emotion_engine is not None

# 全局TTS管理器实例
_tts_manager = None

def get_tts_manager() -> TTSManager:
    """获取TTS管理器实例（单例模式）"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager

# 使用示例
if __name__ == '__main__':
    # 测试TTS管理器
    tts_manager = get_tts_manager()
    
    # 测试标准音频生成
    success = tts_manager.generate_standard_audio(
        text="你好，这是测试音频。",
        output_path="test_output.mp3"
    )
    print(f"标准音频生成: {'成功' if success else '失败'}")
    
    # 测试情感音频生成
    if tts_manager.is_emotion_supported():
        success = tts_manager.generate_emotion_audio(
            text="我今天很开心！",
            emotion="happy",
            output_path="test_emotion.mp3"
        )
        print(f"情感音频生成: {'成功' if success else '失败'}")
    
    # 显示可用功能
    print(f"可用引擎: {tts_manager.get_available_engines()}")
    print(f"可用情感: {tts_manager.get_available_emotions()}")