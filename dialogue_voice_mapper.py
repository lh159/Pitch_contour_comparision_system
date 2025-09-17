# -*- coding: utf-8 -*-
"""
对话角色语音映射器
根据角色名称和场景上下文，智能分配合适的语音类型
"""

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
            '小学生': 'child',
            '中学生': 'child',
            '女儿': 'child',
            '儿子': 'child',
            
            # 成年男性
            '爸爸': 'adult_male',
            '父亲': 'adult_male',
            '叔叔': 'adult_male',
            '老师': 'adult_male',  # 可根据具体场景调整
            '先生': 'adult_male',
            '男朋友': 'adult_male',
            '老公': 'adult_male',
            '丈夫': 'adult_male',
            '哥哥': 'adult_male',
            '弟弟': 'adult_male',
            
            # 成年女性
            '妈妈': 'adult_female',
            '母亲': 'adult_female',
            '阿姨': 'adult_female',
            '女士': 'adult_female',
            '女朋友': 'adult_female',
            '老婆': 'adult_female',
            '妻子': 'adult_female',
            '姐姐': 'adult_female',
            '妹妹': 'adult_female',
            
            # 老年人
            '爷爷': 'elderly',
            '奶奶': 'elderly',
            '外公': 'elderly',
            '外婆': 'elderly',
            '老人': 'elderly',
            
            # 专业人士
            '医生': 'professional',
            '律师': 'professional',
            '客服': 'professional',
            '经理': 'professional',
            '老板': 'professional',
            '销售': 'professional',
            '服务员': 'professional',
            '导购': 'professional'
        }
        
        # 场景到默认语音的映射
        self.scenario_mapping = {
            '教育': 'adult_female',
            '家庭': 'adult_female', 
            '商务': 'professional',
            '医疗': 'professional',
            '服务': 'professional',
            '朋友': 'adult_female',
            '购物': 'professional',
            '餐厅': 'professional',
            '学校': 'adult_female',
            '工作': 'professional'
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
    
    def get_voice_description(self, voice_type: str) -> str:
        """获取语音类型的描述"""
        descriptions = {
            'standard': '标准女声',
            'child': '可爱童声',
            'adult_male': '成年男声',
            'adult_female': '成年女声',
            'elderly': '温和语音',
            'professional': '专业语音'
        }
        return descriptions.get(voice_type, '默认语音')
    
    def add_custom_mapping(self, role_keyword: str, voice_type: str):
        """添加自定义角色映射"""
        self.role_mapping[role_keyword] = voice_type
    
    def get_supported_voice_types(self) -> list:
        """获取支持的语音类型列表"""
        return list(set(self.role_mapping.values()))
