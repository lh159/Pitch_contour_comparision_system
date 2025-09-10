# -*- coding: utf-8 -*-
"""
TTS模块 - 文本转语音功能
支持多种TTS服务：百度TTS、腾讯云TTS、Azure TTS、Edge TTS、离线TTS
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

class TencentTTS(TTSBase):
    """腾讯云TTS"""
    
    def __init__(self):
        self.secret_id = Config.TENCENT_SECRET_ID
        self.secret_key = Config.TENCENT_SECRET_KEY
        self.voice_type = Config.TENCENT_VOICE_TYPE
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯云TTS密钥未配置，请在.env文件中设置TENCENT_SECRET_ID和TENCENT_SECRET_KEY")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """使用腾讯云TTS合成语音"""
        try:
            from tts_engines.tencent_tts import TencentTTS as TencentTTSEngine
            
            engine = TencentTTSEngine(self.secret_id, self.secret_key)
            result = engine.synthesize(text, output_path, VoiceType=self.voice_type)
            
            if result:
                print(f"腾讯云TTS成功合成: {text} -> {output_path}")
                return True
            else:
                print(f"腾讯云TTS合成失败")
                return False
                
        except ImportError as e:
            print(f"腾讯云TTS引擎导入失败: {e}")
            return False
        except Exception as e:
            print(f"腾讯云TTS合成失败: {e}")
            return False

class AzureTTS(TTSBase):
    """Azure认知服务TTS"""
    
    def __init__(self):
        self.speech_key = Config.AZURE_SPEECH_KEY
        self.region = Config.AZURE_SPEECH_REGION
        self.voice_name = Config.AZURE_VOICE_NAME
        
        if not self.speech_key:
            raise ValueError("Azure Speech Key未配置，请在.env文件中设置AZURE_SPEECH_KEY")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """使用Azure TTS合成语音"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # 配置语音服务
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.region
            )
            speech_config.speech_synthesis_voice_name = self.voice_name
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
            )
            
            # 配置音频输出
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            
            # 创建合成器
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # 合成语音
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"Azure TTS成功合成: {text} -> {output_path}")
                return True
            else:
                print(f"Azure TTS合成失败: {result.reason}")
                return False
                
        except ImportError:
            print("Azure TTS SDK未安装，请安装: pip install azure-cognitiveservices-speech")
            return False
        except Exception as e:
            print(f"Azure TTS合成失败: {e}")
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
        self._init_engines()
    
    def _init_engines(self):
        """初始化可用的TTS引擎"""
        
        # 尝试初始化百度TTS (优先级最高，免费额度大)
        try:
            baidu_tts = BaiduTTS()
            self.tts_engines.append(("百度TTS", baidu_tts))
            print("✓ 百度TTS 初始化成功")
        except Exception as e:
            print(f"✗ 百度TTS 初始化失败: {e}")
        
        # 尝试初始化腾讯云TTS
        try:
            tencent_tts = TencentTTS()
            self.tts_engines.append(("腾讯云TTS", tencent_tts))
            print("✓ 腾讯云TTS 初始化成功")
        except Exception as e:
            print(f"✗ 腾讯云TTS 初始化失败: {e}")
        
        # 尝试初始化Azure TTS
        try:
            azure_tts = AzureTTS()
            self.tts_engines.append(("Azure TTS", azure_tts))
            print("✓ Azure TTS 初始化成功")
        except Exception as e:
            print(f"✗ Azure TTS 初始化失败: {e}")
        
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
