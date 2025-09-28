# -*- coding: utf-8 -*-
import parselmouth  # pip install praat-parselmouth
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pydub import AudioSegment
import io
import base64
import os


def load_audio_data(audio_input):
    '''
    音频加载与处理，支持wav、mp3、⾳频⽂件内容Base64编码
    :param audio_input: 音频文件路径（.wav, .mp3）或音频内容的Base64编码字符串
    :return: parselmouth可以处理的格式
    '''
    if os.path.exists(audio_input):
        # 处理文件路径
        file_extension = os.path.splitext(audio_input)[1].lower()
        if file_extension == '.mp3':
            audio = AudioSegment.from_mp3(audio_input)
        else:  # .wav or other formats supported by pydub
            audio = AudioSegment.from_file(audio_input)
    else:
        # 处理Base64编码
        audio_bytes = base64.b64decode(audio_input)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

    # 转换为单声道，以便进行音高分析
    audio = audio.set_channels(1)

    # 转换为parselmouth可以处理的格式
    snd = parselmouth.Sound(audio.get_array_of_samples(), sampling_frequency=audio.frame_rate)

    return snd

def is_chinese_font_available():
    """检测系统是否有可用的中文字体"""
    font_name = None
    # 尝试常见的中文字体，优先使用macOS系统字体
    preferred_fonts = [
        'Arial Unicode MS',    # macOS通用Unicode字体
        'Heiti TC',           # macOS繁体黑体
        'Hannotate SC',       # macOS简体手写字体
        'HanziPen SC',        # macOS简体钢笔字体
        'STHeiti',            # macOS系统黑体
        'PingFang SC',        # macOS苹方字体
        'Source Han Sans CN', # 思源黑体
        'Noto Sans CJK SC',   # Noto字体
        'SimHei'              # Windows黑体
    ]
    
    for font in preferred_fonts:
        try:
            if fm.findfont(font, fallback_to_default=False) != fm.findfont('DejaVu Sans'):
                font_name = font
                print(f"✓ 使用中文字体: {font}")
                break
        except Exception:
            continue
    
    if not font_name:
        print("⚠️  未找到合适的中文字体，将使用英文标签")
    
    return font_name

def plot_pitch_curve(audio_input, output_path, fig_size=(12, 6), dpi=300):
    """
    从音频输入中提取基频（音高），并绘制保存音高曲线图。

    参数:
    - audio_input (str): 音频文件路径（.wav, .mp3）或音频内容的Base64编码字符串。
    - output_path (str): 输出图片的文件路径。
    """
    # --- 1. 字体检测与设置 ---
    font_name = is_chinese_font_available()

    # 如果找到中文字体，则设置，否则使用默认英文字体
    title_text = "音高曲线" if font_name else "Pitch Contour"
    xlabel_text = "时间 (秒)" if font_name else "Time (s)"
    ylabel_text = "基频 (Hz)" if font_name else "Fundamental Frequency (Hz)"

    # --- 2. 音频加载与处理 ---
    try:
        # 转换为parselmouth可以处理的格式
        snd = load_audio_data(audio_input)
    except Exception as e:
        print(f"音频加载失败: {e}")
        return

    # --- 3. 音高提取 ---
    # to_pitch()方法用于提取音高
    pitch = snd.to_pitch()
    pitch_values = pitch.selected_array['frequency']
    # 将0Hz（代表无声或清音）替换为nan，这样在绘图时不会画出一条在0Hz的线
    pitch_values[pitch_values == 0] = np.nan
    times = pitch.xs()

    # --- 4. 绘图与保存 ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=fig_size)

    # 如果找到中文字体，则设置，否则使用默认英文字体
    if font_name:
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    else:
        # 如果没有找到，可以使用任何系统默认的无衬线字体
        plt.rcParams['font.sans-serif'] = ['sans-serif']

    ax.plot(times, pitch_values, 'o', markersize=5, linestyle='-', color='tab:red', label=ylabel_text)  # 🎯 增大标记点
    ax.set_ylim(bottom=0)  # 音高不会是负数

    ax.set_title(title_text, fontsize=20, weight='bold')  # 🎯 16->20 移动端适配
    ax.set_xlabel(xlabel_text, fontsize=16)  # 🎯 12->16 移动端适配
    ax.set_ylabel(ylabel_text, fontsize=16)  # 🎯 12->16 移动端适配
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"音高曲线图已保存至: {output_path}")


def plot_waveform_and_pitch(audio_input, output_path, fig_size=(15, 6), dpi=300):
    """
    在同一幅图中绘制音频波形和音高曲线。
    波形使用左Y轴，音高使用右Y轴。

    参数:
    - audio_input (str): 音频文件路径（.wav, .mp3）或音频内容的Base64编码字符串。
    - output_path (str): 输出图片的文件路径。
    """
    # --- 1. 字体检测与设置 ---
    font_name = None
    preferred_fonts = [
        'Arial Unicode MS', 'Heiti TC', 'Hannotate SC', 'HanziPen SC',
        'STHeiti', 'PingFang SC', 'Source Han Sans CN', 'Noto Sans CJK SC', 'SimHei'
    ]
    for font in preferred_fonts:
        try:
            if fm.findfont(font, fallback_to_default=False) != fm.findfont('DejaVu Sans'):
                font_name = font
                break
        except Exception:
            continue

    title_text = "音频波形与音高曲线" if font_name else "Waveform and Pitch Contour"
    xlabel_text = "时间 (秒)" if font_name else "Time (s)"
    ylabel_waveform = "振幅" if font_name else "Amplitude"
    ylabel_pitch = "基频 (Hz)" if font_name else "Fundamental Frequency (Hz)"
    legend_waveform = "波形" if font_name else "Waveform"
    legend_pitch = "音高" if font_name else "Pitch"

    # --- 2. 音频加载与处理 ---
    try:
        # 转换为parselmouth可以处理的格式
        snd = load_audio_data(audio_input)
    except Exception as e:
        print(f"音频加载失败: {e}")
        return

    # --- 3. 提取数据 ---
    # 音高
    pitch = snd.to_pitch()
    pitch_values = pitch.selected_array['frequency']
    pitch_values[pitch_values == 0] = np.nan
    pitch_times = pitch.xs()

    # 波形
    waveform = snd.values.T
    time_axis = snd.xs()

    # --- 4. 绘图与保存 ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax1 = plt.subplots(figsize=fig_size)

    # 如果找到中文字体，则设置，否则使用默认英文字体
    if font_name:
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    else:
        # 如果没有找到，可以使用任何系统默认的无衬线字体
        plt.rcParams['font.sans-serif'] = ['sans-serif']

    # 绘制波形 (左Y轴)
    ax1.plot(time_axis, waveform, color='tab:blue', alpha=0.8, label=legend_waveform)
    ax1.set_xlabel(xlabel_text, fontsize=16)  # 🎯 12->16 移动端适配
    ax1.set_ylabel(ylabel_waveform, color='tab:blue', fontsize=16)  # 🎯 12->16 移动端适配
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.set_ylim(waveform.min() * 1.1, waveform.max() * 1.1)
    ax1.grid(False)  # 波形图通常不显示网格

    # 创建共享X轴的第二个Y轴
    ax2 = ax1.twinx()

    # 绘制音高 (右Y轴)
    ax2.plot(pitch_times, pitch_values, 'o-', markersize=6, color='tab:red', label=legend_pitch)  # 🎯 增大标记点
    ax2.set_ylabel(ylabel_pitch, color='tab:red', fontsize=16)  # 🎯 12->16 移动端适配
    ax2.tick_params(axis='y', labelcolor='tab:red')
    ax2.set_ylim(bottom=0, top=np.nanmax(pitch_values) * 1.1 if not np.all(np.isnan(pitch_values)) else 500)

    # 设置标题和图例
    fig.suptitle(title_text, fontsize=20, weight='bold')  # 🎯 16->20 移动端适配
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    fig.tight_layout(rect=[0, 0, 1, 0.96])  # 为主标题留出空间
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"波形与音高组合图已保存至: {output_path}")


def plot_wideband_spectrogram(audio_input, output_path, fig_size=(12, 6), dpi=300):
    """
    绘制并保存音频的宽带语图。

    参数:
    - audio_input (str): 音频文件路径（.wav, .mp3）或音频内容的Base64编码字符串。
    - output_path (str): 输出图片的文件路径。
    """
    # --- 1. 字体检测与设置 ---
    font_name = None
    preferred_fonts = [
        'Arial Unicode MS', 'Heiti TC', 'Hannotate SC', 'HanziPen SC',
        'STHeiti', 'PingFang SC', 'Source Han Sans CN', 'Noto Sans CJK SC', 'SimHei'
    ]
    for font in preferred_fonts:
        try:
            if fm.findfont(font, fallback_to_default=False) != fm.findfont('DejaVu Sans'):
                font_name = font
                break
        except Exception:
            continue

    title_text = "宽带语图 (分析带宽 ≈ 300 Hz)" if font_name else "Wideband Spectrogram (Bandwidth ≈ 300 Hz)"
    xlabel_text = "时间 (秒)" if font_name else "Time (s)"
    ylabel_text = "频率 (Hz)" if font_name else "Frequency (Hz)"
    cbar_label = "强度 (dB)" if font_name else "Intensity (dB)"

    # --- 2. 音频加载 ---
    try:
        # 转换为parselmouth可以处理的格式
        snd = load_audio_data(audio_input)
    except Exception as e:
        print(f"音频加载失败: {e}")
        return

    # --- 3. 语图计算 ---
    # 宽带语图需要短的分析窗长，例如 0.005 秒 (5ms)
    # 带宽(Hz) ≈ 1.2 / 窗长(s) for Gaussian window. 1.2 / 0.005s ≈ 240Hz, 接近300Hz
    window_length = 0.005
    spectrogram = snd.to_spectrogram(window_length=window_length, time_step=0.002)

    # --- 4. 绘图与保存 ---
    plt.style.use('default')  # 语图使用默认风格更好看
    fig, ax = plt.subplots(figsize=fig_size)

    # 如果找到中文字体，则设置，否则使用默认英文字体
    if font_name:
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    else:
        # 如果没有找到，可以使用任何系统默认的无衬线字体
        plt.rcParams['font.sans-serif'] = ['sans-serif']

    X, Y = spectrogram.x_grid(), spectrogram.y_grid()
    sg_db = 10 * np.log10(spectrogram.values)

    # 使用pcolormesh绘图，并设置颜色范围和映射
    im = ax.pcolormesh(X, Y, sg_db, vmin=sg_db.max() - 70, cmap='viridis', shading='auto')

    ax.set_ylim([0, 5000])  # 通常关注5000Hz以下的频率
    ax.set_title(title_text, fontsize=16, weight='bold')
    ax.set_xlabel(xlabel_text, fontsize=12)
    ax.set_ylabel(ylabel_text, fontsize=12)

    # 添加颜色条
    cbar = fig.colorbar(im, ax=ax, format='%+2.0f dB')
    cbar.set_label(cbar_label, fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"宽带语图已保存至: {output_path}")


def plot_narrowband_spectrogram(audio_input, output_path, fig_size=(12, 6), dpi=300):
    """
    绘制并保存音频的窄带语图。

    参数:
    - audio_input (str): 音频文件路径（.wav, .mp3）或音频内容的Base64编码字符串。
    - output_path (str): 输出图片的文件路径。
    """
    # --- 1. 字体检测与设置 ---
    font_name = None
    preferred_fonts = [
        'Arial Unicode MS', 'Heiti TC', 'Hannotate SC', 'HanziPen SC',
        'STHeiti', 'PingFang SC', 'Source Han Sans CN', 'Noto Sans CJK SC', 'SimHei'
    ]
    for font in preferred_fonts:
        try:
            if fm.findfont(font, fallback_to_default=False) != fm.findfont('DejaVu Sans'):
                font_name = font
                break
        except Exception:
            continue

    title_text = "窄带语图 (分析带宽 ≈ 45 Hz)" if font_name else "Narrowband Spectrogram (Bandwidth ≈ 45 Hz)"
    xlabel_text = "时间 (秒)" if font_name else "Time (s)"
    ylabel_text = "频率 (Hz)" if font_name else "Frequency (Hz)"
    cbar_label = "强度 (dB)" if font_name else "Intensity (dB)"

    # --- 2. 音频加载 ---
    try:
        # 转换为parselmouth可以处理的格式
        snd = load_audio_data(audio_input)
    except Exception as e:
        print(f"音频加载失败: {e}")
        return

    # --- 3. 语图计算 ---
    # 窄带语图需要长的分析窗长，例如 0.03 秒 (30ms)
    # 带宽(Hz) ≈ 1.2 / 窗长(s) for Gaussian window. 1.2 / 0.03s = 40Hz, 接近45Hz
    window_length = 0.03
    spectrogram = snd.to_spectrogram(window_length=window_length, time_step=0.005)

    # --- 4. 绘图与保存 ---
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=fig_size)

    # 如果找到中文字体，则设置，否则使用默认英文字体
    if font_name:
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    else:
        # 如果没有找到，可以使用任何系统默认的无衬线字体
        plt.rcParams['font.sans-serif'] = ['sans-serif']

    X, Y = spectrogram.x_grid(), spectrogram.y_grid()
    sg_db = 10 * np.log10(spectrogram.values)

    im = ax.pcolormesh(X, Y, sg_db, vmin=sg_db.max() - 70, cmap='viridis', shading='auto')

    ax.set_ylim([0, 5000])
    ax.set_title(title_text, fontsize=16, weight='bold')
    ax.set_xlabel(xlabel_text, fontsize=12)
    ax.set_ylabel(ylabel_text, fontsize=12)

    cbar = fig.colorbar(im, ax=ax, format='%+2.0f dB')
    cbar.set_label(cbar_label, fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"窄带语图已保存至: {output_path}")


# --- 主程序入口 ---
if __name__ == '__main__':
    # 1. 测试用的WAV文件
    test_wav_path = "putonghua/embed_new/词语new_345.wav"
    save_path = "test4/"

    print("\n--- 开始使用文件路径进行绘图 ---")
    # 使用文件路径调用函数
    plot_pitch_curve(test_wav_path, save_path + "pitch_from_file.png")
    plot_waveform_and_pitch(test_wav_path, save_path + "waveform_pitch_from_file.png")
    plot_wideband_spectrogram(test_wav_path, save_path + "spectrogram_wide_from_file.png")
    plot_narrowband_spectrogram(test_wav_path, save_path + "spectrogram_narrow_from_file.png")
