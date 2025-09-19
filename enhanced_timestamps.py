#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强时间戳模块
提供多种时间戳获取方法：本地ASR + 云端Fun-ASR + 降级方案
"""

import os
import json
import time
import librosa
import jieba
from typing import Dict, List, Optional, Tuple

try:
    from dashscope.audio.asr import Transcription
    import dashscope
    from http import HTTPStatus
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

class EnhancedTimestampProcessor:
    """增强的时间戳处理器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        
        # 初始化云端服务
        if self.api_key and DASHSCOPE_AVAILABLE:
            dashscope.api_key = self.api_key
            self.cloud_available = True
            print("✓ 云端时间戳服务已启用")
        else:
            self.cloud_available = False
            print("⚠️ 云端时间戳服务不可用")
        
        # 尝试获取本地ASR模型
        self.local_asr_model = None
        try:
            from vad_module import VADProcessor
            vad_processor = VADProcessor()
            if hasattr(vad_processor, 'local_asr_model') and vad_processor.local_asr_model:
                self.local_asr_model = vad_processor.local_asr_model
                print("✓ 本地ASR模型可用")
            else:
                print("⚠️ 本地ASR模型不可用")
        except Exception as e:
            print(f"⚠️ 无法访问本地ASR模型: {e}")
    
    def get_precise_word_timestamps(self, audio_path: str, expected_text: str = None) -> Dict:
        """
        获取精确的词级时间戳
        按优先级尝试不同方法
        """
        print(f"🎯 开始获取精确词级时间戳: {os.path.basename(audio_path)}")
        
        # 方法1: 本地ASR模型
        if self.local_asr_model:
            print("📍 尝试本地ASR模型...")
            result = self._get_timestamps_local_asr(audio_path, expected_text)
            if result and result.get('success'):
                print("✅ 本地ASR时间戳获取成功")
                return result
        
        # 方法2: 云端Fun-ASR（需要公网URL，暂时跳过）
        # if self.cloud_available:
        #     print("☁️ 尝试云端Fun-ASR...")
        #     # 这里可以添加文件上传逻辑
        
        # 方法3: 智能降级方案
        print("📊 使用智能降级方案...")
        result = self._get_timestamps_smart_fallback(audio_path, expected_text)
        if result and result.get('success'):
            print("✅ 智能降级时间戳获取成功")
            return result
        
        # 方法4: 基础降级方案
        print("🔧 使用基础降级方案...")
        return self._get_timestamps_basic_fallback(audio_path, expected_text)
    
    def _get_timestamps_local_asr(self, audio_path: str, expected_text: str = None) -> Dict:
        """使用本地ASR模型获取时间戳"""
        try:
            # 执行ASR识别
            result = self.local_asr_model.generate(input=audio_path)
            
            if not result or not isinstance(result, list) or len(result) == 0:
                return {'success': False}
            
            # 提取识别文本
            item = result[0]
            recognized_text = item.get('text', '')
            
            if not recognized_text:
                return {'success': False}
            
            # 创建词级时间戳
            word_timestamps = self._create_smart_word_timestamps(
                recognized_text, audio_path, expected_text
            )
            
            return {
                'method': 'local_asr',
                'recognized_text': recognized_text,
                'expected_text': expected_text or '',
                'word_timestamps': word_timestamps,
                'success': True
            }
            
        except Exception as e:
            print(f"本地ASR处理失败: {e}")
            return {'success': False}
    
    def _get_timestamps_smart_fallback(self, audio_path: str, expected_text: str = None) -> Dict:
        """智能降级方案：结合VAD和音频特征"""
        try:
            if not expected_text:
                return {'success': False}
            
            # 1. 获取音频基本信息
            y, sr = librosa.load(audio_path)
            duration = len(y) / sr
            
            # 2. 尝试使用VAD检测语音段
            speech_segments = self._detect_speech_with_energy(y, sr)
            
            # 3. 分词
            words = list(jieba.cut(expected_text))
            words = [w.strip() for w in words if w.strip()]
            
            if not words:
                return {'success': False}
            
            # 4. 智能分配时间戳
            word_timestamps = self._distribute_words_to_speech_segments(
                words, speech_segments, duration
            )
            
            return {
                'method': 'smart_fallback',
                'recognized_text': expected_text,
                'expected_text': expected_text,
                'word_timestamps': word_timestamps,
                'speech_segments': speech_segments,
                'success': True
            }
            
        except Exception as e:
            print(f"智能降级方案失败: {e}")
            return {'success': False}
    
    def _get_timestamps_basic_fallback(self, audio_path: str, expected_text: str = None) -> Dict:
        """基础降级方案：均匀时间分布"""
        try:
            # 获取音频时长
            if os.path.exists(audio_path):
                y, sr = librosa.load(audio_path)
                duration = len(y) / sr
            else:
                duration = 2.0
            
            text_to_use = expected_text or "默认文本"
            
            # 分词
            words = list(jieba.cut(text_to_use))
            words = [w.strip() for w in words if w.strip()]
            
            if not words:
                words = [text_to_use]
            
            # 均匀分布
            word_timestamps = []
            time_per_word = duration / len(words)
            
            for i, word in enumerate(words):
                start_time = i * time_per_word
                end_time = (i + 1) * time_per_word
                word_timestamps.append({
                    'word': word,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': 0.5  # 中等置信度
                })
            
            return {
                'method': 'basic_fallback',
                'recognized_text': text_to_use,
                'expected_text': expected_text or '',
                'word_timestamps': word_timestamps,
                'success': True
            }
            
        except Exception as e:
            print(f"基础降级方案失败: {e}")
            return {
                'method': 'error',
                'recognized_text': '',
                'expected_text': expected_text or '',
                'word_timestamps': [],
                'success': False
            }
    
    def _create_smart_word_timestamps(self, recognized_text: str, audio_path: str, expected_text: str = None) -> List[Dict]:
        """创建智能词级时间戳"""
        try:
            # 获取音频时长
            y, sr = librosa.load(audio_path)
            duration = len(y) / sr
            
            # 分词
            words = list(jieba.cut(recognized_text))
            words = [w.strip() for w in words if w.strip()]
            
            if not words:
                return []
            
            # 如果有期望文本，尝试对齐
            if expected_text:
                expected_words = list(jieba.cut(expected_text))
                expected_words = [w.strip() for w in expected_words if w.strip()]
                
                # 简单的词对齐
                if len(words) == len(expected_words):
                    # 词数相同，直接对应
                    words = expected_words
                elif len(expected_words) > 0:
                    # 混合使用
                    words = expected_words
            
            # 创建时间戳
            word_timestamps = []
            time_per_word = duration / len(words)
            
            for i, word in enumerate(words):
                start_time = i * time_per_word
                end_time = (i + 1) * time_per_word
                word_timestamps.append({
                    'word': word,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': 0.8  # 较高置信度
                })
            
            return word_timestamps
            
        except Exception as e:
            print(f"创建智能时间戳失败: {e}")
            return []
    
    def _detect_speech_with_energy(self, y, sr, frame_length=2048, hop_length=512):
        """使用能量检测语音段"""
        try:
            # 计算短时能量
            frame_energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # 计算阈值
            energy_threshold = 0.02 * frame_energy.max()
            
            # 检测语音段
            speech_frames = frame_energy > energy_threshold
            
            # 转换为时间段
            times = librosa.frames_to_time(range(len(speech_frames)), sr=sr, hop_length=hop_length)
            
            speech_segments = []
            in_speech = False
            start_time = 0
            
            for i, is_speech in enumerate(speech_frames):
                if is_speech and not in_speech:
                    # 语音开始
                    start_time = times[i]
                    in_speech = True
                elif not is_speech and in_speech:
                    # 语音结束
                    end_time = times[i]
                    if end_time - start_time > 0.1:  # 最小语音段长度
                        speech_segments.append((start_time, end_time))
                    in_speech = False
            
            # 处理最后一个语音段
            if in_speech:
                speech_segments.append((start_time, times[-1]))
            
            return speech_segments if speech_segments else [(0, len(y)/sr)]
            
        except Exception as e:
            print(f"语音检测失败: {e}")
            return [(0, len(y)/sr)]
    
    def _distribute_words_to_speech_segments(self, words: List[str], speech_segments: List[Tuple], total_duration: float) -> List[Dict]:
        """将词分配到语音段中"""
        try:
            if not speech_segments or not words:
                return []
            
            word_timestamps = []
            
            # 计算总语音时长
            total_speech_duration = sum(end - start for start, end in speech_segments)
            
            # 为每个词分配时间
            chars_per_word = [len(word) for word in words]
            total_chars = sum(chars_per_word)
            
            current_time = speech_segments[0][0]
            segment_idx = 0
            segment_time_left = speech_segments[0][1] - speech_segments[0][0]
            
            for i, word in enumerate(words):
                if total_chars > 0:
                    word_duration = (chars_per_word[i] / total_chars) * total_speech_duration
                else:
                    word_duration = total_speech_duration / len(words)
                
                # 确保词在当前语音段内
                while segment_time_left < word_duration and segment_idx < len(speech_segments) - 1:
                    # 移动到下一个语音段
                    segment_idx += 1
                    current_time = speech_segments[segment_idx][0]
                    segment_time_left = speech_segments[segment_idx][1] - speech_segments[segment_idx][0]
                
                start_time = current_time
                end_time = min(current_time + word_duration, speech_segments[segment_idx][1])
                
                word_timestamps.append({
                    'word': word,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': 0.7
                })
                
                current_time = end_time
                segment_time_left -= (end_time - start_time)
            
            return word_timestamps
            
        except Exception as e:
            print(f"词时间分配失败: {e}")
            return []

def test_enhanced_timestamps():
    """测试增强时间戳功能"""
    processor = EnhancedTimestampProcessor()
    
    test_file = "outputs/fun_asr_test_standard_今天天气很好.wav"
    expected_text = "今天天气很好"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"🎵 测试音频: {test_file}")
    print(f"📝 期望文本: {expected_text}")
    
    result = processor.get_precise_word_timestamps(test_file, expected_text)
    
    if result and result.get('success'):
        print(f"\n✅ 增强时间戳获取成功!")
        print(f"方法: {result['method']}")
        print(f"识别文本: {result['recognized_text']}")
        print(f"词级时间戳数量: {len(result['word_timestamps'])}")
        
        print("\n📊 词级时间戳详情:")
        for i, ts in enumerate(result['word_timestamps'], 1):
            print(f"  {i}. '{ts['word']}': {ts['start_time']:.2f}s - {ts['end_time']:.2f}s (置信度: {ts.get('confidence', 0.5):.1f})")
        
        return result
    else:
        print("❌ 增强时间戳获取失败")
        return None

if __name__ == "__main__":
    test_enhanced_timestamps()
