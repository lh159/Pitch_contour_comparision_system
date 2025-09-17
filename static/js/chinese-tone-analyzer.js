// -*- coding: utf-8 -*-
/**
 * 中文声调分析器
 * 基于音高曲线分析的声调识别，利用系统现有的音高分析能力
 */

class ChineseToneAnalyzer {
    constructor() {
        // 从系统获取的音高分析数据
        this.pitchData = null;
        this.toneAnalysisResults = null;
        
        // 声调名称
        this.toneNames = ['轻声', '阴平', '阳平', '上声', '去声'];
        
        // 声调描述
        this.toneDescriptions = {
            0: '轻声 - 短促轻读，音调较低',
            1: '阴平 - 音调高而平，音高保持稳定',
            2: '阳平 - 音调由低向高上升，呈上升趋势',
            3: '上声 - 音调先降后升，呈V字形变化',
            4: '去声 - 音调由高向低下降，呈下降趋势'
        };
        
        // 声调颜色
        this.toneColors = {
            0: '#ffeaa7', // 轻声 - 黄色
            1: '#ff6b6b', // 阴平 - 红色  
            2: '#4ecdc4', // 阳平 - 青色
            3: '#45b7d1', // 上声 - 蓝色
            4: '#96ceb4'  // 去声 - 绿色
        };
    }
    
    /**
     * 设置音高分析数据
     * @param {Object} pitchData 音高数据
     * @param {Array} toneAnalysisResults 声调分析结果
     */
    setPitchAnalysisData(pitchData, toneAnalysisResults = null) {
        this.pitchData = pitchData;
        this.toneAnalysisResults = toneAnalysisResults;
    }
    
    /**
     * 从音高分析结果获取字符声调
     * @param {string} char 汉字
     * @param {number} index 字符在文本中的位置
     * @returns {number} 声调 (0-4)
     */
    analyzeSingleTone(char, index = 0) {
        // 如果有声调分析结果，优先使用
        if (this.toneAnalysisResults && this.toneAnalysisResults.tone_analysis) {
            const analysis = this.toneAnalysisResults.tone_analysis[index];
            if (analysis && analysis.detected_tone) {
                return analysis.detected_tone.tone_type || 1;
            }
        }
        
        // 否则根据字符和音高数据进行简单分析
        return this.analyzeFromPitch(char, index);
    }
    
    /**
     * 基于音高数据分析声调
     * @param {string} char 汉字
     * @param {number} index 字符索引
     * @returns {number} 声调 (0-4)
     */
    analyzeFromPitch(char, index) {
        // 检查是否是中文字符
        if (!this.isChineseCharacter(char)) {
            return 0; // 非中文字符标记为轻声
        }
        
        // 如果没有音高数据，使用默认分析
        if (!this.pitchData || !this.pitchData.pitch_values) {
            return this.getDefaultTone(char);
        }
        
        // 基于音高变化趋势进行简单分析
        const pitchValues = this.pitchData.pitch_values;
        if (pitchValues.length < 2) {
            return this.getDefaultTone(char);
        }
        
        // 计算音高变化特征
        const segment = this.getCharacterPitchSegment(index, pitchValues);
        return this.classifyToneFromPitch(segment);
    }
    
    /**
     * 获取字符对应的音高片段
     * @param {number} charIndex 字符索引
     * @param {Array} pitchValues 音高数组
     * @returns {Array} 音高片段
     */
    getCharacterPitchSegment(charIndex, pitchValues) {
        const totalChars = this.getCurrentTextLength();
        if (totalChars <= 0) return pitchValues;
        
        const segmentSize = Math.floor(pitchValues.length / totalChars);
        const start = charIndex * segmentSize;
        const end = Math.min((charIndex + 1) * segmentSize, pitchValues.length);
        
        return pitchValues.slice(start, end);
    }
    
    /**
     * 基于音高片段分类声调
     * @param {Array} pitchSegment 音高片段
     * @returns {number} 声调类型
     */
    classifyToneFromPitch(pitchSegment) {
        if (pitchSegment.length < 2) return 1;
        
        // 过滤NaN值
        const validPitch = pitchSegment.filter(p => !isNaN(p) && p > 0);
        if (validPitch.length < 2) return 1;
        
        const start = validPitch[0];
        const end = validPitch[validPitch.length - 1];
        const totalChange = end - start;
        const maxPitch = Math.max(...validPitch);
        const minPitch = Math.min(...validPitch);
        const range = maxPitch - minPitch;
        
        // 计算音高变化趋势
        let trend = 0;
        for (let i = 1; i < validPitch.length; i++) {
            if (validPitch[i] > validPitch[i-1]) trend++;
            else if (validPitch[i] < validPitch[i-1]) trend--;
        }
        
        // 声调分类逻辑
        if (Math.abs(totalChange) < range * 0.3) {
            return 1; // 阴平 - 相对平稳
        } else if (totalChange > range * 0.3 && trend > 0) {
            return 2; // 阳平 - 上升
        } else if (totalChange < -range * 0.3 && trend < 0) {
            return 4; // 去声 - 下降
        } else if (range > Math.abs(totalChange) * 1.5) {
            return 3; // 上声 - 变化复杂
        }
        
        return 1; // 默认阴平
    }
    
    /**
     * 获取默认声调（当没有音高数据时）
     * @param {string} char 汉字
     * @returns {number} 默认声调
     */
    getDefaultTone(char) {
        // 简单的字符编码分析作为后备方案
        const charCode = char.charCodeAt(0);
        if (charCode >= 0x4e00 && charCode <= 0x9fff) {
            return ((charCode - 0x4e00) % 4) + 1;
        }
        return 1;
    }
    
    /**
     * 获取当前分析文本的长度
     * @returns {number} 文本长度
     */
    getCurrentTextLength() {
        // 这个方法需要从外部设置当前分析的文本
        return this.currentText ? this.currentText.length : 1;
    }
    
    /**
     * 检查是否是中文字符
     * @param {string} char 字符
     * @returns {boolean} 是否是中文字符
     */
    isChineseCharacter(char) {
        const charCode = char.charCodeAt(0);
        return (charCode >= 0x4e00 && charCode <= 0x9fff) || // CJK统一表意文字
               (charCode >= 0x3400 && charCode <= 0x4dbf) || // CJK扩展A
               (charCode >= 0xf900 && charCode <= 0xfaff);   // CJK兼容表意文字
    }
    
    /**
     * 设置当前分析的文本
     * @param {string} text 当前文本
     */
    setCurrentText(text) {
        this.currentText = text;
    }
    
    /**
     * 分析文本中所有字符的声调
     * @param {string} text 文本
     * @returns {Array} 声调数组
     */
    analyzeTextTones(text) {
        this.setCurrentText(text);
        const tones = [];
        
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            if (this.isChineseCharacter(char)) {
                tones.push(this.analyzeSingleTone(char, i));
            } else {
                tones.push(0); // 非中文字符标记为轻声
            }
        }
        return tones;
    }
    
    /**
     * 获取声调名称
     * @param {number} tone 声调
     * @returns {string} 声调名称
     */
    getToneName(tone) {
        return this.toneNames[tone] || '未知';
    }
    
    /**
     * 获取声调描述
     * @param {number} tone 声调
     * @returns {string} 声调描述
     */
    getToneDescription(tone) {
        return this.toneDescriptions[tone] || '未知声调';
    }
    
    /**
     * 获取声调颜色
     * @param {number} tone 声调
     * @returns {string} 颜色代码
     */
    getToneColor(tone) {
        return this.toneColors[tone] || '#cccccc';
    }
    
    /**
     * 获取字符的分析置信度
     * @param {number} index 字符索引
     * @returns {number} 置信度 (0-1)
     */
    getConfidence(index) {
        if (this.toneAnalysisResults && this.toneAnalysisResults.tone_analysis) {
            const analysis = this.toneAnalysisResults.tone_analysis[index];
            if (analysis && analysis.confidence !== undefined) {
                return analysis.confidence;
            }
        }
        return 0.5; // 默认置信度
    }
    
    /**
     * 获取字符的时间信息
     * @param {number} index 字符索引
     * @returns {Object|null} 时间信息
     */
    getTimestamp(index) {
        if (this.toneAnalysisResults && this.toneAnalysisResults.tone_analysis) {
            const analysis = this.toneAnalysisResults.tone_analysis[index];
            if (analysis && analysis.timestamp) {
                return analysis.timestamp;
            }
        }
        
        // 如果没有精确时间戳，根据字符位置估算
        if (this.pitchData && this.pitchData.duration && this.currentText) {
            const charDuration = this.pitchData.duration / this.currentText.length;
            return {
                start_time: index * charDuration,
                end_time: (index + 1) * charDuration
            };
        }
        
        return null;
    }
    
    /**
     * 获取声调统计信息
     * @param {string} text 文本
     * @returns {Object} 统计信息
     */
    getToneStatistics(text) {
        const tones = this.analyzeTextTones(text);
        const stats = {
            total: tones.length,
            toneCount: [0, 0, 0, 0, 0], // 轻声, 阴平, 阳平, 上声, 去声
            toneRatio: [0, 0, 0, 0, 0]
        };
        
        // 统计各声调数量
        tones.forEach(tone => {
            if (tone >= 0 && tone <= 4) {
                stats.toneCount[tone]++;
            }
        });
        
        // 计算比例
        if (stats.total > 0) {
            stats.toneRatio = stats.toneCount.map(count => count / stats.total);
        }
        
        return stats;
    }
    
    /**
     * 生成声调可视化HTML
     * @param {string} text 文本  
     * @returns {string} HTML字符串
     */
    generateToneVisualization(text) {
        const tones = this.analyzeTextTones(text);
        let html = '';
        
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const tone = tones[i];
            const timestamp = this.getTimestamp(i);
            const confidence = this.getConfidence(i);
            
            let title = `${char} - ${this.getToneName(tone)}`;
            title += `\\n置信度: ${(confidence * 100).toFixed(1)}%`;
            
            if (timestamp) {
                const duration = ((timestamp.end_time - timestamp.start_time) * 1000).toFixed(0);
                title += `\\n时间: ${timestamp.start_time.toFixed(2)}s - ${timestamp.end_time.toFixed(2)}s\\n时长: ${duration}ms`;
            }
            
            // 根据置信度调整透明度
            const opacity = Math.max(0.3, confidence);
            const backgroundColor = this.getToneColor(tone);
            
            html += `<span class="text-char tone-${tone}" 
                title="${title}" 
                data-tone="${tone}" 
                data-char="${char}" 
                data-index="${i}"
                data-confidence="${confidence}"
                style="background-color: ${backgroundColor}; opacity: ${opacity};"
                onclick="showCharacterDetails('${char}', ${timestamp ? JSON.stringify(timestamp) : 'null'}, ${tone}, ${i})">
                ${char}
            </span>`;
        }
        
        return html;
    }
    
    /**
     * 获取分析摘要
     * @param {string} text 文本
     * @returns {Object} 分析摘要
     */
    getAnalysisSummary(text = null) {
        if (text) this.setCurrentText(text);
        
        const summary = {
            hasPitchData: !!this.pitchData,
            hasAnalysisResults: !!(this.toneAnalysisResults && this.toneAnalysisResults.tone_analysis),
            textLength: this.currentText ? this.currentText.length : 0,
            averageConfidence: 0,
            analysisMethod: 'unknown'
        };
        
        if (summary.hasAnalysisResults) {
            summary.analysisMethod = 'pitch_analysis';
            const confidences = this.toneAnalysisResults.tone_analysis.map(a => a.confidence || 0.5);
            summary.averageConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
        } else if (summary.hasPitchData) {
            summary.analysisMethod = 'pitch_estimation';
            summary.averageConfidence = 0.6;
        } else {
            summary.analysisMethod = 'fallback';
            summary.averageConfidence = 0.3;
        }
        
        return summary;
    }
}

// 导出到全局作用域
if (typeof window !== 'undefined') {
    window.ChineseToneAnalyzer = ChineseToneAnalyzer;
}

// Node.js导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChineseToneAnalyzer;
}
