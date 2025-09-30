# -*- coding: utf-8 -*-
"""
评分算法模块
基于音高比较指标计算发音评分
"""
import numpy as np
from config import Config

try:
    from chinese_tone_analyzer import ChineseToneAnalyzer
    TONE_ANALYZER_AVAILABLE = True
except ImportError:
    TONE_ANALYZER_AVAILABLE = False
    print("警告: 中文声调分析器不可用")

class ScoringSystem:
    """发音评分系统"""
    
    def __init__(self):
        self.weights = Config.SCORE_WEIGHTS
        
        # 初始化声调分析器
        if TONE_ANALYZER_AVAILABLE:
            self.tone_analyzer = ChineseToneAnalyzer()
        else:
            self.tone_analyzer = None
        
        # 评分阈值配置
        self.thresholds = {
            'correlation': {
                'excellent': 0.85,  # 优秀
                'good': 0.70,       # 良好
                'fair': 0.50,       # 一般
                'poor': 0.30        # 较差
            },
            'rmse': {
                'excellent': 20,    # Hz
                'good': 40,
                'fair': 60,
                'poor': 100
            },
            'trend': {
                'excellent': 0.80,
                'good': 0.65,
                'fair': 0.50,
                'poor': 0.35
            },
            'range': {
                'excellent': 0.85,
                'good': 0.70,
                'fair': 0.50,
                'poor': 0.30
            }
        }
    
    def calculate_score(self, comparison_metrics: dict, input_text: str = None) -> dict:
        """
        根据比较指标计算综合评分 - 针对听障人士优化
        :param comparison_metrics: 音高比较指标
        :param input_text: 输入文本（用于声调分析）
        :return: 评分结果
        """
        
        if 'error' in comparison_metrics:
            return {
                'total_score': 0.0,
                'component_scores': {},
                'level': '录音质量问题',
                'feedback': comparison_metrics.get('error', '未知错误') + 
                          (f"\n建议：{comparison_metrics['suggestion']}" if 'suggestion' in comparison_metrics else ""),
                'tone_analysis': None
            }
        
        metrics = comparison_metrics.get('metrics', {})
        
        # 🎯 检测严重质量问题（静音和极少语音内容），直接返回0分
        critical_quality_flags = ['insufficient_data', 'insufficient_speech', 'silence_detected']
        if metrics.get('quality_flag') in critical_quality_flags:
            quality_issue = metrics.get('quality_flag')
            
            # 根据不同的质量问题提供不同的反馈
            if quality_issue == 'silence_detected':
                feedback = '🔇 检测到静音录音，无法进行音高比较。请重新录音并确保正常说话。'
            else:
                feedback = '🎙️ 录音中检测到的有效语音内容太少，请重新录音并确保正常说话。'
                
            return {
                'total_score': 0.0,
                'component_scores': {
                    'accuracy': 0.0,
                    'trend': 0.0,
                    'stability': 0.0,
                    'range': 0.0
                },
                'level': '录音质量不足',
                'feedback': feedback,
                'tone_analysis': None,
                'quality_issue': quality_issue
            }
        
        # 🔧 检查是否有低质量警告（来自pitch_comparison.py）
        quality_warning = comparison_metrics.get('quality_warning')
        is_low_quality = quality_warning is not None
        
        # 🎯 基本评分计算
        correlation_score = self._calculate_correlation_score(
            metrics.get('correlation', 0)
        )
        
        rmse_score = self._calculate_rmse_score(
            metrics.get('rmse', float('inf'))
        )
        
        trend_score = self._calculate_trend_score(
            metrics.get('trend_consistency', 0)
        )
        
        range_score = self._calculate_range_score(
            metrics.get('pitch_range_ratio', 0)
        )
        
        # 🔧 应用质量调整到各个小模块（而不是总分）
        if is_low_quality:
            quality_adjustments = self._calculate_quality_adjustments(quality_warning)
            
            # 根据质量问题的性质，对不同模块应用不同程度的调整
            correlation_score *= quality_adjustments['correlation']
            rmse_score *= quality_adjustments['stability'] 
            trend_score *= quality_adjustments['trend']
            range_score *= quality_adjustments['range']
            
            print(f"📉 质量调整应用到各模块: 相关性×{quality_adjustments['correlation']:.2f}, "
                  f"稳定性×{quality_adjustments['stability']:.2f}, "
                  f"趋势×{quality_adjustments['trend']:.2f}, "
                  f"音域×{quality_adjustments['range']:.2f}")
        
        # 🎵 声调特征增强评分
        tone_enhancement = 0.0
        tone_analysis = None
        tone_feedback = ""
        
        if self.tone_analyzer and input_text:
            tone_analysis = self._analyze_chinese_tones(
                comparison_metrics, input_text
            )
            if tone_analysis and 'overall_tone_accuracy' in tone_analysis:
                # 声调准确度可以提升趋势分数
                tone_accuracy = tone_analysis['overall_tone_accuracy']
                tone_enhancement = tone_accuracy * 10  # 最多加10分
                trend_score = min(100, trend_score + tone_enhancement)
                
                tone_feedback = self.tone_analyzer.get_tone_feedback(
                    tone_analysis.get('tone_analysis', [])
                )
        
        # 🎯 计算加权总分 (实际权重：相关性50%, 趋势25%, 稳定性15%, 音域10%)
        # 现在总分就是各小模块分数的纯加权和，无额外调整
        total_score = (
            correlation_score * self.weights['correlation'] +
            trend_score * self.weights['trend'] +
            rmse_score * self.weights['stability'] +
            range_score * self.weights['range']
        )
        
        # 限制在0-100分范围内
        total_score = max(0, min(100, total_score))
        
        # 确定评级
        level = self._get_score_level(total_score)
        
        # 🎵 为听障人士生成专门反馈
        hearing_impaired_feedback = self._generate_hearing_impaired_feedback(
            total_score, trend_score, correlation_score, tone_feedback, is_low_quality, quality_warning
        )
        
        result = {
            'total_score': round(total_score, 1),
            'component_scores': {
                'accuracy': round(correlation_score, 1),
                'trend': round(trend_score, 1),
                'stability': round(rmse_score, 1),
                'range': round(range_score, 1)
            },
            'level': level,
            'metrics': metrics,
            'tone_analysis': tone_analysis,
            'tone_enhancement': round(tone_enhancement, 1),
            'feedback': hearing_impaired_feedback,
            'tone_feedback': tone_feedback
        }
        
        # 🔧 如果有质量警告，添加到结果中
        if is_low_quality:
            result['quality_warning'] = quality_warning
            # 不再提供单一的质量惩罚系数，因为现在是分模块调整
        
        return result
    
    def _analyze_chinese_tones(self, comparison_metrics: dict, text: str) -> dict:
        """分析中文声调特征"""
        if not self.tone_analyzer:
            return None
        
        try:
            # 提取音高数据
            standard_pitch_data = comparison_metrics.get('standard_pitch', {})
            user_pitch_data = comparison_metrics.get('user_pitch', {})
            
            user_pitch = user_pitch_data.get('pitch_values', np.array([]))
            user_times = user_pitch_data.get('times', np.array([]))
            
            if len(user_pitch) == 0:
                return None
            
            # 直接分析音高声调，不需要预设的期望声调
            # 对于音高曲线对比分析，我们只需要从音频中检测声调
            tone_result = self.tone_analyzer.analyze_pitch_tones(
                user_pitch, user_times, expected_tones=None
            )
            
            return tone_result
            
        except Exception as e:
            print(f"声调分析失败: {e}")
            return None
    
    def _generate_hearing_impaired_feedback(self, total_score: float, 
                                          trend_score: float, 
                                          correlation_score: float,
                                          tone_feedback: str,
                                          is_low_quality: bool = False,
                                          quality_warning: dict = None) -> str:
        """为听障人士生成专门的反馈建议"""
        feedback_parts = []
        
        # 🔧 如果是低质量录音，优先提示质量问题
        if is_low_quality and quality_warning:
            feedback_parts.append(f"⚠️ {quality_warning.get('message', '录音质量较低')}")
            feedback_parts.append(f"💡 {quality_warning.get('suggestion', '建议重新录音')}")
            feedback_parts.append("\n--- 基于当前录音的分析结果 ---")
        
        # 🎯 总体评价
        if total_score >= 85:
            feedback_parts.append("🌟 优秀！您的发音音调非常准确。")
        elif total_score >= 70:
            feedback_parts.append("👍 良好！您的音调掌握得不错。")
        elif total_score >= 55:
            feedback_parts.append("📈 还不错，继续练习会更好。")
        else:
            if is_low_quality:
                feedback_parts.append("📊 由于录音质量问题，评分可能不够准确。")
            feedback_parts.append("💪 需要多练习，重点关注音调变化。")
        
        # 🎵 音调变化重点反馈
        if trend_score >= 80:
            feedback_parts.append("✅ 音调变化很准确，声调掌握得很好！")
        elif trend_score >= 60:
            feedback_parts.append("⚠️ 音调变化基本正确，但还可以更精确。")
        else:
            feedback_parts.append("❗ 重点改进：注意音调的升降变化，这是中文发音的关键。")
        
        # 🎯 具体建议
        if correlation_score < 60:
            feedback_parts.append("💡 建议：多关注整体音高曲线的相似性。")
        
        # 🎶 声调特定反馈
        if tone_feedback:
            feedback_parts.append(f"\n🎵 声调详细分析：\n{tone_feedback}")
        
        return "\n".join(feedback_parts)
    
    def _calculate_correlation_score(self, correlation: float) -> float:
        """计算相关性得分 - 修复负相关性处理"""
        # 🎯 严格处理负相关性和极低相关性
        if correlation <= -0.1:
            return 0.0  # 负相关性直接0分
        elif correlation < 0.15:
            return 0.0  # 极低相关性也是0分，防止噪声得分
        elif correlation >= self.thresholds['correlation']['excellent']:
            return 95 + 5 * (correlation - self.thresholds['correlation']['excellent']) / (1 - self.thresholds['correlation']['excellent'])
        elif correlation >= self.thresholds['correlation']['good']:
            return 80 + 15 * (correlation - self.thresholds['correlation']['good']) / (self.thresholds['correlation']['excellent'] - self.thresholds['correlation']['good'])
        elif correlation >= self.thresholds['correlation']['fair']:
            return 60 + 20 * (correlation - self.thresholds['correlation']['fair']) / (self.thresholds['correlation']['good'] - self.thresholds['correlation']['fair'])
        elif correlation >= self.thresholds['correlation']['poor']:
            return 30 + 30 * (correlation - self.thresholds['correlation']['poor']) / (self.thresholds['correlation']['fair'] - self.thresholds['correlation']['poor'])
        else:
            # 对于0到poor阈值之间的值，线性递减到10分
            return max(10, 30 * correlation / self.thresholds['correlation']['poor'])
    
    def _calculate_rmse_score(self, rmse: float) -> float:
        """计算RMSE得分（值越小越好）"""
        if rmse <= self.thresholds['rmse']['excellent']:
            return 100
        elif rmse <= self.thresholds['rmse']['good']:
            return 85 + 15 * (self.thresholds['rmse']['good'] - rmse) / (self.thresholds['rmse']['good'] - self.thresholds['rmse']['excellent'])
        elif rmse <= self.thresholds['rmse']['fair']:
            return 65 + 20 * (self.thresholds['rmse']['fair'] - rmse) / (self.thresholds['rmse']['fair'] - self.thresholds['rmse']['good'])
        elif rmse <= self.thresholds['rmse']['poor']:
            return 35 + 30 * (self.thresholds['rmse']['poor'] - rmse) / (self.thresholds['rmse']['poor'] - self.thresholds['rmse']['fair'])
        else:
            return max(0, 35 * self.thresholds['rmse']['poor'] / rmse)
    
    def _calculate_trend_score(self, trend_consistency: float) -> float:
        """计算趋势一致性得分"""
        if trend_consistency >= self.thresholds['trend']['excellent']:
            return 95 + 5 * (trend_consistency - self.thresholds['trend']['excellent']) / (1 - self.thresholds['trend']['excellent'])
        elif trend_consistency >= self.thresholds['trend']['good']:
            return 80 + 15 * (trend_consistency - self.thresholds['trend']['good']) / (self.thresholds['trend']['excellent'] - self.thresholds['trend']['good'])
        elif trend_consistency >= self.thresholds['trend']['fair']:
            return 60 + 20 * (trend_consistency - self.thresholds['trend']['fair']) / (self.thresholds['trend']['good'] - self.thresholds['trend']['fair'])
        elif trend_consistency >= self.thresholds['trend']['poor']:
            return 30 + 30 * (trend_consistency - self.thresholds['trend']['poor']) / (self.thresholds['trend']['fair'] - self.thresholds['trend']['poor'])
        else:
            return max(0, 30 * trend_consistency / self.thresholds['trend']['poor'])
    
    def _calculate_range_score(self, range_ratio: float) -> float:
        """计算音域适配得分"""
        if range_ratio >= self.thresholds['range']['excellent']:
            return 95 + 5 * (range_ratio - self.thresholds['range']['excellent']) / (1 - self.thresholds['range']['excellent'])
        elif range_ratio >= self.thresholds['range']['good']:
            return 80 + 15 * (range_ratio - self.thresholds['range']['good']) / (self.thresholds['range']['excellent'] - self.thresholds['range']['good'])
        elif range_ratio >= self.thresholds['range']['fair']:
            return 60 + 20 * (range_ratio - self.thresholds['range']['fair']) / (self.thresholds['range']['good'] - self.thresholds['range']['fair'])
        elif range_ratio >= self.thresholds['range']['poor']:
            return 30 + 30 * (range_ratio - self.thresholds['range']['poor']) / (self.thresholds['range']['fair'] - self.thresholds['range']['poor'])
        else:
            return max(0, 30 * range_ratio / self.thresholds['range']['poor'])
    
    def _calculate_quality_adjustments(self, quality_warning: dict) -> dict:
        """
        根据录音质量问题计算各模块的调整系数
        
        🎯 设计理念：
        - 不同质量问题对不同模块的影响程度不同
        - 相关性最容易受噪声影响，稳定性次之
        - 趋势和音域相对更稳健
        """
        valid_ratio = quality_warning.get('valid_ratio', 1.0)
        valid_points = quality_warning.get('valid_points', 100)
        
        # 🔧 基础调整系数计算
        # 有效比例影响：50%+ -> 0.95-1.0, 40%+ -> 0.90-0.95, 30%+ -> 0.85-0.90
        if valid_ratio >= 0.50:
            base_ratio_factor = 0.95 + 0.05 * (valid_ratio - 0.50) / 0.50
        elif valid_ratio >= 0.40:
            base_ratio_factor = 0.90 + 0.05 * (valid_ratio - 0.40) / 0.10
        elif valid_ratio >= 0.30:
            base_ratio_factor = 0.85 + 0.05 * (valid_ratio - 0.30) / 0.10
        elif valid_ratio >= 0.20:
            base_ratio_factor = 0.80 + 0.05 * (valid_ratio - 0.20) / 0.10
        else:
            base_ratio_factor = max(0.75, 0.80 * valid_ratio / 0.20)
        
        # 有效点数影响：60+ -> 0.95-1.0, 40+ -> 0.90-0.95, 20+ -> 0.85-0.90
        if valid_points >= 60:
            base_points_factor = 0.95 + 0.05 * min(1.0, (valid_points - 60) / 40)
        elif valid_points >= 40:
            base_points_factor = 0.90 + 0.05 * (valid_points - 40) / 20
        elif valid_points >= 20:
            base_points_factor = 0.85 + 0.05 * (valid_points - 20) / 20
        else:
            base_points_factor = max(0.80, 0.85 * valid_points / 20)
        
        # 综合基础调整系数
        base_factor = (base_ratio_factor * 0.6 + base_points_factor * 0.4)
        
        # 🎯 针对不同模块应用不同的调整策略
        return {
            # 相关性最易受噪声影响，应用较强调整
            'correlation': base_factor * 0.95,
            
            # 稳定性(RMSE)也容易受噪声影响，但稍轻一些  
            'stability': base_factor * 0.97,
            
            # 趋势相对稳健，调整较轻
            'trend': base_factor * 0.98,
            
            # 音域最稳健，调整最轻
            'range': base_factor * 0.99
        }
    
    def _get_score_level(self, score: float) -> str:
        """根据分数确定评级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "需要改进"
    

class DetailedAnalyzer:
    """详细分析器，提供更深入的音高分析"""
    
    def __init__(self):
        self.scoring_system = ScoringSystem()
    
    def analyze_pitch_details(self, comparison_result: dict) -> dict:
        """
        详细分析音高特征
        :param comparison_result: 音高比较结果
        :return: 详细分析结果
        """
        
        if 'error' in comparison_result:
            return {'error': comparison_result['error']}
        
        metrics = comparison_result.get('metrics', {})
        standard_pitch = comparison_result.get('standard_pitch', {})
        user_pitch = comparison_result.get('user_pitch', {})
        
        # 基本统计信息
        analysis = {
            'duration_comparison': {
                'standard_duration': standard_pitch.get('duration', 0),
                'user_duration': user_pitch.get('duration', 0),
                'duration_ratio': self._safe_divide(
                    user_pitch.get('duration', 0),
                    standard_pitch.get('duration', 1)
                )
            },
            'pitch_statistics': {
                'standard': {
                    'mean': metrics.get('std_mean', 0),
                    'std': metrics.get('std_std', 0),
                    'valid_ratio': standard_pitch.get('valid_ratio', 0)
                },
                'user': {
                    'mean': metrics.get('user_mean', 0),
                    'std': metrics.get('user_std', 0),
                    'valid_ratio': user_pitch.get('valid_ratio', 0)
                }
            },
            'quality_assessment': self._assess_quality(standard_pitch, user_pitch),
            'alignment_info': (comparison_result.get('aligned_data') or {}).get('alignment_method', 'unknown')
        }
        
        return analysis
    
    def _safe_divide(self, a: float, b: float) -> float:
        """安全除法，避免除零错误"""
        return a / b if b != 0 else 0
    
    def _assess_quality(self, standard_pitch: dict, user_pitch: dict) -> dict:
        """评估音频质量"""
        
        std_quality = "良好" if standard_pitch.get('valid_ratio', 0) > 0.7 else \
                     "一般" if standard_pitch.get('valid_ratio', 0) > 0.4 else "较差"
        
        user_quality = "良好" if user_pitch.get('valid_ratio', 0) > 0.7 else \
                      "一般" if user_pitch.get('valid_ratio', 0) > 0.4 else "较差"
        
        return {
            'standard_quality': std_quality,
            'user_quality': user_quality,
            'recommendation': self._get_quality_recommendation(
                standard_pitch.get('valid_ratio', 0),
                user_pitch.get('valid_ratio', 0)
            )
        }
    
    def _get_quality_recommendation(self, std_ratio: float, user_ratio: float) -> str:
        """根据音频质量给出建议"""
        if user_ratio < 0.4:
            return "建议在安静环境中重新录音，确保声音清晰"
        elif user_ratio < 0.7:
            return "录音质量一般，可以尝试靠近麦克风或提高音量"
        else:
            return "录音质量良好"

# 使用示例
if __name__ == '__main__':
    # 测试评分系统
    scoring_system = ScoringSystem()
    
    # 模拟比较结果
    test_metrics = {
        'metrics': {
            'correlation': 0.75,
            'rmse': 35.0,
            'trend_consistency': 0.68,
            'pitch_range_ratio': 0.82,
            'std_mean': 200.0,
            'user_mean': 195.0,
            'std_std': 25.0,
            'user_std': 28.0
        }
    }
    
    # 计算评分
    score_result = scoring_system.calculate_score(test_metrics)
    
    print("=== 评分测试结果 ===")
    print(f"总分: {score_result['total_score']}")
    print(f"评级: {score_result['level']}")
    print(f"各项得分: {score_result['component_scores']}")
    print(f"反馈建议:\n{score_result['feedback']}")
