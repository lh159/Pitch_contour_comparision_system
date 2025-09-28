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

try:
    from fun_asr_module import FunASRProcessor
    from visualization import PitchVisualizationWithFunASR
    FUN_ASR_AVAILABLE = True
except ImportError:
    FUN_ASR_AVAILABLE = False
    print("警告: Fun-ASR模块未可用，将使用标准可视化方法")

try:
    from enhanced_pitch_alignment import EnhancedPitchAligner
    ENHANCED_ALIGNMENT_AVAILABLE = True
except ImportError:
    ENHANCED_ALIGNMENT_AVAILABLE = False
    print("警告: 增强音高对齐模块未可用，将使用标准对齐方法")

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
    
    def _aggressive_audio_enhancement(self, sound: 'parselmouth.Sound') -> 'parselmouth.Sound':
        """
        激进的音频增强，用于处理极低质量的手机录音
        :param sound: 输入音频
        :return: 激进增强后的音频
        """
        try:
            enhanced = sound.copy()
            values = enhanced.values[0]
            
            # 1. 更强的预加重
            preemph_coeff = 0.95  # 更强的预加重
            for i in range(1, len(values)):
                values[i] = values[i] - preemph_coeff * values[i-1]
            
            # 2. 动态范围压缩 (压缩器)
            # 计算短时能量
            frame_size = int(enhanced.sampling_frequency * 0.025)  # 25ms窗口
            hop_size = frame_size // 2
            
            for i in range(0, len(values) - frame_size, hop_size):
                frame = values[i:i+frame_size]
                rms = np.sqrt(np.mean(frame**2))
                
                if rms > 0:
                    # 压缩器：强信号压缩，弱信号放大
                    threshold = 0.1
                    ratio = 4.0  # 4:1压缩比
                    
                    if rms > threshold:
                        # 压缩强信号
                        compressed_rms = threshold + (rms - threshold) / ratio
                    else:
                        # 放大弱信号
                        compressed_rms = rms * 2.0
                    
                    gain = compressed_rms / rms
                    values[i:i+frame_size] *= gain
            
            # 3. 高通滤波去除低频噪音
            # 简单的高通滤波器（去除50Hz以下）
            sampling_rate = enhanced.sampling_frequency
            cutoff = 50.0  # Hz
            
            # 一阶高通滤波器系数
            rc = 1.0 / (2 * np.pi * cutoff)
            dt = 1.0 / sampling_rate
            alpha = rc / (rc + dt)
            
            # 应用高通滤波
            filtered_values = np.zeros_like(values)
            filtered_values[0] = values[0]
            for i in range(1, len(values)):
                filtered_values[i] = alpha * (filtered_values[i-1] + values[i] - values[i-1])
            
            # 4. 自动增益控制
            target_rms = 0.15
            current_rms = np.sqrt(np.mean(filtered_values**2))
            if current_rms > 0:
                auto_gain = min(target_rms / current_rms, 8.0)  # 最大放大8倍
                filtered_values *= auto_gain
            
            # 5. 软限幅防止削波
            max_val = np.max(np.abs(filtered_values))
            if max_val > 0.9:
                # 软限幅
                filtered_values = np.tanh(filtered_values * 0.9 / max_val) * 0.9
            
            enhanced_sound = parselmouth.Sound(
                filtered_values,
                sampling_frequency=enhanced.sampling_frequency
            )
            return enhanced_sound
            
        except Exception as e:
            print(f"激进音频增强失败: {e}")
            return sound
    
    def _load_audio_with_format_detection(self, audio_path: str) -> 'parselmouth.Sound':
        """
        带格式检测的音频加载，处理WebM等格式问题
        :param audio_path: 音频文件路径
        :return: parselmouth Sound对象
        """
        import os
        import subprocess
        
        try:
            # 首先尝试直接加载
            return parselmouth.Sound(audio_path)
        except Exception as e:
            print(f"直接加载失败: {e}，尝试格式检测和转换...")
            
            # 检查文件头确定实际格式
            actual_format = None
            try:
                with open(audio_path, 'rb') as f:
                    header = f.read(16)
                    if header[:4] == b'\x1a\x45\xdf\xa3':  # WebM/Matroska文件头
                        actual_format = 'webm'
                        print("⚠️ 检测到WebM格式文件，但扩展名可能不正确")
                    elif header[:4] == b'ftyp':  # MP4文件头
                        actual_format = 'mp4'
                    elif header[:2] == b'\xff\xfb' or header[:2] == b'\xff\xf3':  # MP3文件头
                        actual_format = 'mp3'
            except Exception as header_e:
                print(f"文件头检测失败: {header_e}")
            
            if actual_format:
                # 生成临时转换文件
                temp_wav_path = audio_path.replace('.wav', '_temp_converted.wav')
                
                try:
                    # 使用ffmpeg转换
                    if actual_format == 'webm':
                        ffmpeg_cmd = [
                            'ffmpeg', '-f', 'webm', '-i', audio_path,
                            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                            '-y', temp_wav_path
                        ]
                    elif actual_format == 'mp4':
                        ffmpeg_cmd = [
                            'ffmpeg', '-f', 'mp4', '-i', audio_path,
                            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                            '-y', temp_wav_path
                        ]
                    elif actual_format == 'mp3':
                        ffmpeg_cmd = [
                            'ffmpeg', '-f', 'mp3', '-i', audio_path,
                            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                            '-y', temp_wav_path
                        ]
                    
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and os.path.exists(temp_wav_path):
                        print(f"✅ 格式转换成功: {actual_format} -> WAV")
                        try:
                            # 加载转换后的文件
                            sound = parselmouth.Sound(temp_wav_path)
                            
                            # 清理临时文件
                            if os.path.exists(temp_wav_path):
                                os.remove(temp_wav_path)
                            
                            return sound
                        except Exception as load_e:
                            print(f"转换后文件加载失败: {load_e}")
                            if os.path.exists(temp_wav_path):
                                os.remove(temp_wav_path)
                    else:
                        print(f"ffmpeg转换失败: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print("ffmpeg转换超时")
                except Exception as conv_e:
                    print(f"转换过程出错: {conv_e}")
            
            # 如果所有转换尝试都失败，重新抛出原始异常
            raise e
    
    def extract_pitch(self, audio_path: str) -> dict:
        """
        从音频文件中提取音高曲线
        :param audio_path: 音频文件路径
        :return: 包含音高数据的字典
        """
        try:
            # 加载音频
            if isinstance(audio_path, str):
                # 🔧 检查文件格式，处理WebM伪装成WAV的问题
                snd = self._load_audio_with_format_detection(audio_path)
            else:
                # 如果是Sound对象直接使用
                snd = audio_path
            
            # 🔧 音频预处理：归一化和质量增强
            snd = self._normalize_audio_amplitude(snd)
            snd = self._enhance_audio_quality(snd)
            
            # 🎯 优化手机录音的音高提取参数
            # 使用更宽容的参数设置，适应手机录音特点
            pitch = snd.to_pitch(
                pitch_floor=self.min_freq,
                pitch_ceiling=self.max_freq,
                time_step=self.time_step,
                very_accurate=False,  # 禁用极高精度模式，提高容错性
                max_number_of_candidates=15,  # 增加候选音高数量
                silence_threshold=0.03,  # 降低静音阈值
                voicing_threshold=0.45,  # 降低有声检测阈值（默认0.5）
                octave_cost=0.01,  # 降低八度跳跃惩罚
                octave_jump_cost=0.35,  # 降低八度跳跃成本
                voiced_unvoiced_cost=0.14  # 降低有声/无声切换成本
            )
            
            # 获取音高值和时间轴
            pitch_values = pitch.selected_array['frequency']
            times = pitch.xs()
            
            # 处理无声段（0Hz -> NaN）
            pitch_values[pitch_values == 0] = np.nan
            
            # 计算初始有效比例
            initial_valid_ratio = np.sum(~np.isnan(pitch_values)) / len(pitch_values) if len(pitch_values) > 0 else 0
            
            # 🎯 如果音高检测效果很差，尝试更激进的音频增强
            if initial_valid_ratio < 0.05:
                print(f"⚠️ 初始音高检测效果差({initial_valid_ratio:.1%})，尝试增强音频...")
                
                # 更激进的音频增强
                enhanced_snd = self._aggressive_audio_enhancement(snd)
                
                # 重新提取音高，使用更宽松的参数
                retry_pitch = enhanced_snd.to_pitch(
                    pitch_floor=max(50, self.min_freq - 30),  # 进一步降低音高下限
                    pitch_ceiling=min(800, self.max_freq + 100),  # 提高音高上限
                    time_step=self.time_step * 0.8,  # 增加时间分辨率
                    very_accurate=False,
                    max_number_of_candidates=20,
                    silence_threshold=0.02,  # 更低的静音阈值
                    voicing_threshold=0.35,  # 更低的有声检测阈值
                    octave_cost=0.005,
                    octave_jump_cost=0.25,
                    voiced_unvoiced_cost=0.1
                )
                
                retry_pitch_values = retry_pitch.selected_array['frequency']
                retry_pitch_values[retry_pitch_values == 0] = np.nan
                retry_valid_ratio = np.sum(~np.isnan(retry_pitch_values)) / len(retry_pitch_values) if len(retry_pitch_values) > 0 else 0
                
                # 如果重试效果更好，使用重试结果
                if retry_valid_ratio > initial_valid_ratio:
                    print(f"✓ 音频增强成功，有效比例从{initial_valid_ratio:.1%}提升到{retry_valid_ratio:.1%}")
                    pitch_values = retry_pitch_values
                    times = retry_pitch.xs()
                    initial_valid_ratio = retry_valid_ratio
            
            # 🎯 保留原始音高曲线，不进行平滑处理
            # 让曲线反映归一化后的真实语音特征
            
            return {
                'times': times,
                'pitch_values': pitch_values,
                'smooth_pitch': pitch_values,  # 使用原始值，保持接口兼容性
                'duration': times[-1] if len(times) > 0 else 0,
                'valid_ratio': initial_valid_ratio
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
        智能音高基线对齐：基于中文声调特征的优化对齐算法
        :param standard: 标准音高曲线
        :param user: 用户音高曲线  
        :return: 对齐后的 (标准音高, 用户音高)
        """
        try:
            # 过滤有效值
            std_valid = standard[~np.isnan(standard)]
            user_valid = user[~np.isnan(user)]
            
            if len(std_valid) < 5 or len(user_valid) < 5:
                return standard, user
            
            # 🎯 使用统计分析确定基线和变化范围
            std_stats = self._calculate_pitch_statistics(std_valid)
            user_stats = self._calculate_pitch_statistics(user_valid)
            
            # 计算基线差异 - 使用多种统计量的综合评估
            baseline_diff = user_stats['median'] - std_stats['median']
            mean_diff = user_stats['mean'] - std_stats['mean']
            
            # 🎵 分析音高变化幅度 - 用于保留声调特征
            std_range = std_stats['p75'] - std_stats['p25']  # 四分位距
            user_range = user_stats['p75'] - user_stats['p25']
            
            # 🔍 智能阈值：基于音高范围动态调整
            adaptive_threshold = max(30, min(80, std_range * 0.4))
            
            if abs(baseline_diff) > adaptive_threshold:
                # 🎶 声调感知的对齐策略
                scale_factor = self._calculate_optimal_scale_factor(
                    std_stats, user_stats, baseline_diff
                )
                
                # 📊 相对音高对齐：保持音调变化比例
                if abs(baseline_diff) > abs(mean_diff) * 1.5:
                    # 存在明显系统性偏差（如性别差异）
                    aligned_user = self._apply_relative_alignment(
                        user, std_stats, user_stats, scale_factor
                    )
                    aligned_standard = standard
                    
                    print(f"🎵 智能基线对齐: 差异{baseline_diff:.1f}Hz，"
                          f"缩放因子{scale_factor:.3f}，保持声调特征")
                else:
                    # 轻微调整，主要保持原有特征
                    adjustment = baseline_diff * 0.5  # 更保守的调整
                    aligned_user = user - adjustment
                    aligned_standard = standard
                    
                    print(f"🎶 轻度基线调整: {adjustment:.1f}Hz")
                
                return aligned_standard, aligned_user
            else:
                # 差异在可接受范围内，保持原样
                return standard, user
                
        except Exception as e:
            print(f"智能音高基线对齐失败: {e}")
            return standard, user
    
    def _calculate_pitch_statistics(self, pitch_values: np.ndarray) -> dict:
        """计算音高的详细统计信息"""
        return {
            'mean': np.mean(pitch_values),
            'median': np.median(pitch_values),
            'std': np.std(pitch_values),
            'p25': np.percentile(pitch_values, 25),
            'p75': np.percentile(pitch_values, 75),
            'min': np.min(pitch_values),
            'max': np.max(pitch_values),
            'range': np.max(pitch_values) - np.min(pitch_values)
        }
    
    def _calculate_optimal_scale_factor(self, std_stats: dict, user_stats: dict, 
                                      baseline_diff: float) -> float:
        """计算最优缩放因子，平衡基线对齐和声调保持"""
        # 基于音高范围的智能缩放
        std_range = std_stats['range']
        user_range = user_stats['range']
        
        if std_range > 0 and user_range > 0:
            # 考虑音高范围比例
            range_ratio = user_range / std_range
            # 基线差异的相对大小
            relative_diff = abs(baseline_diff) / std_range
            
            # 智能缩放：差异越大，调整越保守
            if relative_diff > 0.5:  # 大差异
                return 0.3 + 0.2 * (1 / (1 + relative_diff))
            else:  # 小差异
                return 0.6 + 0.3 * (1 - relative_diff)
        else:
            return 0.5  # 默认中等调整
    
    def _apply_relative_alignment(self, user_pitch: np.ndarray, std_stats: dict, 
                                user_stats: dict, scale_factor: float) -> np.ndarray:
        """应用相对音高对齐，保持声调变化比例"""
        # 计算用户音高相对于其基线的偏差
        user_baseline = user_stats['median']
        relative_pitch = user_pitch - user_baseline
        
        # 目标基线
        target_baseline = std_stats['median']
        
        # 应用缩放和平移
        aligned_pitch = target_baseline + relative_pitch * scale_factor
        
        return aligned_pitch
    
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
        
        # 集成Fun-ASR功能
        self.fun_asr_processor = None
        self.use_fun_asr = FUN_ASR_AVAILABLE
        
        if self.use_fun_asr:
            try:
                self.fun_asr_processor = FunASRProcessor()
                print("✓ Fun-ASR时间戳功能已启用")
            except Exception as e:
                print(f"⚠️ Fun-ASR功能初始化失败: {e}")
                self.use_fun_asr = False
        
        # 🚀 集成增强音高对齐功能
        self.enhanced_aligner = None
        self.use_enhanced_alignment = ENHANCED_ALIGNMENT_AVAILABLE
        
        if self.use_enhanced_alignment:
            try:
                self.enhanced_aligner = EnhancedPitchAligner()
                print("✓ 增强音高对齐功能已启用")
            except Exception as e:
                print(f"⚠️ 增强音高对齐功能初始化失败: {e}")
                self.use_enhanced_alignment = False
    
    def compare_pitch_curves(self, standard_audio: str, user_audio: str, 
                           expected_text: str = None, enable_text_alignment: bool = True) -> dict:
        """
        比较两个音频的音高曲线 - 增强版本
        :param standard_audio: 标准发音音频路径
        :param user_audio: 用户发音音频路径
        :param expected_text: 期望的文本（用于文本对齐）
        :param enable_text_alignment: 是否启用文本对齐功能
        :return: 比较结果
        """
        vad_result = None
        actual_standard_audio = standard_audio
        actual_user_audio = user_audio
        enhanced_alignment_result = None
        
        # 🚀 使用增强音高对齐（如果可用）
        if self.use_enhanced_alignment and self.enhanced_aligner and expected_text:
            print("🎯 执行增强音高对齐分析...")
            
            try:
                # 1. 验证用户录音质量
                user_quality = self.enhanced_aligner.validate_user_audio_quality(user_audio)
                if not user_quality['is_valid']:
                    return {
                        'error': f"用户录音质量问题: {user_quality['reason']}",
                        'details': user_quality['details'],
                        'suggestion': '请重新录音，确保清晰发音并避免背景噪音'
                    }
                
                # 2. 获取TTS有效时长
                tts_duration = self.enhanced_aligner.get_tts_audio_duration(standard_audio, expected_text)
                
                # 3. ASR时间轴对齐
                alignment_result = self.enhanced_aligner.align_user_audio_with_tts(
                    user_audio, standard_audio, expected_text
                )
                
                if alignment_result['success']:
                    enhanced_alignment_result = alignment_result
                    print(f"✓ 增强对齐成功，TTS有效时长: {tts_duration:.3f}s")
                else:
                    print(f"⚠️ 增强对齐失败: {alignment_result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"⚠️ 增强对齐处理失败，回退到标准处理: {e}")
        
        # 1. VAD预处理（如果启用且没有使用增强对齐）
        if not enhanced_alignment_result and self.use_vad and self.vad_comparator:
            print("🎯 执行VAD增强预处理...")
            vad_result = self.vad_comparator.align_speech_regions(standard_audio, user_audio)
            
            if vad_result and vad_result.get('success'):
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
                    asr_result = text_alignment_result.get('asr_result', {}) or {}
                    print(f"✓ 文本对齐完成，识别文本: {asr_result.get('text', '无')}")
            else:
                print("⚠️ VAD处理失败，使用原始音频")
        
        # 2. 提取音高
        print("提取标准发音音高...")
        standard_pitch = self.extractor.extract_pitch(actual_standard_audio)
        
        print("提取用户发音音高...")
        user_pitch = self.extractor.extract_pitch(actual_user_audio)
        
        # 检查提取结果 - 放宽手机录音的音高检测要求
        if standard_pitch['valid_ratio'] < 0.05:
            return {'error': '标准发音音高提取失败，可能是音频质量问题'}
        
        # 🔧 手机录音音高检测更宽松的阈值
        user_valid_ratio = user_pitch['valid_ratio']
        if user_valid_ratio < 0.01:  # 进一步降低到0.01
            return {'error': f'用户发音音高提取失败，请检查录音质量（有效音高比例：{user_valid_ratio:.1%}）'}
        
        # 如果音高提取质量较低，给出友好提示但继续处理
        if user_valid_ratio < 0.05:
            print(f"⚠️ 用户录音音高质量较低（{user_valid_ratio:.1%}），但继续处理")
        
        # 3. 对齐音高曲线 - 使用增强对齐或标准对齐
        if enhanced_alignment_result and enhanced_alignment_result['success']:
            print("✂️ 执行增强音高曲线对齐...")
            
            # 使用增强对齐：截断到TTS时长并进行ASR对齐
            tts_duration = enhanced_alignment_result['tts_effective_duration']
            alignment_strategy = enhanced_alignment_result['alignment']
            
            aligned_data = self.enhanced_aligner.truncate_pitch_curves_to_tts_duration(
                standard_pitch, user_pitch, tts_duration, alignment_strategy
            )
            
            if not aligned_data['success']:
                print("⚠️ 增强对齐失败，回退到标准对齐")
                aligned_data = self.aligner.align_pitch_curves(standard_pitch, user_pitch)
                # 增强对齐失败，清除增强对齐结果标记
                enhanced_alignment_result = None
        else:
            print("对齐音高曲线（标准方法）...")
            aligned_data = self.aligner.align_pitch_curves(standard_pitch, user_pitch)
        
        if len(aligned_data['aligned_standard']) == 0:
            return {'error': '音高曲线对齐失败'}
        
        # 4. 计算比较指标
        print("计算比较指标...")
        metrics = self._calculate_metrics(
            aligned_data['aligned_standard'],
            aligned_data['aligned_user']
        )
        
        # 5. 组合结果
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
                'vad_processing': vad_result is not None,
                'enhanced_alignment_enabled': self.use_enhanced_alignment,
                'enhanced_alignment_used': enhanced_alignment_result is not None
            },
            'vad_result': vad_result,
            'enhanced_alignment_result': enhanced_alignment_result,
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
        """
        计算音高变化趋势的一致性 - 针对听障人士优化
        包含方向一致性、幅度相似性和声调模式匹配
        """
        if len(standard) < 3 or len(user) < 3:
            return 0.0
        
        try:
            # 🎯 1. 计算多阶差分，捕捉细微变化
            std_diff1 = np.diff(standard)  # 一阶差分：变化速度
            user_diff1 = np.diff(user)
            
            std_diff2 = np.diff(std_diff1)  # 二阶差分：变化加速度
            user_diff2 = np.diff(user_diff1)
            
            # 🎵 2. 方向一致性分析（权重60%）
            direction_consistency = self._calculate_direction_consistency(
                std_diff1, user_diff1
            )
            
            # 📊 3. 幅度相似性分析（权重25%）
            magnitude_consistency = self._calculate_magnitude_consistency(
                std_diff1, user_diff1
            )
            
            # 🎶 4. 声调模式一致性（权重15%）
            pattern_consistency = self._calculate_tone_pattern_consistency(
                std_diff1, user_diff1, std_diff2, user_diff2
            )
            
            # 🎯 综合评分
            total_consistency = (
                direction_consistency * 0.6 +
                magnitude_consistency * 0.25 +
                pattern_consistency * 0.15
            )
            
            return np.clip(total_consistency, 0.0, 1.0)
            
        except Exception as e:
            print(f"趋势一致性计算失败: {e}")
            return 0.0
    
    def _calculate_direction_consistency(self, std_diff: np.ndarray, 
                                       user_diff: np.ndarray) -> float:
        """计算方向一致性，考虑变化幅度权重"""
        if len(std_diff) == 0:
            return 1.0
        
        # 计算方向符号
        std_signs = np.sign(std_diff)
        user_signs = np.sign(user_diff)
        
        # 变化幅度作为权重
        std_weights = np.abs(std_diff)
        std_weights = std_weights / np.sum(std_weights) if np.sum(std_weights) > 0 else np.ones_like(std_weights)
        
        # 加权方向一致性
        direction_matches = (std_signs == user_signs).astype(float)
        weighted_consistency = np.sum(direction_matches * std_weights)
        
        return weighted_consistency
    
    def _calculate_magnitude_consistency(self, std_diff: np.ndarray, 
                                       user_diff: np.ndarray) -> float:
        """计算变化幅度的相似性"""
        if len(std_diff) == 0:
            return 1.0
        
        # 归一化变化幅度
        std_abs = np.abs(std_diff)
        user_abs = np.abs(user_diff)
        
        # 避免除零
        std_abs_norm = std_abs / (np.max(std_abs) + 1e-6)
        user_abs_norm = user_abs / (np.max(user_abs) + 1e-6)
        
        # 计算幅度相似度
        magnitude_diff = np.abs(std_abs_norm - user_abs_norm)
        magnitude_similarity = np.mean(1.0 - magnitude_diff)
        
        return np.clip(magnitude_similarity, 0.0, 1.0)
    
    def _calculate_tone_pattern_consistency(self, std_diff1: np.ndarray, 
                                          user_diff1: np.ndarray,
                                          std_diff2: np.ndarray, 
                                          user_diff2: np.ndarray) -> float:
        """计算声调模式一致性 - 检测中文声调特征"""
        if len(std_diff2) == 0:
            return 1.0
        
        # 🎵 检测声调模式
        std_pattern = self._identify_tone_pattern(std_diff1, std_diff2)
        user_pattern = self._identify_tone_pattern(user_diff1, user_diff2)
        
        # 计算模式匹配度
        pattern_match = self._compare_tone_patterns(std_pattern, user_pattern)
        
        return pattern_match
    
    def _identify_tone_pattern(self, diff1: np.ndarray, diff2: np.ndarray) -> str:
        """识别音调变化模式"""
        if len(diff1) < 2:
            return 'unknown'
        
        # 分析整体趋势
        total_change = np.sum(diff1)
        monotonic_ratio = np.sum(np.abs(diff1)) / (np.abs(total_change) + 1e-6)
        
        # 分析变化方向的变化（二阶导数）
        direction_changes = np.sum(np.abs(np.diff(np.sign(diff1))))
        
        # 声调模式判断
        if abs(total_change) < np.std(diff1) * 0.5:
            return 'flat'  # 平调（阴平）
        elif total_change > 0 and monotonic_ratio > 0.7:
            return 'rising'  # 升调（阳平）
        elif total_change < 0 and monotonic_ratio > 0.7:
            return 'falling'  # 降调（去声）
        elif direction_changes >= 2:
            return 'dipping'  # 降升调（上声）
        else:
            return 'complex'  # 复杂变化
    
    def _compare_tone_patterns(self, pattern1: str, pattern2: str) -> float:
        """比较两个声调模式的匹配度"""
        if pattern1 == pattern2:
            return 1.0
        
        # 声调相似性矩阵
        similarity_matrix = {
            ('flat', 'flat'): 1.0,
            ('rising', 'rising'): 1.0,
            ('falling', 'falling'): 1.0,
            ('dipping', 'dipping'): 1.0,
            ('flat', 'rising'): 0.3,
            ('flat', 'falling'): 0.3,
            ('rising', 'falling'): 0.2,
            ('dipping', 'complex'): 0.6,
            ('complex', 'complex'): 0.8,
        }
        
        # 对称性
        key = (pattern1, pattern2)
        reverse_key = (pattern2, pattern1)
        
        if key in similarity_matrix:
            return similarity_matrix[key]
        elif reverse_key in similarity_matrix:
            return similarity_matrix[reverse_key]
        else:
            return 0.4  # 默认中等相似度
    
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
    
    def compare_with_fun_asr_visualization(self, standard_audio: str, user_audio: str, 
                                         original_text: str, output_path: str) -> dict:
        """
        使用Fun-ASR进行TTS音频时间戳分析并生成可视化结果
        :param standard_audio: 标准发音音频路径（TTS生成）
        :param user_audio: 用户发音音频路径
        :param original_text: 生成TTS时使用的原始文本
        :param output_path: 可视化结果输出路径
        :return: 完整的比对结果
        """
        try:
            print(f"🎯 开始Fun-ASR增强音高比对分析...")
            print(f"标准音频: {standard_audio}")
            print(f"用户音频: {user_audio}")
            print(f"原始文本: {original_text}")
            
            # 1. 执行标准音高比对
            comparison_result = self.compare_pitch_curves(
                standard_audio, user_audio, original_text, True
            )
            
            if not comparison_result:
                print("❌ 基础音高比对失败")
                return None
            
            # 2. 计算评分
            from scoring_algorithm import ScoringSystem
            scorer = ScoringSystem()
            score_result = scorer.calculate_score(comparison_result.get('metrics', {}), original_text)
            
            # 3. 生成Fun-ASR增强可视化
            if self.use_fun_asr and FUN_ASR_AVAILABLE:
                try:
                    print("📊 正在生成Fun-ASR时间戳可视化...")
                    visualizer = PitchVisualizationWithFunASR()
                    
                    success = visualizer.plot_comparison_with_fun_asr_timestamps(
                        comparison_result=comparison_result,
                        score_result=score_result,
                        output_path=output_path,
                        tts_audio_path=standard_audio,  # TTS音频用于时间戳分析
                        original_text=original_text
                    )
                    
                    if success:
                        print(f"✅ Fun-ASR增强可视化完成: {output_path}")
                    else:
                        print("⚠️ Fun-ASR可视化失败，使用标准可视化")
                        self._fallback_to_standard_visualization(
                            comparison_result, score_result, output_path, original_text
                        )
                        
                except Exception as e:
                    print(f"⚠️ Fun-ASR可视化过程出错: {e}")
                    self._fallback_to_standard_visualization(
                        comparison_result, score_result, output_path, original_text
                    )
            else:
                print("⚠️ Fun-ASR不可用，使用标准可视化")
                self._fallback_to_standard_visualization(
                    comparison_result, score_result, output_path, original_text
                )
            
            # 4. 构建完整结果
            result = {
                'comparison_result': comparison_result,
                'score_result': score_result,
                'visualization_path': output_path,
                'original_text': original_text,
                'fun_asr_enabled': self.use_fun_asr,
                'timestamp': comparison_result.get('timestamp')
            }
            
            print(f"🎉 Fun-ASR增强音高比对分析完成!")
            return result
            
        except Exception as e:
            print(f"❌ Fun-ASR增强音高比对失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fallback_to_standard_visualization(self, comparison_result, score_result, 
                                          output_path, original_text):
        """
        回退到标准可视化方法
        """
        try:
            from visualization import PitchVisualization
            visualizer = PitchVisualization()
            
            text_alignment_data = comparison_result.get('text_alignment_data')
            
            success = visualizer.plot_pitch_comparison(
                comparison_result=comparison_result,
                score_result=score_result,
                output_path=output_path,
                input_text=original_text,
                text_alignment_data=text_alignment_data
            )
            
            if success:
                print(f"✅ 标准可视化完成: {output_path}")
            else:
                print("❌ 标准可视化也失败了")
                
        except Exception as e:
            print(f"❌ 标准可视化回退失败: {e}")


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
