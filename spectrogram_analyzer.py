# -*- coding: utf-8 -*-
"""
频谱图分析模块 - 频谱镜子核心功能
用于可视化发音特征，帮助用户区分送气/不送气音（如 zhi/chi）
"""
import librosa
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非GUI后端
import matplotlib.pyplot as plt
from scipy import signal
import os
import json
from typing import Tuple, Dict, Optional, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpectrogramAnalyzer:
    """频谱图分析器"""
    
    # 默认参数
    SAMPLE_RATE = 16000      # 采样率
    N_FFT = 512              # FFT窗口大小
    HOP_LENGTH = 128         # 帧移
    F_MIN = 80               # 最低频率
    F_MAX = 8000             # 最高频率
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        logger.info(f"频谱分析器初始化完成，采样率: {sample_rate}Hz")
    
    def generate_spectrogram(self, audio_path: str, output_image_path: Optional[str] = None) -> Dict:
        """
        生成完整的频谱图
        
        参数:
            audio_path: 音频文件路径
            output_image_path: 可选，保存图像的路径
        
        返回:
            包含频谱图数据的字典
        """
        try:
            # 加载音频
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            logger.info(f"加载音频: {audio_path}, 时长: {len(y)/sr:.2f}秒")
            
            # 生成STFT（短时傅里叶变换）
            D = librosa.stft(y, n_fft=self.N_FFT, hop_length=self.HOP_LENGTH)
            
            # 转换为分贝刻度
            S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
            
            # 时间和频率轴
            times = librosa.frames_to_time(
                range(S_db.shape[1]), 
                sr=sr, 
                hop_length=self.HOP_LENGTH
            )
            frequencies = librosa.fft_frequencies(sr=sr, n_fft=self.N_FFT)
            
            # 可视化并保存
            if output_image_path:
                self._save_spectrogram_image(S_db, sr, output_image_path)
            
            return {
                'success': True,
                'spectrogram': S_db.tolist(),
                'times': times.tolist(),
                'frequencies': frequencies.tolist(),
                'duration': float(len(y) / sr),
                'sample_rate': sr
            }
        
        except Exception as e:
            logger.error(f"生成频谱图失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_spectrogram_image(self, S_db, sr, output_path):
        """保存频谱图为图片"""
        plt.figure(figsize=(12, 6))
        librosa.display.specshow(
            S_db, 
            sr=sr, 
            hop_length=self.HOP_LENGTH,
            x_axis='time', 
            y_axis='hz',
            cmap='hot'
        )
        plt.colorbar(format='%+2.0f dB')
        plt.title('语音频谱图', fontsize=16, fontproperties='SimHei')
        plt.xlabel('时间 (秒)', fontproperties='SimHei')
        plt.ylabel('频率 (Hz)', fontproperties='SimHei')
        plt.ylim([0, 8000])
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"频谱图已保存: {output_path}")
    
    def detect_vot(self, audio_path: str, threshold_db: float = -40, 
                   min_duration_ms: float = 20) -> Dict:
        """
        自动检测VOT（Voice Onset Time，送气持续时间）
        
        参数:
            audio_path: 音频路径
            threshold_db: 能量阈值（dB）
            min_duration_ms: 最小持续时间（毫秒）
        
        返回:
            包含VOT检测结果的字典
        """
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # 计算短时能量
            frame_length = int(0.01 * sr)  # 10ms帧
            hop_length_energy = frame_length // 2
            
            energy = np.array([
                np.sum(y[i:i+frame_length]**2) 
                for i in range(0, len(y)-frame_length, hop_length_energy)
            ])
            
            # 转换为dB
            energy_db = 10 * np.log10(energy + 1e-10)
            
            # 找到第一个超过阈值的点（爆破开始）
            burst_frames = np.where(energy_db > threshold_db)[0]
            if len(burst_frames) == 0:
                return {
                    'success': False,
                    'error': '未检测到有效音频信号'
                }
            
            burst_start = burst_frames[0]
            
            # 找到能量稳定增长的点（浊音开始）
            peak_energy = np.max(energy_db[burst_start:burst_start+100]) if len(energy_db) > burst_start+100 else np.max(energy_db[burst_start:])
            voice_threshold = peak_energy - 10
            voice_frames = np.where(energy_db[burst_start:] > voice_threshold)[0]
            
            if len(voice_frames) == 0:
                return {
                    'success': False,
                    'error': '未检测到浊音开始点'
                }
            
            voice_start = burst_start + voice_frames[0]
            
            # 计算VOT（毫秒）
            vot_frames = voice_start - burst_start
            vot_ms = vot_frames * hop_length_energy / sr * 1000
            
            # 计算时间点
            burst_time = burst_start * hop_length_energy / sr
            voice_time = voice_start * hop_length_energy / sr
            
            return {
                'success': True,
                'vot_ms': float(vot_ms),
                'burst_start_time': float(burst_time),
                'voice_start_time': float(voice_time),
                'burst_start_frame': int(burst_start),
                'voice_start_frame': int(voice_start)
            }
        
        except Exception as e:
            logger.error(f"VOT检测失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def quantify_aspiration(self, audio_path: str, vot_region: Optional[Tuple[int, int]] = None) -> Dict:
        """
        量化送气段的强度和特征
        
        参数:
            audio_path: 音频路径
            vot_region: 可选，VOT区域的样本索引范围 (start, end)
        
        返回:
            送气强度评分和详细特征
        """
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # 如果没有指定VOT区域，自动检测
            if vot_region is None:
                vot_result = self.detect_vot(audio_path)
                if not vot_result['success']:
                    return vot_result
                
                # 转换为样本索引
                frame_samples = int(0.01 * sr)
                hop = frame_samples // 2
                start_sample = int(vot_result['burst_start_frame'] * hop)
                end_sample = int(vot_result['voice_start_frame'] * hop)
            else:
                start_sample, end_sample = vot_region
            
            # 提取送气段
            aspiration_segment = y[start_sample:end_sample]
            
            if len(aspiration_segment) < 100:  # 太短
                return {
                    'success': False,
                    'error': '送气段过短，无法分析'
                }
            
            # 特征1：持续时间
            duration_ms = len(aspiration_segment) / sr * 1000
            
            # 特征2：平均能量
            energy = np.mean(aspiration_segment**2)
            energy_db = 10 * np.log10(energy + 1e-10)
            
            # 特征3：高频能量占比
            D = librosa.stft(aspiration_segment, n_fft=512)
            power_spectrum = np.abs(D)**2
            freqs = librosa.fft_frequencies(sr=sr, n_fft=512)
            
            high_freq_mask = freqs > 3000
            high_freq_ratio = (np.sum(power_spectrum[high_freq_mask, :]) / 
                              (np.sum(power_spectrum) + 1e-10))
            
            # 特征4：频谱平坦度（噪音特征）
            spectral_flatness = np.mean(librosa.feature.spectral_flatness(y=aspiration_segment))
            
            # 综合评分（经验公式，0-100分）
            duration_score = min(duration_ms / 100 * 100, 100)
            energy_score = min((energy_db + 60) / 30 * 100, 100)
            high_freq_score = high_freq_ratio * 100
            flatness_score = float(spectral_flatness) * 100
            
            aspiration_score = (
                duration_score * 0.4 + 
                energy_score * 0.3 + 
                high_freq_score * 0.2 + 
                flatness_score * 0.1
            )
            
            return {
                'success': True,
                'aspiration_score': float(aspiration_score),
                'duration_ms': float(duration_ms),
                'energy_db': float(energy_db),
                'high_freq_ratio': float(high_freq_ratio),
                'spectral_flatness': float(spectral_flatness),
                'duration_score': float(duration_score),
                'energy_score': float(energy_score),
                'high_freq_score': float(high_freq_score)
            }
        
        except Exception as e:
            logger.error(f"送气强度量化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def classify_zhi_chi(self, audio_path: str) -> Dict:
        """
        自动分类 zhi（不送气）vs chi（送气）
        
        参数:
            audio_path: 音频路径
        
        返回:
            分类结果和详细分析
        """
        try:
            # 检测VOT
            vot_result = self.detect_vot(audio_path)
            if not vot_result['success']:
                return vot_result
            
            vot_ms = vot_result['vot_ms']
            
            # 量化送气强度
            aspiration_result = self.quantify_aspiration(audio_path)
            if not aspiration_result['success']:
                return aspiration_result
            
            aspiration_score = aspiration_result['aspiration_score']
            high_freq_ratio = aspiration_result['high_freq_ratio']
            
            # 分类规则（基于标准普通话数据）
            zhi_score = 0
            chi_score = 0
            
            # VOT维度（最重要）
            if vot_ms < 30:
                zhi_score += 3
            elif vot_ms > 60:
                chi_score += 3
            else:
                ratio = (vot_ms - 30) / 30
                chi_score += ratio * 2
                zhi_score += (1 - ratio) * 2
            
            # 送气强度维度
            if aspiration_score < 40:
                zhi_score += 2
            elif aspiration_score > 60:
                chi_score += 2
            else:
                ratio = (aspiration_score - 40) / 20
                chi_score += ratio
                zhi_score += (1 - ratio)
            
            # 高频能量维度
            if high_freq_ratio > 0.3:
                chi_score += 1
            else:
                zhi_score += 1
            
            # 归一化置信度
            total = zhi_score + chi_score
            zhi_confidence = zhi_score / total
            chi_confidence = chi_score / total
            
            if chi_confidence > zhi_confidence:
                prediction = 'chi'
                confidence = chi_confidence
            else:
                prediction = 'zhi'
                confidence = zhi_confidence
            
            # 生成反馈建议
            feedback = self._generate_feedback(
                prediction, 
                vot_ms, 
                aspiration_score,
                chi_confidence,
                zhi_confidence
            )
            
            return {
                'success': True,
                'prediction': prediction,
                'confidence': float(confidence),
                'vot_ms': float(vot_ms),
                'aspiration_score': float(aspiration_score),
                'zhi_confidence': float(zhi_confidence),
                'chi_confidence': float(chi_confidence),
                'feedback': feedback
            }
        
        except Exception as e:
            logger.error(f"zhi/chi分类失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_feedback(self, prediction: str, vot_ms: float, 
                          aspiration_score: float, chi_conf: float, zhi_conf: float) -> str:
        """生成改进建议"""
        feedback = []
        
        if prediction == 'chi':
            feedback.append(f"✓ 识别为【送气音 chi】，置信度 {chi_conf*100:.1f}%")
            if vot_ms < 60:
                feedback.append("💡 送气时长偏短，尝试更用力地吹气")
            if aspiration_score < 60:
                feedback.append("💡 送气强度可以再强一些")
        else:
            feedback.append(f"✓ 识别为【不送气音 zhi】，置信度 {zhi_conf*100:.1f}%")
            if vot_ms > 30:
                feedback.append("💡 有轻微送气，尝试更轻柔地发音")
            if aspiration_score > 40:
                feedback.append("💡 放松，不要吹气")
        
        # 如果两者接近，给出提示
        if abs(chi_conf - zhi_conf) < 0.2:
            feedback.append("⚠️ 发音特征不够明显，请加强对比")
        
        return " | ".join(feedback)
    
    def analyze_audio(self, audio_path: str, target_phoneme: Optional[str] = None) -> Dict:
        """
        完整音频分析（频谱镜子核心函数）
        
        参数:
            audio_path: 音频路径
            target_phoneme: 目标音素（'zhi'或'chi'），用于评分
        
        返回:
            完整的分析结果
        """
        try:
            # 生成频谱图数据
            spec_result = self.generate_spectrogram(audio_path)
            if not spec_result['success']:
                return spec_result
            
            # 分类
            classify_result = self.classify_zhi_chi(audio_path)
            if not classify_result['success']:
                return classify_result
            
            # 如果指定了目标音素，计算准确性评分
            score = None
            grade = None
            if target_phoneme:
                score = self._calculate_score(
                    classify_result['prediction'],
                    target_phoneme,
                    classify_result['vot_ms'],
                    classify_result['aspiration_score']
                )
                grade = self._get_grade(score)
            
            return {
                'success': True,
                'spectrogram_data': {
                    'spec': spec_result['spectrogram'],
                    'times': spec_result['times'],
                    'frequencies': spec_result['frequencies']
                },
                'classification': {
                    'prediction': classify_result['prediction'],
                    'confidence': classify_result['confidence'],
                    'zhi_confidence': classify_result['zhi_confidence'],
                    'chi_confidence': classify_result['chi_confidence']
                },
                'features': {
                    'vot_ms': classify_result['vot_ms'],
                    'aspiration_score': classify_result['aspiration_score']
                },
                'feedback': classify_result['feedback'],
                'score': score,
                'grade': grade,
                'target_phoneme': target_phoneme
            }
        
        except Exception as e:
            logger.error(f"完整分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_score(self, prediction: str, target: str, 
                        vot_ms: float, aspiration_score: float) -> float:
        """计算评分（0-100）"""
        score = 0
        
        # 分类正确性（40分）
        if prediction == target:
            score += 40
        
        # VOT准确性（30分）
        target_vot = 20 if target == 'zhi' else 80
        vot_error = abs(vot_ms - target_vot)
        score += max(0, 30 - vot_error / 2)
        
        # 送气强度（30分）
        target_aspiration = 30 if target == 'zhi' else 75
        asp_error = abs(aspiration_score - target_aspiration)
        score += max(0, 30 - asp_error / 5)
        
        return min(100, max(0, score))
    
    def _get_grade(self, score: float) -> str:
        """获取等级"""
        if score >= 90:
            return 'S'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'


# 全局实例
_analyzer_instance = None

def get_analyzer(sample_rate=16000) -> SpectrogramAnalyzer:
    """获取频谱分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SpectrogramAnalyzer(sample_rate)
    return _analyzer_instance


if __name__ == '__main__':
    # 测试代码
    analyzer = SpectrogramAnalyzer()
    test_audio = 'test_audio.wav'
    
    if os.path.exists(test_audio):
        print("=" * 50)
        print("测试频谱图生成...")
        result = analyzer.generate_spectrogram(test_audio, 'test_spec.png')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 50)
        print("测试完整分析...")
        analysis = analyzer.analyze_audio(test_audio, target_phoneme='chi')
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    else:
        print(f"测试音频文件不存在: {test_audio}")

