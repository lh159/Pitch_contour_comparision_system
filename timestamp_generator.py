# -*- coding: utf-8 -*-
"""
通用时间戳生成器
支持多种方法生成字级时间戳：TTS原生、Forced Alignment、VAD估算
"""
import os
import numpy as np
import traceback
from typing import Dict, List, Optional
from config import Config

class UniversalTimestampGenerator:
    """通用时间戳生成器"""
    
    def __init__(self, enable_cache: bool = True):
        self.mfa_aligner = None
        self.wav2vec_model = None
        self.initialized = False
        self.enable_cache = enable_cache
        
        # 初始化缓存
        if enable_cache:
            try:
                from cache_manager import timestamp_cache, performance_optimizer, timing_decorator
                self.cache = timestamp_cache
                self.performance_optimizer = performance_optimizer
                self.timing_decorator = timing_decorator
                print("✓ 缓存系统已启用")
            except ImportError as e:
                print(f"⚠️ 缓存模块导入失败，将禁用缓存功能: {e}")
                self.enable_cache = False
                self.cache = None
        
    def initialize(self):
        """初始化各种对齐模型"""
        try:
            print("初始化时间戳生成器...")
            self.initialized = True
            print("✓ 时间戳生成器初始化完成")
            return True
        except Exception as e:
            print(f"✗ 时间戳生成器初始化失败: {e}")
            return False
    
    def generate_timestamps(self, text: str, audio_path: str, 
                          method: str = 'auto', tts_engine: str = 'default') -> Dict:
        """
        通用时间戳生成器（支持缓存）
        :param text: 原始文本
        :param audio_path: 音频文件路径
        :param method: 生成方法 ('auto', 'forced_alignment', 'vad_estimation')
        :param tts_engine: TTS引擎名称（用于缓存键）
        :return: 时间戳生成结果
        """
        if not self.initialized:
            self.initialize()
        
        # 检查缓存
        if self.enable_cache and self.cache:
            cached_result = self.cache.get_timestamps(text, tts_engine, method)
            if cached_result:
                print(f"✓ 从缓存获取时间戳: {text[:20]}...")
                return cached_result['timestamps']
        
        print(f"生成时间戳: {text}, 方法: {method}")
        
        # 性能计时
        timing_id = None
        if self.enable_cache and hasattr(self, 'performance_optimizer'):
            timing_id = self.performance_optimizer.start_timing(f'generate_timestamps_{method}')
        
        try:
            result = None
            
            if method == 'auto':
                # 自动选择最佳方案
                if self._has_native_timestamps(audio_path):
                    result = self._extract_native_timestamps(audio_path, text)
                else:
                    # 尝试VAD估算方法
                    result = self._vad_based_estimation(text, audio_path)
                    if not result['success'] or not result.get('char_timestamps'):
                        # 如果失败或没有时间戳，使用均匀分布估算
                        print("VAD方法无效，降级到均匀分布估算")
                        result = self._uniform_estimation(text, audio_path)
            elif method == 'forced_alignment':
                result = self._forced_alignment(text, audio_path)
            elif method == 'vad_estimation':
                result = self._vad_based_estimation(text, audio_path)
            elif method == 'uniform':
                result = self._uniform_estimation(text, audio_path)
            else:
                result = {'success': False, 'error': f'未知的方法: {method}'}
            
            # 结束计时
            if timing_id and hasattr(self, 'performance_optimizer'):
                duration = self.performance_optimizer.end_timing(timing_id)
                result['generation_time'] = duration
            
            # 保存到缓存
            if self.enable_cache and self.cache and result.get('success'):
                self.cache.set_timestamps(text, result, tts_engine, method)
            
            return result
                
        except Exception as e:
            print(f"时间戳生成失败: {e}")
            traceback.print_exc()
            
            # 结束计时
            if timing_id and hasattr(self, 'performance_optimizer'):
                self.performance_optimizer.end_timing(timing_id)
            
            # 降级到均匀分布估算
            return self._uniform_estimation(text, audio_path)
    
    def _has_native_timestamps(self, audio_path: str) -> bool:
        """检查音频是否包含原生时间戳"""
        # 目前返回False，后续可以扩展检查音频元数据
        return False
    
    def _extract_native_timestamps(self, audio_path: str, text: str) -> Dict:
        """提取原生时间戳（如果支持）"""
        return {'success': False, 'error': '原生时间戳提取暂未实现'}
    
    def _forced_alignment(self, text: str, audio_path: str) -> Dict:
        """
        使用Forced Alignment生成时间戳
        """
        try:
            # 尝试导入MFA库
            try:
                from montreal_forced_aligner import align
                print("使用Montreal Forced Aligner进行对齐...")
            except ImportError:
                print("Montreal Forced Aligner未安装，使用fallback方法")
                return self._fallback_estimation(text, audio_path)
            
            # 准备输入数据
            alignment_data = {
                'text': text,
                'audio': audio_path,
                'language': 'mandarin'
            }
            
            # 执行对齐（这里是示例代码，实际需要根据MFA API调整）
            print("执行强制对齐...")
            # alignment_result = align(alignment_data)
            
            # 由于MFA配置复杂，这里先使用fallback方法
            return self._fallback_estimation(text, audio_path)
            
        except Exception as e:
            print(f"Forced Alignment失败: {e}")
            return self._fallback_estimation(text, audio_path)
    
    def _vad_based_estimation(self, text: str, audio_path: str) -> Dict:
        """
        基于VAD+ASR的时间戳估算
        """
        try:
            # 检查VAD模块是否可用
            try:
                from vad_module import VADProcessor
                print("使用VAD+ASR方法估算时间戳...")
            except ImportError:
                print("VAD模块不可用，使用fallback方法")
                return self._fallback_estimation(text, audio_path)
            
            vad_processor = VADProcessor()
            
            # 获取VAD分段和ASR识别结果
            alignment_result = vad_processor.align_text_with_vad(text, audio_path)
            
            # 基于识别结果估算字级时间戳
            char_timestamps = []
            if alignment_result.get('text_alignment'):
                char_index = 0
                for alignment in alignment_result['text_alignment']:
                    start_time = alignment.get('start_time', 0)
                    end_time = alignment.get('end_time', 0)
                    expected_text = alignment.get('expected', '')
                    
                    if expected_text and end_time > start_time:
                        # 平均分配时间给每个字符
                        char_duration = (end_time - start_time) / len(expected_text)
                        
                        for i, char in enumerate(expected_text):
                            if char_index < len(text):
                                char_timestamps.append({
                                    'char': text[char_index],
                                    'start_time': start_time + i * char_duration,
                                    'end_time': start_time + (i + 1) * char_duration,
                                    'confidence': 0.7,  # VAD估算的置信度
                                    'index': char_index
                                })
                                char_index += 1
            
            # 如果VAD方法没有生成足够的时间戳，用均匀分布补充
            if len(char_timestamps) < len(text):
                print("VAD方法生成的时间戳不完整，使用混合方法补充")
                return self._hybrid_estimation(text, audio_path, char_timestamps)
            
            return {
                'success': True,
                'char_timestamps': char_timestamps,
                'method': 'vad_estimation',
                'duration': char_timestamps[-1]['end_time'] if char_timestamps else 0
            }
            
        except Exception as e:
            print(f"VAD估算失败: {e}")
            traceback.print_exc()
            return self._fallback_estimation(text, audio_path)
    
    def _uniform_estimation(self, text: str, audio_path: str) -> Dict:
        """
        均匀分布时间戳估算（保底方案）
        """
        try:
            # 获取音频时长
            duration = self._get_audio_duration(audio_path)
            if duration <= 0:
                return {'success': False, 'error': '无法获取音频时长'}
            
            char_timestamps = []
            char_count = len(text)
            
            if char_count > 0:
                # 平均分配时间
                char_duration = duration / char_count
                
                for i, char in enumerate(text):
                    start_time = i * char_duration
                    end_time = (i + 1) * char_duration
                    
                    char_timestamps.append({
                        'char': char,
                        'start_time': start_time,
                        'end_time': end_time,
                        'confidence': 0.5,  # 均匀分布的置信度较低
                        'index': i
                    })
            
            return {
                'success': True,
                'char_timestamps': char_timestamps,
                'method': 'uniform_estimation',
                'duration': duration
            }
            
        except Exception as e:
            print(f"均匀分布估算失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _hybrid_estimation(self, text: str, audio_path: str, existing_timestamps: List[Dict]) -> Dict:
        """
        混合估算方法：结合已有时间戳和均匀分布
        """
        try:
            duration = self._get_audio_duration(audio_path)
            char_timestamps = []
            
            # 复制已有的时间戳
            for ts in existing_timestamps:
                char_timestamps.append(ts.copy())
            
            # 为剩余字符生成时间戳
            existing_count = len(existing_timestamps)
            remaining_count = len(text) - existing_count
            
            if remaining_count > 0:
                if existing_count > 0:
                    # 从最后一个已知时间戳开始
                    last_end_time = existing_timestamps[-1]['end_time']
                    remaining_duration = duration - last_end_time
                    
                    if remaining_duration > 0:
                        char_duration = remaining_duration / remaining_count
                        
                        for i in range(remaining_count):
                            char_index = existing_count + i
                            if char_index < len(text):
                                start_time = last_end_time + i * char_duration
                                end_time = last_end_time + (i + 1) * char_duration
                                
                                char_timestamps.append({
                                    'char': text[char_index],
                                    'start_time': start_time,
                                    'end_time': end_time,
                                    'confidence': 0.6,  # 混合方法的置信度
                                    'index': char_index
                                })
                else:
                    # 没有已知时间戳，使用均匀分布
                    print("没有已知时间戳，使用均匀分布方法")
                    return self._uniform_estimation(text, audio_path)
            
            return {
                'success': True,
                'char_timestamps': char_timestamps,
                'method': 'hybrid_estimation',
                'duration': duration
            }
            
        except Exception as e:
            print(f"混合估算失败: {e}")
            return self._uniform_estimation(text, audio_path)
    
    def _fallback_estimation(self, text: str, audio_path: str) -> Dict:
        """fallback到均匀分布估算"""
        print("使用fallback方法：均匀分布估算")
        return self._uniform_estimation(text, audio_path)
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长"""
        try:
            import librosa
            # 使用librosa获取音频时长（只读取header，速度快）
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except ImportError:
            # 如果librosa不可用，尝试使用parselmouth
            try:
                import parselmouth
                sound = parselmouth.Sound(audio_path)
                return sound.duration
            except:
                # 最后尝试使用wave模块
                try:
                    import wave
                    with wave.open(audio_path, 'r') as wav_file:
                        frames = wav_file.getnframes()
                        sample_rate = wav_file.getframerate()
                        return frames / float(sample_rate)
                except:
                    print("无法获取音频时长，使用默认值")
                    return 3.0  # 默认3秒
        except Exception as e:
            print(f"获取音频时长失败: {e}")
            return 3.0  # 默认3秒
    
    def validate_timestamps(self, timestamps: List[Dict]) -> bool:
        """验证时间戳的有效性"""
        if not timestamps:
            return False
        
        for i, ts in enumerate(timestamps):
            # 检查必要字段
            required_fields = ['char', 'start_time', 'end_time', 'index']
            if not all(field in ts for field in required_fields):
                print(f"时间戳 {i} 缺少必要字段")
                return False
            
            # 检查时间逻辑
            if ts['start_time'] >= ts['end_time']:
                print(f"时间戳 {i} 时间逻辑错误: {ts['start_time']} >= {ts['end_time']}")
                return False
            
            # 检查时间顺序
            if i > 0 and ts['start_time'] < timestamps[i-1]['start_time']:
                print(f"时间戳 {i} 时间顺序错误")
                return False
        
        return True

# 使用示例和测试
if __name__ == '__main__':
    import sys
    
    # 创建时间戳生成器
    generator = UniversalTimestampGenerator()
    generator.initialize()
    
    # 测试用例
    if len(sys.argv) >= 3:
        test_text = sys.argv[1]
        test_audio = sys.argv[2]
        
        if os.path.exists(test_audio):
            print(f"\n=== 测试时间戳生成: {test_text} ===")
            
            # 测试不同方法
            methods = ['auto', 'vad_estimation', 'uniform']
            
            for method in methods:
                print(f"\n--- 方法: {method} ---")
                result = generator.generate_timestamps(test_text, test_audio, method)
                
                if result['success']:
                    timestamps = result['char_timestamps']
                    print(f"✓ 成功生成 {len(timestamps)} 个时间戳")
                    print(f"  方法: {result['method']}")
                    print(f"  总时长: {result.get('duration', 0):.2f}秒")
                    
                    # 显示前几个时间戳
                    for i, ts in enumerate(timestamps[:5]):
                        print(f"  {i}: '{ts['char']}' {ts['start_time']:.2f}-{ts['end_time']:.2f}s (置信度: {ts.get('confidence', 1.0):.2f})")
                    
                    if len(timestamps) > 5:
                        print(f"  ... 还有 {len(timestamps) - 5} 个时间戳")
                    
                    # 验证时间戳
                    is_valid = generator.validate_timestamps(timestamps)
                    print(f"  验证结果: {'✓ 有效' if is_valid else '✗ 无效'}")
                else:
                    print(f"✗ 失败: {result.get('error')}")
        else:
            print(f"测试音频文件不存在: {test_audio}")
    else:
        print("使用方法: python timestamp_generator.py '测试文本' 'test_audio.wav'")
        
        # 创建一个简单的测试
        print("\n=== 功能测试 ===")
        test_text = "你好世界"
        
        # 模拟测试（没有真实音频文件）
        dummy_result = generator._uniform_estimation(test_text, "dummy.wav")
        
        if dummy_result['success']:
            print("✓ 基础功能正常")
            timestamps = dummy_result['char_timestamps']
            for ts in timestamps:
                print(f"  '{ts['char']}': {ts['start_time']:.2f}-{ts['end_time']:.2f}s")
        else:
            print("✗ 基础功能异常")
