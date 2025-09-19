# 音高曲线比对系统 - 配置模板
# 复制此文件为 config.py 并填入您的API密钥

# =========================
# TTS 引擎配置
# =========================

# 百度TTS配置
BAIDU_TTS_CONFIG = {
    'api_key': 'your_baidu_api_key_here',
    'secret_key': 'your_baidu_secret_key_here',
    'app_id': 'your_baidu_app_id_here',
}

# =========================
# AI 服务配置
# =========================

# DeepSeek API配置 (用于智能分析)
DEEPSEEK_API_KEY = 'your_deepseek_api_key_here'

# DashScope API配置 (阿里云，用于ASR)
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
