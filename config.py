# -*- coding: utf-8 -*-
"""
音高曲线比对系统配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """系统配置类"""
    
    # === TTS配置 ===
    # 百度TTS配置
    BAIDU_API_KEY = os.getenv('BAIDU_API_KEY', '')
    BAIDU_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY', '')
    BAIDU_VOICE_PER = int(os.getenv('BAIDU_VOICE_PER', '0'))  # 发音人，0=度小美
    
    # === 阿里达摩院语音配置 ===
    ALIBABA_PARAFORMER_API_KEY = os.getenv('ALIBABA_PARAFORMER_API_KEY', '')
    ALIBABA_VAD_MODEL = 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch'  # VAD模型名称
    ALIBABA_ASR_MODEL = 'iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'  # ASR模型名称
    
    # === 音频配置 ===
    SAMPLE_RATE = 16000  # 采样率
    AUDIO_FORMAT = 'wav'  # 音频格式
    
    # === 文件路径配置 ===
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    TEMP_FOLDER = 'temp'
    STATIC_FOLDER = 'static'
    
    # === 音高分析配置 ===
    PITCH_MIN_FREQ = 75   # 最小基频 (Hz)
    PITCH_MAX_FREQ = 600  # 最大基频 (Hz)
    PITCH_TIME_STEP = 0.01  # 时间步长 (秒)
    
    # === VAD配置 ===
    VAD_MIN_SPEECH_DURATION = 0.1  # 最小语音段长度 (秒)
    VAD_MAX_SILENCE_DURATION = 0.5  # 最大静音段长度 (秒)
    VAD_ENERGY_THRESHOLD = 0.01  # 能量阈值
    VAD_ENABLED = True  # 是否启用VAD
    
    # === 评分配置 ===
    SCORE_WEIGHTS = {
        'correlation': 0.4,    # 相关性权重
        'trend': 0.3,          # 趋势一致性权重
        'stability': 0.2,      # 稳定性权重
        'range': 0.1           # 音域适配权重
    }
    
    # === Web配置 ===
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 9999))
    
    # === DeepSeek API配置 ===
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    
    # === 场景对话配置 ===
    MAX_SCENARIO_LENGTH = 200  # 场景描述最大长度
    DEFAULT_DIALOGUE_ROUNDS = 6  # 默认对话轮数
    DIALOGUE_SESSION_TIMEOUT = 3600  # 对话会话超时时间（秒）
    
    # === IndexTTS2配置 ===
    INDEXTTS2_CONFIG = {
        'model_dir': 'third_party/index-tts/checkpoints',
        'use_fp16': True,  # 使用半精度推理
        'use_cuda_kernel': True,  # 使用CUDA内核加速
        'use_deepspeed': False,  # DeepSpeed加速（可选）
        'cache_dir': 'cache/indextts2',
        'max_text_length': 500,  # 最大文本长度
        'default_emo_alpha': 0.8  # 默认情感强度
    }
    
    # === 增强TTS配置 ===
    ENHANCED_TTS_CONFIG = {
        'default_engine': 'indextts2',  # 默认使用IndexTTS2
        'fallback_engine': 'baidu',    # 备用引擎
        'auto_emotion': True,          # 自动情感分析
        'emotion_confidence_threshold': 0.5,  # 情感置信度阈值
        'cache_enabled': True,         # 启用音频缓存
        'max_cache_size': 100,         # 最大缓存数量
        'cache_cleanup_interval': 3600  # 缓存清理间隔（秒）
    }
    
    # === 百度TTS语音配置 ===
    BAIDU_VOICE_PROFILES = {
        'standard': 4,      # 度丫丫，标准女声
        'child': 5,         # 度小娇，可爱童声  
        'adult_male': 1,    # 度小宇，标准男声
        'adult_female': 0,  # 度小美，标准女声
        'elderly': 4,       # 度丫丫，温和女声
        'professional': 3   # 度小博，专业男声
    }
    
    # === 对话语音缓存配置 ===
    DIALOGUE_AUDIO_CACHE_SIZE = 100  # 缓存的对话音频数量
    DIALOGUE_AUDIO_CACHE_TTL = 3600  # 缓存过期时间（秒）
    
    @classmethod
    def create_directories(cls):
        """创建必要的目录"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.OUTPUT_FOLDER, 
            cls.TEMP_FOLDER,
            cls.STATIC_FOLDER
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
