# -*- coding: utf-8 -*-
"""
DeepSeek API集成模块
用于场景对话生成功能
"""
import os
import requests
import json
import time
from typing import Dict, List, Optional
from config import Config

class DeepSeekDialogueGenerator:
    """DeepSeek对话生成器"""
    
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
        if not self.api_key:
            print("⚠ 警告: 未设置DEEPSEEK_API_KEY环境变量")
        else:
            print("✓ DeepSeek API已配置")
    
    def generate_scenario_dialogue(self, scenario_description: str, 
                                 dialogue_rounds: int = 6) -> Dict:
        """
        基于场景描述生成对话
        
        Args:
            scenario_description: 场景描述
            dialogue_rounds: 对话轮数
            
        Returns:
            Dict: 包含生成结果的字典
        """
        
        if not self.api_key:
            return {
                "success": False, 
                "error": "DeepSeek API密钥未配置，请在.env文件中设置DEEPSEEK_API_KEY"
            }
        
        system_prompt = f"""
你是一个专业的中文对话生成助手。根据用户提供的场景描述，生成一个自然、生动的中文对话。

要求：
1. 对话应该包含{dialogue_rounds}轮交互（每轮包含用户和AI各说一句话）
2. 明确区分两个角色的台词
3. 语言自然流畅，符合中文表达习惯
4. 每句台词长度适中（5-20个字）
5. 内容积极正面，适合发音练习
6. 对话要有连贯性和逻辑性

输出格式：严格按照JSON格式输出，不要包含任何其他文字
{{
    "scenario_title": "场景标题",
    "user_role": "用户角色名称",
    "ai_role": "AI角色名称", 
    "dialogues": [
        {{"speaker": "user", "text": "用户台词", "order": 1}},
        {{"speaker": "ai", "text": "AI台词", "order": 2}},
        {{"speaker": "user", "text": "用户台词", "order": 3}},
        {{"speaker": "ai", "text": "AI台词", "order": 4}}
    ]
}}
"""
        
        user_prompt = f"请基于以下场景生成对话：{scenario_description}"
        
        try:
            print(f"正在调用DeepSeek API生成对话...")
            print(f"场景描述: {scenario_description}")
            
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                dialogue_content = result['choices'][0]['message']['content']
                print(f"API调用成功，返回内容长度: {len(dialogue_content)}")
                return self._parse_dialogue_response(dialogue_content)
            else:
                error_msg = f"API调用失败: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                print(f"✗ {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": "API请求超时，请重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "网络连接失败，请检查网络连接"}
        except Exception as e:
            error_msg = f"生成对话失败: {str(e)}"
            print(f"✗ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _parse_dialogue_response(self, content: str) -> Dict:
        """解析AI返回的对话内容"""
        try:
            print("正在解析API返回的对话内容...")
            
            # 清理内容，移除可能的markdown代码块标记
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # 尝试解析JSON
            dialogue_data = json.loads(content)
            
            # 验证必要字段
            required_fields = ['scenario_title', 'user_role', 'ai_role', 'dialogues']
            for field in required_fields:
                if field not in dialogue_data:
                    return {"success": False, "error": f"返回数据缺少必要字段: {field}"}
            
            # 验证对话格式
            dialogues = dialogue_data['dialogues']
            if not isinstance(dialogues, list) or len(dialogues) == 0:
                return {"success": False, "error": "对话数据格式错误"}
            
            # 验证每个对话项
            for i, dialogue in enumerate(dialogues):
                required_dialogue_fields = ['speaker', 'text', 'order']
                for field in required_dialogue_fields:
                    if field not in dialogue:
                        return {"success": False, "error": f"对话项{i+1}缺少字段: {field}"}
                
                if dialogue['speaker'] not in ['user', 'ai']:
                    return {"success": False, "error": f"对话项{i+1}的speaker字段值无效: {dialogue['speaker']}"}
            
            print(f"✓ 对话解析成功，包含{len(dialogues)}轮对话")
            print(f"场景: {dialogue_data['scenario_title']}")
            print(f"用户角色: {dialogue_data['user_role']}")
            print(f"AI角色: {dialogue_data['ai_role']}")
            
            return {"success": True, "data": dialogue_data}
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析失败: {e}")
            print(f"原始内容: {content[:500]}...")
            # 尝试备用解析方法
            return self._fallback_parse(content)
        except Exception as e:
            print(f"✗ 对话解析异常: {e}")
            return {"success": False, "error": f"对话解析失败: {str(e)}"}
    
    def _fallback_parse(self, content: str) -> Dict:
        """备用解析方法，当JSON解析失败时使用"""
        try:
            print("尝试使用备用解析方法...")
            
            # 简单的文本解析逻辑
            lines = content.split('\n')
            scenario_title = "生成的场景对话"
            user_role = "用户"
            ai_role = "AI助手"
            dialogues = []
            
            # 尝试从内容中提取对话
            order = 1
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                
                # 简单的对话识别
                if '：' in line or ':' in line:
                    if order <= Config.DEFAULT_DIALOGUE_ROUNDS * 2:
                        speaker = 'user' if order % 2 == 1 else 'ai'
                        text = line.split('：')[-1].split(':')[-1].strip()
                        if text and len(text) <= 50:  # 合理的台词长度
                            dialogues.append({
                                'speaker': speaker,
                                'text': text,
                                'order': order
                            })
                            order += 1
            
            # 如果没有解析到足够的对话，生成默认对话
            if len(dialogues) < 4:
                print("备用解析也失败，生成默认对话")
                return self._generate_default_dialogue()
            
            dialogue_data = {
                'scenario_title': scenario_title,
                'user_role': user_role,
                'ai_role': ai_role,
                'dialogues': dialogues
            }
            
            print(f"✓ 备用解析成功，生成{len(dialogues)}轮对话")
            return {"success": True, "data": dialogue_data}
            
        except Exception as e:
            print(f"✗ 备用解析也失败: {e}")
            return self._generate_default_dialogue()
    
    def _generate_default_dialogue(self) -> Dict:
        """生成默认对话（当所有解析方法都失败时）"""
        print("生成默认场景对话...")
        
        default_dialogue = {
            'scenario_title': '日常对话练习',
            'user_role': '用户',
            'ai_role': 'AI助手',
            'dialogues': [
                {'speaker': 'user', 'text': '你好，很高兴见到你。', 'order': 1},
                {'speaker': 'ai', 'text': '你好！我也很高兴见到你。', 'order': 2},
                {'speaker': 'user', 'text': '今天天气真不错。', 'order': 3},
                {'speaker': 'ai', 'text': '是的，阳光明媚的日子。', 'order': 4},
                {'speaker': 'user', 'text': '我们来练习发音吧。', 'order': 5},
                {'speaker': 'ai', 'text': '好的，让我们开始吧！', 'order': 6}
            ]
        }
        
        return {"success": True, "data": default_dialogue}
    
    def test_api_connection(self) -> Dict:
        """测试API连接"""
        if not self.api_key:
            return {"success": False, "error": "API密钥未配置"}
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": "你好"}
                    ],
                    "max_tokens": 10
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "API连接正常"}
            else:
                return {"success": False, "error": f"API测试失败: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": f"API连接测试失败: {str(e)}"}

# 全局实例
deepseek_generator = None

def get_deepseek_generator() -> DeepSeekDialogueGenerator:
    """获取DeepSeek生成器实例"""
    global deepseek_generator
    if deepseek_generator is None:
        deepseek_generator = DeepSeekDialogueGenerator()
    return deepseek_generator

if __name__ == "__main__":
    # 测试代码
    generator = DeepSeekDialogueGenerator()
    
    # 测试API连接
    test_result = generator.test_api_connection()
    print(f"API连接测试: {test_result}")
    
    if test_result['success']:
        # 测试对话生成
        result = generator.generate_scenario_dialogue("妈妈教导三年级小孩学习数学")
        print(f"\n对话生成测试: {result}")
