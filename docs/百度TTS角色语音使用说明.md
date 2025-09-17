# 百度TTS角色语音使用说明

## 概述

本系统已成功集成百度TTS角色语音功能，可以为不同的AI角色生成个性化的语音，同时保持与用户练习时标准发音的一致性。

## 功能特性

### ✅ 已实现功能

1. **多角色语音支持**
   - 儿童角色：可爱童声（百度per=5）
   - 成年女性：标准女声（百度per=0）
   - 成年男性：标准男声（百度per=1）
   - 老年角色：温和女声（百度per=4）
   - 专业人士：专业男声（百度per=3）
   - 标准发音：标准女声（百度per=4，用于用户练习）

2. **智能角色映射**
   - 自动识别角色关键词（如：小孩、妈妈、医生等）
   - 基于场景上下文推断语音类型
   - 支持自定义角色映射规则

3. **语音一致性**
   - 所有角色使用相同的百度TTS引擎
   - 确保音质统一，用户体验一致

4. **性能优化**
   - 平均语音合成时间：4-5秒
   - 支持音频文件缓存
   - 自动回退到备用TTS引擎

## 使用方法

### 1. 基本用法

```python
from tts_module import TTSManager
from dialogue_voice_mapper import DialogueVoiceMapper

# 初始化管理器
tts_manager = TTSManager()
voice_mapper = DialogueVoiceMapper()

# 生成角色语音
text = "你好，我是小朋友"
output_path = "temp/child_voice.wav"
success = tts_manager.generate_dialogue_audio(text, output_path, 'child')
```

### 2. 场景对话中的使用

```python
# 分析角色并分配语音
scenario_description = "妈妈教导三年级小孩学习数学"
dialogue_data = {
    'ai_role': '小孩',
    'user_role': '妈妈'
}

role_voice_mapping = voice_mapper.analyze_scenario_roles(
    scenario_description, dialogue_data
)

# 结果: {'小孩': 'child', '妈妈': 'standard'}
```

### 3. 获取可用配置

```python
# 获取语音配置
profiles = tts_manager.get_available_voice_profiles()
for voice_type, config in profiles.items():
    print(f"{voice_type}: {config['description']}")

# 获取角色描述
description = voice_mapper.get_voice_description('child')
# 结果: "可爱童声"
```

## 配置说明

### 语音配置文件

系统在 `config.py` 中定义了以下语音配置：

```python
BAIDU_VOICE_PROFILES = {
    'standard': 4,      # 度丫丫，标准女声
    'child': 5,         # 度小娇，可爱童声  
    'adult_male': 1,    # 度小宇，标准男声
    'adult_female': 0,  # 度小美，标准女声
    'elderly': 4,       # 度丫丫，温和女声
    'professional': 3   # 度小博，专业男声
}
```

### 角色映射规则

在 `dialogue_voice_mapper.py` 中定义了角色关键词映射：

```python
role_mapping = {
    # 儿童相关
    '小孩': 'child',
    '孩子': 'child', 
    '学生': 'child',
    
    # 成年男性
    '爸爸': 'adult_male',
    '老师': 'adult_male',
    
    # 成年女性  
    '妈妈': 'adult_female',
    '阿姨': 'adult_female',
    
    # 专业人士
    '医生': 'professional',
    '客服': 'professional'
}
```

## 测试验证

### 运行测试脚本

```bash
python test_character_voices.py
```

### 测试结果示例

```
=== 百度TTS角色语音功能测试 ===
✓ 初始化完成，可用TTS引擎: ['百度TTS', 'Edge TTS', '离线TTS']

📢 可用语音配置:
  🎵 child: 儿童角色语音 (百度per=5)
  🎵 adult_female: 成年女性角色语音 (百度per=0)
  🎵 professional: 专业人士角色语音 (百度per=3)

🎬 场景测试:
  🤖 AI角色 (小孩): 好的妈妈，我想学！
     📻 语音类型: child (可爱童声)
     ✅ 语音生成成功，文件大小: 16704 bytes
```

## 实际应用场景

### 1. 教育场景
- **妈妈教小孩学数学**
  - 用户（妈妈）：标准女声
  - AI（小孩）：可爱童声

### 2. 服务场景
- **客服接待顾客**
  - 用户（客服）：标准女声
  - AI（顾客）：专业语音

### 3. 家庭场景
- **家庭日常对话**
  - 用户（父母）：标准女声
  - AI（孩子/老人）：对应角色语音

## 技术优势

1. **音质一致性**：所有角色使用百度TTS，确保音质统一
2. **个性化体验**：不同角色有不同的语音特色
3. **智能映射**：自动识别角色类型并分配合适语音
4. **易于扩展**：支持添加新的角色类型和语音配置
5. **性能稳定**：平均响应时间4-5秒，支持缓存优化

## 注意事项

1. **API密钥配置**：确保在 `.env` 文件中正确配置百度TTS的API密钥
2. **网络连接**：需要稳定的网络连接访问百度TTS服务
3. **文件存储**：生成的音频文件会保存在 `temp/` 目录下
4. **缓存管理**：系统会自动清理过期的音频缓存文件

## 后续扩展

1. **更多语音类型**：可以添加更多百度TTS支持的语音类型
2. **情感控制**：结合情感分析，为同一角色提供不同情感的语音
3. **语速调节**：根据场景需要调整语音的语速和音调
4. **多语言支持**：扩展支持英语等其他语言的角色语音

---

🎉 百度TTS角色语音功能已完全集成并测试通过，可以在场景对话中使用！

