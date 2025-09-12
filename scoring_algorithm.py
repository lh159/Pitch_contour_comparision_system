# -*- coding: utf-8 -*-
"""
评分算法模块
基于音高比较指标计算发音评分
"""
import numpy as np
from config import Config

class ScoringSystem:
    """发音评分系统"""
    
    def __init__(self):
        self.weights = Config.SCORE_WEIGHTS
        
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
    
    def calculate_score(self, comparison_metrics: dict) -> dict:
        """
        根据比较指标计算综合评分
        :param comparison_metrics: 音高比较指标
        :return: 评分结果
        """
        
        if 'error' in comparison_metrics:
            return {
                'total_score': 0.0,
                'component_scores': {},
                'level': '错误',
                'feedback': comparison_metrics['error']
            }
        
        metrics = comparison_metrics.get('metrics', {})
        
        # 计算各项子分数
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
        
        # 计算加权总分
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
        
        return {
            'total_score': round(total_score, 1),
            'component_scores': {
                'accuracy': round(correlation_score, 1),
                'trend': round(trend_score, 1),
                'stability': round(rmse_score, 1),
                'range': round(range_score, 1)
            },
            'level': level,
            'metrics': metrics
        }
    
    def _calculate_correlation_score(self, correlation: float) -> float:
        """计算相关性得分"""
        if correlation >= self.thresholds['correlation']['excellent']:
            return 95 + 5 * (correlation - self.thresholds['correlation']['excellent']) / (1 - self.thresholds['correlation']['excellent'])
        elif correlation >= self.thresholds['correlation']['good']:
            return 80 + 15 * (correlation - self.thresholds['correlation']['good']) / (self.thresholds['correlation']['excellent'] - self.thresholds['correlation']['good'])
        elif correlation >= self.thresholds['correlation']['fair']:
            return 60 + 20 * (correlation - self.thresholds['correlation']['fair']) / (self.thresholds['correlation']['good'] - self.thresholds['correlation']['fair'])
        elif correlation >= self.thresholds['correlation']['poor']:
            return 30 + 30 * (correlation - self.thresholds['correlation']['poor']) / (self.thresholds['correlation']['fair'] - self.thresholds['correlation']['poor'])
        else:
            return max(0, 30 * correlation / self.thresholds['correlation']['poor'])
    
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
