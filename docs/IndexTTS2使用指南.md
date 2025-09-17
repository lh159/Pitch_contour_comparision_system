# IndexTTS2使用指南

## 概述

IndexTTS2已成功集成到音高曲线比对系统中，为场景对话功能提供了强大的语音合成能力。本指南将帮助您快速上手使用新功能。

## 快速开始

### 1. 环境检查

首先确保您的环境满足要求：

- Python 3.10 或更高版本
- 推荐使用GPU（支持CUDA）
- 至少8GB内存

### 2. 自动安装

运行自动安装脚本：

```bash
python setup_indextts2.py
```

该脚本将自动完成：
- 检查环境依赖
- 安装IndexTTS2
- 下载模型文件
- 创建必要目录
- 测试安装结果

### 3. 手动安装（可选）

如果自动安装失败，可以手动执行以下步骤：

#### 3.1 安装依赖

```bash
pip install torch torchaudio transformers librosa soundfile jieba
```

#### 3.2 安装IndexTTS2

```bash
cd third_party/index-tts
pip install -e .
```

#### 3.3 下载模型文件

```bash
pip install huggingface_hub
huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=third_party/index-tts/checkpoints
```

### 4. 验证安装

运行测试脚本验证安装：

```bash
python test_indextts2_integration.py
```

## 功能介绍

### 1. 多引擎TTS系统

系统现在支持多种TTS引擎：

- **IndexTTS2**: 高质量情感语音合成
- **百度TTS**: 稳定的云端TTS服务
- **自动切换**: 主引擎失败时自动切换到备用引擎

### 2. 角色语音系统

#### 预定义角色

系统预配置了以下角色：

- **小明**: 8岁男孩，活泼开朗
- **李老师**: 35岁女教师，温和耐心
- **王爸爸**: 40岁男性，严肃负责
- **奶奶**: 70岁老奶奶，慈祥温暖

#### 角色管理

```python
from character_voice_manager import CharacterVoiceManager

manager = CharacterVoiceManager()

# 获取所有角色
characters = manager.get_all_characters()

# 获取角色配置
profile = manager.get_character_voice_config("小明")

# 添加新角色
from character_voice_manager import VoiceProfile
new_profile = VoiceProfile(
    name="小红",
    type="child",
    age=7,
    gender="female",
    personality="害羞内向",
    description="7岁女孩，害羞但聪明"
)
manager.add_character("小红", new_profile)
```

### 3. 情感分析系统

#### 自动情感识别

系统能自动识别文本中的情感：

```python
from dialogue_emotion_analyzer import DialogueEmotionAnalyzer

analyzer = DialogueEmotionAnalyzer()

# 分析单句情感
emotion, confidence = analyzer.analyze_emotion("太好了！我终于通过考试了！")
print(f"情感: {emotion}, 置信度: {confidence}")

# 分析对话情感（考虑上下文）
result = analyzer.analyze_dialogue_emotion(
    dialogue_text="小明，你今天真棒！",
    speaker="李老师",
    previous_dialogues=["今天的作业做得怎么样？", "我都完成了！"]
)
```

#### 支持的情感类型

- **happy**: 开心愉快
- **sad**: 悲伤难过
- **angry**: 生气愤怒
- **surprised**: 惊讶意外
- **fear**: 害怕恐惧
- **calm**: 平静冷静
- **gentle**: 温和亲切

### 4. 语音克隆功能

IndexTTS2支持零样本语音克隆：

```python
from enhanced_tts_manager import EnhancedTTSManager

tts_manager = EnhancedTTSManager()

# 语音克隆
success = tts_manager.clone_voice(
    text="你好，这是克隆的声音。",
    reference_audio="path/to/reference.wav",
    output_path="cloned_output.wav"
)
```

## API使用

### 1. Web API端点

#### 获取可用引擎

```http
GET /api/tts/engines
```

响应：
```json
{
    "success": true,
    "engines": ["indextts2", "baidu"],
    "current_engine": "indextts2",
    "features": {
        "indextts2": {
            "emotion_control": true,
            "voice_cloning": true,
            "multilingual": true
        }
    }
}
```

#### 切换TTS引擎

```http
POST /api/tts/switch_engine
Content-Type: application/json

{
    "engine": "indextts2"
}
```

#### 生成对话音频

```http
POST /api/tts/dialogue/generate
Content-Type: application/json

{
    "text": "小明，你今天真棒！",
    "character": "小明",
    "emotion": "happy",
    "auto_emotion": true,
    "engine": "indextts2"
}
```

响应：
```json
{
    "success": true,
    "audio_url": "/cache/tts/dialogue_小明_happy_indextts2_abc123.wav",
    "file_id": "uuid-here",
    "synthesis_info": {
        "character": "小明",
        "final_emotion": "happy",
        "emotion_confidence": 0.85,
        "engine_used": "indextts2",
        "success": true
    }
}
```

#### 语音克隆

```http
POST /api/tts/voice_clone
Content-Type: application/json

{
    "text": "你好，这是克隆的声音。",
    "reference_audio": "path/to/reference.wav",
    "engine": "indextts2"
}
```

#### 获取角色列表

```http
GET /api/characters
```

响应：
```json
{
    "success": true,
    "characters": [
        {
            "name": "小明",
            "type": "child",
            "description": "8岁男孩，活泼开朗",
            "default_emotion": "happy",
            "available_emotions": ["happy", "surprised", "calm", "excited"]
        }
    ]
}
```

#### 情感分析

```http
POST /api/emotions/analyze
Content-Type: application/json

{
    "text": "太好了！我终于通过考试了！",
    "context": "今天是考试结果公布的日子"
}
```

响应：
```json
{
    "success": true,
    "emotion": "happy",
    "confidence": 0.92,
    "description": "开心愉快",
    "available_emotions": ["happy", "sad", "angry", "surprised", "fear", "calm", "gentle"]
}
```

### 2. Python API

#### 基本使用

```python
from enhanced_tts_manager import EnhancedTTSManager

# 创建TTS管理器
tts_manager = EnhancedTTSManager()

# 标准文本合成
success = tts_manager.synthesize_text("你好世界", "output.wav")

# 对话合成
audio_path, info = tts_manager.synthesize_dialogue(
    text="小明，你今天真棒！",
    character="小明",
    auto_emotion=True
)

# 语音克隆
success = tts_manager.clone_voice(
    text="这是克隆的声音",
    reference_audio="reference.wav",
    output_path="cloned.wav"
)
```

#### 高级配置

```python
# 自定义角色
from character_voice_manager import VoiceProfile

profile = VoiceProfile(
    name="自定义角色",
    type="adult_female",
    age=25,
    gender="female",
    personality="活泼开朗",
    description="25岁女性，声音甜美",
    voice_sample="custom_voice.wav",
    custom_emotions={
        "excited": [0.9, 0, 0, 0, 0, 0, 0.5, 0.2]
    }
)

tts_manager.voice_manager.add_character("自定义角色", profile)

# 使用自定义角色
audio_path, info = tts_manager.synthesize_dialogue(
    text="大家好！",
    character="自定义角色",
    emotion="excited"
)
```

## 配置选项

### 1. 系统配置

在 `config.py` 中可以配置以下选项：

```python
# IndexTTS2配置
INDEXTTS2_CONFIG = {
    'model_dir': 'third_party/index-tts/checkpoints',
    'use_fp16': True,  # 使用半精度推理（节省显存）
    'use_cuda_kernel': True,  # 使用CUDA内核加速
    'use_deepspeed': False,  # DeepSpeed加速（可选）
    'cache_dir': 'cache/indextts2',
    'max_text_length': 500,  # 最大文本长度
    'default_emo_alpha': 0.8  # 默认情感强度
}

# 增强TTS配置
ENHANCED_TTS_CONFIG = {
    'default_engine': 'indextts2',  # 默认引擎
    'fallback_engine': 'baidu',    # 备用引擎
    'auto_emotion': True,          # 自动情感分析
    'emotion_confidence_threshold': 0.5,  # 情感置信度阈值
    'cache_enabled': True,         # 启用音频缓存
    'max_cache_size': 100,         # 最大缓存数量
    'cache_cleanup_interval': 3600  # 缓存清理间隔（秒）
}
```

### 2. 角色配置

角色配置存储在 `config/character_voices.json` 中：

```json
{
  "小明": {
    "name": "小明",
    "type": "child",
    "age": 8,
    "gender": "male",
    "personality": "活泼开朗",
    "description": "8岁男孩，活泼好动，充满好奇心",
    "voice_sample": "examples/voice_01.wav",
    "default_emotion": "happy",
    "common_emotions": ["happy", "surprised", "calm", "excited"],
    "custom_emotions": {
      "excited": [0.9, 0, 0, 0, 0, 0, 0.5, 0.2]
    },
    "engine_specific_config": {
      "indextts2": {
        "voice_sample": "examples/voice_01.wav",
        "emo_alpha": 0.8
      },
      "baidu": {
        "per": 5,
        "spd": 6,
        "pit": 6
      }
    }
  }
}
```

## 性能优化

### 1. GPU加速

- 确保安装了CUDA版本的PyTorch
- 启用FP16推理减少显存占用
- 使用CUDA内核加速

### 2. 缓存策略

- 启用音频缓存避免重复合成
- 定期清理过期缓存
- 设置合理的缓存大小限制

### 3. 批量处理

- 对于长对话，考虑分段处理
- 使用异步音频生成提升响应速度
- 预加载常用角色语音

## 故障排除

### 1. 常见问题

#### IndexTTS2引擎初始化失败

**症状**: 看到"IndexTTS2引擎初始化失败"错误

**解决方案**:
1. 检查模型文件是否已下载
2. 确认Python版本 >= 3.10
3. 检查PyTorch是否正确安装
4. 验证CUDA环境（如果使用GPU）

#### 模型文件下载失败

**症状**: huggingface-cli命令失败

**解决方案**:
1. 检查网络连接
2. 尝试使用代理或VPN
3. 手动从Hugging Face下载模型文件
4. 检查磁盘空间是否足够

#### 内存不足

**症状**: CUDA out of memory 错误

**解决方案**:
1. 启用FP16模式
2. 减少批处理大小
3. 使用CPU模式
4. 升级GPU显存

### 2. 调试技巧

#### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 检查系统状态

```python
from enhanced_tts_manager import EnhancedTTSManager

tts_manager = EnhancedTTSManager()
stats = tts_manager.get_stats()
print(stats)
```

#### 测试单个组件

```python
# 测试IndexTTS2引擎
from tts_engines.index_tts2_engine import IndexTTS2Engine

engine = IndexTTS2Engine()
if engine.initialize():
    print("引擎初始化成功")
    # 进行进一步测试
```

## 更新和维护

### 1. 更新IndexTTS2

```bash
cd third_party/index-tts
git pull origin main
pip install -e .
```

### 2. 清理缓存

```python
from enhanced_tts_manager import EnhancedTTSManager

tts_manager = EnhancedTTSManager()
cleared = tts_manager.clear_cache()
print(f"清理了 {cleared} 个缓存文件")
```

### 3. 备份配置

定期备份以下文件：
- `config/character_voices.json`
- `.env` 文件
- 自定义语音样本

## 支持和反馈

如果您在使用过程中遇到问题：

1. 首先运行测试脚本诊断问题
2. 查看日志文件了解详细错误信息
3. 检查GitHub Issues寻找解决方案
4. 提交新的Issue报告问题

祝您使用愉快！🎉
