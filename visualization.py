# -*- coding: utf-8 -*-
"""
可视化模块 - 扩展audio_plot.py的功能
实现音高曲线对比和评分可视化
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle
import seaborn as sns
import os
from config import Config
from fun_asr_module import FunASRProcessor

class PitchVisualization:
    """音高可视化类"""
    
    def __init__(self):
        self.font_name = self._detect_chinese_font()
        self._setup_matplotlib()
        self.fun_asr = FunASRProcessor()  # 初始化Fun-ASR处理器
    
    def _detect_chinese_font(self):
        """检测可用的中文字体"""
        # 清除matplotlib字体缓存
        try:
            fm._rebuild()
        except:
            pass
            
        # macOS系统常用字体（按优先级排序）
        preferred_fonts = [
            'PingFang SC',           # macOS系统字体（最佳）
            'STHeiti',               # 华文黑体
            'Songti SC',             # 宋体
            'Heiti TC',              # 繁体黑体
            'PingFang HK',           # 香港字体
            'Arial Unicode MS',      # 通用Unicode字体
            'Hannotate SC',          # 手写字体
            'HanziPen SC',           # 手写字体
            'SimHei',                # Windows黑体
            'Source Han Sans CN',    # 思源黑体
            'Noto Sans CJK SC',      # Google字体
            'Microsoft YaHei'        # 微软雅黑
        ]
        
        # 获取系统所有可用字体
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font in preferred_fonts:
            if font in available_fonts:
                print(f"✓ 使用中文字体: {font}")
                return font
        
        # 如果没有找到，尝试查找包含中文的字体
        chinese_keywords = ['chinese', 'han', 'cjk', 'heiti', 'songti', 'pingfang', 'stheiti']
        for font in available_fonts:
            if any(keyword in font.lower() for keyword in chinese_keywords):
                print(f"✓ 使用中文字体: {font}")
                return font
        
        print("⚠️  未找到中文字体，使用默认字体（可能无法显示中文）")
        return 'DejaVu Sans'  # 回退到默认字体
    
    def _setup_matplotlib(self):
        """设置matplotlib的中文字体和样式"""
        if self.font_name:
            # 强制设置中文字体 - 使用多个备选字体
            plt.rcParams['font.sans-serif'] = [self.font_name, 'STHeiti', 'Arial Unicode MS', 'Songti SC', 'Heiti TC', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.family'] = 'sans-serif'
            
            # 额外设置以确保中文显示
            plt.rcParams['font.serif'] = [self.font_name, 'STHeiti', 'Arial Unicode MS']
            plt.rcParams['font.monospace'] = [self.font_name, 'STHeiti', 'Arial Unicode MS']
            
            # 清除matplotlib字体缓存并重新加载
            try:
                import matplotlib
                matplotlib.font_manager._rebuild()
            except:
                pass
        
        # 设置样式
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except:
            plt.style.use('default')
        
        # 🎨 优化色彩主题 - 更加现代和协调
        self.colors = {
            'standard': '#2E86AB',      # 深蓝色 - 标准发音（权威、稳定）
            'user': '#A23B72',          # 深紫色 - 用户发音（个性、活力）
            'difference': '#F18F01',    # 金橙色 - 差异（注意、对比）
            'good': '#C73E1D',          # 深红色 - 良好（鼓励、成功）
            'warning': '#F18F01',       # 金橙色 - 警告（提醒、改进）
            'error': '#C73E1D',         # 深红色 - 错误（重要、需关注）
            'background': '#F8F9FA',    # 极浅灰 - 背景（干净、现代）
            'text': '#212529',          # 深灰色 - 文字（易读、专业）
            'accent': '#6C757D',        # 中灰色 - 辅助色（平衡、低调）
            'highlight': '#FFF3CD'      # 浅黄色 - 高亮（温和、突出）
        }
    
    def _get_font_properties(self, size=10, weight='normal'):
        """获取字体属性"""
        try:
            # 使用明确的字体列表，确保中文显示
            font_list = [self.font_name, 'STHeiti', 'Arial Unicode MS', 'Songti SC', 'Heiti TC']
            return fm.FontProperties(family=font_list, size=size, weight=weight)
        except:
            # 如果失败，至少使用已知的中文字体
            try:
                return fm.FontProperties(family='STHeiti', size=size, weight=weight)
            except:
                return fm.FontProperties(size=size, weight=weight)
    
    def _set_text_with_font(self, ax, text_type, *args, **kwargs):
        """设置带字体的文本"""
        fontsize = kwargs.pop('fontsize', 10)
        fontweight = kwargs.pop('fontweight', 'normal')
        
        # 确保使用正确的字体
        if 'fontproperties' not in kwargs:
            kwargs['fontproperties'] = self._get_font_properties(fontsize, fontweight)
        
        if text_type == 'title':
            return ax.set_title(*args, **kwargs)
        elif text_type == 'xlabel':
            return ax.set_xlabel(*args, **kwargs)
        elif text_type == 'ylabel':
            return ax.set_ylabel(*args, **kwargs)
        elif text_type == 'text':
            return ax.text(*args, **kwargs)
    
    def plot_pitch_comparison(self, comparison_result: dict, score_result: dict, 
                            output_path: str, fig_size=(14, 9), dpi=150, input_text: str = None, 
                            text_alignment_data: dict = None, standard_audio_path: str = None) -> bool:
        """
        绘制音高曲线对比图 - 简洁美观的设计，支持TTS文本标注
        """
        
        if 'error' in comparison_result:
            return self._plot_error_message(comparison_result['error'], output_path)
        
        try:
            # 提取数据
            aligned_data = comparison_result['aligned_data']
            standard_pitch = aligned_data['aligned_standard']
            user_pitch = aligned_data['aligned_user']
            times = aligned_data['aligned_times']
            
            if len(standard_pitch) == 0 or len(user_pitch) == 0:
                return self._plot_error_message("音高数据为空", output_path)
            
            # 🎯 尝试获取TTS音频的ASR时间戳
            tts_timestamp_data = None
            if standard_audio_path and input_text:
                tts_timestamp_data = self._get_tts_timestamps(standard_audio_path, input_text)
            
            # 🎨 创建布局 - 根据是否有文本对齐数据调整
            fig = plt.figure(figsize=fig_size, facecolor='white')
            
            if text_alignment_data and text_alignment_data.get('text_alignment'):
                # 有文本对齐数据时，使用3行布局
                gs = fig.add_gridspec(3, 2, height_ratios=[3, 1, 1], width_ratios=[3, 1], 
                                     hspace=0.3, wspace=0.2)
                
                # 1. 主音高对比图 (左上) - 增强版，支持TTS文本标注
                ax_main = fig.add_subplot(gs[0, 0])
                self._plot_enhanced_comparison_with_tts_text(ax_main, times, standard_pitch, 
                                                          user_pitch, input_text, text_alignment_data, 
                                                          tts_timestamp_data)
                
                # 2. 评分仪表盘 (右上)
                ax_score = fig.add_subplot(gs[0, 1])
                self._plot_clean_score_dashboard(ax_score, score_result)
                
                # 3. 文本时域对齐图 (左中)
                ax_text = fig.add_subplot(gs[1, 0])
                self._plot_text_time_alignment(ax_text, text_alignment_data)
                
                # 4. 评价与建议 (底部，跨两列)
                ax_feedback = fig.add_subplot(gs[2, :])
                self._plot_concise_feedback(ax_feedback, score_result, comparison_result)
            else:
                # 无文本对齐数据时，使用原始2行布局，但仍支持TTS文本标注
                gs = fig.add_gridspec(2, 2, height_ratios=[4, 1], width_ratios=[3, 1], 
                                     hspace=0.25, wspace=0.2)
                
                # 1. 主音高对比图 (左侧，占据主要空间) - 增强版
                ax_main = fig.add_subplot(gs[0, 0])
                self._plot_beautiful_comparison_with_tts_text(ax_main, times, standard_pitch, 
                                                           user_pitch, input_text, tts_timestamp_data)
                
                # 2. 评分仪表盘 (右上)
                ax_score = fig.add_subplot(gs[0, 1])
                self._plot_clean_score_dashboard(ax_score, score_result)
                
                # 3. 评价与建议 (底部，跨两列)
                ax_feedback = fig.add_subplot(gs[1, :])
                self._plot_concise_feedback(ax_feedback, score_result, comparison_result)
            
            # 设置整体标题
            total_score = score_result['total_score']
            level = score_result['level']
            title = f"♫ 音高曲线对比 - 总分: {total_score:.1f}分 ({level})"
            fig.suptitle(title, fontsize=18, weight='bold', y=0.96, 
                        color=self._get_score_color(total_score))
            
            # 保存图片
            plt.tight_layout(rect=[0, 0, 1, 0.93])
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white', 
                       edgecolor='none', pad_inches=0.1)
            plt.close(fig)
            
            print(f"🎨 美化的音高对比图已保存至: {output_path}")
            return True
            
        except Exception as e:
            print(f"绘制音高对比图失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_tts_timestamps(self, audio_path: str, text: str) -> dict:
        """
        获取TTS音频的时间戳数据
        :param audio_path: TTS音频文件路径
        :param text: 原始文本
        :return: 时间戳数据
        """
        try:
            print(f"🔤 正在获取TTS音频时间戳: {audio_path}")
            
            # 检查Fun-ASR是否可用
            if hasattr(self, 'fun_asr') and self.fun_asr:
                result = self.fun_asr.process_tts_audio_with_text(audio_path, text)
                if result:
                    print(f"✅ TTS时间戳获取成功: {len(result.get('aligned_chars', []))}个字符")
                    return result
                else:
                    print("⚠️ Fun-ASR处理TTS音频失败")
            else:
                print("⚠️ Fun-ASR不可用，将生成估算时间戳")
            
            # 回退方案：生成估算的时间戳
            return self._generate_estimated_tts_timestamps(audio_path, text)
            
        except Exception as e:
            print(f"获取TTS时间戳失败: {e}")
            return self._generate_estimated_tts_timestamps(audio_path, text)
    
    def _generate_estimated_tts_timestamps(self, audio_path: str, text: str) -> dict:
        """
        为TTS音频生成估算的时间戳
        :param audio_path: 音频文件路径
        :param text: 原始文本
        :return: 估算的时间戳数据
        """
        try:
            import parselmouth
            
            # 获取音频时长
            sound = parselmouth.Sound(audio_path)
            duration = sound.duration
            
            # 清理文本，只保留有意义的字符
            chars = [char for char in text.strip() if char.strip() and char not in '，。！？、']
            if not chars:
                return {'aligned_chars': [], 'alignment_quality': 0.0}
            
            # 估算每个字符的时间
            char_duration = duration / len(chars)
            
            aligned_chars = []
            for i, char in enumerate(chars):
                start_time = i * char_duration
                end_time = (i + 1) * char_duration
                
                aligned_chars.append({
                    'char': char,
                    'timestamp': start_time,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': 0.8  # 估算置信度
                })
            
            print(f"📝 生成估算时间戳: {len(aligned_chars)}个字符，总时长{duration:.2f}s")
            
            return {
                'aligned_chars': aligned_chars,
                'alignment_quality': 0.6,  # 估算质量
                'asr_result': {
                    'text': ''.join(chars),
                    'word_timestamps': []
                }
            }
            
        except Exception as e:
            print(f"生成估算时间戳失败: {e}")
            return {'aligned_chars': [], 'alignment_quality': 0.0}
    
    def _plot_beautiful_comparison_with_tts_text(self, ax, times, standard_pitch, user_pitch, 
                                               input_text, tts_timestamp_data=None):
        """
        绘制带有TTS文本标注的美观音高对比图
        """
        # 先绘制基础的音高对比
        self._plot_beautiful_comparison(ax, times, standard_pitch, user_pitch, input_text)
        
        # 添加TTS文本标注
        if tts_timestamp_data and tts_timestamp_data.get('aligned_chars'):
            self._add_tts_text_annotations(ax, times, standard_pitch, tts_timestamp_data, input_text)
    
    def _plot_enhanced_comparison_with_tts_text(self, ax, times, standard_pitch, user_pitch, 
                                              input_text, text_alignment_data, tts_timestamp_data):
        """
        绘制带有TTS文本标注的增强版音高对比图
        """
        # 先绘制带文本标记的对比图
        self._plot_beautiful_comparison_with_text_markers(ax, times, standard_pitch, 
                                                        user_pitch, input_text, text_alignment_data)
        
        # 再添加TTS文本标注
        if tts_timestamp_data and tts_timestamp_data.get('aligned_chars'):
            self._add_tts_text_annotations(ax, times, standard_pitch, tts_timestamp_data, input_text)
    
    def _add_tts_text_annotations(self, ax, times, standard_pitch, tts_timestamp_data, original_text):
        """
        在音高图上添加TTS音频对应的文本标注
        :param ax: matplotlib轴对象
        :param times: 时间轴
        :param standard_pitch: 标准音高数据
        :param tts_timestamp_data: TTS时间戳数据
        :param original_text: 原始文本
        """
        try:
            aligned_chars = tts_timestamp_data.get('aligned_chars', [])
            if not aligned_chars:
                return
            
            print(f"🎨 正在添加TTS文本标注: {len(aligned_chars)}个字符")
            
            # 获取图表范围
            ylim = ax.get_ylim()
            xlim = ax.get_xlim()
            y_range = ylim[1] - ylim[0]
            x_range = xlim[1] - xlim[0]
            
            # 🎯 TTS文本标注位置：在标准音高曲线上方
            tts_annotation_y_offset = y_range * 0.15  # 在标准曲线上方15%的位置
            
            # 🎨 初始化声调分析器，为TTS文本着色
            tone_analyzer = self._initialize_tone_analyzer()
            tts_tone_colors = self._get_tone_colors_for_text(tone_analyzer, original_text, 
                                                           standard_pitch, times)
            
            # 用于避免标注重叠
            used_positions = []
            min_distance = x_range * 0.03  # 最小间距
            
            for i, char_info in enumerate(aligned_chars):
                char = char_info.get('char', '')
                start_time = char_info.get('start_time', 0)
                end_time = char_info.get('end_time', start_time + 0.1)
                confidence = char_info.get('confidence', 1.0)
                
                if not char or start_time >= end_time:
                    continue
                
                # 检查时间是否在图表范围内
                if end_time < xlim[0] or start_time > xlim[1]:
                    continue
                
                # 计算字符中心时间
                char_center_time = (start_time + end_time) / 2
                
                # 避免重叠
                is_overlapping = any(abs(char_center_time - pos) < min_distance for pos in used_positions)
                if is_overlapping:
                    offset = min_distance * (1 if i % 2 == 0 else -1)
                    char_center_time = max(xlim[0], min(xlim[1], char_center_time + offset))
                
                used_positions.append(char_center_time)
                
                # 🎨 获取字符对应位置的标准音高
                char_pitch = self._find_pitch_at_time_in_range(char_center_time, times, standard_pitch)
                if char_pitch is None or np.isnan(char_pitch):
                    char_pitch = ylim[0] + y_range * 0.2  # 默认位置
                
                # 计算标注位置
                annotation_y = char_pitch + tts_annotation_y_offset
                
                # 获取声调颜色
                tone_color = tts_tone_colors.get(i, '#2E86AB')  # 默认使用标准音高颜色
                
                # 根据置信度调整透明度
                alpha = max(0.6, confidence)
                
                # 🔤 绘制TTS文本标注
                # 1. 添加背景区域指示字符时间范围
                if end_time - start_time > 0.02:  # 只对有意义的时间段绘制背景
                    rect = plt.Rectangle((start_time, char_pitch), 
                                       end_time - start_time, tts_annotation_y_offset * 0.5,
                                       facecolor=tone_color, alpha=0.1, 
                                       edgecolor=tone_color, linewidth=0.8, linestyle=':')
                    ax.add_patch(rect)
                
                # 2. 添加汉字标注
                bbox_props = dict(boxstyle='round,pad=0.3', 
                                facecolor=tone_color, alpha=alpha, 
                                edgecolor='white', linewidth=1.5)
                
                self._set_text_with_font(ax, 'text', char_center_time, annotation_y, char,
                       ha='center', va='center', fontsize=14, fontweight='bold',
                       color='white', alpha=alpha,
                       bbox=bbox_props, zorder=12)
                
                # 3. 添加连接线到标准音高曲线
                ax.plot([char_center_time, char_center_time], 
                       [char_pitch + tts_annotation_y_offset * 0.1, annotation_y - y_range * 0.02], 
                       color=tone_color, alpha=alpha * 0.7, linewidth=1.5, 
                       linestyle='--', zorder=8)
                
                # 4. 在标准音高曲线上添加精确定位点
                ax.plot(char_center_time, char_pitch, 'o', 
                       color=tone_color, markersize=6, alpha=alpha, 
                       markeredgecolor='white', markeredgewidth=1, zorder=10)
                
                # 5. 添加时间信息（为较长的字符）
                if end_time - start_time > 0.15 and confidence > 0.7:
                    time_text = f'{start_time:.2f}s'
                    ax.text(char_center_time, annotation_y + y_range * 0.03, time_text,
                           ha='center', va='bottom', fontsize=7, 
                           color=tone_color, alpha=0.8, 
                           fontproperties=self._get_font_properties(7))
            
            # 🏷️ 添加TTS文本标注说明
            ax.text(0.02, 0.95, '🎯 蓝色标注: TTS标准发音文本', 
                   transform=ax.transAxes, fontsize=10, fontweight='600',
                   color=self.colors['standard'], alpha=0.9,
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                           alpha=0.9, edgecolor=self.colors['standard'], linewidth=1))
            
            # 📊 添加时间戳质量指示
            alignment_quality = tts_timestamp_data.get('alignment_quality', 0.0)
            quality_text = f"时间戳质量: {alignment_quality:.1%}"
            quality_color = self.colors['good'] if alignment_quality > 0.7 else self.colors['warning']
            
            ax.text(0.98, 0.95, quality_text, 
                   transform=ax.transAxes, fontsize=9, ha='right',
                   color=quality_color, alpha=0.8,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                           alpha=0.8, edgecolor=quality_color, linewidth=1))
            
            print(f"✅ TTS文本标注添加完成: {len(aligned_chars)}个字符")
            
        except Exception as e:
            print(f"添加TTS文本标注失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_pitch_at_time_in_range(self, target_time: float, times: np.ndarray, 
                                   pitch_values: np.ndarray) -> float:
        """
        在指定时间范围内找到对应的音高值
        """
        try:
            if len(times) == 0 or len(pitch_values) == 0:
                return None
            
            # 确保时间在有效范围内
            if target_time < times[0] or target_time > times[-1]:
                return None
            
            # 找到最接近的时间索引
            time_diffs = np.abs(times - target_time)
            min_idx = np.argmin(time_diffs)
            
            # 检查音高值是否有效
            pitch_value = pitch_values[min_idx]
            if np.isnan(pitch_value):
                # 如果当前点无效，尝试找附近的有效点
                for offset in range(1, min(10, len(pitch_values) // 4)):
                    # 先检查左侧
                    if min_idx - offset >= 0 and not np.isnan(pitch_values[min_idx - offset]):
                        return pitch_values[min_idx - offset]
                    # 再检查右侧
                    if min_idx + offset < len(pitch_values) and not np.isnan(pitch_values[min_idx + offset]):
                        return pitch_values[min_idx + offset]
                return None
            
            return pitch_value
            
        except Exception as e:
            print(f"查找时间点音高失败: {e}")
            return None
    
    def _get_score_color(self, score):
        """根据分数返回颜色"""
        if score >= 80:
            return self.colors['good']
        elif score >= 60:
            return self.colors['warning']
        else:
            return self.colors['error']
    
    def _plot_enhanced_comparison(self, ax, times, standard_pitch, user_pitch, score_result, char_timestamps=None):
        """绘制增强版音高对比曲线"""
        
        # 计算差异
        pitch_diff = np.abs(user_pitch - standard_pitch)
        
        # 绘制标准发音曲线
        ax.plot(times, standard_pitch, color=self.colors['standard'], 
                linewidth=3, label='🎯 标准发音 (TTS)', alpha=0.9, zorder=3)
        
        # 绘制用户发音曲线
        ax.plot(times, user_pitch, color=self.colors['user'], 
                linewidth=3, label='🎤 您的发音', alpha=0.9, zorder=3)
        
        # 填充差异区域 - 用颜色深浅表示差异大小
        for i in range(len(times)-1):
            diff = pitch_diff[i]
            if diff > 50:  # 大差异
                color = self.colors['error']
                alpha = 0.4
            elif diff > 20:  # 中等差异
                color = self.colors['warning'] 
                alpha = 0.3
            else:  # 小差异
                color = self.colors['good']
                alpha = 0.2
            
            ax.fill_between([times[i], times[i+1]], 
                           [standard_pitch[i], standard_pitch[i+1]], 
                           [user_pitch[i], user_pitch[i+1]], 
                           color=color, alpha=alpha)
        
        # 🆕 添加汉字时间标注（带声调颜色）
        if char_timestamps:
            input_text_for_analysis = getattr(self, '_current_input_text', None)
            self._add_character_annotations(ax, char_timestamps, times, input_text_for_analysis)
        
        # 设置图表属性
        self._set_text_with_font(ax, 'xlabel', '时间 (秒)', fontsize=14, fontweight='bold')
        self._set_text_with_font(ax, 'ylabel', '基频 (Hz)', fontsize=14, fontweight='bold')  
        self._set_text_with_font(ax, 'title', '📊 音高曲线对比 - 实时差异分析', fontsize=16, fontweight='bold', pad=20)
        
        # 美化图例
        legend = ax.legend(fontsize=12, loc='upper right', 
                          frameon=True, fancybox=True, shadow=True,
                          prop=self._get_font_properties(12))
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)
        
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_facecolor('#fafafa')
        
        # 设置坐标轴刻度字体
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(10))
        
        # 设置y轴范围
        all_pitch = np.concatenate([standard_pitch[~np.isnan(standard_pitch)], 
                                   user_pitch[~np.isnan(user_pitch)]])
        if len(all_pitch) > 0:
            y_min = max(50, np.min(all_pitch) * 0.9)
            y_max = min(500, np.max(all_pitch) * 1.1)
            ax.set_ylim(y_min, y_max)
        
        # 添加差异统计信息
        avg_diff = np.nanmean(pitch_diff)
        max_diff = np.nanmax(pitch_diff)
        info_text = f'平均差异: {avg_diff:.1f} Hz\n最大差异: {max_diff:.1f} Hz'
        self._set_text_with_font(ax, 'text', 0.02, 0.98, info_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=11,
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
    
    def _add_character_annotations(self, ax, char_timestamps, times, input_text=None):
        """
        在音高曲线图上添加汉字时间标注（带声调颜色）
        :param ax: matplotlib轴对象
        :param char_timestamps: 字符时间戳列表，格式: [{'char': '你', 'start_time': 0.0, 'end_time': 0.5}, ...]
        :param times: 时间轴数组
        :param input_text: 输入文本（用于声调分析）
        """
        try:
            if not char_timestamps:
                return
            
            y_min, y_max = ax.get_ylim()
            x_min, x_max = ax.get_xlim()
            
            # 确保汉字标注使用与音高曲线图相同的时间轴范围
            print(f"音高曲线图时间轴范围: {x_min:.3f}s - {x_max:.3f}s")
            
            # 计算标注位置 - 紧贴音高曲线图底部，时间轴对齐
            annotation_y = y_min - (y_max - y_min) * 0.05  # 紧贴在x轴下方，减少空白间距
            
            # 🎵 初始化声调分析器
            tone_analyzer = self._initialize_tone_analyzer()
            text_for_analysis = input_text or ''.join([ci.get('char', '') for ci in char_timestamps])
            tone_colors = self._get_tone_colors_for_text(tone_analyzer, text_for_analysis, None, None)
            
            # 用于避免标注重叠的位置记录
            used_positions = []
            
            for i, char_info in enumerate(char_timestamps):
                char = char_info.get('char', '')
                start_time = char_info.get('start_time', 0)
                end_time = char_info.get('end_time', start_time + 0.1)
                
                # 跳过空字符或无效时间
                if not char or start_time >= end_time:
                    continue
                
                # 检查时间是否在当前图表范围内
                if end_time < x_min or start_time > x_max:
                    continue
                
                # 🎯 精确计算字符在音高曲线上的时间位置
                char_center_time = self._calculate_precise_char_position(start_time, end_time, times)
                
                # 🔍 进一步验证时间位置的有效性
                if char_center_time < x_min or char_center_time > x_max:
                    # 如果计算的位置超出了图表范围，调整到边界内
                    char_center_time = max(x_min, min(x_max, char_center_time))
                    print(f"⚠️ 字符'{char}'位置超出范围，已调整到: {char_center_time:.3f}s")
                
                # 避免标注重叠 - 检查是否与已有标注太近
                min_distance = (x_max - x_min) * 0.03  # 最小间距为图表宽度的3%
                is_overlapping = any(abs(char_center_time - pos) < min_distance for pos in used_positions)
                
                if is_overlapping:
                    # 如果重叠，稍微调整位置
                    offset = min_distance * (1 if i % 2 == 0 else -1)
                    char_center_time = max(x_min, min(x_max, char_center_time + offset))
                
                used_positions.append(char_center_time)
                
                # 🎵 获取字符的声调颜色
                tone_color = tone_colors.get(i, '#cccccc')  # 默认灰色
                
                # 🎨 绘制字符对应的音高曲线背景区域
                if end_time - start_time > 0.05:  # 只对足够长的段绘制背景
                    # 将背景区域扩展到整个音高范围，使关联更明显
                    rect_height = y_max - y_min
                    rect = plt.Rectangle((start_time, y_min), 
                                       end_time - start_time, rect_height,
                                       facecolor=tone_color, alpha=0.15,  # 降低透明度避免干扰
                                       edgecolor=tone_color, linewidth=0.8)
                    ax.add_patch(rect)
                    
                    # 添加垂直分割线明确标记字符边界
                    for boundary_time in [start_time, end_time]:
                        if x_min <= boundary_time <= x_max:
                            ax.axvline(x=boundary_time, color=tone_color, linestyle='--', 
                                     alpha=0.6, linewidth=1.5, zorder=3)
                
                # 🎨 添加汉字标注 - 使用声调颜色背景
                self._set_text_with_font(ax, 'text', char_center_time, annotation_y, char,
                       ha='center', va='center', fontsize=16, fontweight='bold',
                       color='white',  # 白色文字在彩色背景上更清晰
                       bbox=dict(boxstyle='round,pad=0.4', 
                               facecolor=tone_color,  # 使用声调颜色作为背景
                               edgecolor='darkblue', 
                               alpha=0.9,
                               linewidth=2.0,
                               zorder=10))  # 设置高层级，确保在最上层显示
                
                # 🔗 添加精确的字符-曲线对应关系指示线
                if end_time - start_time > 0.05:  # 对有意义的时间段添加连接线
                    # 从汉字位置向上连接到音高曲线底部
                    line_y_start = annotation_y + (y_max - y_min) * 0.02  # 从汉字上方开始
                    line_y_end = y_min + (y_max - y_min) * 0.02  # 到音高曲线底部
                    
                    # 主连接线：从字符中心到曲线
                    ax.plot([char_center_time, char_center_time], 
                           [line_y_start, line_y_end],
                           color=tone_color, linestyle='-', alpha=0.8, linewidth=2.5, zorder=6)
                    
                    # 辅助连接线：标记字符起始和结束位置
                    for boundary_time, line_style in [(start_time, ':'), (end_time, ':')]:
                        if x_min <= boundary_time <= x_max and abs(boundary_time - char_center_time) > 0.02:
                            ax.plot([boundary_time, boundary_time], 
                                   [line_y_start + (y_max - y_min) * 0.01, line_y_end - (y_max - y_min) * 0.01],
                                   color=tone_color, linestyle=line_style, alpha=0.5, linewidth=1.0, zorder=4)
                
                # 🕰️ 添加时间范围标注和持续时间显示
                if end_time - start_time > 0.15:  # 降低门槛，显示更多时间信息
                    duration = end_time - start_time
                    time_text = f'{start_time:.2f}-{end_time:.2f}s ({duration:.2f}s)'
                    self._set_text_with_font(ax, 'text', char_center_time, annotation_y - (y_max - y_min) * 0.04,
                           time_text, ha='center', va='center', fontsize=6, 
                           color='darkblue', alpha=0.7,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='none'))
            
            # 🎵 添加增强的声调图例和时间轴信息
            self._add_enhanced_tone_legend(ax, y_max, x_max, char_timestamps)
            
            # 调整y轴范围以容纳标注，确保汉字完全可见，但减少空白空间
            ax.set_ylim(annotation_y - (y_max - y_min) * 0.08, y_max)  # 减少底部空间，紧凑布局
            
        except Exception as e:
            print(f"添加汉字标注失败: {e}")
            # 不影响主图绘制，继续执行
    
    def _extract_char_timestamps_from_vad(self, vad_result):
        """
        从VAD结果中提取字符时间戳数据
        :param vad_result: VAD处理结果
        :return: 字符时间戳列表
        """
        try:
            if not vad_result:
                return None
            
            char_timestamps = []
            
            # 方法1: 从vad_text_mapping中提取
            if vad_result.get('vad_text_mapping'):
                for mapping in vad_result['vad_text_mapping']:
                    expected_text = mapping.get('expected_text', '')
                    start_time = mapping.get('vad_start', 0)
                    end_time = mapping.get('vad_end', start_time + 0.1)
                    
                    if expected_text and end_time > start_time:
                        # 将文本分割为单个字符，并估算每个字符的时间
                        chars = list(expected_text.strip())
                        if len(chars) > 0:
                            duration_per_char = (end_time - start_time) / len(chars)
                            
                            for i, char in enumerate(chars):
                                if char.strip():  # 跳过空白字符
                                    char_start = start_time + i * duration_per_char
                                    char_end = char_start + duration_per_char
                                    
                                    char_timestamps.append({
                                        'char': char,
                                        'start_time': char_start,
                                        'end_time': char_end
                                    })
            
            # 方法2: 从expected_text和总时长估算（备用方案）
            elif vad_result.get('expected_text'):
                expected_text = vad_result['expected_text']
                
                # 尝试从VAD段获取总时长
                total_duration = 0
                if vad_result.get('vad_segments'):
                    total_duration = max(end for start, end in vad_result['vad_segments'])
                
                if total_duration > 0 and expected_text:
                    chars = list(expected_text.strip())
                    if len(chars) > 0:
                        duration_per_char = total_duration / len(chars)
                        
                        for i, char in enumerate(chars):
                            if char.strip():
                                char_start = i * duration_per_char
                                char_end = char_start + duration_per_char
                                
                                char_timestamps.append({
                                    'char': char,
                                    'start_time': char_start,
                                    'end_time': char_end
                                })
            
            return char_timestamps if char_timestamps else None
            
        except Exception as e:
            print(f"从VAD结果提取字符时间戳失败: {e}")
            return None
    
    def _generate_simple_char_timestamps(self, input_text, times):
        """
        为输入文本生成简单的字符时间戳（均匀分布）
        :param input_text: 输入的文本
        :param times: 时间轴数组
        :return: 字符时间戳列表
        """
        try:
            if not input_text or len(times) == 0:
                return None
            
            # 清理文本，只保留有意义的字符
            chars = [char for char in input_text.strip() if char.strip()]
            if not chars:
                return None
            
            # 计算总时长
            total_duration = times[-1] - times[0]
            if total_duration <= 0:
                return None
            
            # 均匀分配时间给每个字符
            duration_per_char = total_duration / len(chars)
            start_time = times[0]
            
            char_timestamps = []
            for i, char in enumerate(chars):
                char_start = start_time + i * duration_per_char
                char_end = char_start + duration_per_char
                
                char_timestamps.append({
                    'char': char,
                    'start_time': char_start,
                    'end_time': char_end
                })
            
            return char_timestamps
            
        except Exception as e:
            print(f"生成简单字符时间戳失败: {e}")
            return None
    
    def _plot_enhanced_comparison_with_text(self, ax, times, standard_pitch, user_pitch, score_result, vad_result):
        """绘制带文本标注的增强版音高对比曲线"""
        
        # 提取字符时间戳数据
        char_timestamps = self._extract_char_timestamps_from_vad(vad_result)
        
        # 🎵 保存VAD结果中的期望文本供声调分析使用
        expected_text = vad_result.get('expected_text', '') if vad_result else ''
        self._current_input_text = expected_text
        
        # 先绘制基础对比曲线（包含汉字标注）
        self._plot_enhanced_comparison(ax, times, standard_pitch, user_pitch, score_result, char_timestamps)
        
        # 添加VAD区域标注
        if vad_result and vad_result.get('vad_segments'):
            y_min, y_max = ax.get_ylim()
            
            # 绘制VAD语音活动区域
            for i, (start_time, end_time) in enumerate(vad_result['vad_segments']):
                # 为每个VAD段添加背景色
                ax.axvspan(start_time, end_time, alpha=0.15, color='green', 
                          label='语音活动区域' if i == 0 else "")
                
                # 添加区域编号
                mid_time = (start_time + end_time) / 2
                self._set_text_with_font(ax, 'text', mid_time, y_max * 0.95, f'段{i+1}', 
                       ha='center', va='top', fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))
        
        # 更新图例
        handles, labels = ax.get_legend_handles_labels()
        if any('语音活动区域' in label for label in labels):
            ax.legend(handles, labels, fontsize=11, loc='upper right', 
                     frameon=True, fancybox=True, shadow=True,
                     prop=self._get_font_properties(11))
    
    def _plot_text_alignment(self, ax, vad_result):
        """绘制文本时域对齐图"""
        ax.clear()
        
        if not vad_result or not vad_result.get('vad_text_mapping'):
            ax.text(0.5, 0.5, '暂无文本对齐数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14, color='gray')
            ax.set_title('📝 文本时域对齐分析', fontsize=14, fontweight='bold')
            ax.axis('off')
            return
        
        # 获取数据
        text_mapping = vad_result['vad_text_mapping']
        expected_text = vad_result.get('expected_text', '')
        
        # 设置图表
        ax.set_xlim(0, max(mapping['vad_end'] for mapping in text_mapping) if text_mapping else 1)
        ax.set_ylim(-0.5, len(text_mapping) + 0.5)
        
        # 绘制每个VAD段的文本对齐
        for i, mapping in enumerate(text_mapping):
            y_pos = len(text_mapping) - 1 - i  # 从上到下显示
            
            # VAD段时间范围
            start_time = mapping['vad_start']
            end_time = mapping['vad_end']
            duration = end_time - start_time
            
            # 期望文本
            expected = mapping.get('expected_text', '')
            recognized = mapping.get('recognized_text', '')
            match_quality = mapping.get('match_quality', 0.0)
            
            # 根据匹配质量选择颜色
            if match_quality >= 0.8:
                color = self.colors['good']
                alpha = 0.8
            elif match_quality >= 0.5:
                color = self.colors['warning']
                alpha = 0.7
            else:
                color = self.colors['error']
                alpha = 0.6
            
            # 绘制时间段背景
            rect = Rectangle((start_time, y_pos - 0.3), duration, 0.6, 
                           facecolor=color, alpha=alpha, edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            
            # 添加文本标注
            mid_time = (start_time + end_time) / 2
            
            # 期望文本（上方） - 调整间距避免重叠
            if expected:
                self._set_text_with_font(ax, 'text', mid_time, y_pos + 0.15, f'标准: {expected}', 
                       ha='center', va='bottom', fontsize=9, fontweight='bold',
                       color='darkblue')
            
            # 识别文本（下方） - 调整间距避免重叠
            if recognized:
                self._set_text_with_font(ax, 'text', mid_time, y_pos - 0.15, f'识别: {recognized}', 
                       ha='center', va='top', fontsize=9, 
                       color='darkred' if match_quality < 0.5 else 'darkgreen')
            
            # 时间标注 - 调整位置和字体大小
            self._set_text_with_font(ax, 'text', start_time, y_pos - 0.4, f'{start_time:.2f}s', 
                   ha='left', va='top', fontsize=7, color='gray')
            self._set_text_with_font(ax, 'text', end_time, y_pos - 0.4, f'{end_time:.2f}s', 
                   ha='right', va='top', fontsize=7, color='gray')
            
            # 匹配质量指示 - 调整位置和字体大小
            quality_text = f'{match_quality:.1%}'
            self._set_text_with_font(ax, 'text', end_time + 0.1, y_pos, quality_text, 
                   ha='left', va='center', fontsize=8, fontweight='bold',
                   color=color)
        
        # 设置标签
        segment_labels = [f'段{i+1}' for i in range(len(text_mapping))]
        ax.set_yticks(range(len(text_mapping)))
        ax.set_yticklabels(reversed(segment_labels))  # 从上到下显示
        
        self._set_text_with_font(ax, 'xlabel', '时间 (秒)', fontsize=11, fontweight='bold')
        self._set_text_with_font(ax, 'title', '📝 文本时域对齐分析 - 语音段与文字对应关系', 
               fontsize=12, fontweight='bold')
        
        # 设置坐标轴刻度字体 - 文本对齐图专用
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(9))
        
        ax.grid(True, alpha=0.3, axis='x')
        
        # 添加图例 - 调整字体大小
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['good'], alpha=0.8, label='匹配良好 (≥80%)'),
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['warning'], alpha=0.7, label='匹配一般 (≥50%)'),
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['error'], alpha=0.6, label='匹配较差 (<50%)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9,
                 prop=self._get_font_properties(9))
        
        # 添加统计信息 - 调整字体大小
        if text_mapping:
            avg_quality = sum(m.get('match_quality', 0) for m in text_mapping) / len(text_mapping)
            total_words = sum(m.get('word_count', 0) for m in text_mapping)
            info_text = f'平均匹配度: {avg_quality:.1%}\n总词数: {total_words}'
            self._set_text_with_font(ax, 'text', 0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))
    
    def _plot_score_overview(self, ax, score_result):
        """绘制评分总览"""
        ax.clear()
        ax.axis('off')
        
        total_score = score_result['total_score']
        level = score_result['level']
        
        # 绘制大分数 - 调整字体大小避免重叠
        color = self._get_score_color(total_score)
        self._set_text_with_font(ax, 'text', 0.5, 0.65, f'{total_score:.1f}', 
               horizontalalignment='center', verticalalignment='center',
               fontsize=32, fontweight='bold', color=color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.45, '分', 
               horizontalalignment='center', verticalalignment='center',
               fontsize=16, color=color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.25, level, 
               horizontalalignment='center', verticalalignment='center',
               fontsize=12, fontweight='bold', color=color, transform=ax.transAxes)
        
        # 添加背景圆圈 - 调整大小避免与文字重叠
        circle = plt.Circle((0.5, 0.45), 0.35, transform=ax.transAxes, 
                           fill=False, linewidth=2, color=color, alpha=0.3)
        ax.add_patch(circle)
        
        self._set_text_with_font(ax, 'title', '🏆 总体评分', fontsize=12, fontweight='bold', pad=8)
    
    def _plot_component_scores(self, ax, component_scores):
        """绘制各项能力评分"""
        
        # 准备数据
        categories = ['准确性', '变化性', '稳定性', '适配性']
        scores = [
            component_scores.get('accuracy', 0),
            component_scores.get('trend', 0),
            component_scores.get('stability', 0),
            component_scores.get('range', 0)
        ]
        
        # 创建颜色列表
        colors = [self._get_score_color(score) for score in scores]
        
        # 绘制水平条形图 - 调整高度和字体大小
        y_pos = np.arange(len(categories))
        bars = ax.barh(y_pos, scores, color=colors, alpha=0.7, height=0.5)
        
        # 添加分数标签 - 调整位置避免重叠
        for i, (bar, score) in enumerate(zip(bars, scores)):
            width = bar.get_width()
            self._set_text_with_font(ax, 'text', width + 2, bar.get_y() + bar.get_height()/2,
                   f'{score:.0f}', ha='left', va='center', fontsize=9, fontweight='bold')
        
        # 设置图表属性 - 调整字体大小
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=9, fontproperties=self._get_font_properties(9))
        self._set_text_with_font(ax, 'xlabel', '得分', fontsize=10, fontweight='bold')
        self._set_text_with_font(ax, 'title', '🎯 各项能力评分', fontsize=12, fontweight='bold')
        ax.set_xlim(0, 105)  # 增加右侧空间给分数标签
        ax.grid(True, alpha=0.3, axis='x')
        
        # 设置坐标轴刻度字体 - 调整字体大小
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(8))
        
        # 添加参考线 - 调整透明度避免干扰
        ax.axvline(x=60, color='orange', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=80, color='green', linestyle='--', alpha=0.5, linewidth=1)
    
    
    def _plot_main_comparison(self, ax, times, standard_pitch, user_pitch):
        """绘制主要的音高对比曲线"""
        
        # 绘制标准发音
        ax.plot(times, standard_pitch, color=self.colors['standard'], 
                linewidth=3, label='标准发音', alpha=0.8)
        
        # 绘制用户发音
        ax.plot(times, user_pitch, color=self.colors['user'], 
                linewidth=3, label='用户发音', alpha=0.8)
        
        # 填充差异区域
        ax.fill_between(times, standard_pitch, user_pitch, 
                       alpha=0.2, color='gray', label='差异区域')
        
        # 设置图表属性
        ax.set_xlabel('时间 (秒)', fontsize=14)
        ax.set_ylabel('基频 (Hz)', fontsize=14)
        ax.set_title('音高曲线对比', fontsize=16, weight='bold', pad=20)
        ax.legend(fontsize=12, loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # 设置y轴范围
        all_pitch = np.concatenate([standard_pitch[~np.isnan(standard_pitch)], 
                                   user_pitch[~np.isnan(user_pitch)]])
        if len(all_pitch) > 0:
            y_min = max(50, np.min(all_pitch) * 0.9)
            y_max = min(500, np.max(all_pitch) * 1.1)
            ax.set_ylim(y_min, y_max)
    
    def _plot_score_radar(self, ax, component_scores):
        """绘制评分雷达图"""
        
        # 准备数据
        categories = ['音高准确性', '音调变化', '发音稳定性', '音域适配']
        scores = [
            component_scores.get('accuracy', 0),
            component_scores.get('trend', 0),
            component_scores.get('stability', 0),
            component_scores.get('range', 0)
        ]
        
        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        scores += scores[:1]  # 闭合图形
        angles += angles[:1]
        
        # 清除坐标轴
        ax.clear()
        
        # 绘制雷达图
        ax = plt.subplot(111, projection='polar')
        ax.plot(angles, scores, color=self.colors['user'], linewidth=2, marker='o')
        ax.fill(angles, scores, color=self.colors['user'], alpha=0.25)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        
        # 设置评分范围
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)
        
        ax.set_title('各项评分', fontsize=12, weight='bold', pad=20)
    
    def _plot_statistics(self, ax, metrics):
        """绘制统计信息"""
        
        # 准备统计数据
        stats_text = [
            f"相关系数: {metrics.get('correlation', 0):.3f}",
            f"均方根误差: {metrics.get('rmse', 0):.1f} Hz",
            f"趋势一致性: {metrics.get('trend_consistency', 0):.1%}",
            f"有效数据点: {metrics.get('valid_points', 0)}",
            f"标准音高: {metrics.get('std_mean', 0):.1f} Hz",
            f"用户音高: {metrics.get('user_mean', 0):.1f} Hz"
        ]
        
        # 清除坐标轴
        ax.clear()
        ax.axis('off')
        
        # 添加文本
        for i, text in enumerate(stats_text):
            ax.text(0.1, 0.9 - i * 0.15, text, fontsize=11, 
                   transform=ax.transAxes, verticalalignment='top')
        
        ax.set_title('统计信息', fontsize=12, weight='bold')
    
    
    def _plot_error_message(self, error_message: str, output_path: str) -> bool:
        """绘制错误信息图"""
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f"错误: {error_message}", 
                   fontsize=16, ha='center', va='center',
                   transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))
            
            ax.set_title('音高分析失败', fontsize=18, weight='bold')
            ax.axis('off')
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            return True
            
        except Exception as e:
            print(f"绘制错误信息失败: {e}")
            return False
    
    def plot_individual_pitch(self, pitch_data: dict, output_path: str, 
                            title: str = "音高曲线（真实特征）", text: str = "", fig_size=(14, 8)) -> bool:
        """
        绘制单个音高曲线 - 显示归一化后的真实语音特征
        不进行平滑处理，保留音高的自然变化和分段特征
        :param pitch_data: 音高数据
        :param output_path: 输出路径
        :param title: 图表标题
        :param text: 对应的文本内容（用于声调分析）
        :param fig_size: 图片尺寸
        :return: 是否成功
        """
        print("🚨🚨🚨 CALLED plot_individual_pitch 🚨🚨🚨")
        print(f"🚨 Args: text='{text}', output_path={output_path}")
        
        try:
            times = pitch_data.get('times', [])
            # 🎯 使用原始音高数据，不使用平滑处理的数据
            pitch_values = pitch_data.get('pitch_values', [])
            
            if len(times) == 0 or len(pitch_values) == 0:
                return self._plot_error_message("音高数据为空", output_path)
            
            fig, ax = plt.subplots(figsize=fig_size)
            
            # 如果有文本，获取声调颜色
            tone_colors = []
            print(f"🔍 DEBUG: plot_individual_pitch - text='{text}', text.strip()='{text.strip() if text else None}'")
            
            if text and text.strip():
                tone_analyzer = self._initialize_tone_analyzer()
                print(f"🔍 DEBUG: tone_analyzer={tone_analyzer}")
                tone_colors_dict = self._get_tone_colors_for_text(tone_analyzer, text.strip(), pitch_values, times)
                print(f"🔍 DEBUG: tone_colors_dict={tone_colors_dict}")
                # 转换为列表
                tone_colors = [tone_colors_dict.get(i, '#cccccc') for i in range(len(text.strip()))]
                print(f"🔍 DEBUG: tone_colors={tone_colors}")
            else:
                print(f"🔍 DEBUG: 跳过声调分析 - text empty or None")
            
            # 绘制音高曲线
            if tone_colors and len(tone_colors) > 1:
                # 按段绘制不同声调的音高曲线
                chars_per_segment = len(times) // len(tone_colors)
                
                for i, color in enumerate(tone_colors):
                    start_idx = i * chars_per_segment
                    end_idx = (i + 1) * chars_per_segment if i < len(tone_colors) - 1 else len(times)
                    
                    if start_idx < len(times) and end_idx <= len(times):
                        segment_times = times[start_idx:end_idx]
                        segment_pitch = pitch_values[start_idx:end_idx]
                        
                        ax.plot(segment_times, segment_pitch, 'o-', color=color, 
                               markersize=3, linewidth=2, alpha=0.8)
            else:
                # 使用默认颜色绘制整条曲线
                ax.plot(times, pitch_values, 'o-', color=self.colors['standard'], 
                       markersize=3, linewidth=2, alpha=0.8)
            
            # 设置图表属性 - 使用正确的中文字体
            self._set_text_with_font(ax, 'xlabel', '时间 (秒)', fontsize=12)
            self._set_text_with_font(ax, 'ylabel', '基频 (Hz)', fontsize=12)
            self._set_text_with_font(ax, 'title', title, fontsize=16, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # 设置y轴范围
            pitch_array = np.array(pitch_values)
            valid_pitch = pitch_array[~np.isnan(pitch_array)]
            if len(valid_pitch) > 0:
                y_min = max(50, np.min(valid_pitch) * 0.9)
                y_max = min(500, np.max(valid_pitch) * 1.1)
                ax.set_ylim(y_min, y_max)
            
            # 🕐 设置时间轴范围
            if len(times) > 0:
                time_max = max(times)
                print(f"🕐 DEBUG: 时间范围 - 最小:{min(times):.2f}s, 最大:{time_max:.2f}s")
                # 确保显示完整时间范围，不限制在1秒内
                ax.set_xlim(0, max(time_max, 1.0))  # 至少显示1秒，如果音频更长则完整显示
            
            # 添加汉字标注（如果有文本）
            print(f"🔍 DEBUG: 汉字标注条件检查 - text={bool(text)}, text.strip()={bool(text.strip() if text else False)}, tone_colors={bool(tone_colors)}")
            if text and text.strip() and tone_colors:
                print(f"🔍 DEBUG: 开始添加汉字标注")
                self._add_character_annotations_individual(
                    ax, text.strip(), times, pitch_values, tone_colors
                )
            else:
                print(f"🔍 DEBUG: 跳过汉字标注 - 条件不满足")
                
                # 添加增强的声调图例
                y_limits = ax.get_ylim()
                x_limits = ax.get_xlim()
                
                # 创建字符时间戳用于增强图例
                char_timestamps = []
                if len(tone_colors) > 0:
                    chars_per_segment = len(times) // len(tone_colors)
                    for i, char in enumerate(text.strip()):
                        start_idx = i * chars_per_segment
                        end_idx = (i + 1) * chars_per_segment if i < len(tone_colors) - 1 else len(times)
                        if start_idx < len(times) and end_idx <= len(times):
                            char_timestamps.append({
                                'char': char,
                                'start_time': times[start_idx] if start_idx < len(times) else 0,
                                'end_time': times[min(end_idx-1, len(times)-1)] if end_idx > 0 else 0
                            })
                
                self._add_enhanced_tone_legend(ax, y_limits[1], x_limits[1], char_timestamps)
            
            # 添加统计信息 - 反映原始音高曲线的真实特征
            duration = pitch_data.get('duration', 0)
            valid_ratio = pitch_data.get('valid_ratio', 0)
            mean_pitch = np.nanmean(pitch_array)
            
            info_text = f"时长: {duration:.2f}s\n有效比例: {valid_ratio:.1%}\n平均音高: {mean_pitch:.1f}Hz\n(原始特征，未平滑)"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   fontproperties=self._get_font_properties(10),
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # 保存图片
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            print(f"音高曲线图已保存至: {output_path}")
            return True
            
        except Exception as e:
            print(f"绘制音高曲线失败: {e}")
            return False
    
    def _add_character_annotations_individual(self, ax, text: str, times: list, 
                                           pitch_values: list, tone_colors: list):
        """
        为单个音高图添加增强的汉字标注
        """
        try:
            if not text or len(text) == 0:
                return
            
            # 🎯 使用改进的精确字符位置计算
            chars_per_segment = len(times) // len(text)
            
            # 计算每个字符的精确时间位置
            for i, char in enumerate(text):
                if i < len(tone_colors):
                    # 🎯 精确计算字符对应的时间段
                    start_idx = i * chars_per_segment
                    end_idx = (i + 1) * chars_per_segment if i < len(text) - 1 else len(times)
                    
                    if start_idx < len(times) and end_idx <= len(times):
                        # 计算字符的中心时间
                        char_start_time = times[start_idx]
                        char_end_time = times[min(end_idx-1, len(times)-1)]
                        char_center_time = (char_start_time + char_end_time) / 2
                        
                        # 获取字符时间段的平均音高
                        segment_pitch = pitch_values[start_idx:end_idx]
                        valid_pitch = [p for p in segment_pitch if not np.isnan(p)]
                        
                        if valid_pitch:
                            char_pitch = np.mean(valid_pitch)
                            color = tone_colors[i]
                            
                            # 🎨 增强的汉字标注设计
                            # 添加字符时间范围的背景区域
                            y_min, y_max = ax.get_ylim()
                            background_height = (y_max - y_min) * 0.08
                            
                            # 背景矩形
                            rect = plt.Rectangle((char_start_time, y_min), 
                                               char_end_time - char_start_time, 
                                               background_height,
                                               facecolor=color, alpha=0.15, 
                                               edgecolor=color, linewidth=1, linestyle='--')
                            ax.add_patch(rect)
                            
                            # 🎯 精确的汉字标注位置
                            annotation_y = char_pitch + (y_max - y_min) * 0.06
                            
                            # 汉字标注
                            ax.annotate(char, 
                                      xy=(char_center_time, char_pitch),
                                      xytext=(char_center_time, annotation_y),
                                      ha='center', va='center',
                                      fontsize=16, fontweight='bold',
                                      color='white',
                                      fontproperties=self._get_font_properties(16, 'bold'),
                                      bbox=dict(boxstyle='round,pad=0.4', 
                                              facecolor=color, alpha=0.9, 
                                              edgecolor='black', linewidth=1),
                                      arrowprops=dict(arrowstyle='->', 
                                                    connectionstyle='arc3,rad=0',
                                                    color=color, alpha=0.8, lw=2))
                            
                            # 🔗 添加连接线到时间轴
                            ax.plot([char_center_time, char_center_time], 
                                   [y_min, char_pitch], 
                                   color=color, alpha=0.5, linewidth=1, linestyle=':')
                            
                            # ⏰ 时间信息标注
                            time_text = f"{char_start_time:.2f}-{char_end_time:.2f}s"
                            ax.text(char_center_time, y_min + background_height/2, 
                                   time_text, ha='center', va='center', fontsize=8, 
                                   color='darkblue', alpha=0.8,
                                   fontproperties=self._get_font_properties(8),
                                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='none'))
                        
        except Exception as e:
            print(f"添加汉字标注失败: {e}")
    
    def _find_pitch_at_time(self, target_time: float, times: list, pitch_values: list):
        """
        找到指定时间最接近的音高值
        """
        try:
            if not times or not pitch_values:
                return None
            
            # 找到最接近的时间索引
            time_diffs = [abs(t - target_time) for t in times]
            min_idx = time_diffs.index(min(time_diffs))
            
            return pitch_values[min_idx]
        except Exception:
            return None
    
    def create_progress_chart(self, history_scores: list, output_path: str) -> bool:
        """
        创建练习进度图表
        :param history_scores: 历史评分列表
        :param output_path: 输出路径
        :return: 是否成功
        """
        
        if len(history_scores) < 2:
            return self._plot_error_message("需要至少2次练习记录", output_path)
        
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 练习次数
            attempts = list(range(1, len(history_scores) + 1))
            
            # 总分趋势
            total_scores = [score.get('total_score', 0) for score in history_scores]
            ax1.plot(attempts, total_scores, 'o-', color=self.colors['user'], 
                    linewidth=3, markersize=8, label='总分')
            ax1.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='良好线(80分)')
            ax1.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='及格线(60分)')
            
            ax1.set_xlabel('练习次数', fontsize=12)
            ax1.set_ylabel('总分', fontsize=12)
            ax1.set_title('练习进度 - 总分趋势', fontsize=14, weight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0, 100)
            
            # 各项能力趋势
            accuracy_scores = [(score.get('component_scores') or {}).get('accuracy', 0) for score in history_scores]
            trend_scores = [(score.get('component_scores') or {}).get('trend', 0) for score in history_scores]
            stability_scores = [(score.get('component_scores') or {}).get('stability', 0) for score in history_scores]
            range_scores = [(score.get('component_scores') or {}).get('range', 0) for score in history_scores]
            
            ax2.plot(attempts, accuracy_scores, 'o-', label='音高准确性', linewidth=2)
            ax2.plot(attempts, trend_scores, 's-', label='音调变化', linewidth=2)
            ax2.plot(attempts, stability_scores, '^-', label='发音稳定性', linewidth=2)
            ax2.plot(attempts, range_scores, 'd-', label='音域适配', linewidth=2)
            
            ax2.set_xlabel('练习次数', fontsize=12)
            ax2.set_ylabel('各项得分', fontsize=12)
            ax2.set_title('练习进度 - 各项能力趋势', fontsize=14, weight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
            
            # 保存图片
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            print(f"进度图表已保存至: {output_path}")
            return True
            
        except Exception as e:
            print(f"绘制进度图表失败: {e}")
            return False
    
    def _initialize_tone_analyzer(self):
        """初始化声调分析器"""
        try:
            from chinese_tone_analyzer import ChineseToneAnalyzer
            return ChineseToneAnalyzer()
        except ImportError:
            print("⚠️ 无法导入声调分析器，将使用默认颜色")
            return None
        except Exception as e:
            print(f"⚠️ 声调分析器初始化失败: {e}")
            return None
    
    def _get_tone_colors_for_text(self, tone_analyzer, text, pitch_values=None, times=None):
        """
        获取文本中每个字符的声调颜色 - 基于音高分析
        :param tone_analyzer: 声调分析器
        :param text: 输入文本
        :param pitch_values: 音高数据（用于基于音高的声调分析）
        :param times: 时间数据
        :return: 字符索引到颜色的映射字典
        """
        # 📊 优化的声调颜色映射 - 根据声调特征设计直观颜色
        tone_colors_map = {
            0: '#B0B0B0',  # 轻声 - 浅灰色（轻柔、中性）
            1: '#E74C3C',  # 阴平 - 鲜红色（平稳、持续的高音）
            2: '#3498DB',  # 阳平 - 蓝色（从低到高的上升）
            3: '#F39C12',  # 上声 - 橙色（先降后升的曲折）
            4: '#27AE60'   # 去声 - 绿色（从高到低的下降）
        }
        
        try:
            if not tone_analyzer or not text:
                # 如果没有分析器或文本，返回默认颜色
                return {i: '#cccccc' for i in range(len(text))}
            
            # 基于音高分析声调（如果有音高数据）
            if pitch_values is not None and times is not None:
                print(f"🎵 使用音高数据分析声调: text='{text}'")
                tones = tone_analyzer.analyze_pitch_based_tones(pitch_values, times, text)
            else:
                print(f"🎵 无音高数据，使用默认声调分配: text='{text}'")
                # 如果没有音高数据，为每个字符分配不同的默认声调进行演示
                tones = [(i % 4) + 1 for i in range(len(text.strip()))]
            
            print(f"🎵 声调分析结果: text='{text}', tones={tones}")
            
            # 创建颜色映射
            color_mapping = {}
            for i, tone in enumerate(tones):
                color = tone_colors_map.get(tone, '#cccccc')
                color_mapping[i] = color
                if i < len(text):
                    print(f"🎨 字符'{text[i]}' -> 声调{tone} -> 颜色{color}")
            
            return color_mapping
            
        except Exception as e:
            print(f"⚠️ 声调颜色分析失败: {e}")
            # 返回默认颜色
            return {i: '#cccccc' for i in range(len(text) if text else 0)}
    
    def _calculate_precise_char_position(self, start_time, end_time, times):
        """
        🎯 精确计算字符在音高曲线上的时间位置
        增强时间轴匹配精度，确保汉字标注与音高曲线完美对齐
        :param start_time: 字符开始时间
        :param end_time: 字符结束时间
        :param times: 音高曲线的时间轴
        :return: 精确的字符中心时间位置
        """
        try:
            # 🎯 方法1: 高精度时间轴匹配
            if len(times) > 10:
                # 计算字符的有效时间中心点
                char_center_time = (start_time + end_time) / 2
                
                # 🔍 在有效时间范围内查找最接近的音高数据点
                valid_indices = np.where((times >= start_time) & (times <= end_time))[0]
                
                if len(valid_indices) > 0:
                    # 如果在时间范围内有数据点，选择中间位置的点
                    mid_idx = valid_indices[len(valid_indices) // 2]
                    precise_time = times[mid_idx]
                    print(f"🎯 字符精确匹配: {start_time:.3f}-{end_time:.3f}s -> {precise_time:.3f}s")
                    return precise_time
                else:
                    # 如果范围内没有数据点，找最接近中心点的
                    closest_idx = np.argmin(np.abs(times - char_center_time))
                    precise_time = times[closest_idx]
                    print(f"📍 字符近似匹配: {start_time:.3f}-{end_time:.3f}s -> {precise_time:.3f}s")
                    return precise_time
            else:
                # 方法2: 简单取中点（备用方案）
                return (start_time + end_time) / 2
                
        except Exception as e:
            print(f"⚠️ 计算字符精确位置失败: {e}")
            return (start_time + end_time) / 2
    
    def _add_tone_legend(self, ax, y_max, x_max):
        """
        添加声调图例到图表中
        :param ax: matplotlib轴对象
        :param y_max: y轴最大值
        :param x_max: x轴最大值
        """
        try:
            # 📊 更新声调标签和颜色 - 与声调特征匹配
            tone_labels = ['轻声', '阴平', '阳平', '上声', '去声']
            tone_colors = ['#B0B0B0', '#E74C3C', '#3498DB', '#F39C12', '#27AE60']
            
            # 在右上角添加图例
            legend_x = x_max * 0.85
            legend_y_start = y_max * 0.85
            
            # 添加图例标题
            self._set_text_with_font(ax, 'text', legend_x, legend_y_start + y_max * 0.05, 
                   '声调图例:', ha='left', va='bottom', fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            # 添加每个声调的图例项
            for i, (label, color) in enumerate(zip(tone_labels, tone_colors)):
                legend_y = legend_y_start - i * y_max * 0.04
                
                # 绘制颜色方块
                rect = plt.Rectangle((legend_x, legend_y - y_max * 0.01), 
                                   x_max * 0.02, y_max * 0.02,
                                   facecolor=color, alpha=0.8, 
                                   edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
                
                # 添加标签
                self._set_text_with_font(ax, 'text', legend_x + x_max * 0.03, legend_y, 
                       label, ha='left', va='center', fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
                
        except Exception as e:
            print(f"⚠️ 添加声调图例失败: {e}")
            
    def _add_enhanced_tone_legend(self, ax, y_max, x_max, char_timestamps=None):
        """
        🎵 添加增强的声调图例和时间轴信息
        :param ax: matplotlib轴对象
        :param y_max: y轴最大值
        :param x_max: x轴最大值
        :param char_timestamps: 字符时间戳信息（用于显示统计）
        """
        try:
            # 📊 声调标签、颜色和特征描述
            tone_info = [
                ('轻声', '#B0B0B0', '中性、轻柔'),
                ('阴平', '#E74C3C', '高平、持续'),
                ('阳平', '#3498DB', '低升高、上扬'),
                ('上声', '#F39C12', '下降上升、曲折'),
                ('去声', '#27AE60', '高降低、下降')
            ]
            
            # 计算图例位置 - 放在右上角，但避免遮挡曲线
            legend_x = x_max * 0.78
            legend_y_start = y_max * 0.92
            
            # 添加背景框
            legend_bg = plt.Rectangle((legend_x - x_max * 0.01, legend_y_start - y_max * 0.25), 
                                     x_max * 0.24, y_max * 0.28,
                                     facecolor='white', alpha=0.95, 
                                     edgecolor='darkblue', linewidth=1.5, zorder=15)
            ax.add_patch(legend_bg)
            
            # 添加图例标题
            self._set_text_with_font(ax, 'text', legend_x, legend_y_start, 
                   '🎵 声调颜色映射', ha='left', va='top', fontsize=11, fontweight='bold',
                   color='darkblue', zorder=20)
            
            # 添加每个声调的详细信息
            for i, (label, color, description) in enumerate(tone_info):
                legend_y = legend_y_start - (i + 1) * y_max * 0.045
                
                # 绘制增强的颜色标识
                circle = plt.Circle((legend_x + x_max * 0.01, legend_y), 
                                   y_max * 0.008, facecolor=color, alpha=0.9, 
                                   edgecolor='white', linewidth=1.5, zorder=18)
                ax.add_patch(circle)
                
                # 添加声调名称和特征
                self._set_text_with_font(ax, 'text', legend_x + x_max * 0.025, legend_y, 
                       f'{label} - {description}', ha='left', va='center', fontsize=8,
                       color='black', zorder=20)
            
            # 添加时间轴对齐说明
            help_y = legend_y_start - len(tone_info) * y_max * 0.045 - y_max * 0.03
            self._set_text_with_font(ax, 'text', legend_x, help_y, 
                   '🎯 汉字位置与音高曲线时间轴对齐', 
                   ha='left', va='center', fontsize=7, style='italic',
                   color='darkgreen', zorder=20)
            
            # 添加统计信息（如果有字符时间戳）
            if char_timestamps:
                total_chars = len(char_timestamps)
                total_duration = sum(c.get('end_time', 0) - c.get('start_time', 0) for c in char_timestamps)
                avg_char_duration = total_duration / total_chars if total_chars > 0 else 0
                
                stats_y = help_y - y_max * 0.025
                stats_text = f'字符数: {total_chars} | 平均时长: {avg_char_duration:.2f}s'
                self._set_text_with_font(ax, 'text', legend_x, stats_y, 
                       stats_text, ha='left', va='center', fontsize=6,
                       color='gray', zorder=20)
                
        except Exception as e:
            print(f"⚠️ 添加增强声调图例失败: {e}")
            # 如果增强图例失败，使用简单版本
            self._add_simple_tone_legend(ax, y_max, x_max)
            
    def _add_simple_tone_legend(self, ax, y_max, x_max):
        """
        添加简单的声调图例（备用方案）
        """
        try:
            tone_labels = ['轻声', '阴平', '阳平', '上声', '去声']
            tone_colors = ['#B0B0B0', '#E74C3C', '#3498DB', '#F39C12', '#27AE60']
            
            legend_x = x_max * 0.85
            legend_y_start = y_max * 0.85
            
            for i, (label, color) in enumerate(zip(tone_labels, tone_colors)):
                legend_y = legend_y_start - i * y_max * 0.04
                rect = plt.Rectangle((legend_x, legend_y - y_max * 0.01), 
                                   x_max * 0.02, y_max * 0.02,
                                   facecolor=color, alpha=0.8, 
                                   edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
                
                self._set_text_with_font(ax, 'text', legend_x + x_max * 0.03, legend_y, 
                       label, ha='left', va='center', fontsize=9)
                
        except Exception as e:
            print(f"⚠️ 添加简单声调图例失败: {e}")
    
    def _plot_beautiful_comparison(self, ax, times, standard_pitch, user_pitch, input_text=None):
        """
        🎨 绘制美观的音高对比曲线 - 简洁现代风格
        """
        # 设置背景
        ax.set_facecolor(self.colors['background'])
        
        # 🎯 绘制标准发音曲线 - 使用更粗的线条和优雅的样式
        line_std = ax.plot(times, standard_pitch, color=self.colors['standard'], 
                          linewidth=4, label='● 标准发音 (TTS)', alpha=0.9, 
                          linestyle='-', marker='none', zorder=3)
        
        # 🎤 绘制用户发音曲线
        line_user = ax.plot(times, user_pitch, color=self.colors['user'], 
                           linewidth=4, label='◆ 您的发音', alpha=0.9,
                           linestyle='-', marker='none', zorder=3)
        
        # 🌟 添加柔和的差异填充区域
        ax.fill_between(times, standard_pitch, user_pitch, 
                       color=self.colors['difference'], alpha=0.2, 
                       interpolate=True, zorder=1, label='差异区域')
        
        # ✨ 设置优雅的图表属性
        self._set_text_with_font(ax, 'xlabel', '时间 (秒)', fontsize=14, fontweight='600', 
                               color=self.colors['text'])
        self._set_text_with_font(ax, 'ylabel', '基频 (Hz)', fontsize=14, fontweight='600',
                               color=self.colors['text'])
        self._set_text_with_font(ax, 'title', '■ 音高曲线对比分析', fontsize=16, fontweight='bold', 
                               color=self.colors['text'], pad=20)
        
        # 🎨 美化网格
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8, color=self.colors['accent'])
        ax.set_axisbelow(True)
        
        # 📊 优化y轴范围，确保曲线清晰可见
        all_pitch = np.concatenate([standard_pitch[~np.isnan(standard_pitch)], 
                                   user_pitch[~np.isnan(user_pitch)]])
        if len(all_pitch) > 0:
            y_min = max(50, np.min(all_pitch) * 0.85)
            y_max = min(500, np.max(all_pitch) * 1.15)
            ax.set_ylim(y_min, y_max)
        
        # 🎭 美化图例
        legend = ax.legend(fontsize=12, loc='upper right', 
                          frameon=True, fancybox=True, shadow=True,
                          prop=self._get_font_properties(12), 
                          edgecolor=self.colors['accent'], facecolor='white',
                          framealpha=0.95)
        legend.get_frame().set_linewidth(1.5)
        
        # 📝 添加简洁的统计信息
        pitch_diff = np.abs(user_pitch - standard_pitch)
        avg_diff = np.nanmean(pitch_diff)
        correlation = np.corrcoef(standard_pitch[~np.isnan(standard_pitch)], 
                                 user_pitch[~np.isnan(user_pitch)])[0,1] if len(all_pitch) > 10 else 0
        
        info_text = f'平均差异: {avg_diff:.1f} Hz\n相似度: {correlation:.2f}'
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=11, fontweight='500',
               fontproperties=self._get_font_properties(11),
               bbox=dict(boxstyle='round,pad=0.6', facecolor=self.colors['highlight'], 
                        alpha=0.9, edgecolor=self.colors['accent'], linewidth=1.2))
        
        # 🔧 调整边框和刻度
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
            spine.set_color(self.colors['accent'])
        
        ax.tick_params(colors=self.colors['text'], labelsize=10)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(10))
    
    def _plot_clean_score_dashboard(self, ax, score_result):
        """
        🏆 绘制简洁的评分仪表盘
        """
        ax.clear()
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        total_score = score_result['total_score']
        level = score_result['level']
        component_scores = score_result.get('component_scores', {})
        
        # 🎯 中心大分数显示
        score_color = self._get_score_color(total_score)
        self._set_text_with_font(ax, 'text', 0.5, 0.7, f'{total_score:.0f}', 
               ha='center', va='center', fontsize=48, fontweight='bold', 
               color=score_color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.55, '分', 
               ha='center', va='center', fontsize=16, fontweight='600',
               color=score_color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.4, level, 
               ha='center', va='center', fontsize=14, fontweight='bold',
               color=score_color, transform=ax.transAxes,
               bbox=dict(boxstyle='round,pad=0.4', facecolor=score_color, 
                        alpha=0.1, edgecolor=score_color, linewidth=1.5))
        
        # 🎨 绘制评分环形图
        circle_outer = plt.Circle((0.5, 0.65), 0.35, transform=ax.transAxes, 
                                 fill=False, linewidth=8, color=score_color, alpha=0.2)
        ax.add_patch(circle_outer)
        
        # 根据分数绘制进度弧
        from matplotlib.patches import Arc
        arc_length = (total_score / 100) * 360
        arc = Arc((0.5, 0.65), 0.7, 0.7, angle=0, theta1=90, theta2=90+arc_length,
                 linewidth=8, color=score_color, alpha=0.8, transform=ax.transAxes)
        ax.add_patch(arc)
        
        # 📊 各项能力快速预览
        categories = ['准确性', '流畅性', '稳定性', '适配性']
        scores = [
            component_scores.get('accuracy', 0),
            component_scores.get('trend', 0),
            component_scores.get('stability', 0),
            component_scores.get('range', 0)
        ]
        
        y_start = 0.25
        for i, (cat, score) in enumerate(zip(categories, scores)):
            y_pos = y_start - i * 0.05
            score_color_mini = self._get_score_color(score)
            
            # 能力名称
            self._set_text_with_font(ax, 'text', 0.05, y_pos, cat, 
                   ha='left', va='center', fontsize=10, fontweight='500',
                   color=self.colors['text'], transform=ax.transAxes)
            
            # 分数
            self._set_text_with_font(ax, 'text', 0.95, y_pos, f'{score:.0f}', 
                   ha='right', va='center', fontsize=10, fontweight='bold',
                   color=score_color_mini, transform=ax.transAxes)
        
        # 标题
        self._set_text_with_font(ax, 'title', '★ 综合评分', fontsize=14, fontweight='bold',
                               color=self.colors['text'], pad=15)
    
    def _plot_concise_feedback(self, ax, score_result, comparison_result):
        """
        💡 绘制简洁的反馈和建议
        """
        ax.clear()
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        total_score = score_result['total_score']
        component_scores = score_result.get('component_scores', {})
        
        # 🎯 根据分数生成建议
        suggestions = []
        
        if total_score >= 85:
            suggestions.append("🎉 您的发音表现优秀！继续保持这种水准。")
        elif total_score >= 70:
            suggestions.append("👍 您的发音表现良好，还有进步空间。")
        else:
            suggestions.append("💪 加油练习，您的发音会越来越好！")
        
        # 根据各项分数给出具体建议
        if component_scores.get('accuracy', 0) < 70:
            suggestions.append("🎯 注意音高准确度：多听标准发音，模仿音调变化")
        
        if component_scores.get('trend', 0) < 70:
            suggestions.append("📈 改善音调变化：练习声调的起伏和变化规律")
        
        if component_scores.get('stability', 0) < 70:
            suggestions.append("🎵 提高发音稳定性：保持匀速说话，避免音高剧烈跳动")
        
        if component_scores.get('range', 0) < 70:
            suggestions.append("🎼 扩展音域适配：适当调整音高范围，使其更接近标准")
        
        # 限制建议数量
        suggestions = suggestions[:3]
        
        # 📝 显示建议
        self._set_text_with_font(ax, 'text', 0.02, 0.9, '◉ 评价与建议', 
               ha='left', va='top', fontsize=14, fontweight='bold',
               color=self.colors['text'], transform=ax.transAxes)
        
        for i, suggestion in enumerate(suggestions):
            y_pos = 0.7 - i * 0.25
            self._set_text_with_font(ax, 'text', 0.02, y_pos, suggestion, 
                   ha='left', va='top', fontsize=11, fontweight='400',
                   color=self.colors['text'], transform=ax.transAxes,
                   wrap=True)
        
        # 🌟 添加鼓励性的背景装饰
        if total_score >= 80:
            decoration_color = self.colors['good']
            decoration_text = "◆ 表现优秀"
        elif total_score >= 60:
            decoration_color = self.colors['warning']
            decoration_text = "▲ 继续努力"
        else:
            decoration_color = self.colors['error']
            decoration_text = "● 加油练习"
        
        # 右侧装饰
        self._set_text_with_font(ax, 'text', 0.95, 0.5, decoration_text, 
               ha='right', va='center', fontsize=12, fontweight='bold',
               color=decoration_color, transform=ax.transAxes, alpha=0.7)
    
    def _plot_beautiful_comparison_with_text_markers(self, ax, times, standard_pitch, user_pitch, 
                                                   input_text, text_alignment_data):
        """
        绘制带有文本标注的音高对比图
        """
        # 先绘制基础的音高对比
        self._plot_beautiful_comparison(ax, times, standard_pitch, user_pitch, input_text)
        
        # 添加文本标注
        if text_alignment_data and text_alignment_data.get('text_alignment'):
            self._add_text_markers_to_pitch_plot(ax, times, text_alignment_data)
    
    def _add_text_markers_to_pitch_plot(self, ax, times, text_alignment_data):
        """
        在音高图上添加文本标注
        """
        try:
            text_alignment = text_alignment_data.get('text_alignment', [])
            if not text_alignment:
                return
            
            # 获取y轴范围用于放置文本
            ylim = ax.get_ylim()
            y_range = ylim[1] - ylim[0]
            text_y_offset = y_range * 0.1  # 文本位置偏移
            
            # 遍历对齐的文本并添加标注
            for i, alignment in enumerate(text_alignment):
                if alignment.get('match_type') in ['exact', 'partial']:
                    expected_word = alignment.get('expected_word', '')
                    start_time = alignment.get('start_time', 0)
                    end_time = alignment.get('end_time', 0)
                    
                    if start_time is not None and end_time is not None and expected_word:
                        # 计算文本在时间轴上的中间位置
                        text_time = (start_time + end_time) / 2
                        
                        # 确保时间在显示范围内
                        if times[0] <= text_time <= times[-1]:
                            # 根据匹配质量选择颜色
                            if alignment.get('match_type') == 'exact':
                                color = self.colors['good']
                                alpha = 0.9
                            else:
                                color = self.colors['warning']
                                alpha = 0.7
                            
                            # 计算文本y位置 (在图的上方)
                            text_y = ylim[1] - text_y_offset * (1 + i % 3)
                            
                            # 添加文本标注
                            self._set_text_with_font(ax, 'text', text_time, text_y, expected_word,
                                   ha='center', va='center', fontsize=11, fontweight='bold',
                                   color=color, alpha=alpha,
                                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', 
                                           edgecolor=color, alpha=0.8))
                            
                            # 添加指示线
                            ax.axvline(x=text_time, color=color, linestyle='--', 
                                     alpha=0.5, linewidth=1)
        
        except Exception as e:
            print(f"添加文本标注失败: {e}")
    
    def _plot_text_time_alignment(self, ax, text_alignment_data):
        """
        绘制文本时域对齐图
        """
        try:
            ax.clear()
            
            # 设置标题
            self._set_text_with_font(ax, 'title', "🔤 文本时域对齐分析", 
                   fontsize=14, fontweight='bold', color=self.colors['text'], pad=15)
            
            text_alignment = text_alignment_data.get('text_alignment', [])
            vad_segments = text_alignment_data.get('vad_segments', [])
            
            if not text_alignment:
                self._set_text_with_font(ax, 'text', 0.5, 0.5, '未检测到文本对齐数据', 
                       ha='center', va='center', fontsize=12, color=self.colors['accent'],
                       transform=ax.transAxes)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
                return
            
            # 计算时间范围
            max_time = 0
            for alignment in text_alignment:
                if alignment.get('end_time'):
                    max_time = max(max_time, alignment.get('end_time', 0))
            
            if max_time == 0:
                max_time = 1
            
            # 绘制文本段
            y_pos = 0
            text_height = 0.8
            
            for i, alignment in enumerate(text_alignment):
                expected_word = alignment.get('expected_word', '')
                recognized_word = alignment.get('recognized_word', '')
                start_time = alignment.get('start_time', 0)
                end_time = alignment.get('end_time', 0)
                match_type = alignment.get('match_type', 'unknown')
                
                if start_time is not None and end_time is not None:
                    # 选择颜色
                    if match_type == 'exact':
                        color = self.colors['good']
                        confidence_text = "✓"
                    elif match_type == 'partial':
                        color = self.colors['warning']  
                        confidence_text = "≈"
                    else:
                        color = self.colors['error']
                        confidence_text = "✗"
                    
                    # 绘制时间段矩形
                    width = end_time - start_time
                    rect = Rectangle((start_time, y_pos), width, text_height, 
                                   facecolor=color, alpha=0.3, edgecolor=color, linewidth=2)
                    ax.add_patch(rect)
                    
                    # 添加文本标签
                    text_x = start_time + width / 2
                    text_y = y_pos + text_height / 2
                    
                    # 期望文本
                    self._set_text_with_font(ax, 'text', text_x, text_y + 0.2, expected_word,
                           ha='center', va='center', fontsize=12, fontweight='bold',
                           color=color)
                    
                    # 识别文本
                    if recognized_word and recognized_word != expected_word:
                        self._set_text_with_font(ax, 'text', text_x, text_y - 0.1, 
                               f"({recognized_word})", ha='center', va='center', 
                               fontsize=10, color=self.colors['accent'], style='italic')
                    
                    # 时间标签
                    self._set_text_with_font(ax, 'text', text_x, text_y - 0.3, 
                           f"{start_time:.2f}s-{end_time:.2f}s", ha='center', va='center',
                           fontsize=9, color=self.colors['accent'])
                    
                    # 匹配指示
                    self._set_text_with_font(ax, 'text', start_time - 0.1, text_y, confidence_text,
                           ha='center', va='center', fontsize=14, fontweight='bold',
                           color=color)
                
                y_pos += 1.2
            
            # 设置坐标轴
            ax.set_xlim(-0.5, max_time + 0.5)
            ax.set_ylim(-0.2, y_pos)
            ax.set_xlabel('时间 (秒)', fontsize=11, color=self.colors['text'])
            ax.set_ylabel('识别文本', fontsize=11, color=self.colors['text'])
            
            # 添加网格
            ax.grid(True, alpha=0.3, linestyle=':')
            ax.set_facecolor(self.colors['background'])
            
            # 添加统计信息
            total_words = len(text_alignment)
            exact_matches = sum(1 for a in text_alignment if a.get('match_type') == 'exact')
            accuracy = (exact_matches / total_words * 100) if total_words > 0 else 0
            
            stats_text = f"匹配度: {accuracy:.1f}% ({exact_matches}/{total_words})"
            self._set_text_with_font(ax, 'text', 0.02, 0.98, stats_text,
                   ha='left', va='top', fontsize=10, color=self.colors['accent'],
                   transform=ax.transAxes, bbox=dict(boxstyle="round,pad=0.3", 
                   facecolor='white', alpha=0.8))
        
        except Exception as e:
            print(f"绘制文本时域对齐图失败: {e}")
            import traceback
            traceback.print_exc()

# 使用示例
if __name__ == '__main__':
    # 测试可视化功能
    visualizer = PitchVisualization()
    
    # 创建模拟数据
    times = np.linspace(0, 2, 100)
    standard_pitch = 200 + 50 * np.sin(times * 3) + np.random.normal(0, 5, 100)
    user_pitch = 195 + 45 * np.sin(times * 3 + 0.2) + np.random.normal(0, 8, 100)
    
    mock_comparison = {
        'aligned_data': {
            'aligned_standard': standard_pitch,
            'aligned_user': user_pitch,
            'aligned_times': times
        },
        'metrics': {
            'correlation': 0.75,
            'rmse': 35.0,
            'trend_consistency': 0.68,
            'std_mean': 200.0,
            'user_mean': 195.0,
            'valid_points': 90
        }
    }
    
    mock_score = {
        'total_score': 76.5,
        'level': '良好',
        'component_scores': {
            'accuracy': 75.0,
            'trend': 68.0,
            'stability': 80.0,
            'range': 82.0
        }
    }
    
    # 测试对比图
    Config.create_directories()
    output_path = os.path.join(Config.OUTPUT_FOLDER, 'test_comparison.png')
    success = visualizer.plot_pitch_comparison(mock_comparison, mock_score, output_path)
    
    if success:
        print("可视化测试成功！")
    else:
        print("可视化测试失败！")


# Fun-ASR时间戳可视化扩展
class PitchVisualizationWithFunASR(PitchVisualization):
    """扩展版音高可视化类，支持Fun-ASR时间戳"""
    
    def plot_comparison_with_fun_asr_timestamps(self, comparison_result: dict, score_result: dict,
                                               output_path: str, tts_audio_path: str, original_text: str,
                                               fig_size=(16, 10), dpi=150) -> bool:
        """
        绘制带有Fun-ASR时间戳标注的音高对比图
        :param comparison_result: 音高对比结果
        :param score_result: 评分结果  
        :param output_path: 输出图片路径
        :param tts_audio_path: TTS生成的音频文件路径
        :param original_text: 原始文本
        :param fig_size: 图片尺寸
        :param dpi: 图片分辨率
        :return: 是否成功
        """
        try:
            print("🎯 开始绘制带Fun-ASR时间戳的音高对比图...")
            
            # 1. 使用Fun-ASR处理TTS音频获取时间戳
            print("📝 正在使用Fun-ASR获取时间戳...")
            timestamp_result = self.fun_asr.process_tts_audio_with_text(tts_audio_path, original_text)
            
            if not timestamp_result:
                print("⚠️ Fun-ASR时间戳获取失败，使用标准绘图方式")
                return self.plot_pitch_comparison(comparison_result, score_result, output_path, 
                                                fig_size, dpi, original_text)
            
            # 2. 准备绘图数据
            times = comparison_result['times']
            standard_pitch = comparison_result['standard_pitch']  
            user_pitch = comparison_result['user_pitch']
            
            # 3. 创建图形
            plt.style.use('seaborn-v0_8-whitegrid')
            fig = plt.figure(figsize=fig_size, dpi=dpi, facecolor='white')
            
            # 创建主要布局
            gs = fig.add_gridspec(3, 2, height_ratios=[3, 1, 1], width_ratios=[3, 1], 
                                hspace=0.3, wspace=0.2)
            
            # 主要音高对比图 (占据大部分空间)
            ax_main = fig.add_subplot(gs[:2, 0])
            
            # 4. 绘制带时间戳标注的音高对比
            self._plot_pitch_comparison_with_fun_asr(ax_main, times, standard_pitch, user_pitch, 
                                                   timestamp_result, original_text)
            
            # 5. 绘制评分和反馈信息
            ax_score = fig.add_subplot(gs[:2, 1])
            self._plot_score_panel_with_timestamps(ax_score, score_result, timestamp_result)
            
            # 6. 绘制时间戳详情表 
            ax_timeline = fig.add_subplot(gs[2, :])
            self._plot_timestamp_timeline(ax_timeline, timestamp_result, times[-1])
            
            # 7. 设置整体标题和样式
            fig.suptitle('🎵 音高曲线对比分析 (Fun-ASR时间戳版)', 
                        fontsize=18, fontweight='bold', y=0.95, fontname=self.font_name)
            
            # 8. 保存图片
            plt.tight_layout()
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            print(f"✅ Fun-ASR时间戳音高对比图已保存: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 绘制Fun-ASR时间戳音高对比图失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _plot_pitch_comparison_with_fun_asr(self, ax, times, standard_pitch, user_pitch, 
                                          timestamp_result, original_text):
        """
        绘制带有Fun-ASR时间戳标注的音高对比曲线
        """
        try:
            # 1. 绘制基础音高曲线
            self._plot_beautiful_comparison(ax, times, standard_pitch, user_pitch, original_text)
            
            # 2. 添加Fun-ASR时间戳标注
            if timestamp_result and timestamp_result.get('aligned_chars'):
                self._add_fun_asr_text_markers(ax, times, timestamp_result)
            
            # 3. 添加时间戳质量指示器
            alignment_quality = timestamp_result.get('alignment_quality', 0.0) if timestamp_result else 0.0
            self._add_alignment_quality_indicator(ax, alignment_quality)
            
        except Exception as e:
            print(f"绘制Fun-ASR时间戳音高图失败: {e}")
    
    def _add_fun_asr_text_markers(self, ax, times, timestamp_result):
        """
        在音高图上添加Fun-ASR的时间戳标注
        """
        try:
            aligned_chars = timestamp_result.get('aligned_chars', [])
            if not aligned_chars:
                return
            
            # 获取y轴范围
            ylim = ax.get_ylim()
            y_range = ylim[1] - ylim[0]
            
            # 收集连续的词或短语
            current_word = ""
            word_start_time = None
            word_end_time = None
            
            for i, char_info in enumerate(aligned_chars):
                char = char_info.get('char', '')
                timestamp = char_info.get('timestamp')
                
                if timestamp is not None:
                    if word_start_time is None:
                        word_start_time = timestamp
                        current_word = char
                    else:
                        current_word += char
                    word_end_time = timestamp
                else:
                    # 遇到没有时间戳的字符，输出当前词
                    if current_word and word_start_time is not None:
                        self._add_word_marker(ax, current_word, word_start_time, word_end_time, ylim, y_range)
                    current_word = ""
                    word_start_time = None
                    word_end_time = None
                
                # 如果是词的结束或空格，输出当前词
                if char in ['，', '。', '！', '？', ' ', '\n'] and current_word and word_start_time is not None:
                    self._add_word_marker(ax, current_word, word_start_time, word_end_time, ylim, y_range)
                    current_word = ""
                    word_start_time = None
                    word_end_time = None
            
            # 处理最后一个词
            if current_word and word_start_time is not None:
                self._add_word_marker(ax, current_word, word_start_time, word_end_time, ylim, y_range)
                
        except Exception as e:
            print(f"添加Fun-ASR时间戳标注失败: {e}")
    
    def _add_word_marker(self, ax, word, start_time, end_time, ylim, y_range):
        """
        添加单个词的时间戳标注
        """
        try:
            if not word.strip():
                return
                
            # 计算词的中心时间
            center_time = (start_time + end_time) / 2
            
            # 文本位置 (稍微在曲线上方)
            text_y = ylim[1] - y_range * 0.05
            
            # 添加文本标注
            ax.annotate(word.strip(), 
                       xy=(center_time, text_y),
                       xytext=(center_time, text_y + y_range * 0.08),
                       fontsize=10,
                       fontname=self.font_name,
                       ha='center',
                       va='bottom',
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='lightblue', 
                               alpha=0.7,
                               edgecolor='steelblue'),
                       arrowprops=dict(arrowstyle='->', 
                                     connectionstyle='arc3,rad=0',
                                     color='steelblue',
                                     alpha=0.6))
            
            # 添加时间区间标记 
            duration = end_time - start_time
            if duration > 0.1:  # 只为足够长的词添加区间标记
                ax.axvspan(start_time, end_time, 
                          ymin=0.95, ymax=1.0,
                          alpha=0.3, 
                          color='lightblue',
                          label=f'{word}: {duration:.2f}s' if duration > 0.5 else None)
                
        except Exception as e:
            print(f"添加词标记失败: {e}")
    
    def _add_alignment_quality_indicator(self, ax, alignment_quality):
        """
        添加对齐质量指示器
        """
        try:
            # 在图的右上角添加质量指示器
            quality_text = f"时间戳对齐质量: {alignment_quality:.1%}"
            if alignment_quality >= 0.8:
                color = self.colors['good']
                emoji = "🟢"
            elif alignment_quality >= 0.6:
                color = self.colors['warning'] 
                emoji = "🟡"
            else:
                color = self.colors['error']
                emoji = "🔴"
            
            ax.text(0.98, 0.98, f"{emoji} {quality_text}",
                   transform=ax.transAxes,
                   fontsize=10,
                   fontname=self.font_name,
                   ha='right', va='top',
                   bbox=dict(boxstyle='round,pad=0.4',
                           facecolor=color,
                           alpha=0.2,
                           edgecolor=color))
                           
        except Exception as e:
            print(f"添加对齐质量指示器失败: {e}")
    
    def _plot_score_panel_with_timestamps(self, ax, score_result, timestamp_result):
        """
        绘制包含时间戳信息的评分面板
        """
        try:
            # 复用现有的评分面板绘制方法
            self._plot_clean_score_dashboard(ax, score_result)
            
            # 添加时间戳统计信息
            if timestamp_result:
                asr_result = timestamp_result.get('asr_result', {})
                word_count = len(asr_result.get('word_timestamps', []))
                alignment_quality = timestamp_result.get('alignment_quality', 0.0)
                
                # 在评分面板底部添加时间戳信息
                ax.text(0.05, 0.15, f"📝 词级时间戳: {word_count}个",
                       transform=ax.transAxes,
                       fontsize=9,
                       fontname=self.font_name,
                       color='darkblue')
                
                ax.text(0.05, 0.05, f"🎯 对齐准确度: {alignment_quality:.1%}",
                       transform=ax.transAxes,
                       fontsize=9,
                       fontname=self.font_name,
                       color='darkgreen' if alignment_quality > 0.7 else 'orange')
                       
        except Exception as e:
            print(f"绘制时间戳评分面板失败: {e}")
    
    def _plot_timestamp_timeline(self, ax, timestamp_result, total_duration):
        """
        绘制时间戳时间线详情
        """
        try:
            ax.clear()
            
            if not timestamp_result or not timestamp_result.get('aligned_chars'):
                ax.text(0.5, 0.5, "⚠️ 未获取到时间戳数据", 
                       transform=ax.transAxes, ha='center', va='center',
                       fontname=self.font_name, fontsize=12)
                ax.set_title("时间戳时间线", fontname=self.font_name, fontsize=12)
                ax.axis('off')
                return
            
            # 提取词级时间戳用于时间线展示
            asr_result = timestamp_result.get('asr_result', {})
            word_timestamps = asr_result.get('word_timestamps', [])
            
            if not word_timestamps:
                ax.text(0.5, 0.5, "📝 正在处理时间戳数据...", 
                       transform=ax.transAxes, ha='center', va='center',
                       fontname=self.font_name, fontsize=12)
                ax.set_title("时间戳时间线", fontname=self.font_name, fontsize=12)
                ax.axis('off')
                return
            
            # 绘制时间线
            y_pos = 0.5
            
            for i, word_info in enumerate(word_timestamps[:20]):  # 限制显示前20个词
                word = word_info.get('word', '')
                start_time = word_info.get('start_time', 0)
                end_time = word_info.get('end_time', 0)
                confidence = word_info.get('confidence', 1.0)
                
                if word.strip():
                    # 计算在时间轴上的相对位置
                    start_pos = start_time / total_duration if total_duration > 0 else 0
                    end_pos = end_time / total_duration if total_duration > 0 else 0
                    
                    # 根据置信度选择颜色
                    if confidence >= 0.9:
                        color = 'green'
                        alpha = 0.8
                    elif confidence >= 0.7:
                        color = 'orange'
                        alpha = 0.7
                    else:
                        color = 'red'
                        alpha = 0.6
                    
                    # 绘制词的时间区间
                    ax.barh(y_pos, end_pos - start_pos, left=start_pos, height=0.3,
                           color=color, alpha=alpha, edgecolor='black', linewidth=0.5)
                    
                    # 添加词文本
                    text_pos = (start_pos + end_pos) / 2
                    ax.text(text_pos, y_pos, word, ha='center', va='center',
                           fontsize=8, fontname=self.font_name, color='white', weight='bold')
            
            # 设置坐标轴
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_xlabel("时间进度", fontname=self.font_name, fontsize=10)
            ax.set_title("📊 Fun-ASR词级时间戳时间线", fontname=self.font_name, fontsize=12)
            
            # 添加时间刻度
            time_ticks = [0, 0.25, 0.5, 0.75, 1.0]
            time_labels = [f"{tick * total_duration:.1f}s" for tick in time_ticks]
            ax.set_xticks(time_ticks)
            ax.set_xticklabels(time_labels)
            ax.set_yticks([])
            
        except Exception as e:
            print(f"绘制时间戳时间线失败: {e}")
            ax.text(0.5, 0.5, f"❌ 时间线绘制错误: {str(e)[:50]}", 
                   transform=ax.transAxes, ha='center', va='center',
                   fontname=self.font_name, fontsize=10)
