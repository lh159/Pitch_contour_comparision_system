# 百度TTS在场景对话中的集成方案

## 概述

为了确保AI角色语音与用户练习时的标准发音保持一致的音质和风格，我们将复用当前系统中已有的百度TTS模块来为AI角色生成语音。这样可以：

1. **保持音质一致性** - 用户和AI使用相同的TTS引擎
2. **降低开发成本** - 复用现有的TTS基础设施
3. **提升用户体验** - 统一的语音风格更自然

## 技术实现方案

### 1. 扩展现有TTS模块

#### 1.1 增强TTS管理器以支持角色语音

```python
# tts_module.py 扩展
class TTSManager:
    def __init__(self):
        self.tts_engines = []
        self.voice_profiles = {}  # 新增：语音配置文件
        self._init_engines()
        self._init_voice_profiles()  # 新增：初始化语音配置
    
    def _init_voice_profiles(self):
        """初始化不同角色的语音配置"""
        self.voice_profiles = {
            # 标准发音（用户练习用）
            'standard': {
                'baidu_per': 4,  # 度丫丫，标准女声
                'description': '标准女声，用于用户练习'
            },
            
            # AI角色语音配置
            'child': {
                'baidu_per': 5,  # 度小娇，可爱童声
                'description': '儿童角色语音'
            },
            'adult_male': {
                'baidu_per': 1,  # 度小宇，标准男声
                'description': '成年男性角色语音'
            },
            'adult_female': {
                'baidu_per': 0,  # 度小美，标准女声
                'description': '成年女性角色语音'
            },
            'elderly': {
                'baidu_per': 4,  # 度丫丫，温和女声
                'description': '老年角色语音'
            },
            'professional': {
                'baidu_per': 3,  # 度小博，专业男声
                'description': '专业人士角色语音'
            }
        }
    
    def generate_dialogue_audio(self, text: str, output_path: str, 
                               role_type: str = 'standard') -> bool:
        """
        为对话角色生成语音
        :param text: 要合成的文本
        :param output_path: 输出音频文件路径
        :param role_type: 角色类型，决定使用的语音
        :return: 是否成功
        """
        
        # 获取角色语音配置
        voice_config = self.voice_profiles.get(role_type, self.voice_profiles['standard'])
        target_per = voice_config['baidu_per']
        
        print(f"为角色 '{role_type}' 生成语音: {text}")
        print(f"使用语音配置: {voice_config['description']} (per={target_per})")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 依次尝试各个TTS引擎，优先使用百度TTS以保持一致性
        for engine_name, engine in self.tts_engines:
            try:
                # 如果是百度TTS，设置特定的语音
                if isinstance(engine, BaiduTTS):
                    # 临时修改语音配置
                    original_per = engine.voice_per
                    engine.voice_per = target_per
                    
                    success = engine.synthesize(text, output_path)
                    
                    # 恢复原始配置
                    engine.voice_per = original_per
                    
                    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ 使用百度TTS成功生成角色语音: {role_type}")
                        return True
                else:
                    # 其他TTS引擎使用默认配置
                    if engine.synthesize(text, output_path):
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            print(f"✓ 使用 {engine_name} 成功生成角色语音")
                            return True
                            
            except Exception as e:
                print(f"✗ {engine_name} 生成角色语音失败: {e}")
                continue
        
        print("✗ 所有TTS引擎都无法生成角色语音")
        return False
    
    def get_available_voice_profiles(self) -> dict:
        """获取可用的语音配置文件"""
        return self.voice_profiles.copy()
```

#### 1.2 智能角色语音映射

```python
# dialogue_voice_mapper.py - 新建文件
class DialogueVoiceMapper:
    """对话角色语音映射器"""
    
    def __init__(self):
        # 角色关键词到语音类型的映射
        self.role_mapping = {
            # 儿童相关
            '小孩': 'child',
            '孩子': 'child', 
            '小朋友': 'child',
            '宝宝': 'child',
            '学生': 'child',
            
            # 成年男性
            '爸爸': 'adult_male',
            '父亲': 'adult_male',
            '叔叔': 'adult_male',
            '老师': 'adult_male',  # 可根据具体场景调整
            '先生': 'adult_male',
            '男朋友': 'adult_male',
            
            # 成年女性
            '妈妈': 'adult_female',
            '母亲': 'adult_female',
            '阿姨': 'adult_female',
            '女士': 'adult_female',
            '女朋友': 'adult_female',
            
            # 老年人
            '爷爷': 'elderly',
            '奶奶': 'elderly',
            '外公': 'elderly',
            '外婆': 'elderly',
            
            # 专业人士
            '医生': 'professional',
            '律师': 'professional',
            '客服': 'professional',
            '经理': 'professional',
            '老板': 'professional'
        }
        
        # 场景到默认语音的映射
        self.scenario_mapping = {
            '教育': 'adult_female',
            '家庭': 'adult_female', 
            '商务': 'professional',
            '医疗': 'professional',
            '服务': 'professional',
            '朋友': 'adult_female'
        }
    
    def map_role_to_voice(self, role_name: str, scenario_context: str = '') -> str:
        """
        将角色名称映射到语音类型
        :param role_name: 角色名称
        :param scenario_context: 场景上下文
        :return: 语音类型
        """
        
        # 直接匹配角色名称
        for keyword, voice_type in self.role_mapping.items():
            if keyword in role_name:
                return voice_type
        
        # 基于场景上下文推断
        for scenario_keyword, voice_type in self.scenario_mapping.items():
            if scenario_keyword in scenario_context:
                return voice_type
        
        # 默认返回成年女性语音
        return 'adult_female'
    
    def analyze_scenario_roles(self, scenario_description: str, 
                              dialogue_data: dict) -> dict:
        """
        分析场景中的角色并分配语音
        :param scenario_description: 场景描述
        :param dialogue_data: 对话数据
        :return: 角色语音映射
        """
        
        role_voice_mapping = {}
        
        # 获取AI角色信息
        ai_role = dialogue_data.get('ai_role', '')
        user_role = dialogue_data.get('user_role', '')
        
        # 为AI角色分配语音
        ai_voice_type = self.map_role_to_voice(ai_role, scenario_description)
        role_voice_mapping[ai_role] = ai_voice_type
        
        # 用户角色总是使用标准语音
        role_voice_mapping[user_role] = 'standard'
        
        print(f"角色语音映射: {role_voice_mapping}")
        
        return role_voice_mapping
```

### 2. 更新Web接口以支持角色语音

#### 2.1 修改场景对话API

```python
# web_interface.py 更新
from dialogue_voice_mapper import DialogueVoiceMapper

# 全局变量
dialogue_sessions = {}  # 对话会话存储
voice_mapper = DialogueVoiceMapper()  # 语音映射器

@app.route('/api/scenario/generate', methods=['POST'])
def generate_scenario_dialogue():
    """生成场景对话（增强版）"""
    try:
        data = request.get_json()
        scenario = data.get('scenario', '').strip()
        
        if not scenario:
            return jsonify({
                'success': False,
                'error': '请输入场景描述'
            }), 400
        
        # 调用DeepSeek生成对话
        generator = DeepSeekDialogueGenerator()
        result = generator.generate_scenario_dialogue(scenario)
        
        if result.get('success'):
            dialogue_data = result['data']
            
            # 分析角色并分配语音
            role_voice_mapping = voice_mapper.analyze_scenario_roles(
                scenario, dialogue_data
            )
            
            # 保存对话会话（包含语音映射）
            session_id = str(uuid.uuid4())
            dialogue_sessions[session_id] = {
                'dialogue_data': dialogue_data,
                'voice_mapping': role_voice_mapping,
                'scenario_description': scenario,
                'created_at': time.time()
            }
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'dialogue_data': dialogue_data,
                'voice_mapping': role_voice_mapping
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '对话生成失败')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/scenario/next', methods=['POST'])
def get_next_dialogue():
    """获取下一句对话（增强版，支持角色语音）"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        current_order = data.get('current_order', 0)
        
        if session_id not in dialogue_sessions:
            return jsonify({
                'success': False,
                'error': '对话会话不存在'
            }), 404
        
        session_data = dialogue_sessions[session_id]
        dialogue_data = session_data['dialogue_data']
        voice_mapping = session_data['voice_mapping']
        
        next_dialogue = None
        
        for dialogue in dialogue_data['dialogues']:
            if dialogue['order'] == current_order + 1:
                next_dialogue = dialogue
                break
        
        if next_dialogue:
            # 如果是AI角色台词，生成带角色语音的TTS音频
            if next_dialogue['speaker'] == 'ai':
                file_id = str(uuid.uuid4())
                filename = f"ai_dialogue_{file_id}.wav"
                output_path = os.path.join(Config.TEMP_FOLDER, filename)
                
                # 获取AI角色的语音类型
                ai_role = dialogue_data['ai_role']
                voice_type = voice_mapping.get(ai_role, 'adult_female')
                
                # 使用角色语音生成音频
                success = tts_manager.generate_dialogue_audio(
                    next_dialogue['text'], output_path, voice_type
                )
                
                if success:
                    next_dialogue['audio_url'] = url_for('serve_temp_file', filename=filename)
                    next_dialogue['voice_type'] = voice_type
                    next_dialogue['voice_description'] = tts_manager.voice_profiles.get(
                        voice_type, {}
                    ).get('description', '默认语音')
            
            return jsonify({
                'success': True,
                'dialogue': next_dialogue,
                'is_complete': current_order + 1 >= len(dialogue_data['dialogues'])
            })
        else:
            return jsonify({
                'success': True,
                'dialogue': None,
                'is_complete': True
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取对话失败: {str(e)}'
        }), 500

@app.route('/api/voice/profiles', methods=['GET'])
def get_voice_profiles():
    """获取可用的语音配置"""
    try:
        profiles = tts_manager.get_available_voice_profiles()
        return jsonify({
            'success': True,
            'profiles': profiles
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### 3. 前端界面增强

#### 3.1 显示语音信息

```javascript
// scenario-dialogue.js 更新
class ScenarioDialogueManager {
    // ... 现有代码 ...
    
    displayDialogue() {
        const container = document.getElementById('dialogueContainer');
        const titleEl = document.getElementById('scenarioTitle');
        const contentEl = document.getElementById('dialogueContent');
        
        titleEl.textContent = `场景：${this.dialogueData.scenario_title}`;
        
        // 显示角色信息（增强版，包含语音信息）
        const userRole = this.dialogueData.user_role;
        const aiRole = this.dialogueData.ai_role;
        const voiceMapping = this.voiceMapping || {};
        
        document.querySelector('.user-role').innerHTML = 
            `👤 您的角色：${userRole} <small class="text-muted">(标准语音)</small>`;
        
        const aiVoiceType = voiceMapping[aiRole] || 'adult_female';
        const voiceDesc = this.getVoiceDescription(aiVoiceType);
        document.querySelector('.ai-role').innerHTML = 
            `🤖 AI角色：${aiRole} <small class="text-muted">(${voiceDesc})</small>`;
        
        // ... 其余代码保持不变 ...
    }
    
    getVoiceDescription(voiceType) {
        const descriptions = {
            'standard': '标准女声',
            'child': '可爱童声',
            'adult_male': '成年男声',
            'adult_female': '成年女声',
            'elderly': '温和语音',
            'professional': '专业语音'
        };
        return descriptions[voiceType] || '默认语音';
    }
    
    async generateScenario() {
        // ... 现有代码 ...
        
        try {
            const response = await fetch('/api/scenario/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario: scenario })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentSession = data.session_id;
                this.dialogueData = data.dialogue_data;
                this.voiceMapping = data.voice_mapping;  // 新增：保存语音映射
                this.currentOrder = 0;
                
                this.displayDialogue();
                showAlert('场景对话生成成功！', 'success');
            } else {
                showAlert(`生成失败: ${data.error}`, 'danger');
            }
        } catch (error) {
            showAlert(`网络错误: ${error.message}`, 'danger');
        }
        
        // ... 其余代码保持不变 ...
    }
    
    async playAIDialogue(dialogue) {
        try {
            // 获取AI对话音频
            const response = await fetch('/api/scenario/next', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.currentSession,
                    current_order: this.currentOrder - 1
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.dialogue && data.dialogue.audio_url) {
                const dialogueInfo = data.dialogue;
                const audio = new Audio(dialogueInfo.audio_url);
                
                // 显示语音信息
                if (dialogueInfo.voice_description) {
                    const statusEl = document.getElementById(`status-${this.currentOrder}`);
                    statusEl.innerHTML = `播放中 <small>(${dialogueInfo.voice_description})</small>`;
                }
                
                audio.onplay = () => {
                    this.isPlaying = true;
                };
                
                audio.onended = () => {
                    this.isPlaying = false;
                    const statusEl = document.getElementById(`status-${this.currentOrder}`);
                    statusEl.textContent = '已完成';
                    statusEl.className = 'dialogue-status completed';
                    
                    // 自动进入下一轮对话
                    setTimeout(() => {
                        this.currentOrder++;
                        this.processCurrentDialogue();
                    }, 1000);
                };
                
                audio.play();
            }
        } catch (error) {
            showAlert(`播放失败: ${error.message}`, 'danger');
        }
    }
}
```

### 4. 配置文件更新

#### 4.1 百度TTS语音配置

```python
# config.py 更新
class Config:
    # ... 现有配置 ...
    
    # 百度TTS语音配置
    BAIDU_VOICE_PROFILES = {
        'standard': 4,      # 度丫丫，标准女声
        'child': 5,         # 度小娇，可爱童声  
        'adult_male': 1,    # 度小宇，标准男声
        'adult_female': 0,  # 度小美，标准女声
        'elderly': 4,       # 度丫丫，温和女声
        'professional': 3   # 度小博，专业男声
    }
    
    # 对话语音缓存配置
    DIALOGUE_AUDIO_CACHE_SIZE = 100  # 缓存的对话音频数量
    DIALOGUE_AUDIO_CACHE_TTL = 3600  # 缓存过期时间（秒）
```

## 使用示例

### 场景：妈妈教小孩学数学

```
用户输入场景：妈妈教导三年级小孩学习数学

系统生成对话：
1. 妈妈（用户）："宝贝，我们来学习加法好吗？" [标准女声]
2. 小孩（AI）："好的妈妈，我想学！" [可爱童声] 
3. 妈妈（用户）："那么3加2等于多少呢？" [标准女声]
4. 小孩（AI）："让我想想...是5吗？" [可爱童声]
```

### 场景：客服接待顾客

```
用户输入场景：客服接待顾客咨询产品信息

系统生成对话：
1. 客服（用户）："您好，请问有什么可以帮助您的？" [标准女声]
2. 顾客（AI）："我想了解一下你们的新产品。" [专业男声]
3. 客服（用户）："当然可以，我来为您详细介绍。" [标准女声]
```

## 技术优势

### 1. 语音一致性
- 所有角色都使用百度TTS，确保音质统一
- 不同角色使用不同的语音参数，增加真实感

### 2. 智能角色映射
- 自动识别角色类型并分配合适的语音
- 支持场景上下文分析，提高映射准确性

### 3. 用户体验优化
- 显示语音类型信息，让用户了解AI角色特点
- 保持与现有系统的无缝集成

### 4. 性能优化
- 复用现有TTS基础设施，降低延迟
- 支持音频缓存，提高响应速度

这个方案确保了AI角色语音与用户练习时的标准发音使用相同的TTS引擎，同时通过不同的语音参数为不同角色提供个性化的语音特色，大大提升了场景对话的沉浸感和真实性。
