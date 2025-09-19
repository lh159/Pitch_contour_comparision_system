# 音高曲线比对系统 - 配置模板
# 复制此文件为 config.py 并填入您的API密钥

# =========================
# TTS 引擎配置
# =========================

# 阿里云智能语音TTS配置 (推荐使用，支持情感表达)
ALIBABA_TTS_CONFIG = {
    'api_key': 'your_dashscope_api_key_here',  # 您的阿里云API密钥
    'default_voice': 'zhimiao_emo',            # 默认发音人 (知妙女声)
    'default_emotion': 'neutral',               # 默认情感
    'sample_rate': 48000,                      # 音频采样率
    'enabled': True                            # 启用阿里云TTS
}

# 备用TTS配置 (Edge TTS - 免费)
EDGE_TTS_CONFIG = {
    'enabled': True,                           # 启用Edge TTS作为备用
    'voice': 'zh-CN-XiaoxiaoNeural',          # Edge TTS发音人
    'rate': '+0%',                             # 语速
    'volume': '+0%'                            # 音量
}

# =========================
# AI 服务配置
# =========================

# DeepSeek API配置 (用于智能分析)
DEEPSEEK_API_KEY = 'your_deepseek_api_key_here'

# DashScope API配置 (阿里云，用于ASR和TTS)
DASHSCOPE_API_KEY = 'your_dashscope_api_key_here'

# =========================
# 系统配置
# =========================

# 调试模式
DEBUG = True

# 系统功能开关
ENABLE_VAD = True           # 语音活动检测
ENABLE_ENHANCED_ALIGNMENT = True  # 增强对齐功能
ENABLE_FUNASR = True        # Fun-ASR时间戳功能
ENABLE_EMOTION_TTS = True   # 情感TTS功能

# 音频处理参数
AUDIO_CONFIG = {
    'sample_rate': 16000,
    'chunk_size': 1024,
    'channels': 1,
    'format': 'wav'
}

# 文件路径配置
PATHS = {
    'temp_dir': 'temp/',
    'cache_dir': 'cache/',
    'upload_dir': 'uploads/',
    'output_dir': 'outputs/',
    'model_dir': 'models/'
}

# =========================
# 高级配置
# =========================

# 音高分析参数
PITCH_CONFIG = {
    'f0_min': 75,
    'f0_max': 500,
    'hop_length': 512,
    'frame_length': 2048
}

# VAD配置
VAD_CONFIG = {
    'model': 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
    'model_revision': 'v2.0.4',
    'mode': 'offline'
}

# ASR配置
ASR_CONFIG = {
    'model': 'iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404',
    'model_revision': 'v2.0.4',
    'mode': 'offline'
}

# =========================
# 情感TTS配置
# =========================

# 可用的情感类型
AVAILABLE_EMOTIONS = {
    'neutral': '中性',
    'happy': '开心',
    'sad': '悲伤', 
    'angry': '生气',
    'gentle': '温柔',
    'serious': '严肃',
    'surprise': '惊讶',
    'fear': '害怕'
}

# 场景对话配置
DIALOGUE_CONFIG = {
    'male_voice': 'zhifeng_emo',     # 男声发音人
    'female_voice': 'zhimiao_emo',   # 女声发音人
    'default_emotion': 'neutral',     # 默认情感
    'volume': 70,                     # 音量
    'speech_rate': 0                  # 语速
}