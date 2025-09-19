#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的音高对齐模块
解决音高曲线比对中的关键问题：
1. 截断音高曲线到TTS结束时间
2. 使用ASR对齐用户发音与TTS标准发音的时间轴  
3. 验证用户真实录音输入，处理静音和假音频问题
"""

import numpy as np
import parselmouth
import librosa
import soundfile as sf
from typing import Dict, List, Tuple, Optional
import os
import tempfile
from scipy.interpolate import interp1d
from config import Config

try:
    from vad_module import VADProcessor
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("警告: VAD模块不可用")

try:
    from fun_asr_module import FunASRProcessor
    FUN_ASR_AVAILABLE = True
except ImportError:
    FUN_ASR_AVAILABLE = False
    print("警告: Fun-ASR模块不可用")


class EnhancedPitchAligner:
    """增强的音高对齐器"""
    
    def __init__(self):
        """初始化增强的音高对齐器"""
        # 初始化VAD处理器
        self.vad_processor = None
        if VAD_AVAILABLE:
            try:
                self.vad_processor = VADProcessor()
                print("✓ VAD处理器初始化成功")
            except Exception as e:
                print(f"⚠️ VAD处理器初始化失败: {e}")
        
        # 初始化Fun-ASR处理器
        self.fun_asr_processor = None
        if FUN_ASR_AVAILABLE:
            try:
                self.fun_asr_processor = FunASRProcessor()
                print("✓ Fun-ASR处理器初始化成功")
            except Exception as e:
                print(f"⚠️ Fun-ASR处理器初始化失败: {e}")
        
        # 音频质量检测阈值
        self.silence_energy_threshold = 0.005  # 静音能量阈值
        self.min_speech_ratio = 0.1  # 最小语音比例
        self.min_pitch_validity = 0.15  # 最小有效音高比例
    
    def get_tts_audio_duration(self, tts_audio_path: str, text: str = None) -> float:
        """
        获取TTS音频的实际有效时长（排除尾部静音）
        :param tts_audio_path: TTS音频文件路径
        :param text: 原始文本（用于辅助验证）
        :return: 有效音频时长（秒）
        """
        try:
            print(f"🔍 分析TTS音频时长: {tts_audio_path}")
            
            # 方法1: 使用VAD检测语音结束时间
            if self.vad_processor:
                vad_info = self.vad_processor.get_speech_regions_timestamps(tts_audio_path)
                speech_segments = vad_info.get('speech_segments', [])
                
                if speech_segments:
                    # 找到最后一个语音段的结束时间
                    last_speech_end = max(end for start, end in speech_segments)
                    print(f"✓ VAD检测到的语音结束时间: {last_speech_end:.3f}s")
                    return last_speech_end
            
            # 方法2: 使用能量检测
            y, sr = librosa.load(tts_audio_path, sr=None)
            
            # 计算短时能量
            frame_length = int(0.025 * sr)  # 25ms
            hop_length = int(0.010 * sr)    # 10ms
            
            rms = librosa.feature.rms(
                y=y, 
                frame_length=frame_length, 
                hop_length=hop_length
            )[0]
            
            # 动态阈值：平均能量的30%
            energy_threshold = np.mean(rms) * 0.3
            
            # 从后向前查找最后的有效语音
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
            
            for i in range(len(rms) - 1, -1, -1):
                if rms[i] > energy_threshold:
                    # 找到最后的有效语音帧，再延长一点点
                    effective_duration = times[i] + 0.1  # 增加100ms缓冲
                    print(f"✓ 能量检测到的语音结束时间: {effective_duration:.3f}s")
                    return min(effective_duration, len(y) / sr)  # 不超过总时长
            
            # 方法3: 如果都失败，使用总时长的90%作为保守估计
            total_duration = len(y) / sr
            conservative_duration = total_duration * 0.9
            print(f"⚠️ 使用保守估计的语音结束时间: {conservative_duration:.3f}s")
            return conservative_duration
            
        except Exception as e:
            print(f"❌ 获取TTS音频时长失败: {e}")
            # 最后的兜底方案：尝试直接获取音频时长
            try:
                sound = parselmouth.Sound(tts_audio_path)
                return sound.duration * 0.9  # 取90%作为保守估计
            except:
                return 3.0  # 默认3秒
    
    def validate_user_audio_quality(self, user_audio_path: str) -> Dict:
        """
        验证用户录音的质量，检测是否为真实录音
        :param user_audio_path: 用户音频文件路径
        :return: 验证结果
        """
        try:
            print(f"🎯 验证用户录音质量: {user_audio_path}")
            
            # 加载音频
            y, sr = librosa.load(user_audio_path, sr=None)
            total_duration = len(y) / sr
            
            # 检查1: 音频长度是否合理
            if total_duration < 0.3:
                return {
                    'is_valid': False,
                    'reason': '录音时间过短',
                    'details': f'录音时长仅{total_duration:.2f}s，可能未正确录音'
                }
            
            # 检查2: 计算RMS能量
            rms = np.sqrt(np.mean(y**2))
            if rms < self.silence_energy_threshold:
                return {
                    'is_valid': False,
                    'reason': '录音音量过小或为静音',
                    'details': f'RMS能量{rms:.6f}低于阈值{self.silence_energy_threshold}'
                }
            
            # 检查3: 使用VAD检测实际语音比例
            speech_ratio = 0.0
            speech_segments = []
            
            if self.vad_processor:
                vad_info = self.vad_processor.get_speech_regions_timestamps(user_audio_path)
                speech_ratio = vad_info.get('speech_ratio', 0.0)
                speech_segments = vad_info.get('speech_segments', [])
            else:
                # 简单的能量检测
                frame_length = int(0.025 * sr)
                hop_length = int(0.010 * sr)
                rms_frames = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
                
                # 动态阈值
                energy_threshold = np.mean(rms_frames) * 0.3
                speech_frames = rms_frames > energy_threshold
                speech_ratio = np.mean(speech_frames)
            
            if speech_ratio < self.min_speech_ratio:
                return {
                    'is_valid': False,
                    'reason': '语音内容比例过低',
                    'details': f'语音比例{speech_ratio:.2%}低于{self.min_speech_ratio:.2%}，可能录音有问题'
                }
            
            # 检查4: 音高检测验证
            try:
                sound = parselmouth.Sound(user_audio_path)
                pitch = sound.to_pitch()
                pitch_values = pitch.selected_array['frequency']
                pitch_values = pitch_values[pitch_values > 0]  # 只考虑有效音高
                
                if len(pitch_values) == 0:
                    return {
                        'is_valid': False,
                        'reason': '未检测到有效音高',
                        'details': '无法从录音中提取音高信息，可能为纯噪音或静音'
                    }
                
                valid_pitch_ratio = len(pitch_values) / len(pitch.selected_array['frequency'])
                if valid_pitch_ratio < self.min_pitch_validity:
                    return {
                        'is_valid': False,
                        'reason': '有效音高比例过低',
                        'details': f'有效音高比例{valid_pitch_ratio:.2%}低于{self.min_pitch_validity:.2%}'
                    }
                
            except Exception as e:
                print(f"⚠️ 音高检测失败: {e}")
                # 音高检测失败不一定意味着录音无效，继续其他检查
            
            # 检查5: 音频动态范围
            amplitude_range = np.max(np.abs(y)) - np.min(np.abs(y))
            if amplitude_range < 0.01:  # 动态范围过小
                return {
                    'is_valid': False,
                    'reason': '音频动态范围过小',
                    'details': f'可能为单调音频或损坏文件，动态范围{amplitude_range:.4f}'
                }
            
            # 所有检查通过
            return {
                'is_valid': True,
                'reason': '录音质量良好',
                'details': {
                    'duration': total_duration,
                    'rms_energy': rms,
                    'speech_ratio': speech_ratio,
                    'speech_segments_count': len(speech_segments),
                    'amplitude_range': amplitude_range
                }
            }
            
        except Exception as e:
            print(f"❌ 用户录音质量验证失败: {e}")
            return {
                'is_valid': False,
                'reason': '录音文件分析失败',
                'details': f'无法分析录音文件: {str(e)}'
            }
    
    def align_user_audio_with_tts(self, user_audio_path: str, tts_audio_path: str, 
                                expected_text: str) -> Dict:
        """
        使用ASR将用户发音与TTS标准发音进行时间轴对齐
        :param user_audio_path: 用户音频路径
        :param tts_audio_path: TTS音频路径
        :param expected_text: 期望文本
        :return: 对齐结果
        """
        try:
            print(f"🔄 开始ASR时间轴对齐...")
            
            # 1. 验证用户录音质量
            user_quality = self.validate_user_audio_quality(user_audio_path)
            if not user_quality['is_valid']:
                return {
                    'success': False,
                    'error': f"用户录音质量问题: {user_quality['reason']}",
                    'details': user_quality['details']
                }
            
            # 2. 获取TTS音频的有效时长
            tts_duration = self.get_tts_audio_duration(tts_audio_path, expected_text)
            
            # 3. 使用ASR分析用户音频
            user_asr_result = None
            if self.vad_processor:
                user_asr_result = self.vad_processor.recognize_speech_with_timestamps(
                    user_audio_path, expected_text
                )
            
            # 4. 获取用户录音的语音段
            user_speech_segments = []
            if self.vad_processor:
                vad_info = self.vad_processor.get_speech_regions_timestamps(user_audio_path)
                user_speech_segments = vad_info.get('speech_segments', [])
            
            # 5. 计算对齐策略
            alignment_result = self._calculate_temporal_alignment(
                user_asr_result, user_speech_segments, tts_duration, expected_text
            )
            
            return {
                'success': True,
                'tts_effective_duration': tts_duration,
                'user_quality': user_quality,
                'user_asr_result': user_asr_result,
                'user_speech_segments': user_speech_segments,
                'alignment': alignment_result
            }
            
        except Exception as e:
            print(f"❌ ASR时间轴对齐失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'ASR对齐过程失败: {str(e)}'
            }
    
    def _calculate_temporal_alignment(self, user_asr_result: Optional[Dict], 
                                    user_speech_segments: List[Tuple], 
                                    tts_duration: float, 
                                    expected_text: str) -> Dict:
        """
        计算时间轴对齐策略
        :param user_asr_result: 用户ASR识别结果
        :param user_speech_segments: 用户语音段
        :param tts_duration: TTS有效时长
        :param expected_text: 期望文本
        :return: 对齐策略
        """
        try:
            # 清理期望文本
            clean_text = ''.join(c for c in expected_text if c.strip() and c not in '，。！？、')
            char_count = len(clean_text)
            
            alignment_strategy = {
                'method': 'uniform',  # 默认均匀分布
                'user_start_time': 0.0,
                'user_end_time': tts_duration,
                'scaling_factor': 1.0,
                'time_offset': 0.0
            }
            
            # 策略1: 如果有ASR时间戳，使用基于ASR的对齐
            if (user_asr_result and user_asr_result.get('timestamps') and 
                len(user_asr_result['timestamps']) > 0):
                
                timestamps = user_asr_result['timestamps']
                first_word_start = timestamps[0]['start']
                last_word_end = timestamps[-1]['end']
                user_speech_duration = last_word_end - first_word_start
                
                if user_speech_duration > 0:
                    # 计算缩放因子（用户说话速度 vs TTS速度）
                    scaling_factor = user_speech_duration / tts_duration
                    
                    alignment_strategy.update({
                        'method': 'asr_based',
                        'user_start_time': first_word_start,
                        'user_end_time': last_word_end,
                        'scaling_factor': scaling_factor,
                        'time_offset': first_word_start,
                        'asr_word_count': len(timestamps)
                    })
                    
                    print(f"✓ 使用ASR对齐: 用户语音{user_speech_duration:.2f}s, TTS{tts_duration:.2f}s, 缩放{scaling_factor:.2f}")
            
            # 策略2: 如果有VAD语音段，使用基于VAD的对齐
            elif user_speech_segments:
                # 合并所有语音段
                speech_start = min(start for start, end in user_speech_segments)
                speech_end = max(end for start, end in user_speech_segments)
                user_speech_duration = speech_end - speech_start
                
                if user_speech_duration > 0:
                    scaling_factor = user_speech_duration / tts_duration
                    
                    alignment_strategy.update({
                        'method': 'vad_based',
                        'user_start_time': speech_start,
                        'user_end_time': speech_end,
                        'scaling_factor': scaling_factor,
                        'time_offset': speech_start,
                        'speech_segments_count': len(user_speech_segments)
                    })
                    
                    print(f"✓ 使用VAD对齐: 用户语音{user_speech_duration:.2f}s, TTS{tts_duration:.2f}s, 缩放{scaling_factor:.2f}")
            
            # 策略3: 简单的时长对齐（用户音频总时长 vs TTS时长）
            else:
                print("⚠️ 使用简单时长对齐（无ASR和VAD信息）")
                alignment_strategy.update({
                    'method': 'duration_based',
                    'user_end_time': tts_duration  # 假设用户说话时长等于TTS时长
                })
            
            return alignment_strategy
            
        except Exception as e:
            print(f"❌ 计算时间轴对齐失败: {e}")
            # 返回默认的均匀对齐
            return {
                'method': 'uniform',
                'user_start_time': 0.0,
                'user_end_time': tts_duration,
                'scaling_factor': 1.0,
                'time_offset': 0.0
            }
    
    def truncate_pitch_curves_to_tts_duration(self, standard_pitch: Dict, user_pitch: Dict, 
                                            tts_duration: float, alignment: Dict) -> Dict:
        """
        将音高曲线截断到TTS有效时长，并进行时间对齐
        :param standard_pitch: 标准音高数据
        :param user_pitch: 用户音高数据
        :param tts_duration: TTS有效时长
        :param alignment: 对齐策略
        :return: 截断和对齐后的音高数据
        """
        try:
            print(f"✂️ 截断音高曲线到TTS时长: {tts_duration:.3f}s")
            
            # 1. 截断标准音高到TTS有效时长
            std_times = standard_pitch['times']
            std_pitch_values = standard_pitch['pitch_values']
            
            # 找到TTS有效时长内的标准音高点
            tts_mask = std_times <= tts_duration
            truncated_std_times = std_times[tts_mask]
            truncated_std_pitch = std_pitch_values[tts_mask]
            
            print(f"✓ 标准音高截断: {len(std_times)} -> {len(truncated_std_times)} 点")
            
            # 2. 对用户音高进行时间轴对齐和截断
            user_times = user_pitch['times']
            user_pitch_values = user_pitch['pitch_values']
            
            # 根据对齐策略调整用户时间轴
            aligned_user_times, aligned_user_pitch = self._align_user_timeline(
                user_times, user_pitch_values, alignment, tts_duration
            )
            
            # 3. 将两个音高曲线插值到统一的时间轴
            if len(truncated_std_times) > 0 and len(aligned_user_times) > 0:
                # 创建统一时间轴（从0到TTS结束时间）
                unified_times = np.linspace(0, tts_duration, 
                                          max(len(truncated_std_times), len(aligned_user_times), 200))
                
                # 插值标准音高到统一时间轴
                unified_std_pitch = self._interpolate_pitch_to_timeline(
                    truncated_std_times, truncated_std_pitch, unified_times
                )
                
                # 插值用户音高到统一时间轴
                unified_user_pitch = self._interpolate_pitch_to_timeline(
                    aligned_user_times, aligned_user_pitch, unified_times
                )
                
                print(f"✓ 音高曲线对齐完成: 统一时间轴{len(unified_times)}点")
                
                return {
                    'aligned_times': unified_times,
                    'aligned_standard': unified_std_pitch,
                    'aligned_user': unified_user_pitch,
                    'tts_duration': tts_duration,
                    'alignment_method': alignment['method'],
                    'success': True
                }
            else:
                print("❌ 音高数据不足，无法进行对齐")
                return {
                    'aligned_times': np.array([]),
                    'aligned_standard': np.array([]),
                    'aligned_user': np.array([]),
                    'tts_duration': tts_duration,
                    'alignment_method': 'failed',
                    'success': False
                }
                
        except Exception as e:
            print(f"❌ 音高曲线截断对齐失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'aligned_times': np.array([]),
                'aligned_standard': np.array([]),
                'aligned_user': np.array([]),
                'tts_duration': tts_duration,
                'alignment_method': 'error',
                'success': False,
                'error': str(e)
            }
    
    def _align_user_timeline(self, user_times: np.ndarray, user_pitch: np.ndarray, 
                           alignment: Dict, tts_duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        根据对齐策略调整用户音高的时间轴
        :param user_times: 用户原始时间轴
        :param user_pitch: 用户音高值
        :param alignment: 对齐策略
        :param tts_duration: TTS时长
        :return: 对齐后的时间轴和音高
        """
        try:
            method = alignment.get('method', 'uniform')
            
            if method == 'asr_based':
                # 基于ASR的精确对齐
                user_start = alignment['user_start_time']
                user_end = alignment['user_end_time']
                scaling_factor = alignment['scaling_factor']
                
                # 提取用户语音时间段内的音高
                speech_mask = (user_times >= user_start) & (user_times <= user_end)
                speech_times = user_times[speech_mask]
                speech_pitch = user_pitch[speech_mask]
                
                if len(speech_times) > 0:
                    # 将用户语音时间映射到TTS时间轴（0到tts_duration）
                    normalized_times = (speech_times - user_start) / (user_end - user_start) * tts_duration
                    return normalized_times, speech_pitch
            
            elif method == 'vad_based':
                # 基于VAD的对齐
                user_start = alignment['user_start_time']
                user_end = alignment['user_end_time']
                
                # 提取语音时间段
                speech_mask = (user_times >= user_start) & (user_times <= user_end)
                speech_times = user_times[speech_mask]
                speech_pitch = user_pitch[speech_mask]
                
                if len(speech_times) > 0:
                    # 线性映射到TTS时间轴
                    normalized_times = (speech_times - user_start) / (user_end - user_start) * tts_duration
                    return normalized_times, speech_pitch
            
            elif method == 'duration_based':
                # 基于总时长的简单对齐
                max_user_time = user_times[-1] if len(user_times) > 0 else tts_duration
                # 线性缩放到TTS时长
                scaled_times = user_times * (tts_duration / max_user_time)
                return scaled_times, user_pitch
            
            # 默认：均匀分布对齐
            if len(user_times) > 0:
                # 简单线性缩放
                max_user_time = user_times[-1]
                if max_user_time > 0:
                    scaled_times = user_times * (tts_duration / max_user_time)
                    return scaled_times, user_pitch
            
            return user_times, user_pitch
            
        except Exception as e:
            print(f"❌ 用户时间轴对齐失败: {e}")
            return user_times, user_pitch
    
    def _interpolate_pitch_to_timeline(self, source_times: np.ndarray, source_pitch: np.ndarray, 
                                     target_times: np.ndarray) -> np.ndarray:
        """
        将音高数据插值到目标时间轴
        :param source_times: 源时间轴
        :param source_pitch: 源音高值
        :param target_times: 目标时间轴
        :return: 插值后的音高值
        """
        try:
            if len(source_times) == 0 or len(source_pitch) == 0:
                return np.full(len(target_times), np.nan)
            
            # 过滤有效的音高值
            valid_mask = ~np.isnan(source_pitch) & (source_pitch > 0)
            if np.sum(valid_mask) < 2:
                return np.full(len(target_times), np.nan)
            
            valid_times = source_times[valid_mask]
            valid_pitch = source_pitch[valid_mask]
            
            # 创建插值函数
            f = interp1d(valid_times, valid_pitch, kind='linear',
                        bounds_error=False, fill_value=np.nan)
            
            # 插值到目标时间轴
            interpolated_pitch = f(target_times)
            
            return interpolated_pitch
            
        except Exception as e:
            print(f"❌ 音高插值失败: {e}")
            return np.full(len(target_times), np.nan)


def test_enhanced_alignment():
    """测试增强的音高对齐功能"""
    print("=== 测试增强的音高对齐功能 ===")
    
    aligner = EnhancedPitchAligner()
    
    # 如果有测试音频文件
    test_tts_audio = "temp/test_tts.wav"
    test_user_audio = "temp/test_user.wav"
    test_text = "你好世界"
    
    if os.path.exists(test_tts_audio) and os.path.exists(test_user_audio):
        print(f"测试文件: TTS={test_tts_audio}, User={test_user_audio}")
        
        # 测试TTS时长检测
        tts_duration = aligner.get_tts_audio_duration(test_tts_audio, test_text)
        print(f"TTS有效时长: {tts_duration:.3f}s")
        
        # 测试用户录音质量验证
        quality_result = aligner.validate_user_audio_quality(test_user_audio)
        print(f"用户录音质量: {quality_result}")
        
        # 测试ASR对齐
        alignment_result = aligner.align_user_audio_with_tts(
            test_user_audio, test_tts_audio, test_text
        )
        print(f"ASR对齐结果: {alignment_result.get('success', False)}")
        
    else:
        print("未找到测试音频文件，跳过测试")


if __name__ == "__main__":
    test_enhanced_alignment()
