# -*- coding: utf-8 -*-
"""
主控制器模块
整合所有系统组件，提供统一的接口
"""
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from tts_module import TTSManager
from pitch_comparison import PitchComparator
from scoring_algorithm import ScoringSystem, DetailedAnalyzer
from visualization import PitchVisualization

class PitchComparisonSystem:
    """音高曲线比对系统主控制器"""
    
    def __init__(self):
        self.tts_manager = None
        self.comparator = None
        self.scoring_system = None
        self.analyzer = None
        self.visualizer = None
        self.initialized = False
        
        # 历史记录
        self.session_history = []
    
    def initialize(self) -> bool:
        """
        初始化系统所有组件
        :return: 是否初始化成功
        """
        try:
            print("🔧 正在初始化音高曲线比对系统...")
            
            # 创建必要目录
            Config.create_directories()
            
            # 初始化TTS管理器
            print("  ├─ 初始化TTS模块...")
            self.tts_manager = TTSManager()
            print(f"     ✓ 可用TTS引擎: {self.tts_manager.get_available_engines()}")
            
            # 初始化音高比较器
            print("  ├─ 初始化音高比较模块...")
            self.comparator = PitchComparator()
            print("     ✓ 音高比较器就绪")
            
            # 初始化评分系统
            print("  ├─ 初始化评分系统...")
            self.scoring_system = ScoringSystem()
            self.analyzer = DetailedAnalyzer()
            print("     ✓ 评分系统就绪")
            
            # 初始化可视化模块
            print("  ├─ 初始化可视化模块...")
            self.visualizer = PitchVisualization()
            print("     ✓ 可视化模块就绪")
            
            self.initialized = True
            print("🎉 系统初始化完成！")
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            traceback.print_exc()
            return False
    
    def process_word(self, text: str, user_audio_path: str, 
                    output_dir: str = None) -> Dict:
        """
        处理单个词汇的完整流程
        :param text: 要练习的文本
        :param user_audio_path: 用户音频文件路径
        :param output_dir: 输出目录
        :return: 处理结果
        """
        if not self.initialized:
            return {'error': '系统未初始化'}
        
        try:
            print(f"🎯 开始处理词汇: {text}")
            
            # 1. 生成标准发音
            print("  ├─ 生成标准发音...")
            output_dir = output_dir or Config.TEMP_FOLDER
            standard_audio_path = os.path.join(output_dir, f"standard_{text}_{int(datetime.now().timestamp())}.wav")
            
            if not self.tts_manager.generate_standard_audio(text, standard_audio_path):
                return {'error': '标准发音生成失败'}
            
            # 2. 比较音高曲线
            print("  ├─ 比较音高曲线...")
            comparison_result = self.comparator.compare_pitch_curves(
                standard_audio_path, user_audio_path, 
                expected_text=text, enable_text_alignment=True
            )
            
            if 'error' in comparison_result:
                return comparison_result
            
            # 3. 计算评分
            print("  ├─ 计算评分...")
            score_result = self.scoring_system.calculate_score(comparison_result)
            
            # 3.5 VAD增强评分（如果使用了VAD）
            vad_enhanced_score = None
            if comparison_result.get('vad_result'):
                print("  ├─ 计算VAD增强评分...")
                vad_enhanced_score = self.comparator.calculate_vad_enhanced_score(comparison_result)
            
            # 4. 详细分析
            print("  ├─ 详细分析...")
            detailed_analysis = self.analyzer.analyze_pitch_details(comparison_result)
            
            # 5. 生成可视化图表
            print("  ├─ 生成可视化图表...")
            chart_path = os.path.join(
                output_dir, 
                f"comparison_{text}_{int(datetime.now().timestamp())}.png"
            )
            
            chart_success = self.visualizer.plot_pitch_comparison(
                comparison_result, score_result, chart_path
            )
            
            # 6. 记录到历史
            session_record = {
                'text': text,
                'timestamp': datetime.now().isoformat(),
                'score': score_result,
                'vad_enhanced_score': vad_enhanced_score,
                'analysis': detailed_analysis,
                'standard_audio': standard_audio_path,
                'user_audio': user_audio_path,
                'chart_path': chart_path if chart_success else None,
                'vad_processing': comparison_result.get('preprocessing_info', {}).get('vad_processing', False)
            }
            
            self.session_history.append(session_record)
            
            print(f"✅ 处理完成 - 得分: {score_result['total_score']}分")
            
            # 显示VAD增强评分结果
            if vad_enhanced_score:
                enhancement = vad_enhanced_score.get('total_enhancement', 0.0) * 100
                print(f"   VAD增强: +{enhancement:.1f}% (总分: {vad_enhanced_score.get('enhanced_score', 0)*100:.1f})")
            
            return {
                'success': True,
                'text': text,
                'score': score_result,
                'vad_enhanced_score': vad_enhanced_score,
                'analysis': detailed_analysis,
                'comparison': comparison_result,
                'chart_path': chart_path if chart_success else None,
                'standard_audio': standard_audio_path,
                'session_id': len(self.session_history) - 1,
                'vad_processing_used': comparison_result.get('preprocessing_info', {}).get('vad_processing', False)
            }
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return {'error': error_msg}
    
    def get_session_history(self) -> List[Dict]:
        """获取当前会话的历史记录"""
        return self.session_history.copy()
    
    def generate_progress_report(self, output_path: str) -> bool:
        """
        生成学习进度报告
        :param output_path: 输出路径
        :return: 是否成功
        """
        if len(self.session_history) < 2:
            print("需要至少2次练习记录才能生成进度报告")
            return False
        
        try:
            # 提取历史评分
            history_scores = [record['score'] for record in self.session_history]
            
            # 生成进度图表
            success = self.visualizer.create_progress_chart(history_scores, output_path)
            
            if success:
                print(f"进度报告已生成: {output_path}")
            
            return success
            
        except Exception as e:
            print(f"生成进度报告失败: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """获取系统状态信息"""
        vad_status = {
            'enabled': False,
            'available': False,
            'processor_ready': False
        }
        
        if self.comparator:
            vad_status = {
                'enabled': self.comparator.use_vad,
                'available': hasattr(self.comparator, 'vad_comparator') and self.comparator.vad_comparator is not None,
                'processor_ready': (self.comparator.vad_comparator is not None and 
                                  hasattr(self.comparator.vad_comparator, 'vad_processor'))
            }
        
        return {
            'initialized': self.initialized,
            'tts_available': self.tts_manager is not None,
            'tts_engines': self.tts_manager.get_available_engines() if self.tts_manager else [],
            'components': {
                'tts_manager': self.tts_manager is not None,
                'comparator': self.comparator is not None,
                'scoring_system': self.scoring_system is not None,
                'analyzer': self.analyzer is not None,
                'visualizer': self.visualizer is not None
            },
            'vad_status': vad_status,
            'session_records': len(self.session_history)
        }
    
    def cleanup_temp_files(self, keep_recent: int = 5) -> int:
        """
        清理临时文件
        :param keep_recent: 保留最近的文件数量
        :return: 清理的文件数量
        """
        cleaned_count = 0
        
        try:
            # 清理临时音频文件
            temp_files = []
            for folder in [Config.TEMP_FOLDER, Config.UPLOAD_FOLDER]:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        if filename.endswith(('.wav', '.mp3', '.m4a')):
                            filepath = os.path.join(folder, filename)
                            temp_files.append((filepath, os.path.getctime(filepath)))
            
            # 按创建时间排序，删除旧文件
            temp_files.sort(key=lambda x: x[1], reverse=True)
            
            for filepath, _ in temp_files[keep_recent:]:
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass
            
            print(f"清理了 {cleaned_count} 个临时文件")
            
        except Exception as e:
            print(f"清理临时文件失败: {e}")
        
        return cleaned_count

# 使用示例和测试
if __name__ == '__main__':
    import sys
    
    # 创建系统实例
    system = PitchComparisonSystem()
    
    # 初始化系统
    if not system.initialize():
        print("系统初始化失败")
        sys.exit(1)
    
    # 检查系统状态
    status = system.get_system_status()
    print("\n=== 系统状态 ===")
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # 如果提供了测试参数，进行测试
    if len(sys.argv) >= 3:
        test_text = sys.argv[1]
        test_audio = sys.argv[2]
        
        if os.path.exists(test_audio):
            print(f"\n=== 测试处理: {test_text} ===")
            result = system.process_word(test_text, test_audio)
            
            if result.get('success'):
                print(f"✅ 测试成功")
                print(f"   总分: {result['score']['total_score']}")
                print(f"   评级: {result['score']['level']}")
                print(f"   图表: {result['chart_path']}")
            else:
                print(f"❌ 测试失败: {result.get('error')}")
        else:
            print(f"测试音频文件不存在: {test_audio}")
    
    else:
        print("\n提示: 可以使用以下命令进行测试:")
        print("python main_controller.py '你好' 'test_audio.wav'")
    
    # 清理演示
    cleaned = system.cleanup_temp_files(keep_recent=2)
    print(f"\n清理了 {cleaned} 个临时文件")
