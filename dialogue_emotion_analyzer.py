# -*- coding: utf-8 -*-
"""
对话情感分析器
基于文本内容自动识别情感表达
"""

import re
import jieba
from typing import Dict, List, Tuple, Optional
from collections import Counter

class DialogueEmotionAnalyzer:
    """对话情感分析器"""
    
    def __init__(self):
        # 情感关键词映射
        self.emotion_keywords = {
            'happy': {
                'keywords': ['高兴', '开心', '快乐', '兴奋', '哈哈', '太好了', '棒极了', 
                           '真棒', '厉害', '不错', '满意', '喜欢', '爱', '笑', '乐', 
                           '欢乐', '愉快', '舒服', '幸福', '美好', '棒', '好极了'],
                'weight': 1.0
            },
            'sad': {
                'keywords': ['难过', '伤心', '沮丧', '失望', '哭', '眼泪', '痛苦', 
                           '悲伤', '委屈', '郁闷', '忧愁', '愁', '苦', '惨', 
                           '可怜', '心疼', '遗憾', '无奈', '绝望', '孤独'],
                'weight': 1.0
            },
            'angry': {
                'keywords': ['生气', '愤怒', '气死了', '讨厌', '烦人', '混蛋', 
                           '可恶', '该死', '愤慨', '恼火', '火大', '气愤', 
                           '恨', '怒', '暴躁', '不爽', '烦躁', '恶心'],
                'weight': 1.2
            },
            'surprised': {
                'keywords': ['惊讶', '吃惊', '不敢相信', '天哪', '哇', '真的吗', 
                           '什么', '怎么可能', '不可能', '震惊', '意外', '没想到',
                           '竟然', '居然', '原来', '难道', '咦', '呀'],
                'weight': 0.8
            },
            'fear': {
                'keywords': ['害怕', '恐惧', '担心', '紧张', '吓人', '可怕', 
                           '恐怖', '惊恐', '慌张', '不安', '焦虑', '忧虑',
                           '怕', '吓', '慌', '紧张', '胆怯', '畏惧'],
                'weight': 1.0
            },
            'calm': {
                'keywords': ['平静', '冷静', '正常', '好的', '明白', '知道了', 
                           '理解', '清楚', '当然', '没问题', '可以', '行',
                           '嗯', '哦', '是的', '对', '好'],
                'weight': 0.5
            },
            'gentle': {
                'keywords': ['温柔', '轻柔', '温和', '柔和', '温暖', '亲切', 
                           '和蔼', '慈祥', '体贴', '关心', '照顾', '呵护',
                           '宝贝', '亲爱的', '小心', '慢慢来'],
                'weight': 0.7
            }
        }
        
        # 标点符号情感提示
        self.punctuation_emotions = {
            '！': ('surprised', 0.6),
            '!': ('surprised', 0.6),
            '？': ('surprised', 0.4),
            '?': ('surprised', 0.4),
            '。': ('calm', 0.2),
            '.': ('calm', 0.2),
            '...': ('sad', 0.5),
            '…': ('sad', 0.5),
            '！！': ('happy', 0.8),
            '!!': ('happy', 0.8),
            '？？': ('surprised', 0.7),
            '??': ('surprised', 0.7)
        }
        
        # 语气词情感提示
        self.modal_particles = {
            '哈哈': ('happy', 0.9),
            '呵呵': ('happy', 0.6),
            '嘿嘿': ('happy', 0.7),
            '哼': ('angry', 0.6),
            '唉': ('sad', 0.7),
            '啊': ('surprised', 0.4),
            '呀': ('surprised', 0.5),
            '哇': ('surprised', 0.8),
            '嗯': ('calm', 0.3),
            '哦': ('calm', 0.3)
        }
        
        # 初始化jieba分词
        try:
            jieba.initialize()
        except:
            pass
    
    def analyze_emotion(self, text: str, context: str = '') -> Tuple[str, float]:
        """
        分析文本情感
        
        Args:
            text: 要分析的文本
            context: 上下文信息（可选）
            
        Returns:
            Tuple[emotion, confidence]: 情感类型和置信度
        """
        if not text.strip():
            return 'calm', 0.8
        
        # 初始化情感分数
        emotion_scores = {emotion: 0.0 for emotion in self.emotion_keywords.keys()}
        
        # 1. 关键词匹配分析
        self._analyze_keywords(text, emotion_scores)
        
        # 2. 标点符号分析
        self._analyze_punctuation(text, emotion_scores)
        
        # 3. 语气词分析
        self._analyze_modal_particles(text, emotion_scores)
        
        # 4. 句式结构分析
        self._analyze_sentence_structure(text, emotion_scores)
        
        # 5. 上下文分析（如果提供）
        if context:
            self._analyze_context(text, context, emotion_scores)
        
        # 6. 计算最终情感和置信度
        return self._calculate_final_emotion(emotion_scores, text)
    
    def _analyze_keywords(self, text: str, emotion_scores: Dict[str, float]):
        """关键词匹配分析"""
        # 使用jieba分词
        try:
            words = list(jieba.cut(text))
        except:
            words = list(text)  # 如果分词失败，按字符处理
        
        for emotion, config in self.emotion_keywords.items():
            keywords = config['keywords']
            weight = config['weight']
            
            for keyword in keywords:
                # 完全匹配
                if keyword in text:
                    emotion_scores[emotion] += 1.0 * weight
                
                # 分词匹配
                for word in words:
                    if keyword == word:
                        emotion_scores[emotion] += 0.8 * weight
                    elif keyword in word:
                        emotion_scores[emotion] += 0.5 * weight
    
    def _analyze_punctuation(self, text: str, emotion_scores: Dict[str, float]):
        """标点符号分析"""
        for punct, (emotion, score) in self.punctuation_emotions.items():
            count = text.count(punct)
            if count > 0:
                emotion_scores[emotion] += score * min(count, 3)  # 最多计算3个
    
    def _analyze_modal_particles(self, text: str, emotion_scores: Dict[str, float]):
        """语气词分析"""
        for particle, (emotion, score) in self.modal_particles.items():
            count = text.count(particle)
            if count > 0:
                emotion_scores[emotion] += score * min(count, 2)  # 最多计算2个
    
    def _analyze_sentence_structure(self, text: str, emotion_scores: Dict[str, float]):
        """句式结构分析"""
        # 疑问句
        if '吗' in text or '呢' in text or text.endswith('?') or text.endswith('？'):
            emotion_scores['surprised'] += 0.3
        
        # 感叹句
        if text.endswith('!') or text.endswith('！'):
            if any(word in text for word in ['太', '真', '好', '棒']):
                emotion_scores['happy'] += 0.4
            else:
                emotion_scores['surprised'] += 0.3
        
        # 否定句
        negative_words = ['不', '没', '别', '非', '未', '无']
        for word in negative_words:
            if word in text:
                emotion_scores['sad'] += 0.2
                emotion_scores['angry'] += 0.1
                break
        
        # 重复词语（表示强调）
        words = list(text)
        word_counts = Counter(words)
        for word, count in word_counts.items():
            if count > 2 and len(word) > 1:
                # 重复可能表示强烈情感
                emotion_scores['happy'] += 0.2
                emotion_scores['angry'] += 0.2
    
    def _analyze_context(self, text: str, context: str, emotion_scores: Dict[str, float]):
        """上下文分析"""
        # 简单的上下文情感延续
        context_emotion, context_confidence = self.analyze_emotion(context)
        if context_confidence > 0.6:
            emotion_scores[context_emotion] += 0.3 * context_confidence
    
    def _calculate_final_emotion(self, emotion_scores: Dict[str, float], text: str) -> Tuple[str, float]:
        """计算最终情感和置信度"""
        # 找出得分最高的情感
        max_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        max_score = emotion_scores[max_emotion]
        
        # 计算总分
        total_score = sum(emotion_scores.values())
        
        # 计算置信度
        if total_score == 0:
            return 'calm', 0.8  # 无明显情感特征时返回平静
        
        confidence = max_score / total_score
        
        # 调整置信度（考虑文本长度）
        text_length_factor = min(len(text) / 20.0, 1.0)  # 文本越长，置信度可能越高
        confidence = confidence * (0.5 + 0.5 * text_length_factor)
        
        # 最小置信度阈值
        if confidence < 0.3:
            return 'calm', 0.8
        
        return max_emotion, min(confidence, 1.0)
    
    def analyze_dialogue_emotion(self, dialogue_text: str, speaker: str = '', 
                               previous_dialogues: List[str] = None) -> Dict:
        """
        分析对话情感（增强版）
        
        Args:
            dialogue_text: 对话文本
            speaker: 说话人
            previous_dialogues: 之前的对话列表
            
        Returns:
            Dict: 包含情感分析结果的字典
        """
        # 基础情感分析
        emotion, confidence = self.analyze_emotion(dialogue_text)
        
        # 考虑对话历史
        context_emotion = None
        context_confidence = 0.0
        
        if previous_dialogues:
            # 分析最近几句对话的情感趋势
            recent_emotions = []
            for prev_dialogue in previous_dialogues[-3:]:  # 最近3句
                prev_emotion, prev_conf = self.analyze_emotion(prev_dialogue)
                if prev_conf > 0.5:
                    recent_emotions.append((prev_emotion, prev_conf))
            
            if recent_emotions:
                # 计算上下文情感
                emotion_weights = {}
                for emo, conf in recent_emotions:
                    emotion_weights[emo] = emotion_weights.get(emo, 0) + conf
                
                if emotion_weights:
                    context_emotion = max(emotion_weights.keys(), 
                                        key=lambda k: emotion_weights[k])
                    context_confidence = emotion_weights[context_emotion] / len(recent_emotions)
        
        # 综合考虑当前情感和上下文情感
        if context_emotion and context_confidence > 0.4:
            if emotion == 'calm' and confidence < 0.6:
                # 如果当前情感不明显，采用上下文情感
                final_emotion = context_emotion
                final_confidence = (confidence + context_confidence) / 2
            elif context_emotion == emotion:
                # 如果上下文情感与当前情感一致，增强置信度
                final_confidence = min(confidence + context_confidence * 0.3, 1.0)
                final_emotion = emotion
            else:
                # 情感转换
                final_emotion = emotion
                final_confidence = confidence
        else:
            final_emotion = emotion
            final_confidence = confidence
        
        return {
            'emotion': final_emotion,
            'confidence': final_confidence,
            'raw_emotion': emotion,
            'raw_confidence': confidence,
            'context_emotion': context_emotion,
            'context_confidence': context_confidence,
            'analysis_details': {
                'text_length': len(dialogue_text),
                'has_context': context_emotion is not None,
                'speaker': speaker
            }
        }
    
    def get_emotion_description(self, emotion: str) -> str:
        """获取情感描述"""
        descriptions = {
            'happy': '开心愉快',
            'sad': '悲伤难过',
            'angry': '生气愤怒',
            'surprised': '惊讶意外',
            'fear': '害怕恐惧',
            'calm': '平静冷静',
            'gentle': '温和亲切'
        }
        return descriptions.get(emotion, '未知情感')
    
    def get_available_emotions(self) -> List[str]:
        """获取所有支持的情感类型"""
        return list(self.emotion_keywords.keys())

# 使用示例
if __name__ == '__main__':
    analyzer = DialogueEmotionAnalyzer()
    
    test_texts = [
        "太好了！我终于通过考试了！",
        "我今天心情不好，什么都不想做...",
        "你这个混蛋！怎么能这样对我！",
        "天哪，这怎么可能？真的假的？",
        "我有点害怕，这个地方看起来很可怕。",
        "好的，我知道了，没问题。",
        "宝贝，你要小心一点哦。"
    ]
    
    print("=== 情感分析测试 ===")
    for text in test_texts:
        emotion, confidence = analyzer.analyze_emotion(text)
        description = analyzer.get_emotion_description(emotion)
        print(f"文本: {text}")
        print(f"情感: {emotion} ({description}) - 置信度: {confidence:.2f}")
        print()
