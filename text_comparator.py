# -*- coding: utf-8 -*-
"""
文字比对模块
用于听觉反馈系统的文字智能比对
"""

import difflib
import re
from typing import Dict, List, Tuple

class TextComparator:
    """文字比对器 - P0核心功能版本（基础比对算法）"""
    
    def __init__(self):
        print("✓ 文字比对器初始化完成（基础版本）")
    
    def compare(self, original: str, user_input: str) -> Dict:
        """
        智能比对两段文字
        
        Args:
            original: 原始文本
            user_input: 用户输入
            
        Returns:
            Dict: 比对结果
        """
        # 1. 预处理
        original_clean = self._preprocess(original)
        user_input_clean = self._preprocess(user_input)
        
        print(f"📊 比对输入:")
        print(f"   原文: '{original}' -> '{original_clean}'")
        print(f"   用户: '{user_input}' -> '{user_input_clean}'")
        
        # 2. 计算编辑距离
        distance = self._edit_distance(original_clean, user_input_clean)
        print(f"   编辑距离: {distance}")
        
        # 3. 字符级别对比
        char_diff = self._char_level_diff(original_clean, user_input_clean)
        
        # 4. 标记错误
        marked_text = self._mark_errors(user_input_clean, char_diff)
        
        # 5. 计算准确率
        accuracy = self._calculate_accuracy(original_clean, user_input_clean, distance)
        print(f"   准确率: {accuracy}%")
        
        # 6. 错误分析
        error_analysis = self._analyze_errors(char_diff)
        print(f"   错误数: {error_analysis['total_errors']}")
        
        # 7. 生成建议
        suggestions = self._generate_suggestions(error_analysis, accuracy)
        
        return {
            'original': original,
            'user_input': user_input,
            'user_input_marked': marked_text,
            'accuracy': accuracy,
            'error_count': error_analysis['total_errors'],
            'error_types': error_analysis['error_types'],
            'suggestions': suggestions
        }
    
    def _preprocess(self, text: str) -> str:
        """
        预处理文本
        - 去除多余的空格
        - 去除标点符号（标点符号不影响准确率）
        """
        # 去除首尾空格
        text = text.strip()
        
        # 将多个空格替换为单个空格
        text = re.sub(r'\s+', '', text)
        
        # 去除所有标点符号（中英文标点）
        # 保留汉字、字母、数字
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        
        return text
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """
        计算编辑距离（Levenshtein距离）
        使用动态规划算法
        """
        m, n = len(s1), len(s2)
        
        # 创建DP表
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # 初始化第一行和第一列
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # 填充DP表
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    # 字符相同，不需要操作
                    dp[i][j] = dp[i-1][j-1]
                else:
                    # 字符不同，取三种操作中的最小值
                    dp[i][j] = min(
                        dp[i-1][j] + 1,    # 删除
                        dp[i][j-1] + 1,    # 插入
                        dp[i-1][j-1] + 1   # 替换
                    )
        
        return dp[m][n]
    
    def _char_level_diff(self, s1: str, s2: str) -> List[Tuple]:
        """
        字符级别差异比对
        返回格式: [('equal', 'a'), ('replace', 'b', 'c'), ('delete', 'd'), ('insert', 'e')]
        """
        matcher = difflib.SequenceMatcher(None, s1, s2)
        diffs = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # 相同的字符
                for k in range(i1, i2):
                    diffs.append(('equal', s1[k]))
            elif tag == 'replace':
                # 替换的字符
                diffs.append(('replace', s1[i1:i2], s2[j1:j2]))
            elif tag == 'delete':
                # 删除的字符（原文有，用户输入缺少）
                diffs.append(('delete', s1[i1:i2]))
            elif tag == 'insert':
                # 插入的字符（用户输入多余）
                diffs.append(('insert', s2[j1:j2]))
        
        return diffs
    
    def _mark_errors(self, user_input: str, char_diff: List) -> str:
        """
        标记错误的HTML
        将错误用不同颜色和样式标记出来
        """
        marked = []
        
        for item in char_diff:
            if item[0] == 'equal':
                # 正确的字符
                marked.append(item[1])
            elif item[0] == 'replace':
                # 替换错误（写错了）
                original_char = item[1]
                user_char = item[2]
                marked.append(
                    f'<span class="error-replace" title="应为：{original_char}">{user_char}</span>'
                )
            elif item[0] == 'delete':
                # 缺少的字符（漏听了）
                missing_char = item[1]
                marked.append(
                    f'<span class="error-missing" title="缺少：{missing_char}">_</span>'
                )
            elif item[0] == 'insert':
                # 多余的字符（听多了）
                extra_char = item[1]
                marked.append(
                    f'<span class="error-extra" title="多余">{extra_char}</span>'
                )
        
        return ''.join(marked)
    
    def _calculate_accuracy(self, original: str, user_input: str, distance: int) -> float:
        """
        计算准确率
        准确率 = (1 - 编辑距离 / 最大长度) × 100
        """
        max_len = max(len(original), len(user_input))
        
        if max_len == 0:
            return 100.0
        
        accuracy = (1 - distance / max_len) * 100
        
        # 确保准确率在0-100之间
        accuracy = max(0.0, min(100.0, accuracy))
        
        # 保留两位小数
        return round(accuracy, 2)
    
    def _analyze_errors(self, char_diff: List) -> Dict:
        """
        错误分析
        统计各种类型的错误数量
        """
        error_types = {
            'replace': 0,   # 替换错误（写错）
            'delete': 0,    # 缺少（漏听）
            'insert': 0,    # 多余（听多）
        }
        
        for item in char_diff:
            error_type = item[0]
            if error_type in error_types:
                # 计算错误字符数
                if error_type == 'replace':
                    # 替换错误按较长的长度计算
                    error_count = max(len(item[1]), len(item[2]))
                else:
                    # 删除和插入按实际长度计算
                    error_count = len(item[1])
                
                error_types[error_type] += error_count
        
        total_errors = sum(error_types.values())
        
        return {
            'total_errors': total_errors,
            'error_types': error_types
        }
    
    def _generate_suggestions(self, error_analysis: Dict, accuracy: float) -> List[str]:
        """
        生成改进建议
        根据错误类型和准确率给出个性化建议
        """
        suggestions = []
        error_types = error_analysis['error_types']
        
        # 根据准确率给出总体建议
        if accuracy == 100:
            suggestions.append('✨ 完美！继续保持这样的水平！')
        elif accuracy >= 90:
            suggestions.append('👍 非常好！只有细微的错误。')
        elif accuracy >= 70:
            suggestions.append('💪 不错！再努力一点就会更好。')
        else:
            suggestions.append('🤔 可以尝试降低播放速度，多听几遍。')
        
        # 根据错误类型给出具体建议
        if error_types['delete'] > 2:
            suggestions.append('📢 注意：有些字可能漏听了，建议放慢速度仔细听。')
        
        if error_types['insert'] > 2:
            suggestions.append('🎯 注意：有些地方可能听多了，注意区分音节。')
        
        if error_types['replace'] > 2:
            suggestions.append('✏️ 注意：有些字听错了，可以结合上下文理解。')
        
        return suggestions
    
    def batch_compare(self, comparisons: List[Tuple[str, str]]) -> List[Dict]:
        """
        批量比对
        
        Args:
            comparisons: [(original1, user_input1), (original2, user_input2), ...]
            
        Returns:
            List[Dict]: 比对结果列表
        """
        results = []
        for original, user_input in comparisons:
            result = self.compare(original, user_input)
            results.append(result)
        return results


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("文字比对器测试")
    print("=" * 60)
    
    comparator = TextComparator()
    
    # 测试用例1: 完全正确
    print("\n【测试1：完全正确】")
    result1 = comparator.compare("你好世界", "你好世界")
    print(f"准确率: {result1['accuracy']}%")
    print(f"标记结果: {result1['user_input_marked']}")
    
    # 测试用例2: 部分错误
    print("\n【测试2：部分错误】")
    result2 = comparator.compare("欢迎来到语训平台", "欢迎来到语言平台")
    print(f"准确率: {result2['accuracy']}%")
    print(f"错误数: {result2['error_count']}")
    print(f"标记结果: {result2['user_input_marked']}")
    print(f"建议: {result2['suggestions']}")
    
    # 测试用例3: 缺字
    print("\n【测试3：缺字】")
    result3 = comparator.compare("今天天气很好", "今天很好")
    print(f"准确率: {result3['accuracy']}%")
    print(f"错误数: {result3['error_count']}")
    print(f"错误类型: {result3['error_types']}")
    print(f"标记结果: {result3['user_input_marked']}")
    
    # 测试用例4: 多字
    print("\n【测试4：多字】")
    result4 = comparator.compare("早上好", "早上好啊")
    print(f"准确率: {result4['accuracy']}%")
    print(f"错误数: {result4['error_count']}")
    print(f"标记结果: {result4['user_input_marked']}")
    
    # 测试用例5: 完全错误
    print("\n【测试5：完全错误】")
    result5 = comparator.compare("苹果", "香蕉")
    print(f"准确率: {result5['accuracy']}%")
    print(f"错误数: {result5['error_count']}")
    print(f"标记结果: {result5['user_input_marked']}")
    print(f"建议: {result5['suggestions']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

