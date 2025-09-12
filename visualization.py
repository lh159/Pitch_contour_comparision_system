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

class PitchVisualization:
    """音高可视化类"""
    
    def __init__(self):
        self.font_name = self._detect_chinese_font()
        self._setup_matplotlib()
    
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
            # 强制设置中文字体
            plt.rcParams['font.sans-serif'] = [self.font_name]
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.family'] = 'sans-serif'
            
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
        
        # 设置色彩主题
        self.colors = {
            'standard': '#1f77b4',      # 蓝色 - 标准发音
            'user': '#ff7f0e',          # 橙色 - 用户发音
            'difference': '#d62728',    # 红色 - 差异
            'good': '#2ca02c',          # 绿色 - 良好
            'warning': '#ff7f0e',       # 橙色 - 警告
            'error': '#d62728',         # 红色 - 错误
            'background': '#f5f5f5',    # 浅灰色 - 背景
            'text': '#333333'           # 深灰色 - 文字
        }
    
    def _get_font_properties(self, size=10, weight='normal'):
        """获取字体属性"""
        try:
            return fm.FontProperties(fname=None, family=self.font_name, size=size, weight=weight)
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
                            output_path: str, fig_size=(16, 12), dpi=300, input_text: str = None) -> bool:
        """
        绘制音高曲线对比图 - 全新设计，更加直观
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
            
            # 检查是否有VAD和文本对齐数据
            has_text_alignment = (comparison_result.get('vad_result') and 
                                comparison_result['vad_result'].get('text_alignment'))
            
            # 创建更清晰的布局：主图 + 侧边栏（删除反馈建议模块）
            if has_text_alignment:
                # 有文本对齐时，只显示主图、文本对齐图和评分
                fig = plt.figure(figsize=(fig_size[0], fig_size[1] - 2), facecolor='white')
                gs = fig.add_gridspec(2, 3, height_ratios=[3.5, 0.8], width_ratios=[2, 1, 1], 
                                     hspace=0.3, wspace=0.3)
                
                # 1. 主要音高对比图 (占据左侧大部分空间)
                ax_main = fig.add_subplot(gs[0, :2])
                self._plot_enhanced_comparison_with_text(ax_main, times, standard_pitch, user_pitch, 
                                                       score_result, comparison_result['vad_result'])
                
                # 2. 文本时域对齐图
                ax_text = fig.add_subplot(gs[1, :2])
                self._plot_text_alignment(ax_text, comparison_result['vad_result'])
                
                # 调整评分子图位置
                score_row, components_row = 0, 1
            else:
                fig = plt.figure(figsize=(fig_size[0], fig_size[1] - 3), facecolor='white')
                gs = fig.add_gridspec(1, 3, width_ratios=[2, 1, 1], wspace=0.3)
                
                # 1. 主要音高对比图 (占据左侧大部分空间)
                ax_main = fig.add_subplot(gs[0, :2])
                # 为没有VAD数据的情况生成简单字符时间戳
                char_timestamps = self._generate_simple_char_timestamps(input_text, times) if input_text else None
                self._plot_enhanced_comparison(ax_main, times, standard_pitch, user_pitch, score_result, char_timestamps)
                
                score_row, components_row = 0, 0
            
            # 2. 评分总览 (右上角)
            ax_score = fig.add_subplot(gs[score_row, 2])
            self._plot_score_overview(ax_score, score_result)
            
            # 3. 各项能力评分 (右下角)
            if has_text_alignment:
                ax_components = fig.add_subplot(gs[components_row, 2])
            else:
                # 没有文本对齐时，将组件评分放在评分总览下方
                gs_components = gs[score_row, 2].subgridspec(2, 1, hspace=0.3)
                ax_score = fig.add_subplot(gs_components[0])
                self._plot_score_overview(ax_score, score_result)
                ax_components = fig.add_subplot(gs_components[1])
            self._plot_component_scores(ax_components, score_result['component_scores'])
            
            # 设置整体标题
            total_score = score_result['total_score']
            level = score_result['level']
            title = f"🎵 音高曲线对比分析报告 - 总分: {total_score:.1f}分 ({level})"
            if has_text_alignment:
                title += " (含文本对齐分析)"
            fig.suptitle(title, fontsize=18, weight='bold', y=0.95, 
                        color=self._get_score_color(total_score))
            
            # 保存图片
            plt.tight_layout(rect=[0, 0, 1, 0.92])
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            print(f"音高对比图已保存至: {output_path}")
            return True
            
        except Exception as e:
            print(f"绘制音高对比图失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
        
        # 🆕 添加汉字时间标注
        if char_timestamps:
            self._add_character_annotations(ax, char_timestamps, times)
        
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
    
    def _add_character_annotations(self, ax, char_timestamps, times):
        """
        在音高曲线图上添加汉字时间标注
        :param ax: matplotlib轴对象
        :param char_timestamps: 字符时间戳列表，格式: [{'char': '你', 'start_time': 0.0, 'end_time': 0.5}, ...]
        :param times: 时间轴数组
        """
        try:
            if not char_timestamps:
                return
            
            y_min, y_max = ax.get_ylim()
            x_min, x_max = ax.get_xlim()
            
            # 确保汉字标注使用与音高曲线图相同的时间轴范围
            print(f"音高曲线图时间轴范围: {x_min:.3f}s - {x_max:.3f}s")
            
            # 计算标注位置 - 紧贴音高曲线图底部，时间轴对齐，增加更多空间确保完全可见
            annotation_y = y_min - (y_max - y_min) * 0.15  # 紧贴在x轴下方，增加到15%确保完全可见
            
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
                
                # 计算字符的中心位置
                char_center_time = (start_time + end_time) / 2
                
                # 避免标注重叠 - 检查是否与已有标注太近
                min_distance = (x_max - x_min) * 0.03  # 最小间距为图表宽度的3%
                is_overlapping = any(abs(char_center_time - pos) < min_distance for pos in used_positions)
                
                if is_overlapping:
                    # 如果重叠，稍微调整位置
                    offset = min_distance * (1 if i % 2 == 0 else -1)
                    char_center_time = max(x_min, min(x_max, char_center_time + offset))
                
                used_positions.append(char_center_time)
                
                # 绘制字符背景区域 (可选)
                if end_time - start_time > 0.05:  # 只对足够长的段绘制背景
                    rect_height = (y_max - y_min) * 0.05
                    rect = plt.Rectangle((start_time, y_min - rect_height/2), 
                                       end_time - start_time, rect_height,
                                       facecolor='lightgray', alpha=0.3, 
                                       edgecolor='gray', linewidth=0.5)
                    ax.add_patch(rect)
                
                # 添加汉字标注 - 紧贴音高曲线图底部，时间轴对齐
                self._set_text_with_font(ax, 'text', char_center_time, annotation_y, char,
                       ha='center', va='center', fontsize=16, fontweight='bold',
                       color='darkblue',
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor='darkblue', 
                               alpha=0.95,
                               linewidth=1.5,
                               zorder=10))  # 设置高层级，确保在最上层显示
                
                # 添加连接线，明确显示汉字与音高曲线的时间对应关系
                if end_time - start_time > 0.05:  # 对有意义的时间段添加连接线
                    # 从汉字位置向上连接到音高曲线底部
                    line_y_start = annotation_y + (y_max - y_min) * 0.02  # 从汉字上方开始
                    line_y_end = y_min - (y_max - y_min) * 0.02  # 到音高曲线底部
                    ax.plot([char_center_time, char_center_time], 
                           [line_y_start, line_y_end],
                           color='lightblue', linestyle='-', alpha=0.6, linewidth=1.5, zorder=5)
                
                # 添加时间范围标注 (小字体，在字符下方)
                if end_time - start_time > 0.2:  # 只对足够长的段显示时间
                    time_text = f'{start_time:.2f}-{end_time:.2f}s'
                    self._set_text_with_font(ax, 'text', char_center_time, annotation_y - (y_max - y_min) * 0.04,
                           time_text, ha='center', va='center', fontsize=8, 
                           color='gray', alpha=0.8)
            
            # 调整y轴范围以容纳标注，确保汉字完全可见
            ax.set_ylim(annotation_y - (y_max - y_min) * 0.20, y_max)  # 底部增加更多空间确保汉字完全可见
            
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
            
            # 期望文本（上方）
            if expected:
                self._set_text_with_font(ax, 'text', mid_time, y_pos + 0.1, f'标准: {expected}', 
                       ha='center', va='bottom', fontsize=10, fontweight='bold',
                       color='darkblue')
            
            # 识别文本（下方）
            if recognized:
                self._set_text_with_font(ax, 'text', mid_time, y_pos - 0.1, f'识别: {recognized}', 
                       ha='center', va='top', fontsize=10, 
                       color='darkred' if match_quality < 0.5 else 'darkgreen')
            
            # 时间标注
            self._set_text_with_font(ax, 'text', start_time, y_pos - 0.35, f'{start_time:.2f}s', 
                   ha='left', va='top', fontsize=8, color='gray')
            self._set_text_with_font(ax, 'text', end_time, y_pos - 0.35, f'{end_time:.2f}s', 
                   ha='right', va='top', fontsize=8, color='gray')
            
            # 匹配质量指示
            quality_text = f'{match_quality:.1%}'
            self._set_text_with_font(ax, 'text', end_time + 0.05, y_pos, quality_text, 
                   ha='left', va='center', fontsize=9, fontweight='bold',
                   color=color)
        
        # 设置标签
        segment_labels = [f'段{i+1}' for i in range(len(text_mapping))]
        ax.set_yticks(range(len(text_mapping)))
        ax.set_yticklabels(reversed(segment_labels))  # 从上到下显示
        
        self._set_text_with_font(ax, 'xlabel', '时间 (秒)', fontsize=12, fontweight='bold')
        self._set_text_with_font(ax, 'title', '📝 文本时域对齐分析 - 语音段与文字对应关系', 
               fontsize=14, fontweight='bold')
        
        # 设置坐标轴刻度字体
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(10))
        
        ax.grid(True, alpha=0.3, axis='x')
        
        # 添加图例
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['good'], alpha=0.8, label='匹配良好 (≥80%)'),
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['warning'], alpha=0.7, label='匹配一般 (≥50%)'),
            plt.Rectangle((0, 0), 1, 1, facecolor=self.colors['error'], alpha=0.6, label='匹配较差 (<50%)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10,
                 prop=self._get_font_properties(10))
        
        # 添加统计信息
        if text_mapping:
            avg_quality = sum(m.get('match_quality', 0) for m in text_mapping) / len(text_mapping)
            total_words = sum(m.get('word_count', 0) for m in text_mapping)
            info_text = f'平均匹配度: {avg_quality:.1%}\n总词数: {total_words}'
            self._set_text_with_font(ax, 'text', 0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))
    
    def _plot_score_overview(self, ax, score_result):
        """绘制评分总览"""
        ax.clear()
        ax.axis('off')
        
        total_score = score_result['total_score']
        level = score_result['level']
        
        # 绘制大分数
        color = self._get_score_color(total_score)
        self._set_text_with_font(ax, 'text', 0.5, 0.7, f'{total_score:.1f}', 
               horizontalalignment='center', verticalalignment='center',
               fontsize=48, fontweight='bold', color=color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.4, '分', 
               horizontalalignment='center', verticalalignment='center',
               fontsize=24, color=color, transform=ax.transAxes)
        
        self._set_text_with_font(ax, 'text', 0.5, 0.2, level, 
               horizontalalignment='center', verticalalignment='center',
               fontsize=16, fontweight='bold', color=color, transform=ax.transAxes)
        
        # 添加背景圆圈
        circle = plt.Circle((0.5, 0.5), 0.4, transform=ax.transAxes, 
                           fill=False, linewidth=3, color=color, alpha=0.3)
        ax.add_patch(circle)
        
        self._set_text_with_font(ax, 'title', '🏆 总体评分', fontsize=14, fontweight='bold', pad=10)
    
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
        
        # 绘制水平条形图
        y_pos = np.arange(len(categories))
        bars = ax.barh(y_pos, scores, color=colors, alpha=0.7, height=0.6)
        
        # 添加分数标签
        for i, (bar, score) in enumerate(zip(bars, scores)):
            width = bar.get_width()
            self._set_text_with_font(ax, 'text', width + 1, bar.get_y() + bar.get_height()/2,
                   f'{score:.0f}', ha='left', va='center', fontsize=11, fontweight='bold')
        
        # 设置图表属性
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=11, fontproperties=self._get_font_properties(11))
        self._set_text_with_font(ax, 'xlabel', '得分', fontsize=12, fontweight='bold')
        self._set_text_with_font(ax, 'title', '🎯 各项能力评分', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(True, alpha=0.3, axis='x')
        
        # 设置坐标轴刻度字体
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self._get_font_properties(10))
        
        # 添加参考线
        ax.axvline(x=60, color='orange', linestyle='--', alpha=0.7, label='及格线')
        ax.axvline(x=80, color='green', linestyle='--', alpha=0.7, label='良好线')
    
    
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
                            title: str = "音高曲线", fig_size=(12, 6)) -> bool:
        """
        绘制单个音高曲线
        :param pitch_data: 音高数据
        :param output_path: 输出路径
        :param title: 图表标题
        :param fig_size: 图片尺寸
        :return: 是否成功
        """
        
        try:
            times = pitch_data.get('times', [])
            pitch_values = pitch_data.get('smooth_pitch', [])
            
            if len(times) == 0 or len(pitch_values) == 0:
                return self._plot_error_message("音高数据为空", output_path)
            
            fig, ax = plt.subplots(figsize=fig_size)
            
            # 绘制音高曲线
            ax.plot(times, pitch_values, 'o-', color=self.colors['standard'], 
                   markersize=3, linewidth=2, alpha=0.8)
            
            # 设置图表属性
            ax.set_xlabel('时间 (秒)', fontsize=12)
            ax.set_ylabel('基频 (Hz)', fontsize=12)
            ax.set_title(title, fontsize=16, weight='bold')
            ax.grid(True, alpha=0.3)
            
            # 设置y轴范围
            valid_pitch = pitch_values[~np.isnan(pitch_values)]
            if len(valid_pitch) > 0:
                y_min = max(50, np.min(valid_pitch) * 0.9)
                y_max = min(500, np.max(valid_pitch) * 1.1)
                ax.set_ylim(y_min, y_max)
            
            # 添加统计信息
            duration = pitch_data.get('duration', 0)
            valid_ratio = pitch_data.get('valid_ratio', 0)
            mean_pitch = np.nanmean(pitch_values)
            
            info_text = f"时长: {duration:.2f}s\n有效比例: {valid_ratio:.1%}\n平均音高: {mean_pitch:.1f}Hz"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
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
