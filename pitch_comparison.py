# -*- coding: utf-8 -*-
"""
音高比对算法模块
实现音高曲线的提取、对齐和比较功能
"""
import numpy as np
import parselmouth
from scipy import stats
from scipy.interpolate import interp1d
from scipy.ndimage import median_filter
from config import Config

try:
    from dtaidistance import dtw
    DTW_AVAILABLE = True
except ImportError:
    DTW_AVAILABLE = False
    print("警告: DTW库未安装，将使用简单线性对齐方法")

try:
    from vad_module import VADComparator
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("警告: VAD模块未可用，将使用传统音高比对方法")

class PitchExtractor:
    """音高提取器"""
    
    def __init__(self):
        self.min_freq = Config.PITCH_MIN_FREQ
        self.max_freq = Config.PITCH_MAX_FREQ
        self.time_step = Config.PITCH_TIME_STEP
    
    def _normalize_audio_amplitude(self, sound: 'parselmouth.Sound') -> 'parselmouth.Sound':
        """
        音频信号振幅归一化
        :param sound: 原始音频信号
        :return: 归一化后的音频信号
        """
        try:
            # 获取音频数据
            values = sound.values[0]  # 获取第一个声道
            
            # 计算RMS (均方根) 能量
            rms = np.sqrt(np.mean(values**2))
            
            if rms > 0:
                # 归一化到目标RMS水平 (约-20dB)
                target_rms = 0.1
                scaling_factor = target_rms / rms
                
                # 应用缩放，但避免过度放大
                scaling_factor = min(scaling_factor, 5.0)  # 最大放大5倍
                normalized_values = values * scaling_factor
                
                # 防止削波 (clipping)
                max_val = np.max(np.abs(normalized_values))
                if max_val > 0.95:
                    normalized_values = normalized_values * (0.95 / max_val)
                
                # 创建新的Sound对象
                normalized_sound = parselmouth.Sound(
                    normalized_values, 
                    sampling_frequency=sound.sampling_frequency
                )
                return normalized_sound
            else:
                return sound
                
        except Exception as e:
            print(f"音频振幅归一化失败: {e}")
            return sound
    
    def _enhance_audio_quality(self, sound: 'parselmouth.Sound') -> 'parselmouth.Sound':
        """
        音频质量增强：降噪和预加重
        :param sound: 输入音频
        :return: 增强后的音频
        """
        try:
            # 1. 预加重滤波 (提升高频，改善音高检测)
            preemphasized = sound.copy()
            values = preemphasized.values[0]
            
            # 应用预加重滤波器 y[n] = x[n] - 0.97*x[n-1]
            preemph_coeff = 0.97
            for i in range(1, len(values)):
                values[i] = values[i] - preemph_coeff * values[i-1]
            
            # 2. 简单的噪声门限 (去除过小的信号)
            # 计算信号的动态范围
            signal_max = np.max(np.abs(values))
            noise_floor = signal_max * 0.01  # 噪声门限设为最大值的1%
            
            # 应用噪声门限
            values[np.abs(values) < noise_floor] *= 0.1
            
            enhanced_sound = parselmouth.Sound(
                values,
                sampling_frequency=sound.sampling_frequency
            )
            return enhanced_sound
            
        except Exception as e:
            print(f"音频质量增强失败: {e}")
            return sound
    
    def extract_pitch(self, audio_path: str) -> dict:
        """
        从音频文件中提取音高曲线
        :param audio_path: 音频文件路径
        :return: 包含音高数据的字典
        """
        try:
            # 加载音频
            if isinstance(audio_path, str):
                snd = parselmouth.Sound(audio_path)
            else:
                # 如果是Sound对象直接使用
                snd = audio_path
            
            # 🔧 音频预处理：归一化和质量增强
            snd = self._normalize_audio_amplitude(snd)
            snd = self._enhance_audio_quality(snd)
            
            # 提取音高
            pitch = snd.to_pitch(
                pitch_floor=self.min_freq,
                pitch_ceiling=self.max_freq,
                time_step=self.time_step
            )
            
            # 获取音高值和时间轴
            pitch_values = pitch.selected_array['frequency']
            times = pitch.xs()
            
            # 处理无声段（0Hz -> NaN）
            pitch_values[pitch_values == 0] = np.nan
            
            # 平滑处理，去除噪声
            smooth_pitch = self._smooth_pitch(pitch_values)
            
            return {
                'times': times,
                'pitch_values': pitch_values,
                'smooth_pitch': smooth_pitch,
                'duration': times[-1] if len(times) > 0 else 0,
                'valid_ratio': np.sum(~np.isnan(pitch_values)) / len(pitch_values) if len(pitch_values) > 0 else 0
            }
            
        except Exception as e:
            print(f"音高提取失败: {e}")
            return {
                'times': np.array([]),
                'pitch_values': np.array([]),
                'smooth_pitch': np.array([]),
                'duration': 0,
                'valid_ratio': 0
            }
    
    def _smooth_pitch(self, pitch_values: np.ndarray, window_size: int = 3) -> np.ndarray:
        """
        平滑音高曲线，去除噪声
        :param pitch_values: 原始音高值
        :param window_size: 平滑窗口大小
        :return: 平滑后的音高值
        """
        if len(pitch_values) == 0:
            return pitch_values
        
        # 对有效值进行中值滤波
        smooth_pitch = pitch_values.copy()
        valid_mask = ~np.isnan(pitch_values)
        
        if np.sum(valid_mask) > window_size:
            # 只对有效部分进行平滑
            valid_indices = np.where(valid_mask)[0]
            valid_values = pitch_values[valid_mask]
            
            # 中值滤波
            smoothed_valid = median_filter(valid_values, size=window_size)
            smooth_pitch[valid_indices] = smoothed_valid
        
        return smooth_pitch

class PitchAligner:
    """音高曲线对齐器"""
    
    def __init__(self):
        self.use_dtw = DTW_AVAILABLE
    
    def align_pitch_curves(self, standard_pitch: dict, user_pitch: dict) -> dict:
        """
        对齐两个音高曲线
        :param standard_pitch: 标准发音的音高数据
        :param user_pitch: 用户发音的音高数据
        :return: 对齐后的音高数据
        """
        
        # 提取有效的音高数据
        std_times = standard_pitch['times']
        std_pitch = standard_pitch['smooth_pitch']
        user_times = user_pitch['times']
        user_pitch_values = user_pitch['smooth_pitch']
        
        if len(std_pitch) == 0 or len(user_pitch_values) == 0:
            return {
                'aligned_standard': np.array([]),
                'aligned_user': np.array([]),
                'aligned_times': np.array([]),
                'alignment_method': 'none'
            }
        
        # 选择对齐方法
        if self.use_dtw and len(std_pitch) > 10 and len(user_pitch_values) > 10:
            return self._dtw_align(std_times, std_pitch, user_times, user_pitch_values)
        else:
            return self._linear_align(std_times, std_pitch, user_times, user_pitch_values)
    
    def _dtw_align(self, std_times: np.ndarray, std_pitch: np.ndarray, 
                   user_times: np.ndarray, user_pitch: np.ndarray) -> dict:
        """使用DTW算法进行时间对齐"""
        
        # 预处理：去除NaN值并插值
        std_clean = self._interpolate_nan(std_pitch)
        user_clean = self._interpolate_nan(user_pitch)
        
        if len(std_clean) == 0 or len(user_clean) == 0:
            return self._linear_align(std_times, std_pitch, user_times, user_pitch)
        
        try:
            # 归一化音高值以提高DTW效果
            std_norm = self._normalize_pitch(std_clean)
            user_norm = self._normalize_pitch(user_clean)
            
            # 执行DTW对齐
            path = dtw.warping_path(std_norm, user_norm)
            
            # 根据对齐路径重新采样
            aligned_length = len(path)
            aligned_times = np.linspace(0, max(std_times[-1], user_times[-1]), aligned_length)
            
            # 提取对齐后的序列
            aligned_standard = np.array([std_clean[i] for i, j in path])
            aligned_user = np.array([user_clean[j] for i, j in path])
            
            # 🎯 应用音高基线对齐
            aligned_standard, aligned_user = self._align_pitch_baseline(aligned_standard, aligned_user)
            
            return {
                'aligned_standard': aligned_standard,
                'aligned_user': aligned_user,
                'aligned_times': aligned_times,
                'alignment_method': 'dtw'
            }
            
        except Exception as e:
            print(f"DTW对齐失败，使用线性对齐: {e}")
            return self._linear_align(std_times, std_pitch, user_times, user_pitch)
    
    def _linear_align(self, std_times: np.ndarray, std_pitch: np.ndarray,
                      user_times: np.ndarray, user_pitch: np.ndarray) -> dict:
        """使用线性插值进行简单对齐"""
        
        # 确定统一的时间轴
        max_duration = max(std_times[-1] if len(std_times) > 0 else 0,
                          user_times[-1] if len(user_times) > 0 else 0)
        
        if max_duration == 0:
            return {
                'aligned_standard': np.array([]),
                'aligned_user': np.array([]),
                'aligned_times': np.array([]),
                'alignment_method': 'linear'
            }
        
        # 创建统一时间轴
        aligned_times = np.linspace(0, max_duration, 
                                   max(len(std_times), len(user_times), 100))
        
        # 插值到统一时间轴
        try:
            aligned_standard = self._interpolate_to_timeline(
                std_times, std_pitch, aligned_times)
            aligned_user = self._interpolate_to_timeline(
                user_times, user_pitch, aligned_times)
            
            # 🎯 应用音高基线对齐
            aligned_standard, aligned_user = self._align_pitch_baseline(aligned_standard, aligned_user)
            
            return {
                'aligned_standard': aligned_standard,
                'aligned_user': aligned_user,
                'aligned_times': aligned_times,
                'alignment_method': 'linear'
            }
        except Exception as e:
            print(f"线性对齐失败: {e}")
            return {
                'aligned_standard': np.array([]),
                'aligned_user': np.array([]),
                'aligned_times': np.array([]),
                'alignment_method': 'failed'
            }
    
    def _interpolate_nan(self, pitch_values: np.ndarray) -> np.ndarray:
        """插值填补NaN值"""
        if len(pitch_values) == 0:
            return pitch_values
        
        # 找到有效值
        valid_mask = ~np.isnan(pitch_values)
        if np.sum(valid_mask) < 2:
            return np.array([])
        
        # 线性插值填补NaN
        x = np.arange(len(pitch_values))
        valid_x = x[valid_mask]
        valid_y = pitch_values[valid_mask]
        
        # 创建插值函数
        f = interp1d(valid_x, valid_y, kind='linear', 
                    bounds_error=False, fill_value='extrapolate')
        
        # 插值
        interpolated = f(x)
        
        return interpolated
    
    def _normalize_pitch(self, pitch_values: np.ndarray) -> np.ndarray:
        """归一化音高值 (用于DTW对齐)"""
        if len(pitch_values) == 0:
            return pitch_values
        
        mean_pitch = np.mean(pitch_values)
        std_pitch = np.std(pitch_values)
        
        if std_pitch == 0:
            return pitch_values - mean_pitch
        
        return (pitch_values - mean_pitch) / std_pitch
    
    def _align_pitch_baseline(self, standard: np.ndarray, user: np.ndarray) -> tuple:
        """
        音高基线对齐：处理不同性别/年龄的基频差异
        :param standard: 标准音高曲线
        :param user: 用户音高曲线  
        :return: 对齐后的 (标准音高, 用户音高)
        """
        try:
            # 过滤有效值
            std_valid = standard[~np.isnan(standard)]
            user_valid = user[~np.isnan(user)]
            
            if len(std_valid) < 3 or len(user_valid) < 3:
                return standard, user
            
            # 计算基线音高 (中位数更稳定)
            std_baseline = np.median(std_valid)
            user_baseline = np.median(user_valid)
            
            # 计算基线差异
            baseline_diff = user_baseline - std_baseline
            
            # 如果差异过大，可能是不同性别，需要调整
            if abs(baseline_diff) > 50:  # 50Hz以上认为是显著差异
                
                # 方法1: 简单平移对齐
                if baseline_diff > 0:
                    # 用户音高偏高，下调用户音高
                    aligned_user = user - baseline_diff * 0.7  # 保留30%的个人特色
                    aligned_standard = standard
                else:
                    # 用户音高偏低，上调用户音高  
                    aligned_user = user - baseline_diff * 0.7
                    aligned_standard = standard
                
                print(f"检测到音高基线差异: {baseline_diff:.1f}Hz，已进行基线对齐")
                return aligned_standard, aligned_user
            else:
                # 差异不大，保持原样
                return standard, user
                
        except Exception as e:
            print(f"音高基线对齐失败: {e}")
            return standard, user
    
    def _interpolate_to_timeline(self, times: np.ndarray, values: np.ndarray, 
                                target_times: np.ndarray) -> np.ndarray:
        """插值到目标时间轴"""
        if len(times) == 0 or len(values) == 0:
            return np.full(len(target_times), np.nan)
        
        # 只使用有效值进行插值
        valid_mask = ~np.isnan(values)
        if np.sum(valid_mask) < 2:
            return np.full(len(target_times), np.nan)
        
        valid_times = times[valid_mask]
        valid_values = values[valid_mask]
        
        # 创建插值函数
        f = interp1d(valid_times, valid_values, kind='linear',
                    bounds_error=False, fill_value=np.nan)
        
        return f(target_times)

class PitchComparator:
    """音高曲线比较器"""
    
    def __init__(self):
        self.extractor = PitchExtractor()
        self.aligner = PitchAligner()
        
        # 集成VAD功能
        self.vad_comparator = None
        self.use_vad = Config.VAD_ENABLED and VAD_AVAILABLE
        
        if self.use_vad:
            try:
                self.vad_comparator = VADComparator()
                print("✓ VAD增强功能已启用")
            except Exception as e:
                print(f"⚠️ VAD功能初始化失败: {e}")
                self.use_vad = False
    
    def compare_pitch_curves(self, standard_audio: str, user_audio: str, 
                           expected_text: str = None, enable_text_alignment: bool = True) -> dict:
        """
        比较两个音频的音高曲线
        :param standard_audio: 标准发音音频路径
        :param user_audio: 用户发音音频路径
        :param expected_text: 期望的文本（用于文本对齐）
        :param enable_text_alignment: 是否启用文本对齐功能
        :return: 比较结果
        """
        vad_result = None
        actual_standard_audio = standard_audio
        actual_user_audio = user_audio
        
        # 1. VAD预处理（如果启用）
        if self.use_vad and self.vad_comparator:
            print("🎯 执行VAD增强预处理...")
            vad_result = self.vad_comparator.align_speech_regions(standard_audio, user_audio)
            
            if vad_result.get('success'):
                actual_standard_audio = vad_result['standard_speech_audio']
                actual_user_audio = vad_result['user_speech_audio']
                print(f"✓ VAD处理完成，对齐质量: {vad_result['alignment_quality']['quality_level']}")
                
                # 1.5 文本对齐（如果启用且提供了期望文本）
                if enable_text_alignment and expected_text and hasattr(self.vad_comparator, 'vad_processor'):
                    print("🔤 执行文本时域对齐...")
                    text_alignment_result = self.vad_comparator.vad_processor.align_text_with_vad(
                        expected_text, user_audio
                    )
                    # 将文本对齐结果合并到VAD结果中
                    vad_result.update(text_alignment_result)
                    print(f"✓ 文本对齐完成，识别文本: {text_alignment_result.get('asr_result', {}).get('text', '无')}")
            else:
                print("⚠️ VAD处理失败，使用原始音频")
        
        # 2. 提取音高
        print("提取标准发音音高...")
        standard_pitch = self.extractor.extract_pitch(actual_standard_audio)
        
        print("提取用户发音音高...")
        user_pitch = self.extractor.extract_pitch(actual_user_audio)
        
        # 检查提取结果
        if standard_pitch['valid_ratio'] < 0.1:
            return {'error': '标准发音音高提取失败，可能是音频质量问题'}
        
        if user_pitch['valid_ratio'] < 0.1:
            return {'error': '用户发音音高提取失败，请检查录音质量'}
        
        # 对齐音高曲线
        print("对齐音高曲线...")
        aligned_data = self.aligner.align_pitch_curves(standard_pitch, user_pitch)
        
        if len(aligned_data['aligned_standard']) == 0:
            return {'error': '音高曲线对齐失败'}
        
        # 计算比较指标
        print("计算比较指标...")
        metrics = self._calculate_metrics(
            aligned_data['aligned_standard'],
            aligned_data['aligned_user']
        )
        
        # 组合结果
        result = {
            'standard_pitch': standard_pitch,
            'user_pitch': user_pitch,
            'aligned_data': aligned_data,
            'metrics': metrics,
            'preprocessing_info': {
                'audio_normalized': True,
                'quality_enhanced': True,
                'pitch_baseline_aligned': True,
                'alignment_method': aligned_data.get('alignment_method', 'unknown'),
                'vad_enabled': self.use_vad,
                'vad_processing': vad_result is not None
            },
            'vad_result': vad_result,
            'processed_audio_paths': {
                'standard': actual_standard_audio,
                'user': actual_user_audio
            },
            'success': True
        }
        
        return result
    
    def _calculate_metrics(self, standard: np.ndarray, user: np.ndarray) -> dict:
        """计算比较指标"""
        
        # 过滤有效值
        valid_mask = ~(np.isnan(standard) | np.isnan(user))
        if np.sum(valid_mask) < 3:
            return {
                'correlation': 0.0,
                'rmse': float('inf'),
                'trend_consistency': 0.0,
                'pitch_range_ratio': 0.0,
                'valid_points': 0
            }
        
        std_valid = standard[valid_mask]
        user_valid = user[valid_mask]
        
        # 1. 皮尔逊相关系数
        try:
            correlation, _ = stats.pearsonr(std_valid, user_valid)
            if np.isnan(correlation):
                correlation = 0.0
        except:
            correlation = 0.0
        
        # 2. 均方根误差 (RMSE)
        try:
            rmse = np.sqrt(np.mean((std_valid - user_valid) ** 2))
            if np.isnan(rmse) or np.isinf(rmse):
                rmse = 1000.0  # 设置一个较大的默认值表示差异很大
        except:
            rmse = 1000.0
        
        # 3. 趋势一致性 (计算变化方向的一致性)
        trend_consistency = self._calculate_trend_consistency(std_valid, user_valid)
        
        # 4. 音高范围比较
        std_range = np.max(std_valid) - np.min(std_valid)
        user_range = np.max(user_valid) - np.min(user_valid)
        
        if std_range > 0:
            pitch_range_ratio = min(user_range / std_range, std_range / user_range)
        else:
            pitch_range_ratio = 1.0 if user_range == 0 else 0.0
        
        # 安全转换，避免NaN和inf
        def safe_float(value):
            if np.isnan(value) or np.isinf(value):
                return 0.0
            return float(value)
        
        return {
            'correlation': safe_float(correlation),
            'rmse': safe_float(rmse),
            'trend_consistency': safe_float(trend_consistency),
            'pitch_range_ratio': safe_float(pitch_range_ratio),
            'valid_points': int(np.sum(valid_mask)),
            'std_mean': safe_float(np.mean(std_valid)),
            'user_mean': safe_float(np.mean(user_valid)),
            'std_std': safe_float(np.std(std_valid)),
            'user_std': safe_float(np.std(user_valid))
        }
    
    def _calculate_trend_consistency(self, standard: np.ndarray, user: np.ndarray) -> float:
        """计算音高变化趋势的一致性"""
        if len(standard) < 2 or len(user) < 2:
            return 0.0
        
        # 计算差分（变化方向）
        std_diff = np.diff(standard)
        user_diff = np.diff(user)
        
        # 计算符号一致性
        same_direction = np.sum(np.sign(std_diff) == np.sign(user_diff))
        total_changes = len(std_diff)
        
        if total_changes == 0:
            return 1.0
        
        return same_direction / total_changes
    
    def calculate_vad_enhanced_score(self, comparison_result: dict) -> dict:
        """
        基于VAD结果计算增强评分
        :param comparison_result: 比较结果
        :return: 增强评分信息
        """
        base_metrics = comparison_result.get('metrics', {})
        vad_result = comparison_result.get('vad_result')
        
        if not vad_result or not vad_result.get('success'):
            return {
                'enhanced_score': base_metrics.get('correlation', 0.0),
                'vad_bonus': 0.0,
                'alignment_quality_bonus': 0.0,
                'total_enhancement': 0.0
            }
        
        # 基础相关性分数
        base_correlation = base_metrics.get('correlation', 0.0)
        
        # VAD质量加成
        alignment_quality = vad_result.get('alignment_quality', {})
        quality_score = alignment_quality.get('overall_score', 0.5)
        
        # 计算VAD加成 (最多增加20%的分数)
        vad_bonus = min(0.2, quality_score * 0.2)
        
        # 语音比例一致性加成 (最多增加10%的分数)
        std_info = vad_result.get('standard_info', {})
        user_info = vad_result.get('user_info', {})
        
        std_ratio = std_info.get('speech_ratio', 0.5)
        user_ratio = user_info.get('speech_ratio', 0.5)
        ratio_diff = abs(std_ratio - user_ratio)
        
        ratio_bonus = max(0, (0.1 - ratio_diff)) if ratio_diff < 0.1 else 0
        
        # 总增强分数
        total_enhancement = vad_bonus + ratio_bonus
        enhanced_score = min(1.0, base_correlation + total_enhancement)
        
        return {
            'enhanced_score': enhanced_score,
            'vad_bonus': vad_bonus,
            'alignment_quality_bonus': ratio_bonus,
            'total_enhancement': total_enhancement,
            'speech_ratio_consistency': 1.0 - ratio_diff if ratio_diff < 1.0 else 0.0
        }

# 使用示例
if __name__ == '__main__':
    from tts_module import TTSManager
    import os
    
    # 创建必要目录
    Config.create_directories()
    
    # 测试比较功能
    comparator = PitchComparator()
    
    # 如果有测试音频文件，可以进行比较
    test_audio = "test_audio.wav"
    if os.path.exists(test_audio):
        # 提取音高
        pitch_data = comparator.extractor.extract_pitch(test_audio)
        print(f"音高提取结果:")
        print(f"  时长: {pitch_data['duration']:.2f} 秒")
        print(f"  有效比例: {pitch_data['valid_ratio']:.2%}")
        print(f"  平均音高: {np.nanmean(pitch_data['pitch_values']):.1f} Hz")
    else:
        print("未找到测试音频文件，跳过测试")
