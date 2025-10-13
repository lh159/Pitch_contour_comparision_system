/**
 * 听觉反馈训练系统 - 核心JavaScript逻辑
 */

class HearingFeedbackTrainer {
    constructor(sessionId, dialogueData) {
        this.sessionId = sessionId;
        this.dialogueData = dialogueData;
        this.currentIndex = 0;
        this.currentAudio = null;
        this.playCount = 0;
        this.records = []; // 记录每句的答题情况
        
        this.initElements();
        this.bindEvents();
    }
    
    /**
     * 初始化DOM元素
     */
    initElements() {
        // 场景信息
        this.scenarioTitle = document.getElementById('scenarioTitle');
        
        // 进度条
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');
        
        // 音频控制
        this.playBtn = document.getElementById('playBtn');
        this.playCount元素 = document.getElementById('playCount');
        this.speedControl = document.getElementById('speedControl');
        
        // 输入区域
        this.userInput = document.getElementById('userInput');
        this.charCount = document.getElementById('charCount');
        this.clearBtn = document.getElementById('clearBtn');
        this.submitBtn = document.getElementById('submitBtn');
        
        // 结果展示
        this.resultCard = document.getElementById('resultCard');
        this.accuracyValue = document.getElementById('accuracyValue');
        this.originalText = document.getElementById('originalText');
        this.userText = document.getElementById('userText');
        this.errorStats = document.getElementById('errorStats');
        this.feedbackMessage = document.getElementById('feedbackMessage');
        
        // 操作按钮
        this.replayBtn = document.getElementById('replayBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.finishBtn = document.getElementById('finishBtn');
        
        // 庆祝动画
        this.celebrationOverlay = document.getElementById('celebrationOverlay');
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 播放按钮
        this.playBtn.addEventListener('click', () => this.playAudio());
        
        // 速度控制
        this.speedControl.addEventListener('change', () => this.updatePlaybackSpeed());
        
        // 输入区域
        this.userInput.addEventListener('input', () => this.updateCharCount());
        
        // 清空按钮
        this.clearBtn.addEventListener('click', () => this.clearInput());
        
        // 提交按钮
        this.submitBtn.addEventListener('click', () => this.submitAnswer());
        
        // 重新听按钮
        this.replayBtn.addEventListener('click', () => this.replayAudio());
        
        // 下一句按钮
        this.nextBtn.addEventListener('click', () => this.nextSentence());
        
        // 完成按钮
        this.finishBtn.addEventListener('click', () => this.finishTraining());
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
    }
    
    /**
     * 开始训练
     */
    start() {
        console.log('🚀 开始听觉反馈训练');
        console.log('场景数据:', this.dialogueData);
        
        // 显示场景信息
        this.scenarioTitle.textContent = this.dialogueData.scenario_title || '场景训练';
        
        // 加载第一句
        this.loadSentence(0);
    }
    
    /**
     * 加载指定句子
     */
    loadSentence(index) {
        if (index >= this.dialogueData.dialogues.length) {
            console.log('✓ 所有句子已完成');
            this.finishTraining();
            return;
        }
        
        this.currentIndex = index;
        const dialogue = this.dialogueData.dialogues[index];
        
        console.log(`📖 加载第 ${index + 1} 句:`, dialogue);
        
        // 重置状态
        this.playCount = 0;
        this.userInput.value = '';
        this.resultCard.style.display = 'none';
        this.nextBtn.style.display = 'none';
        this.submitBtn.disabled = false;
        this.playBtn.disabled = false;
        this.replayBtn.disabled = true;
        
        // 更新进度
        this.updateProgress();
        
        // 准备音频
        this.prepareAudio(dialogue);
        
        // 如果是第一句，不自动播放（避免浏览器阻止）
        // 其他句子可以尝试自动播放
        if (this.currentIndex > 0) {
            setTimeout(() => this.playAudio(), 500);
        } else {
            console.log('💡 第一句不自动播放，请点击播放按钮');
        }
    }
    
    /**
     * 准备音频
     */
    prepareAudio(dialogue) {
        // 如果有音频URL，使用它
        if (dialogue.audio_url) {
            console.log('🎵 准备音频:', dialogue.audio_url);
            
            this.currentAudio = new Audio(dialogue.audio_url);
            this.currentAudio.playbackRate = parseFloat(this.speedControl.value);
            
            // 预加载音频
            this.currentAudio.preload = 'auto';
            
            // 音频加载成功
            this.currentAudio.addEventListener('canplaythrough', () => {
                console.log('✓ 音频加载完成，可以播放');
            });
            
            // 音频播放结束
            this.currentAudio.addEventListener('ended', () => {
                console.log('✓ 音频播放结束');
                this.playBtn.innerHTML = '<i class="fas fa-play me-2"></i>播放音频';
                this.playBtn.disabled = false;
                this.replayBtn.disabled = false;
            });
            
            // 音频加载或播放失败
            this.currentAudio.addEventListener('error', (e) => {
                console.error('音频加载失败:', e);
                console.error('音频URL:', dialogue.audio_url);
                console.error('错误详情:', this.currentAudio.error);
                
                this.playBtn.innerHTML = '<i class="fas fa-play me-2"></i>播放音频';
                this.playBtn.disabled = false;
                
                showAlert('音频加载失败，请检查网络连接或联系管理员', 'danger');
            });
            
            // 开始加载音频
            this.currentAudio.load();
        } else {
            console.warn('当前句子没有音频URL');
            showAlert('当前句子没有音频，请联系管理员', 'warning');
        }
    }
    
    /**
     * 播放音频
     */
    async playAudio() {
        if (!this.currentAudio) {
            showAlert('音频未准备好，请稍候', 'warning');
            return;
        }
        
        try {
            // 从头播放
            this.currentAudio.currentTime = 0;
            
            this.playBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>播放中...';
            this.playBtn.disabled = true;
            
            // 播放音频并等待Promise
            await this.currentAudio.play();
            
            this.playCount++;
            this.playCount元素.textContent = this.playCount;
            
            console.log(`🔊 播放第 ${this.playCount} 次`);
        } catch (error) {
            console.error('音频播放失败:', error);
            
            // 恢复按钮状态
            this.playBtn.innerHTML = '<i class="fas fa-play me-2"></i>播放音频';
            this.playBtn.disabled = false;
            
            // 根据错误类型给出不同提示
            if (error.name === 'NotAllowedError') {
                showAlert('浏览器阻止了自动播放，请点击播放按钮手动播放', 'warning');
            } else if (error.name === 'NotSupportedError') {
                showAlert('音频格式不支持，请联系管理员', 'danger');
            } else {
                showAlert(`音频播放失败: ${error.message}`, 'danger');
            }
        }
    }
    
    /**
     * 重新播放
     */
    replayAudio() {
        this.playAudio();
    }
    
    /**
     * 更新播放速度
     */
    updatePlaybackSpeed() {
        const speed = parseFloat(this.speedControl.value);
        if (this.currentAudio) {
            this.currentAudio.playbackRate = speed;
        }
        console.log(`⚙️ 播放速度设置为: ${speed}x`);
    }
    
    /**
     * 更新字数统计
     */
    updateCharCount() {
        const count = this.userInput.value.length;
        this.charCount.textContent = count;
    }
    
    /**
     * 清空输入
     */
    clearInput() {
        this.userInput.value = '';
        this.updateCharCount();
        this.userInput.focus();
    }
    
    /**
     * 提交答案
     */
    async submitAnswer() {
        const userInputText = this.userInput.value.trim();
        
        if (!userInputText) {
            showAlert('请先输入您听到的内容', 'warning');
            return;
        }
        
        const dialogue = this.dialogueData.dialogues[this.currentIndex];
        const originalText = dialogue.text;
        
        console.log('📝 提交答案:', userInputText);
        console.log('📄 原文:', originalText);
        
        // 禁用提交按钮
        this.submitBtn.disabled = true;
        this.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>比对中...';
        
        try {
            // 调用文字比对API
            const response = await fetch('/api/feedback/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original: originalText,
                    user_input: userInputText,
                    session_id: this.sessionId,
                    sentence_index: this.currentIndex
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✓ 比对结果:', result);
                
                // 保存记录
                this.records.push({
                    index: this.currentIndex,
                    original: originalText,
                    user_input: userInputText,
                    accuracy: result.accuracy,
                    play_count: this.playCount,
                    error_count: result.error_count
                });
                
                // 显示结果
                this.showResult(result);
            } else {
                showAlert(`比对失败: ${result.error}`, 'danger');
                this.submitBtn.disabled = false;
                this.submitBtn.innerHTML = '<i class="fas fa-check me-1"></i>提交';
            }
        } catch (error) {
            console.error('提交失败:', error);
            showAlert(`网络错误: ${error.message}`, 'danger');
            this.submitBtn.disabled = false;
            this.submitBtn.innerHTML = '<i class="fas fa-check me-1"></i>提交';
        }
    }
    
    /**
     * 显示比对结果
     */
    showResult(result) {
        // 恢复提交按钮状态
        this.submitBtn.disabled = false;
        this.submitBtn.innerHTML = '<i class="fas fa-check me-1"></i>提交';
        
        // 显示结果卡片
        this.resultCard.style.display = 'block';
        
        // 显示准确率
        this.accuracyValue.textContent = result.accuracy + '%';
        this.accuracyValue.className = this.getAccuracyClass(result.accuracy);
        
        // 显示原文
        this.originalText.innerHTML = result.original;
        
        // 显示用户输入（带错误标记）
        this.userText.innerHTML = result.user_input_marked;
        
        // 显示错误统计
        if (result.error_count > 0) {
            this.errorStats.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    共发现 <strong>${result.error_count}</strong> 处错误
                    ${result.suggestions ? '<br><small>' + result.suggestions.join('；') + '</small>' : ''}
                </div>
            `;
            this.errorStats.style.display = 'block';
        } else {
            this.errorStats.style.display = 'none';
        }
        
        // 显示激励信息
        this.showFeedback(result.accuracy);
        
        // 显示下一句按钮
        if (this.currentIndex < this.dialogueData.dialogues.length - 1) {
            this.nextBtn.style.display = 'inline-block';
            this.finishBtn.style.display = 'none';
        } else {
            this.nextBtn.style.display = 'none';
            this.finishBtn.style.display = 'inline-block';
        }
        
        // 滚动到结果区域
        this.resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    /**
     * 根据准确率获取样式类
     */
    getAccuracyClass(accuracy) {
        if (accuracy === 100) return 'text-success';
        if (accuracy >= 90) return 'text-info';
        if (accuracy >= 70) return 'text-warning';
        return 'text-danger';
    }
    
    /**
     * 显示激励反馈
     */
    showFeedback(accuracy) {
        let icon = '';
        let title = '';
        let message = '';
        let className = '';
        
        if (accuracy === 100) {
            icon = '🎉';
            title = '完全正确！';
            message = '太棒了！您的听力理解非常准确！';
            className = 'bg-success text-white';
            
            // 显示庆祝动画
            this.showCelebration();
        } else if (accuracy >= 90) {
            icon = '👍';
            title = '非常好！';
            message = '只有小瑕疵，继续保持！';
            className = 'bg-info text-white';
        } else if (accuracy >= 70) {
            icon = '💪';
            title = '不错！';
            message = '继续加油，您可以做得更好！';
            className = 'bg-warning';
        } else {
            icon = '🤔';
            title = '没关系！';
            message = '再听几遍，或者降低播放速度试试。';
            className = 'bg-secondary text-white';
        }
        
        this.feedbackMessage.innerHTML = `
            <h3>${icon} ${title}</h3>
            <p class="mb-0">${message}</p>
        `;
        this.feedbackMessage.className = 'feedback-message text-center p-3 rounded ' + className;
    }
    
    /**
     * 显示庆祝动画（满分时）
     */
    showCelebration() {
        this.celebrationOverlay.style.display = 'flex';
        
        setTimeout(() => {
            this.celebrationOverlay.style.display = 'none';
        }, 2000);
    }
    
    /**
     * 下一句
     */
    nextSentence() {
        console.log('➡️ 进入下一句');
        this.loadSentence(this.currentIndex + 1);
        
        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    /**
     * 完成训练
     */
    async finishTraining() {
        console.log('🏁 训练完成');
        
        // 计算总体统计
        const totalSentences = this.records.length;
        const totalAccuracy = this.records.reduce((sum, r) => sum + r.accuracy, 0);
        const avgAccuracy = totalSentences > 0 ? (totalAccuracy / totalSentences).toFixed(2) : 0;
        const perfectCount = this.records.filter(r => r.accuracy === 100).length;
        
        console.log('📊 训练统计:', {
            totalSentences,
            avgAccuracy,
            perfectCount
        });
        
        // 检查 SweetAlert2 是否可用
        if (typeof Swal === 'undefined') {
            console.warn('⚠️ SweetAlert2 未加载，使用原生对话框');
            // 使用原生对话框作为回退方案
            const message = `🎊 训练完成！\n\n完成句数：${totalSentences} 句\n平均准确率：${avgAccuracy}%\n完全正确：${perfectCount} 句\n\n是否查看详细统计？\n（点击"取消"返回首页）`;
            const showStats = confirm(message);
            
            if (showStats) {
                this.showDetailedStats();
            } else {
                window.location.href = '/home';
            }
            return;
        }
        
        // 显示完成提示，提供查看详细统计选项
        const result = await Swal.fire({
            title: '🎊 训练完成！',
            html: `
                <div class="text-start">
                    <p><strong>完成句数：</strong>${totalSentences} 句</p>
                    <p><strong>平均准确率：</strong>${avgAccuracy}%</p>
                    <p><strong>完全正确：</strong>${perfectCount} 句</p>
                </div>
            `,
            icon: 'success',
            showDenyButton: true,
            confirmButtonText: '返回首页',
            denyButtonText: '查看详细统计',
            confirmButtonColor: '#17a2b8',
            denyButtonColor: '#6c757d',
            timer: 3000,
            timerProgressBar: true,
            allowOutsideClick: false
        });
        
        // 处理用户选择
        if (result.isDenied) {
            // 显示详细统计
            this.showDetailedStats();
        } else {
            // 返回首页
            window.location.href = '/home';
        }
    }
    
    /**
     * 显示详细统计
     */
    showDetailedStats() {
        // 计算总体统计
        const totalSentences = this.records.length;
        const totalAccuracy = this.records.reduce((sum, r) => sum + r.accuracy, 0);
        const avgAccuracy = totalSentences > 0 ? (totalAccuracy / totalSentences).toFixed(2) : 0;
        const perfectCount = this.records.filter(r => r.accuracy === 100).length;
        const totalPlayCount = this.records.reduce((sum, r) => sum + r.play_count, 0);
        
        // 检查 SweetAlert2 是否可用
        if (typeof Swal === 'undefined') {
            console.warn('⚠️ SweetAlert2 未加载，使用原生alert');
            // 使用原生 alert 作为回退方案
            let message = `📊 详细统计报告\n\n`;
            message += `📈 总体表现\n`;
            message += `平均准确率：${avgAccuracy}%\n`;
            message += `完全正确：${perfectCount} 句\n`;
            message += `总播放次数：${totalPlayCount} 次\n\n`;
            message += `📝 每句详情\n`;
            message += `${'='.repeat(40)}\n`;
            
            this.records.forEach((record, index) => {
                const statusText = record.accuracy === 100 ? '完美' : 
                                 record.accuracy >= 90 ? '优秀' : 
                                 record.accuracy >= 70 ? '良好' : '加油';
                message += `句${index + 1}: ${record.accuracy}% (${statusText}) - 播放${record.play_count}次, 错误${record.error_count}个\n`;
            });
            
            alert(message);
            window.location.href = '/home';
            return;
        }
        
        let statsHTML = `
            <div style="text-align: left;">
                <div class="mb-4 p-3 bg-light rounded">
                    <h6 class="fw-bold mb-3">📈 总体表现</h6>
                    <div class="row text-center">
                        <div class="col-4">
                            <div class="fs-4 fw-bold text-info">${avgAccuracy}%</div>
                            <small class="text-muted">平均准确率</small>
                        </div>
                        <div class="col-4">
                            <div class="fs-4 fw-bold text-success">${perfectCount}</div>
                            <small class="text-muted">完全正确</small>
                        </div>
                        <div class="col-4">
                            <div class="fs-4 fw-bold text-warning">${totalPlayCount}</div>
                            <small class="text-muted">总播放次数</small>
                        </div>
                    </div>
                </div>
                
                <h6 class="fw-bold mb-3">📝 每句详情</h6>
                <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                    <table class="table table-sm table-hover">
                        <thead class="table-light sticky-top">
                            <tr>
                                <th>句号</th>
                                <th>准确率</th>
                                <th>播放</th>
                                <th>错误</th>
                                <th>状态</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        this.records.forEach((record, index) => {
            const accuracyClass = this.getAccuracyClass(record.accuracy);
            const statusIcon = record.accuracy === 100 ? '🏆' : 
                             record.accuracy >= 90 ? '👍' : 
                             record.accuracy >= 70 ? '👌' : '💪';
            const statusText = record.accuracy === 100 ? '完美' : 
                             record.accuracy >= 90 ? '优秀' : 
                             record.accuracy >= 70 ? '良好' : '加油';
            
            statsHTML += `
                <tr>
                    <td><strong>${index + 1}</strong></td>
                    <td class="${accuracyClass} fw-bold">${record.accuracy}%</td>
                    <td>${record.play_count} 次</td>
                    <td>${record.error_count} 个</td>
                    <td>${statusIcon} ${statusText}</td>
                </tr>
            `;
        });
        
        statsHTML += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        Swal.fire({
            title: '📊 详细统计报告',
            html: statsHTML,
            width: '700px',
            confirmButtonText: '返回首页',
            confirmButtonColor: '#17a2b8',
            allowOutsideClick: false
        }).then(() => {
            window.location.href = '/home';
        });
    }
    
    /**
     * 更新进度
     */
    updateProgress() {
        const total = this.dialogueData.dialogues.length;
        const current = this.currentIndex + 1;
        const percentage = (current / total) * 100;
        
        this.progressBar.style.width = percentage + '%';
        this.progressText.textContent = `第 ${current} / ${total} 句`;
    }
    
    /**
     * 处理键盘快捷键
     */
    handleKeyPress(e) {
        // Ctrl/Cmd + Enter: 提交
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (!this.submitBtn.disabled) {
                this.submitAnswer();
            }
        }
        
        // Space: 播放/重播（当输入框没有焦点时）
        if (e.code === 'Space' && document.activeElement !== this.userInput) {
            e.preventDefault();
            if (!this.playBtn.disabled) {
                this.playAudio();
            }
        }
    }
}

// 全局函数：显示提示信息（复用common.js中的函数）
if (typeof showAlert !== 'function') {
    function showAlert(message, type = 'info') {
        alert(message);
    }
}

