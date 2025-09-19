# -*- coding: utf-8 -*-
"""
增强型TTS管理器
支持多种TTS引擎和场景对话功能
"""

import os
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from config import Config
from tts_engines import TTSEngineBase, DialogueTTSEngine, VoiceCloningEngine
# 百度TTS引擎已移除
# IndexTTS2引擎已移除
from character_voice_manager import CharacterVoiceManager
from dialogue_emotion_analyzer import DialogueEmotionAnalyzer

class EnhancedTTSManager:
    """增强型TTS管理器"""
    
    def __init__(self):
        self.engines: Dict[str, TTSEngineBase] = {}
        self.current_engine = 'alibaba'  # 默认引擎
        self.fallback_engine = 'edge'  # 备用引擎
        
        # 初始化管理器
        self.voice_manager = CharacterVoiceManager()
        self.emotion_analyzer = DialogueEmotionAnalyzer()
        
        # 缓存设置
        self.cache_enabled = True
        self.cache_dir = 'cache/tts'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'successful_syntheses': 0,
            'failed_syntheses': 0,
            'engine_usage': {}
        }
        
        self._init_engines()
    
    def _init_engines(self):
        """初始化所有TTS引擎"""
        print("正在初始化TTS引擎...")
        
        
        # 3. 检查可用引擎
        if not self.engines:
            raise RuntimeError("没有可用的TTS引擎，请检查配置和依赖")
        
        # 4. 设置备用引擎
        available_engines = list(self.engines.keys())
        if self.current_engine not in available_engines:
            self.current_engine = available_engines[0]
        
        if len(available_engines) > 1:
            self.fallback_engine = available_engines[1] if available_engines[0] == self.current_engine else available_engines[0]
        else:
            self.fallback_engine = self.current_engine
        
        print(f"✓ 共初始化了 {len(self.engines)} 个TTS引擎")
        print(f"当前引擎: {self.current_engine}")
        print(f"备用引擎: {self.fallback_engine}")
    
    def switch_engine(self, engine_name: str) -> bool:
        """切换TTS引擎"""
        if engine_name in self.engines:
            self.current_engine = engine_name
            print(f"✓ 切换到引擎: {engine_name}")
            return True
        else:
            print(f"✗ 引擎不存在: {engine_name}")
            return False
    
    def get_available_engines(self) -> List[str]:
        """获取可用的TTS引擎列表"""
        return list(self.engines.keys())
    
    def get_engine_features(self, engine_name: str = None) -> Dict[str, bool]:
        """获取引擎支持的功能特性"""
        engine_name = engine_name or self.current_engine
        if engine_name in self.engines:
            return self.engines[engine_name].get_supported_features()
        return {}
    
    def generate_standard_audio(self, text: str, output_path: str) -> bool:
        """生成标准发音音频（兼容原接口）"""
        return self.synthesize_text(text, output_path)
    
    def synthesize_text(self, text: str, output_path: str, 
                       engine: str = None, **kwargs) -> bool:
        """
        合成文本语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            engine: 指定引擎（可选）
            **kwargs: 其他参数
        
        Returns:
            bool: 合成是否成功
        """
        self.stats['total_requests'] += 1
        
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._generate_cache_key(text, engine or self.current_engine, kwargs)
            cached_path = self._get_cached_audio(cache_key)
            if cached_path:
                try:
                    import shutil
                    shutil.copy2(cached_path, output_path)
                    self.stats['cache_hits'] += 1
                    print(f"✓ 使用缓存音频: {text}")
                    return True
                except Exception as e:
                    print(f"缓存复制失败: {e}")
        
        # 选择引擎
        engine_name = engine or self.current_engine
        selected_engine = self.engines.get(engine_name)
        
        if not selected_engine:
            print(f"引擎不存在: {engine_name}")
            return False
        
        # 尝试合成
        success = False
        try:
            success = selected_engine.synthesize(text, output_path, **kwargs)
            if success:
                self.stats['successful_syntheses'] += 1
                self.stats['engine_usage'][engine_name] = self.stats['engine_usage'].get(engine_name, 0) + 1
                
                # 保存到缓存
                if self.cache_enabled:
                    self._cache_audio(cache_key, output_path)
            else:
                self.stats['failed_syntheses'] += 1
                
        except Exception as e:
            print(f"合成异常: {e}")
            self.stats['failed_syntheses'] += 1
        
        # 如果失败且有备用引擎，尝试备用引擎
        if not success and engine_name != self.fallback_engine and self.fallback_engine in self.engines:
            print(f"使用备用引擎重试: {self.fallback_engine}")
            try:
                fallback_engine = self.engines[self.fallback_engine]
                success = fallback_engine.synthesize(text, output_path, **kwargs)
                if success:
                    self.stats['successful_syntheses'] += 1
                    self.stats['engine_usage'][self.fallback_engine] = self.stats['engine_usage'].get(self.fallback_engine, 0) + 1
            except Exception as e:
                print(f"备用引擎合成异常: {e}")
        
        return success
    
    def synthesize_dialogue(self, text: str, character: str = None, 
                          emotion: str = None, auto_emotion: bool = True,
                          engine: str = None, **kwargs) -> Tuple[Optional[str], Dict]:
        """
        为场景对话合成语音
        
        Args:
            text: 对话文本
            character: 角色名称
            emotion: 指定情感
            auto_emotion: 是否自动分析情感
            engine: 指定引擎
            **kwargs: 其他参数
        
        Returns:
            Tuple[audio_path, synthesis_info]: 音频文件路径和合成信息
        """
        self.stats['total_requests'] += 1
        
        synthesis_info = {
            'character': character,
            'original_emotion': emotion,
            'final_emotion': emotion,
            'emotion_confidence': 0.0,
            'engine_used': engine or self.current_engine,
            'success': False,
            'cache_hit': False
        }
        
        # 1. 处理角色配置
        if character:
            profile = self.voice_manager.get_character_voice_config(character)
            if not profile:
                print(f"角色不存在，使用默认配置: {character}")
                character = None
        
        # 2. 情感分析
        if auto_emotion and not emotion:
            analyzed_emotion, confidence = self.emotion_analyzer.analyze_emotion(text)
            emotion = analyzed_emotion
            synthesis_info['final_emotion'] = emotion
            synthesis_info['emotion_confidence'] = confidence
            print(f"自动情感分析: {emotion} (置信度: {confidence:.2f})")
        elif not emotion:
            emotion = 'calm'  # 默认情感
            synthesis_info['final_emotion'] = emotion
        
        # 3. 生成输出路径
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        char_part = character or 'default'
        emo_part = emotion or 'calm'
        engine_part = engine or self.current_engine
        
        filename = f"dialogue_{char_part}_{emo_part}_{engine_part}_{text_hash}.wav"
        output_path = os.path.join(self.cache_dir, filename)
        
        # 4. 检查缓存
        if self.cache_enabled and os.path.exists(output_path):
            self.stats['cache_hits'] += 1
            synthesis_info['success'] = True
            synthesis_info['cache_hit'] = True
            print(f"✓ 使用缓存对话音频: {text}")
            return output_path, synthesis_info
        
        # 5. 选择引擎并合成
        engine_name = engine or self.current_engine
        selected_engine = self.engines.get(engine_name)
        
        if not selected_engine:
            print(f"引擎不存在: {engine_name}")
            return None, synthesis_info
        
        # 6. 尝试使用对话合成接口
        success = False
        if isinstance(selected_engine, DialogueTTSEngine):
            try:
                # 获取角色类型
                if character and profile:
                    char_config = self.voice_manager.get_character_config_for_engine(character, engine_name)
                    char_type = char_config.get('type', 'adult_female')
                else:
                    char_type = 'adult_female'
                
                success = selected_engine.synthesize_dialogue(
                    text=text,
                    character=char_type,
                    emotion=emotion,
                    output_path=output_path,
                    **kwargs
                )
                
            except Exception as e:
                print(f"对话合成异常: {e}")
        
        # 7. 如果对话合成失败，尝试标准合成
        if not success:
            try:
                success = selected_engine.synthesize(text, output_path, **kwargs)
            except Exception as e:
                print(f"标准合成异常: {e}")
        
        # 8. 备用引擎重试
        if not success and engine_name != self.fallback_engine and self.fallback_engine in self.engines:
            print(f"使用备用引擎重试: {self.fallback_engine}")
            fallback_engine = self.engines[self.fallback_engine]
            synthesis_info['engine_used'] = self.fallback_engine
            
            if isinstance(fallback_engine, DialogueTTSEngine):
                try:
                    if character and profile:
                        char_config = self.voice_manager.get_character_config_for_engine(character, self.fallback_engine)
                        char_type = char_config.get('type', 'adult_female')
                    else:
                        char_type = 'adult_female'
                    
                    success = fallback_engine.synthesize_dialogue(
                        text=text,
                        character=char_type,
                        emotion=emotion,
                        output_path=output_path,
                        **kwargs
                    )
                except Exception as e:
                    print(f"备用引擎对话合成异常: {e}")
            
            if not success:
                try:
                    success = fallback_engine.synthesize(text, output_path, **kwargs)
                except Exception as e:
                    print(f"备用引擎标准合成异常: {e}")
        
        # 9. 更新统计
        if success:
            self.stats['successful_syntheses'] += 1
            self.stats['engine_usage'][synthesis_info['engine_used']] = \
                self.stats['engine_usage'].get(synthesis_info['engine_used'], 0) + 1
        else:
            self.stats['failed_syntheses'] += 1
        
        synthesis_info['success'] = success
        
        if success:
            return output_path, synthesis_info
        else:
            return None, synthesis_info
    
    def clone_voice(self, text: str, reference_audio: str, 
                   output_path: str = None, engine: str = None, **kwargs) -> bool:
        """
        语音克隆
        
        Args:
            text: 要合成的文本
            reference_audio: 参考音频文件路径
            output_path: 输出文件路径
            engine: 指定引擎
            **kwargs: 其他参数
        
        Returns:
            bool: 克隆是否成功
        """
        # 选择支持语音克隆的引擎
        engine_name = engine or self.current_engine
        selected_engine = self.engines.get(engine_name)
        
        if not selected_engine:
            print(f"引擎不存在: {engine_name}")
            return False
        
        if not isinstance(selected_engine, VoiceCloningEngine):
            # 尝试其他支持语音克隆的引擎
            for name, eng in self.engines.items():
                if isinstance(eng, VoiceCloningEngine):
                    selected_engine = eng
                    engine_name = name
                    break
            else:
                print("没有支持语音克隆的引擎")
                return False
        
        # 生成输出路径
        if output_path is None:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            ref_hash = hashlib.md5(reference_audio.encode()).hexdigest()[:8]
            output_path = os.path.join(self.cache_dir, f"cloned_{ref_hash}_{text_hash}.wav")
        
        try:
            success = selected_engine.clone_voice(text, reference_audio, output_path, **kwargs)
            if success:
                self.stats['successful_syntheses'] += 1
                self.stats['engine_usage'][engine_name] = self.stats['engine_usage'].get(engine_name, 0) + 1
            else:
                self.stats['failed_syntheses'] += 1
            return success
        except Exception as e:
            print(f"语音克隆异常: {e}")
            self.stats['failed_syntheses'] += 1
            return False
    
    def _generate_cache_key(self, text: str, engine: str, params: Dict) -> str:
        """生成缓存键"""
        cache_data = f"{text}_{engine}_{str(sorted(params.items()))}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _get_cached_audio(self, cache_key: str) -> Optional[str]:
        """获取缓存音频"""
        cache_path = os.path.join(self.cache_dir, f"cache_{cache_key}.wav")
        if os.path.exists(cache_path):
            return cache_path
        return None
    
    def _cache_audio(self, cache_key: str, audio_path: str):
        """保存音频到缓存"""
        try:
            cache_path = os.path.join(self.cache_dir, f"cache_{cache_key}.wav")
            import shutil
            shutil.copy2(audio_path, cache_path)
        except Exception as e:
            print(f"缓存保存失败: {e}")
    
    def clear_cache(self) -> int:
        """清理缓存"""
        cleared_count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('cache_') and filename.endswith('.wav'):
                    os.remove(os.path.join(self.cache_dir, filename))
                    cleared_count += 1
            print(f"✓ 清理了 {cleared_count} 个缓存文件")
        except Exception as e:
            print(f"清理缓存失败: {e}")
        return cleared_count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['available_engines'] = list(self.engines.keys())
        stats['current_engine'] = self.current_engine
        stats['cache_enabled'] = self.cache_enabled
        
        # 计算成功率
        total_attempts = stats['successful_syntheses'] + stats['failed_syntheses']
        if total_attempts > 0:
            stats['success_rate'] = stats['successful_syntheses'] / total_attempts
        else:
            stats['success_rate'] = 0.0
        
        # 计算缓存命中率
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_requests']
        else:
            stats['cache_hit_rate'] = 0.0
        
        return stats
    
    def cleanup(self):
        """清理资源"""
        for engine in self.engines.values():
            try:
                engine.cleanup()
            except Exception as e:
                print(f"引擎清理异常: {e}")
        
        self.engines.clear()
        print("✓ TTS管理器已清理")

# 使用示例
if __name__ == '__main__':
    try:
        # 创建增强型TTS管理器
        tts_manager = EnhancedTTSManager()
        
        # 显示可用引擎
        print(f"可用引擎: {tts_manager.get_available_engines()}")
        
        # 测试标准合成
        print("\n=== 测试标准合成 ===")
        success = tts_manager.synthesize_text("你好，这是一个测试。", "test_standard.wav")
        print(f"标准合成结果: {success}")
        
        # 测试对话合成
        print("\n=== 测试对话合成 ===")
        audio_path, info = tts_manager.synthesize_dialogue(
            text="小明，你今天真棒！",
            character="小明",
            auto_emotion=True
        )
        print(f"对话合成结果: {audio_path}")
        print(f"合成信息: {info}")
        
        # 显示统计信息
        print("\n=== 统计信息 ===")
        stats = tts_manager.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
