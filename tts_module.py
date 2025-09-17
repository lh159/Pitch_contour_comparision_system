# -*- coding: utf-8 -*-
"""
TTS模块 - 文本转语音功能
支持多种TTS服务：百度TTS、Edge TTS、离线TTS
"""
import os
import io
import wave
from abc import ABC, abstractmethod
from config import Config

class TTSBase(ABC):
    """TTS基类"""
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        合成语音
        :param text: 要合成的文本
        :param output_path: 输出音频文件路径
        :return: 是否成功
        """
        pass

class BaiduTTS(TTSBase):
    """百度智能云TTS"""
    
    def __init__(self):
        self.api_key = Config.BAIDU_API_KEY
        self.secret_key = Config.BAIDU_SECRET_KEY
        self.voice_per = Config.BAIDU_VOICE_PER
        
        if not self.api_key or not self.secret_key:
            raise ValueError("百度TTS密钥未配置，请在.env文件中设置BAIDU_API_KEY和BAIDU_SECRET_KEY")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """使用百度TTS合成语音"""
        try:
            from tts_engines.baidu_tts import BaiduTTS as BaiduTTSEngine
            
            engine = BaiduTTSEngine(self.api_key, self.secret_key)
            result = engine.synthesize(text, output_path, per=self.voice_per)
            
            if result:
                print(f"百度TTS成功合成: {text} -> {output_path}")
                return True
            else:
                print(f"百度TTS合成失败")
                return False
                
        except ImportError as e:
            print(f"百度TTS引擎导入失败: {e}")
            return False
        except Exception as e:
            print(f"百度TTS合成失败: {e}")
            return False


class EdgeTTS(TTSBase):
    """Edge TTS (免费替代方案)"""
    
    def __init__(self):
        self.voice = "zh-CN-XiaoxiaoNeural"
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """使用Edge TTS合成语音"""
        try:
            import edge_tts
            import asyncio
            
            async def _synthesize():
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(output_path)
            
            # 运行异步合成
            asyncio.run(_synthesize())
            print(f"Edge TTS成功合成: {text} -> {output_path}")
            return True
            
        except ImportError:
            print("Edge TTS未安装，请安装: pip install edge-tts")
            return False
        except Exception as e:
            print(f"Edge TTS合成失败: {e}")
            return False

class OfflineTTS(TTSBase):
    """离线TTS (pyttsx3)"""
    
    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            
            # 设置中文语音
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            # 设置语速和音量
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
            
        except ImportError:
            raise ImportError("离线TTS未安装，请安装: pip install pyttsx3")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """使用离线TTS合成语音"""
        try:
            import pyttsx3
            
            # 保存到文件
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            print(f"离线TTS成功合成: {text} -> {output_path}")
            return True
            
        except Exception as e:
            print(f"离线TTS合成失败: {e}")
            return False

class TTSManager:
    """TTS管理器，支持多种TTS服务的自动切换"""
    
    def __init__(self):
        self.tts_engines = []
        self.voice_profiles = {}  # 新增：语音配置文件
        self._init_engines()
        self._init_voice_profiles()  # 新增：初始化语音配置
    
    def _init_engines(self):
        """初始化可用的TTS引擎"""
        
        # 尝试初始化百度TTS (优先级最高，免费额度大)
        try:
            baidu_tts = BaiduTTS()
            self.tts_engines.append(("百度TTS", baidu_tts))
            print("✓ 百度TTS 初始化成功")
        except Exception as e:
            print(f"✗ 百度TTS 初始化失败: {e}")
        
        # 尝试初始化Edge TTS
        try:
            edge_tts = EdgeTTS()
            self.tts_engines.append(("Edge TTS", edge_tts))
            print("✓ Edge TTS 初始化成功")
        except Exception as e:
            print(f"✗ Edge TTS 初始化失败: {e}")
        
        # 尝试初始化离线TTS
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
            # 标准发音（用户练习用）
            'standard': {
                'baidu_per': 4,  # 度丫丫，标准女声
                'description': '标准女声，用于用户练习'
            },
            
            # AI角色语音配置
            'child': {
                'baidu_per': 5,  # 度小娇，可爱童声
                'description': '儿童角色语音'
            },
            'adult_male': {
                'baidu_per': 1,  # 度小宇，标准男声
                'description': '成年男性角色语音'
            },
            'adult_female': {
                'baidu_per': 0,  # 度小美，标准女声
                'description': '成年女性角色语音'
            },
            'elderly': {
                'baidu_per': 4,  # 度丫丫，温和女声
                'description': '老年角色语音'
            },
            'professional': {
                'baidu_per': 3,  # 度小博，专业男声
                'description': '专业人士角色语音'
            }
        }
    
    def generate_standard_audio(self, text: str, output_path: str) -> bool:
        """
        生成标准发音音频
        :param text: 要合成的中文文本
        :param output_path: 输出音频文件路径
        :return: 是否成功
        """
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 依次尝试各个TTS引擎
        for engine_name, engine in self.tts_engines:
            print(f"尝试使用 {engine_name} 合成语音...")
            
            try:
                if engine.synthesize(text, output_path):
                    # 验证生成的音频文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ 使用 {engine_name} 成功生成标准发音: {text}")
                        return True
                    else:
                        print(f"✗ {engine_name} 生成的音频文件无效")
                        continue
            except Exception as e:
                print(f"✗ {engine_name} 合成失败: {e}")
                continue
        
        print("✗ 所有TTS引擎都无法生成音频")
        return False
    
    def generate_dialogue_audio(self, text: str, output_path: str, 
                               role_type: str = 'standard') -> bool:
        """
        为对话角色生成语音
        :param text: 要合成的文本
        :param output_path: 输出音频文件路径
        :param role_type: 角色类型，决定使用的语音
        :return: 是否成功
        """
        
        # 获取角色语音配置
        voice_config = self.voice_profiles.get(role_type, self.voice_profiles['standard'])
        target_per = voice_config['baidu_per']
        
        print(f"为角色 '{role_type}' 生成语音: {text}")
        print(f"使用语音配置: {voice_config['description']} (per={target_per})")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 依次尝试各个TTS引擎，优先使用百度TTS以保持一致性
        for engine_name, engine in self.tts_engines:
            try:
                # 如果是百度TTS，设置特定的语音
                if isinstance(engine, BaiduTTS):
                    # 临时修改语音配置
                    original_per = engine.voice_per
                    engine.voice_per = target_per
                    
                    success = engine.synthesize(text, output_path)
                    
                    # 恢复原始配置
                    engine.voice_per = original_per
                    
                    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ 使用百度TTS成功生成角色语音: {role_type}")
                        return True
                else:
                    # 其他TTS引擎使用默认配置
                    if engine.synthesize(text, output_path):
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            print(f"✓ 使用 {engine_name} 成功生成角色语音")
                            return True
                            
            except Exception as e:
                print(f"✗ {engine_name} 生成角色语音失败: {e}")
                continue
        
        print("✗ 所有TTS引擎都无法生成角色语音")
        return False
    
    def get_available_voice_profiles(self) -> dict:
        """获取可用的语音配置文件"""
        return self.voice_profiles.copy()
    
    def get_available_engines(self) -> list:
        """获取可用的TTS引擎列表"""
        return [name for name, _ in self.tts_engines]

# 使用示例
if __name__ == '__main__':
    # 创建必要目录
    Config.create_directories()
    
    # 测试TTS功能
    tts_manager = TTSManager()
    
    test_words = ["你好", "早上好", "欢迎光临"]
    
    print("\n=== 测试TTS功能 ===")
    for word in test_words:
        output_path = os.path.join(Config.TEMP_FOLDER, f"standard_{word}.wav")
        success = tts_manager.generate_standard_audio(word, output_path)
        
        if success:
            print(f"✓ 成功生成: {word} -> {output_path}")
        else:
            print(f"✗ 生成失败: {word}")
    
    print(f"\n可用的TTS引擎: {tts_manager.get_available_engines()}")
