# -*- coding: utf-8 -*-
"""
中文声调分析模块
专门针对听障人士的音调训练需求，提供精确的声调识别和比对功能
"""
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from config import Config

class ChineseToneAnalyzer:
    """中文声调分析器 - 专为听障人士音调训练优化"""
    
    def __init__(self):
        self.tone_config = Config.CHINESE_TONE_CONFIG
        self.tone_patterns = self.tone_config['tone_patterns']
        self.tone_weights = self.tone_config['tone_weights']
        
        # 声调检测阈值
        self.thresholds = {
            'flat_tolerance': 0.15,      # 平调容差
            'rising_slope': 0.3,         # 升调最小斜率
            'falling_slope': -0.3,       # 降调最大斜率
            'dipping_complexity': 0.4,   # 上声复杂度阈值
            'min_duration': 0.1          # 最小分析时长(秒)
        }
    
    def analyze_pitch_based_tones(self, pitch_values: np.ndarray, 
                                 times: np.ndarray, 
                                 text: str) -> List[int]:
        """
        基于音高曲线分析文本的声调序列
        :param pitch_values: 音高序列
        :param times: 时间序列
        :param text: 中文文本（用于确定分段数量）
        :return: 声调序列 [1,2,3,4,0] 对应 [阴平,阳平,上声,去声,轻声]
        """
        if len(pitch_values) < 5 or len(text.strip()) == 0:
            return [1] * len(text.strip())  # 默认返回阴平
        
        # 过滤有效音高
        valid_mask = ~np.isnan(pitch_values)
        if np.sum(valid_mask) < 3:
            return [1] * len(text.strip())
        
        valid_pitch = pitch_values[valid_mask]
        valid_times = times[valid_mask]
        
        # 音高归一化（相对音高）
        normalized_pitch = self._normalize_pitch_for_tone_analysis(valid_pitch)
        
        # 按字符数分段分析
        char_count = len(text.strip())
        segments = self._segment_pitch_by_characters(
            normalized_pitch, valid_times, char_count
        )
        
        detected_tones = []
        for segment in segments:
            if len(segment['pitch']) > 2:
                tone_info = self._detect_tone_from_segment(segment)
                detected_tones.append(tone_info['tone_type'])
            else:
                detected_tones.append(0)  # 默认轻声
        
        return detected_tones
    
    def analyze_pitch_tones(self, pitch_values: np.ndarray, 
                           times: np.ndarray, 
                           expected_tones: List[int] = None) -> Dict:
        """
        分析音高曲线的声调特征
        :param pitch_values: 音高序列
        :param times: 时间序列
        :param expected_tones: 期望的声调序列
        :return: 声调分析结果
        """
        if len(pitch_values) < 5:
            return {'error': '音频太短，无法分析声调'}
        
        # 过滤有效音高
        valid_mask = ~np.isnan(pitch_values)
        if np.sum(valid_mask) < 3:
            return {'error': '有效音高点太少'}
        
        valid_pitch = pitch_values[valid_mask]
        valid_times = times[valid_mask]
        
        # 音高归一化（相对音高）
        normalized_pitch = self._normalize_pitch_for_tone_analysis(valid_pitch)
        
        # 分段分析（假设每个字占等时长）
        if expected_tones:
            segments = self._segment_pitch_by_characters(
                normalized_pitch, valid_times, len(expected_tones)
            )
            tone_analysis = []
            
            for i, segment in enumerate(segments):
                if len(segment['pitch']) > 2:
                    detected_tone = self._detect_tone_from_segment(segment)
                    expected_tone = expected_tones[i] if i < len(expected_tones) else 1
                    
                    tone_analysis.append({
                        'segment_index': i,
                        'detected_tone': detected_tone,
                        'expected_tone': expected_tone,
                        'confidence': detected_tone.get('confidence', 0.5),
                        'match': self._compare_tones(
                            detected_tone['tone_type'], expected_tone
                        )
                    })
        else:
            # 整体分析
            detected_tone = self._detect_tone_from_segment({
                'pitch': normalized_pitch,
                'times': valid_times
            })
            tone_analysis = [detected_tone]
        
        return {
            'tone_analysis': tone_analysis,
            'overall_tone_accuracy': self._calculate_overall_accuracy(tone_analysis),
            'pitch_statistics': self._calculate_pitch_statistics(valid_pitch)
        }
    
    def _normalize_pitch_for_tone_analysis(self, pitch_values: np.ndarray) -> np.ndarray:
        """为声调分析优化的音高归一化"""
        # 使用对数变换，更符合音高感知
        log_pitch = np.log2(pitch_values / np.min(pitch_values))
        
        # 标准化到0-1范围
        normalized = (log_pitch - np.min(log_pitch)) / (np.max(log_pitch) - np.min(log_pitch))
        
        return normalized
    
    def _segment_pitch_by_characters(self, pitch: np.ndarray, 
                                   times: np.ndarray, 
                                   num_chars: int) -> List[Dict]:
        """按字符数分段音高序列"""
        segments = []
        total_duration = times[-1] - times[0]
        char_duration = total_duration / num_chars
        
        for i in range(num_chars):
            start_time = times[0] + i * char_duration
            end_time = start_time + char_duration
            
            # 找到时间段内的音高点
            mask = (times >= start_time) & (times < end_time)
            if np.sum(mask) > 0:
                segments.append({
                    'pitch': pitch[mask],
                    'times': times[mask],
                    'start_time': start_time,
                    'end_time': end_time,
                    'character_index': i
                })
        
        return segments
    
    def _detect_tone_from_segment(self, segment: Dict) -> Dict:
        """从音高片段检测声调"""
        pitch = segment['pitch']
        times = segment['times']
        
        if len(pitch) < 2:
            return {'tone_type': 1, 'confidence': 0.0, 'pattern': 'unknown'}
        
        # 计算音高变化特征
        features = self._extract_tone_features(pitch, times)
        
        # 声调分类
        tone_type, confidence = self._classify_tone(features, pitch, times)
        
        return {
            'tone_type': tone_type,
            'confidence': confidence,
            'pattern': self.tone_patterns.get(tone_type, 'unknown'),
            'features': features
        }
    
    def _extract_tone_features(self, pitch: np.ndarray, times: np.ndarray) -> Dict:
        """提取声调特征"""
        # 基本统计特征
        mean_pitch = np.mean(pitch)
        std_pitch = np.std(pitch)
        pitch_range = np.max(pitch) - np.min(pitch)
        
        # 趋势特征
        total_change = pitch[-1] - pitch[0]
        linear_slope = total_change / (times[-1] - times[0]) if len(times) > 1 else 0
        
        # 单调性特征
        diff = np.diff(pitch)
        monotonic_ratio = np.sum(diff > 0) / len(diff) if len(diff) > 0 else 0.5
        
        # 变化复杂度
        direction_changes = np.sum(np.abs(np.diff(np.sign(diff))))
        complexity = direction_changes / len(diff) if len(diff) > 0 else 0
        
        # 峰值特征
        peak_position = np.argmax(pitch) / len(pitch)
        valley_position = np.argmin(pitch) / len(pitch)
        
        return {
            'mean_pitch': mean_pitch,
            'std_pitch': std_pitch,
            'pitch_range': pitch_range,
            'total_change': total_change,
            'linear_slope': linear_slope,
            'monotonic_ratio': monotonic_ratio,
            'complexity': complexity,
            'peak_position': peak_position,
            'valley_position': valley_position,
            'duration': times[-1] - times[0] if len(times) > 1 else 0
        }
    
    def _classify_tone(self, features: Dict, pitch: np.ndarray = None, times: np.ndarray = None) -> Tuple[int, float]:
        """基于特征分类声调 - 改进的算法"""
        slope = features['linear_slope']
        complexity = features['complexity']
        monotonic_ratio = features['monotonic_ratio']
        total_change = features['total_change']
        peak_pos = features['peak_position']
        valley_pos = features['valley_position']
        pitch_range = features['pitch_range']
        
        print(f"🔍 声调分类特征: slope={slope:.3f}, complexity={complexity:.3f}, "
              f"monotonic_ratio={monotonic_ratio:.3f}, total_change={total_change:.3f}")
        
        # 声调分类逻辑 - 基于中文声调的实际特征
        
        # 1. 阴平（第一声）- 高平调，音高相对平稳
        if (abs(total_change) < 0.2 and complexity < 0.3 and 
            abs(slope) < 0.15):
            return 1, 0.85
        
        # 2. 阳平（第二声）- 升调，从中低音升到高音
        elif (slope > 0.2 and monotonic_ratio > 0.6 and 
              total_change > 0.15 and complexity < 0.4):
            return 2, 0.9
        
        # 3. 上声（第三声）- 降升调，先降后升，最复杂
        # 分析前半部分和后半部分的趋势
        mid_point = len(times) // 2
        if mid_point > 2:
            first_half = pitch[:mid_point] if len(pitch) > mid_point else pitch
            second_half = pitch[mid_point:] if len(pitch) > mid_point else pitch
            
            first_trend = np.polyfit(range(len(first_half)), first_half, 1)[0] if len(first_half) > 1 else 0
            second_trend = np.polyfit(range(len(second_half)), second_half, 1)[0] if len(second_half) > 1 else 0
            
            # 上声特征：前半下降，后半上升，有明显谷点
            is_dipping = (first_trend < -0.05 and second_trend > 0.05 and 
                         0.2 < valley_pos < 0.8 and pitch_range > 0.15)
            
            print(f"🔍 上声检测: first_trend={first_trend:.3f}, second_trend={second_trend:.3f}, "
                  f"valley_pos={valley_pos:.3f}, is_dipping={is_dipping}")
            
            if is_dipping:
                return 3, 0.9
        
        # 备选上声检测：基于复杂度和变化范围
        high_complexity = complexity > 0.4
        mid_valley = 0.2 < valley_pos < 0.8
        moderate_range = pitch_range > 0.25
        
        if (high_complexity and mid_valley and moderate_range):
            return 3, 0.75
        
        # 4. 去声（第四声）- 降调，从高音快速下降
        elif (slope < -0.2 and monotonic_ratio < 0.4 and 
              total_change < -0.15 and complexity < 0.4):
            return 4, 0.9
        
        # 备选判断逻辑
        else:
            # 基于主要特征的次要判断
            if total_change > 0.1 and slope > 0:
                return 2, 0.6  # 倾向阳平（升调）
            elif total_change < -0.1 and slope < 0:
                return 4, 0.6  # 倾向去声（降调）
            elif complexity > 0.3:
                return 3, 0.5  # 倾向上声（复杂变化）
            else:
                return 1, 0.5  # 默认阴平（平调）
    
    def _compare_tones(self, detected: int, expected: int) -> Dict:
        """比较检测声调与期望声调"""
        if detected == expected:
            return {'match': True, 'accuracy': 1.0, 'type': 'perfect'}
        
        # 声调相似度矩阵
        similarity_scores = {
            (1, 2): 0.3, (1, 3): 0.2, (1, 4): 0.2,
            (2, 3): 0.4, (2, 4): 0.1,
            (3, 4): 0.3
        }
        
        key = (min(detected, expected), max(detected, expected))
        similarity = similarity_scores.get(key, 0.0)
        
        return {
            'match': False,
            'accuracy': similarity,
            'type': 'partial' if similarity > 0.2 else 'mismatch'
        }
    
    def _calculate_overall_accuracy(self, tone_analysis: List[Dict]) -> float:
        """计算整体声调准确度"""
        if not tone_analysis:
            return 0.0
        
        total_accuracy = 0.0
        total_weight = 0.0
        
        for analysis in tone_analysis:
            if 'match' in analysis:
                accuracy = analysis['match']['accuracy']
                confidence = analysis.get('confidence', 0.5)
                expected_tone = analysis.get('expected_tone', 1)
                
                # 声调重要性权重
                tone_weight = self.tone_weights.get(expected_tone, 1.0)
                
                weighted_accuracy = accuracy * confidence * tone_weight
                total_accuracy += weighted_accuracy
                total_weight += tone_weight
        
        return total_accuracy / total_weight if total_weight > 0 else 0.0
    
    def _calculate_pitch_statistics(self, pitch_values: np.ndarray) -> Dict:
        """计算音高统计信息"""
        return {
            'mean': float(np.mean(pitch_values)),
            'std': float(np.std(pitch_values)),
            'min': float(np.min(pitch_values)),
            'max': float(np.max(pitch_values)),
            'range': float(np.max(pitch_values) - np.min(pitch_values)),
            'median': float(np.median(pitch_values))
        }
    
    def get_tone_feedback(self, tone_analysis: List[Dict], 
                         target_language: str = 'chinese') -> str:
        """
        为听障人士生成专门的声调反馈建议
        """
        if not tone_analysis:
            return "无法分析声调，请检查录音质量。"
        
        feedback_parts = []
        
        for i, analysis in enumerate(tone_analysis):
            char_num = i + 1
            detected = analysis.get('detected_tone', {}).get('tone_type', 1)
            expected = analysis.get('expected_tone', 1)
            confidence = analysis.get('confidence', 0.5)
            
            if analysis.get('match', {}).get('match', False):
                feedback_parts.append(f"第{char_num}个字的声调很准确！")
            else:
                tone_names = {1: '阴平(一声)', 2: '阳平(二声)', 3: '上声(三声)', 4: '去声(四声)'}
                expected_name = tone_names.get(expected, '未知')
                detected_name = tone_names.get(detected, '未知')
                
                feedback_parts.append(
                    f"第{char_num}个字应该是{expected_name}，"
                    f"您发的是{detected_name}。"
                )
                
                # 提供具体改进建议
                if expected == 1:  # 阴平
                    feedback_parts.append("  💡 建议：保持音高平稳，不要有明显升降。")
                elif expected == 2:  # 阳平
                    feedback_parts.append("  💡 建议：音调从低往高上升，像疑问句。")
                elif expected == 3:  # 上声
                    feedback_parts.append("  💡 建议：先轻微下降，然后明显上升。")
                elif expected == 4:  # 去声
                    feedback_parts.append("  💡 建议：音调从高往低下降，要有力。")
        
        overall_accuracy = self._calculate_overall_accuracy(tone_analysis)
        
        if overall_accuracy > 0.8:
            feedback_parts.append("\n🌟 总体表现优秀！您的声调掌握得很好。")
        elif overall_accuracy > 0.6:
            feedback_parts.append("\n👍 总体表现良好，继续练习会更好。")
        else:
            feedback_parts.append("\n💪 声调还需要多练习，重点关注音调的升降变化。")
        
        return "\n".join(feedback_parts)

# 使用示例和测试
if __name__ == '__main__':
    analyzer = ChineseToneAnalyzer()
    
    # 测试文本声调分析
    test_text = "你好"
    tones = analyzer.analyze_text_tones(test_text)
    print(f"文本 '{test_text}' 的声调序列: {tones}")
    
    # 测试音高声调分析
    # 模拟音高数据
    test_pitch = np.array([200, 210, 220, 215, 210, 205, 200])
    test_times = np.linspace(0, 1, len(test_pitch))
    
    result = analyzer.analyze_pitch_tones(test_pitch, test_times, [3, 3])
    print(f"音高声调分析结果: {result}")
