# -*- coding: utf-8 -*-
"""
角色语音管理器
管理不同角色的语音配置和个性化设置
"""

import json
import os
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class VoiceProfile:
    """语音配置文件"""
    name: str
    type: str  # child, adult_female, adult_male, elderly
    age: int
    gender: str  # male, female, neutral
    personality: str
    description: str
    voice_sample: Optional[str] = None
    default_emotion: str = 'calm'
    common_emotions: List[str] = None
    custom_emotions: Dict[str, List[float]] = None
    engine_specific_config: Dict[str, Any] = None
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.common_emotions is None:
            self.common_emotions = ['calm', 'happy']
        if self.custom_emotions is None:
            self.custom_emotions = {}
        if self.engine_specific_config is None:
            self.engine_specific_config = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

class CharacterVoiceManager:
    """角色语音管理器"""
    
    def __init__(self, config_file: str = 'config/character_voices.json'):
        self.config_file = config_file
        self.characters: Dict[str, VoiceProfile] = {}
        self.load_character_config()
    
    def load_character_config(self):
        """加载角色语音配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 转换为VoiceProfile对象
                for name, config in data.items():
                    try:
                        self.characters[name] = VoiceProfile(**config)
                    except Exception as e:
                        print(f"加载角色 {name} 配置失败: {e}")
                        
                print(f"✓ 成功加载 {len(self.characters)} 个角色配置")
            except Exception as e:
                print(f"✗ 加载角色配置失败: {e}")
                self.create_default_config()
        else:
            # 创建默认配置
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认角色配置"""
        default_characters = {
            "小明": VoiceProfile(
                name="小明",
                type="child",
                age=8,
                gender="male",
                personality="活泼开朗",
                description="8岁男孩，活泼好动，充满好奇心",
                voice_sample="examples/voice_01.wav",
                default_emotion="happy",
                common_emotions=["happy", "surprised", "calm", "excited"],
                custom_emotions={
                    "excited": [0.9, 0, 0, 0, 0, 0, 0.5, 0.2]
                },
                engine_specific_config={
                    "indextts2": {
                        "voice_sample": "examples/voice_01.wav",
                        "emo_alpha": 0.8
                    },
                    "baidu": {
                        "per": 5,  # 度小娇
                        "spd": 6,
                        "pit": 6
                    }
                }
            ),
            
            "李老师": VoiceProfile(
                name="李老师",
                type="adult_female",
                age=35,
                gender="female",
                personality="温和耐心",
                description="35岁女教师，温和亲切，有耐心",
                voice_sample="examples/voice_07.wav",
                default_emotion="calm",
                common_emotions=["calm", "happy", "gentle", "encouraging"],
                custom_emotions={
                    "encouraging": [0.3, 0, 0, 0, 0, 0, 0.2, 0.7],
                    "patient": [0, 0, 0, 0, 0, 0, 0.1, 0.9]
                },
                engine_specific_config={
                    "indextts2": {
                        "voice_sample": "examples/voice_07.wav",
                        "emo_alpha": 0.7
                    },
                    "baidu": {
                        "per": 0,  # 度小美
                        "spd": 4,
                        "pit": 4
                    }
                }
            ),
            
            "王爸爸": VoiceProfile(
                name="王爸爸",
                type="adult_male",
                age=40,
                gender="male",
                personality="严肃负责",
                description="40岁男性，严肃但关爱家人",
                voice_sample="examples/voice_10.wav",
                default_emotion="calm",
                common_emotions=["calm", "serious", "happy", "proud"],
                custom_emotions={
                    "serious": [0, 0, 0, 0, 0, 0, 0, 1.0],
                    "proud": [0.5, 0, 0, 0, 0, 0, 0.3, 0.4]
                },
                engine_specific_config={
                    "indextts2": {
                        "voice_sample": "examples/voice_10.wav",
                        "emo_alpha": 0.6
                    },
                    "baidu": {
                        "per": 1,  # 度小宇
                        "spd": 5,
                        "pit": 3
                    }
                }
            ),
            
            "奶奶": VoiceProfile(
                name="奶奶",
                type="elderly",
                age=70,
                gender="female",
                personality="慈祥温暖",
                description="70岁老奶奶，慈祥温暖，充满智慧",
                voice_sample="examples/voice_04.wav",
                default_emotion="gentle",
                common_emotions=["gentle", "calm", "happy", "caring"],
                custom_emotions={
                    "caring": [0.2, 0, 0, 0, 0, 0, 0.1, 0.8],
                    "wise": [0, 0, 0, 0, 0, 0.2, 0, 0.8]
                },
                engine_specific_config={
                    "indextts2": {
                        "voice_sample": "examples/voice_04.wav",
                        "emo_alpha": 0.9
                    },
                    "baidu": {
                        "per": 4,  # 度丫丫
                        "spd": 4,
                        "pit": 4
                    }
                }
            )
        }
        
        self.characters = default_characters
        self.save_character_config()
        print("✓ 创建默认角色配置")
    
    def save_character_config(self):
        """保存角色配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 转换为字典格式保存
            data = {}
            for name, profile in self.characters.items():
                profile.updated_at = datetime.now().isoformat()
                data[name] = asdict(profile)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 角色配置已保存到 {self.config_file}")
        except Exception as e:
            print(f"✗ 保存角色配置失败: {e}")
    
    def get_character_voice_config(self, character_name: str) -> Optional[VoiceProfile]:
        """获取角色语音配置"""
        return self.characters.get(character_name)
    
    def get_character_config_for_engine(self, character_name: str, engine_name: str) -> Dict:
        """获取特定引擎的角色配置"""
        profile = self.get_character_voice_config(character_name)
        if not profile:
            return {}
        
        base_config = {
            'type': profile.type,
            'default_emotion': profile.default_emotion,
            'description': profile.description
        }
        
        # 添加引擎特定配置
        engine_config = profile.engine_specific_config.get(engine_name, {})
        base_config.update(engine_config)
        
        return base_config
    
    def add_character(self, name: str, profile: VoiceProfile):
        """添加新角色"""
        profile.name = name
        profile.created_at = datetime.now().isoformat()
        profile.updated_at = datetime.now().isoformat()
        
        self.characters[name] = profile
        self.save_character_config()
        print(f"✓ 添加角色: {name}")
    
    def update_character(self, name: str, **kwargs):
        """更新角色配置"""
        if name not in self.characters:
            print(f"✗ 角色不存在: {name}")
            return False
        
        profile = self.characters[name]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now().isoformat()
        self.save_character_config()
        print(f"✓ 更新角色: {name}")
        return True
    
    def remove_character(self, name: str) -> bool:
        """删除角色"""
        if name in self.characters:
            del self.characters[name]
            self.save_character_config()
            print(f"✓ 删除角色: {name}")
            return True
        else:
            print(f"✗ 角色不存在: {name}")
            return False
    
    def get_all_characters(self) -> List[str]:
        """获取所有角色名称"""
        return list(self.characters.keys())
    
    def get_characters_by_type(self, character_type: str) -> List[str]:
        """根据类型获取角色列表"""
        return [name for name, profile in self.characters.items() 
                if profile.type == character_type]
    
    def get_characters_by_gender(self, gender: str) -> List[str]:
        """根据性别获取角色列表"""
        return [name for name, profile in self.characters.items() 
                if profile.gender == gender]
    
    def get_character_emotions(self, character_name: str) -> List[str]:
        """获取角色支持的情感列表"""
        profile = self.get_character_voice_config(character_name)
        if profile:
            emotions = profile.common_emotions.copy()
            emotions.extend(profile.custom_emotions.keys())
            return list(set(emotions))  # 去重
        return []
    
    def add_character_emotion(self, character_name: str, emotion_name: str, 
                            emotion_vector: List[float] = None):
        """为角色添加自定义情感"""
        if character_name not in self.characters:
            print(f"✗ 角色不存在: {character_name}")
            return False
        
        profile = self.characters[character_name]
        
        if emotion_vector:
            # 添加自定义情感向量
            profile.custom_emotions[emotion_name] = emotion_vector
        else:
            # 添加到常用情感列表
            if emotion_name not in profile.common_emotions:
                profile.common_emotions.append(emotion_name)
        
        self.save_character_config()
        print(f"✓ 为角色 {character_name} 添加情感: {emotion_name}")
        return True
    
    def clone_character(self, source_name: str, new_name: str, **modifications) -> bool:
        """克隆角色配置"""
        if source_name not in self.characters:
            print(f"✗ 源角色不存在: {source_name}")
            return False
        
        if new_name in self.characters:
            print(f"✗ 目标角色已存在: {new_name}")
            return False
        
        # 复制源角色配置
        source_profile = self.characters[source_name]
        new_profile = VoiceProfile(
            name=new_name,
            type=source_profile.type,
            age=source_profile.age,
            gender=source_profile.gender,
            personality=source_profile.personality,
            description=source_profile.description,
            voice_sample=source_profile.voice_sample,
            default_emotion=source_profile.default_emotion,
            common_emotions=source_profile.common_emotions.copy(),
            custom_emotions=source_profile.custom_emotions.copy(),
            engine_specific_config=source_profile.engine_specific_config.copy()
        )
        
        # 应用修改
        for key, value in modifications.items():
            if hasattr(new_profile, key):
                setattr(new_profile, key, value)
        
        self.add_character(new_name, new_profile)
        return True
    
    def import_character_from_audio(self, name: str, audio_path: str, 
                                  character_type: str = 'adult_female',
                                  **kwargs) -> bool:
        """从音频文件导入角色"""
        if not os.path.exists(audio_path):
            print(f"✗ 音频文件不存在: {audio_path}")
            return False
        
        # 创建角色配置
        profile = VoiceProfile(
            name=name,
            type=character_type,
            age=kwargs.get('age', 30),
            gender=kwargs.get('gender', 'female'),
            personality=kwargs.get('personality', '未知'),
            description=kwargs.get('description', f'从音频文件导入的角色: {name}'),
            voice_sample=audio_path,
            default_emotion=kwargs.get('default_emotion', 'calm')
        )
        
        self.add_character(name, profile)
        return True
    
    def export_character_config(self, character_name: str, export_path: str) -> bool:
        """导出角色配置"""
        if character_name not in self.characters:
            print(f"✗ 角色不存在: {character_name}")
            return False
        
        try:
            profile = self.characters[character_name]
            config_data = asdict(profile)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 角色配置已导出到: {export_path}")
            return True
        except Exception as e:
            print(f"✗ 导出角色配置失败: {e}")
            return False
    
    def import_character_config(self, import_path: str) -> bool:
        """导入角色配置"""
        if not os.path.exists(import_path):
            print(f"✗ 配置文件不存在: {import_path}")
            return False
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            profile = VoiceProfile(**config_data)
            self.add_character(profile.name, profile)
            return True
        except Exception as e:
            print(f"✗ 导入角色配置失败: {e}")
            return False
    
    def get_character_stats(self) -> Dict:
        """获取角色统计信息"""
        stats = {
            'total_characters': len(self.characters),
            'by_type': {},
            'by_gender': {},
            'by_age_group': {},
            'total_emotions': 0
        }
        
        for profile in self.characters.values():
            # 按类型统计
            stats['by_type'][profile.type] = stats['by_type'].get(profile.type, 0) + 1
            
            # 按性别统计
            stats['by_gender'][profile.gender] = stats['by_gender'].get(profile.gender, 0) + 1
            
            # 按年龄组统计
            if profile.age < 18:
                age_group = 'child'
            elif profile.age < 60:
                age_group = 'adult'
            else:
                age_group = 'elderly'
            stats['by_age_group'][age_group] = stats['by_age_group'].get(age_group, 0) + 1
            
            # 情感统计
            emotions_count = len(profile.common_emotions) + len(profile.custom_emotions)
            stats['total_emotions'] += emotions_count
        
        return stats

# 使用示例
if __name__ == '__main__':
    # 创建角色管理器
    manager = CharacterVoiceManager()
    
    # 显示所有角色
    print("=== 所有角色 ===")
    for name in manager.get_all_characters():
        profile = manager.get_character_voice_config(name)
        print(f"{name}: {profile.description}")
    
    # 显示统计信息
    print("\n=== 角色统计 ===")
    stats = manager.get_character_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # 测试角色情感
    print("\n=== 角色情感测试 ===")
    for character in ["小明", "李老师"]:
        emotions = manager.get_character_emotions(character)
        print(f"{character} 支持的情感: {emotions}")
