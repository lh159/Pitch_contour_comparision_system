/**
 * 录音实时指导组件
 * 继承自RealtimeTextSync，实现录音时的实时字词提示功能
 */
class RecordingGuide extends RealtimeTextSync {
    constructor(container, options = {}) {
        super(container, {
            ...options,
            showRecordingHints: true,
            recordingClass: 'recording-active',
            missedClass: 'missed-char',
            correctClass: 'correct-char',
            warningClass: 'warning-char',
            earlyClass: 'early-char',
            lateClass: 'late-char'
        });
        
        this.isRecording = false;
        this.recordingStartTime = null;
        this.userProgress = [];
        this.missedThreshold = 0.5; // 超过0.5秒未说视为错过
        this.earlyThreshold = 0.3;   // 提前0.3秒说视为太早
        this.lateThreshold = 0.3;    // 延迟0.3秒说视为太晚
        
        // 录音指导特有的配置
        this.guideConfig = {
            showUpcomingCount: 2,     // 显示接下来几个字符
            highlightDuration: 1000,  // 高亮持续时间
            warningBeforeTime: 0.5,   // 提前多久开始警告
            autoAdvanceTime: 0.2,     // 自动推进时间
            enableVoiceDetection: false, // 是否启用语音检测
            enableHapticFeedback: false, // 是否启用触觉反馈
            reactionTime: 0.5,        // 用户反应时间补偿（秒）
            preparationTime: 3.0,     // 录音前准备时间（秒）
            flexibleWindow: 0.8,      // 宽松时间窗口（秒）
            enablePreparationPhase: true // 是否启用准备阶段
        };
        
        // 语音检测相关
        this.voiceDetector = null;
        this.lastVoiceTime = 0;
        
        // 性能统计
        this.stats = {
            correctCount: 0,
            missedCount: 0,
            earlyCount: 0,
            lateCount: 0,
            averageDelay: 0,
            totalDelay: 0
        };
    }
    
    /**
     * 开始录音指导
     */
    startRecordingGuide(charTimestamps, options = {}) {
        console.log('开始录音指导模式');
        
        this.charTimestamps = charTimestamps || [];
        
        // 合并配置选项
        this.guideConfig = { ...this.guideConfig, ...options };
        
        // 初始化状态
        this.currentCharIndex = 0;
        this.userProgress = new Array(this.charTimestamps.length).fill(null);
        this.preparationStartTime = null;
        this.isInPreparation = false;
        
        // 重置统计
        this.resetStats();
        
        // 合并配置
        Object.assign(this.guideConfig, options);
        
        // 如果启用准备阶段，先进入准备模式
        if (this.guideConfig.enablePreparationPhase) {
            this.startPreparationPhase();
        } else {
            this.startActualRecording();
        }
    }
    
    /**
     * 开始准备阶段
     */
    startPreparationPhase() {
        console.log('进入录音准备阶段...');
        
        this.isInPreparation = true;
        this.preparationStartTime = Date.now();
        
        // 显示准备提示
        this.showPreparationHint();
        
        // 立即显示初始倒计时状态
        this.updatePreparationDisplay(this.guideConfig.preparationTime);
        
        // 设置准备阶段倒计时
        const countdownInterval = setInterval(() => {
            const elapsed = (Date.now() - this.preparationStartTime) / 1000;
            const remaining = Math.max(0, this.guideConfig.preparationTime - elapsed);
            
            if (remaining <= 0) {
                clearInterval(countdownInterval);
                this.endPreparationPhase();
            } else {
                this.updatePreparationDisplay(remaining);
            }
        }, 100);
    }
    
    /**
     * 显示准备提示
     */
    showPreparationHint() {
        // 在容器中显示准备提示
        const hintElement = document.createElement('div');
        hintElement.className = 'preparation-hint';
        hintElement.innerHTML = `
            <div class="preparation-content">
                <div class="preparation-header">
                    <h4>📢 录音准备中</h4>
                    <p>请先熟悉一下要朗读的内容</p>
                </div>
                <div class="preparation-text">${this.getTextPreview()}</div>
                
                <!-- 跨年式倒计时显示区域 -->
                <div class="countdown-display" id="countdownDisplay">
                    <div class="countdown-circle">
                        <div class="countdown-number" id="countdownNumber">3</div>
                        <div class="countdown-text">准备开始</div>
                    </div>
                </div>
            </div>
        `;
        
        this.container.appendChild(hintElement);
        
        // 添加倒计时样式
        this.addCountdownStyles();
    }
    
    /**
     * 添加倒计时样式
     */
    addCountdownStyles() {
        // 检查是否已经添加过样式
        if (document.getElementById('countdown-styles')) {
            return;
        }
        
        const style = document.createElement('style');
        style.id = 'countdown-styles';
        style.textContent = `
            /* 倒计时容器样式 */
            .countdown-display {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 30px 0;
                min-height: 200px;
                position: relative;
            }
            
            /* 倒计时圆圈 */
            .countdown-circle {
                width: 150px;
                height: 150px;
                border-radius: 50%;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
                transition: all 0.3s ease;
            }
            
            /* 不同状态的颜色 */
            .countdown-3 .countdown-circle {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                box-shadow: 0 10px 30px rgba(255, 107, 107, 0.4);
            }
            
            .countdown-2 .countdown-circle {
                background: linear-gradient(135deg, #feca57 0%, #ff9ff3 100%);
                box-shadow: 0 10px 30px rgba(254, 202, 87, 0.4);
            }
            
            .countdown-1 .countdown-circle {
                background: linear-gradient(135deg, #48dbfb 0%, #0abde3 100%);
                box-shadow: 0 10px 30px rgba(72, 219, 251, 0.4);
            }
            
            .countdown-start .countdown-circle {
                background: linear-gradient(135deg, #1dd1a1 0%, #10ac84 100%);
                box-shadow: 0 10px 30px rgba(29, 209, 161, 0.4);
                animation: pulse-success 0.6s ease-in-out;
            }
            
            /* 倒计时数字 */
            .countdown-number {
                font-size: 48px;
                font-weight: bold;
                color: white;
                text-shadow: 0 2px 10px rgba(0,0,0,0.3);
                transform: scale(1);
                transition: transform 0.3s ease;
            }
            
            /* 数字变化动画 */
            .countdown-animate {
                animation: countdown-bounce 0.6s ease-in-out;
            }
            
            .countdown-start-animate {
                animation: start-celebration 1s ease-in-out;
            }
            
            /* 倒计时文本 */
            .countdown-text {
                color: white;
                font-size: 14px;
                font-weight: 500;
                margin-top: 8px;
                text-shadow: 0 1px 5px rgba(0,0,0,0.3);
                text-align: center;
            }
            
            /* 动画定义 */
            @keyframes countdown-bounce {
                0% {
                    transform: scale(1);
                }
                50% {
                    transform: scale(1.3);
                }
                100% {
                    transform: scale(1);
                }
            }
            
            @keyframes start-celebration {
                0% {
                    transform: scale(1);
                }
                25% {
                    transform: scale(1.4);
                }
                50% {
                    transform: scale(1.2) rotate(10deg);
                }
                75% {
                    transform: scale(1.3) rotate(-5deg);
                }
                100% {
                    transform: scale(1.1);
                }
            }
            
            @keyframes pulse-success {
                0% {
                    transform: scale(1);
                    box-shadow: 0 10px 30px rgba(29, 209, 161, 0.4);
                }
                50% {
                    transform: scale(1.05);
                    box-shadow: 0 15px 40px rgba(29, 209, 161, 0.6);
                }
                100% {
                    transform: scale(1);
                    box-shadow: 0 10px 30px rgba(29, 209, 161, 0.4);
                }
            }
            
            /* 准备阶段整体样式优化 */
            .preparation-hint {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 15px;
                padding: 30px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                border: 1px solid rgba(255,255,255,0.2);
            }
            
            .preparation-header h4 {
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 20px;
            }
            
            .preparation-header p {
                color: #7f8c8d;
                margin-bottom: 20px;
            }
            
            .preparation-text {
                background: white;
                padding: 15px 20px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 16px;
                line-height: 1.6;
                color: #2c3e50;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                border-left: 4px solid #3498db;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 更新准备阶段显示
     */
    updatePreparationDisplay(remaining) {
        console.log('更新倒计时显示:', remaining); // 调试信息
        
        const countdownNumber = document.getElementById('countdownNumber');
        const countdownDisplay = document.getElementById('countdownDisplay');
        const countdownText = countdownDisplay?.querySelector('.countdown-text');
        
        if (!countdownNumber || !countdownDisplay) {
            console.log('倒计时元素未找到', { countdownNumber, countdownDisplay }); // 调试信息
            return;
        }
        
        const currentCount = Math.ceil(remaining);
        const previousCount = parseInt(countdownNumber.textContent) || 0;
        
        // 当数字发生变化时触发动画
        if (currentCount !== previousCount && currentCount > 0) {
            // 更新数字
            countdownNumber.textContent = currentCount;
            
            // 触发缩放动画
            countdownNumber.classList.remove('countdown-animate');
            void countdownNumber.offsetWidth; // 强制重排
            countdownNumber.classList.add('countdown-animate');
            
            // 更新文本
            if (countdownText) {
                if (currentCount === 3) {
                    countdownText.textContent = '准备开始';
                    countdownDisplay.className = 'countdown-display countdown-3';
                } else if (currentCount === 2) {
                    countdownText.textContent = '深呼吸';
                    countdownDisplay.className = 'countdown-display countdown-2';
                } else if (currentCount === 1) {
                    countdownText.textContent = '马上开始';
                    countdownDisplay.className = 'countdown-display countdown-1';
                }
            }
        } else if (currentCount === 0 && previousCount > 0) {
            // 倒计时结束，显示"开始！"
            countdownNumber.textContent = '🎤';
            countdownText.textContent = '开始录音！';
            countdownDisplay.className = 'countdown-display countdown-start';
            
            // 触发最终动画
            countdownNumber.classList.remove('countdown-animate');
            void countdownNumber.offsetWidth;
            countdownNumber.classList.add('countdown-start-animate');
        }
    }
    
    /**
     * 获取文本预览
     */
    getTextPreview() {
        if (!this.charTimestamps || this.charTimestamps.length === 0) {
            return '';
        }
        
        return this.charTimestamps.map(ts => ts.char || ts.text).join('');
    }
    
    /**
     * 结束准备阶段
     */
    endPreparationPhase() {
        console.log('准备阶段结束，开始正式录音');
        
        this.isInPreparation = false;
        
        // 移除准备提示
        const hintElement = this.container.querySelector('.preparation-hint');
        if (hintElement) {
            hintElement.remove();
        }
        
        // 开始正式录音
        this.startActualRecording();
    }
    
    /**
     * 开始实际录音
     */
    startActualRecording() {
        console.log('开始实际录音指导');
        
        // 渲染录音指导界面
        this.renderRecordingInterface();
        
        // 重置按钮状态
        this.resetButtonStates();
        
        // 初始化语音检测（如果启用）
        if (this.guideConfig.enableVoiceDetection) {
            this.initVoiceDetection();
        }
        
        this.isRecording = true;
        this.recordingStartTime = Date.now();
        
        // 开始录音循环
        this.startRecordingLoop();
    }
    
    /**
     * 渲染录音指导界面
     */
    renderRecordingInterface() {
        const text = this.charTimestamps.map(t => t.char).join('');
        
        const interfaceHTML = `
            <div class="recording-guide-container">
                <!-- 录音状态栏 -->
                <div class="recording-status">
                    <div class="recording-indicator">
                        <i class="fas fa-microphone recording-icon"></i>
                        <span class="recording-text">录音指导中...</span>
                    </div>
                    <div class="recording-timer" id="recordingTimer">00:00</div>
                    <div class="recording-progress">
                        <span id="progressText">0 / ${this.charTimestamps.length}</span>
                        <div class="progress-ring">
                            <svg class="progress-ring-svg" width="40" height="40">
                                <circle class="progress-ring-circle-bg" cx="20" cy="20" r="18"></circle>
                                <circle class="progress-ring-circle" cx="20" cy="20" r="18" id="progressRingCircle"></circle>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <!-- 大字显示区域 -->
                <div class="guide-text-large">
                    ${Array.from(text).map((char, index) => 
                        `<span class="guide-char" data-index="${index}" data-char="${char}">${char}</span>`
                    ).join('')}
                </div>
                
                <!-- 实时提示区域 -->
                <div class="recording-hints">
                    <div class="current-hint" id="currentHint">
                        准备开始朗读第一个字...
                    </div>
                    <div class="timing-hint" id="timingHint">
                        请跟随高亮提示进行朗读
                    </div>
                    <div class="upcoming-hint" id="upcomingHint">
                        <!-- 即将朗读的字符提示 -->
                    </div>
                </div>
                
                <!-- 实时反馈区域 -->
                <div class="realtime-feedback" id="realtimeFeedback">
                    <div class="feedback-item">
                        <span class="feedback-label">准确:</span>
                        <span class="feedback-value correct-count" id="correctCount">0</span>
                    </div>
                    <div class="feedback-item">
                        <span class="feedback-label">错过:</span>
                        <span class="feedback-value missed-count" id="missedCount">0</span>
                    </div>
                    <div class="feedback-item">
                        <span class="feedback-label">节奏:</span>
                        <span class="feedback-value timing-score" id="timingScore">--</span>
                    </div>
                </div>
                
                <!-- 控制按钮 -->
                <div class="recording-controls">
                    <button class="btn btn-danger guide-control-btn" id="stopRecordingBtn">
                        <i class="fas fa-stop"></i> 停止录音
                    </button>
                    <button class="btn btn-warning guide-control-btn" id="restartRecordingBtn" style="display: none;">
                        <i class="fas fa-redo"></i> 重新录制
                    </button>
                </div>
                
                <!-- 设置面板 -->
                <div class="guide-settings collapsed" id="guideSettings">
                    <div class="settings-toggle" id="settingsToggle">
                        <i class="fas fa-cog"></i> 设置
                    </div>
                    <div class="settings-content">
                        <div class="setting-item">
                            <label>错过阈值 (秒):</label>
                            <input type="range" min="0.1" max="2.0" step="0.1" 
                                   value="${this.missedThreshold}" id="missedThresholdSlider">
                            <span id="missedThresholdValue">${this.missedThreshold}</span>
                        </div>
                        <div class="setting-item">
                            <label>提前警告时间 (秒):</label>
                            <input type="range" min="0.1" max="1.0" step="0.1" 
                                   value="${this.guideConfig.warningBeforeTime}" id="warningTimeSlider">
                            <span id="warningTimeValue">${this.guideConfig.warningBeforeTime}</span>
                        </div>
                        <div class="setting-item">
                            <label>语音检测:</label>
                            <input type="checkbox" id="voiceDetectionToggle" 
                                   ${this.guideConfig.enableVoiceDetection ? 'checked' : ''}>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = interfaceHTML;
        
        // 绑定事件
        this.bindRecordingEvents();
        
        // 初始化进度环
        this.initProgressRing();
    }
    
    /**
     * 绑定录音指导事件
     */
    bindRecordingEvents() {
        // 控制按钮事件
        const stopBtn = this.container.querySelector('#stopRecordingBtn');
        const restartBtn = this.container.querySelector('#restartRecordingBtn');
        const settingsToggle = this.container.querySelector('#settingsToggle');
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopRecording());
        }
        
        if (restartBtn) {
            restartBtn.addEventListener('click', () => this.restartRecording());
        }
        
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => this.toggleSettings());
        }
        
        // 设置面板事件
        this.bindSettingsEvents();
        
        // 字符点击事件（调试用）
        this.container.querySelectorAll('.guide-char').forEach((char, index) => {
            char.addEventListener('click', () => {
                console.log(`点击字符: ${char.textContent} (索引: ${index})`);
                this.jumpToCharacter(index);
            });
        });
    }
    
    /**
     * 绑定设置面板事件
     */
    bindSettingsEvents() {
        const missedSlider = this.container.querySelector('#missedThresholdSlider');
        const warningSlider = this.container.querySelector('#warningTimeSlider');
        const voiceToggle = this.container.querySelector('#voiceDetectionToggle');
        
        if (missedSlider) {
            missedSlider.addEventListener('input', (e) => {
                this.missedThreshold = parseFloat(e.target.value);
                this.container.querySelector('#missedThresholdValue').textContent = this.missedThreshold;
            });
        }
        
        if (warningSlider) {
            warningSlider.addEventListener('input', (e) => {
                this.guideConfig.warningBeforeTime = parseFloat(e.target.value);
                this.container.querySelector('#warningTimeValue').textContent = this.guideConfig.warningBeforeTime;
            });
        }
        
        if (voiceToggle) {
            voiceToggle.addEventListener('change', (e) => {
                this.guideConfig.enableVoiceDetection = e.target.checked;
                if (e.target.checked) {
                    this.initVoiceDetection();
                } else {
                    this.stopVoiceDetection();
                }
            });
        }
    }
    
    /**
     * 开始录音指导循环
     */
    startRecordingLoop() {
        const guide = () => {
            if (this.isRecording) {
                const currentTime = (Date.now() - this.recordingStartTime) / 1000;
                this.updateRecordingGuide(currentTime);
                
                // 更新录音计时器
                this.updateTimerDisplay(currentTime);
                
                // 更新进度显示
                this.updateProgressDisplay();
            }
            
            if (this.isRecording) {
                this.recordingTimer = requestAnimationFrame(guide);
            }
        };
        
        guide();
    }
    
    /**
     * 更新录音指导状态（增强版，支持反应时间补偿）
     */
    updateRecordingGuide(currentTime) {
        // 如果还在准备阶段，不进行指导
        if (this.isInPreparation) {
            return;
        }
        
        // 找到当前应该朗读的字符（考虑反应时间补偿）
        let targetIndex = -1;
        let nextIndex = -1;
        let warningIndex = -1;
        
        // 应用反应时间补偿：用户听到TTS后需要时间反应
        const compensatedTime = currentTime + this.guideConfig.reactionTime;
        
        for (let i = 0; i < this.charTimestamps.length; i++) {
            const timestamp = this.charTimestamps[i];
            
            // 扩展时间窗口，给用户更多容错空间
            const startTime = timestamp.start_time - this.guideConfig.flexibleWindow / 2;
            const endTime = timestamp.end_time + this.guideConfig.flexibleWindow / 2;
            
            if (compensatedTime >= startTime && compensatedTime < endTime) {
                targetIndex = i;
                nextIndex = i + 1;
                break;
            } else if (compensatedTime < startTime) {
                nextIndex = i;
                
                // 检查是否需要提前警告（也要考虑反应时间）
                if (compensatedTime >= startTime - this.guideConfig.warningBeforeTime) {
                    warningIndex = i;
                }
                break;
            }
        }
        
        // 更新字符状态
        if (targetIndex !== this.currentCharIndex || warningIndex !== -1) {
            this.updateCharacterStatus(targetIndex, nextIndex, warningIndex);
            this.currentCharIndex = targetIndex;
        }
        
        // 更新提示信息
        this.updateHints(targetIndex, nextIndex, currentTime);
        
        // 检查错过的字符
        this.checkMissedCharacters(currentTime);
        
        // 更新实时反馈
        this.updateRealtimeFeedback();
    }
    
    /**
     * 更新字符状态显示
     */
    updateCharacterStatus(currentIndex, nextIndex, warningIndex) {
        this.container.querySelectorAll('.guide-char').forEach((char, index) => {
            char.className = 'guide-char';
            
            if (this.userProgress[index] === 'missed') {
                char.classList.add('missed-char');
            } else if (this.userProgress[index] === 'correct') {
                char.classList.add('correct-char');
            } else if (this.userProgress[index] === 'early') {
                char.classList.add('early-char');
            } else if (this.userProgress[index] === 'late') {
                char.classList.add('late-char');
            } else if (index === currentIndex) {
                char.classList.add('current-char', 'pulse-highlight');
            } else if (index === warningIndex) {
                char.classList.add('warning-char', 'warning-pulse');
            } else if (index === nextIndex) {
                char.classList.add('next-char');
            } else if (index > currentIndex && index <= currentIndex + this.guideConfig.showUpcomingCount) {
                char.classList.add('upcoming-char');
            } else if (index < currentIndex && !this.userProgress[index]) {
                char.classList.add('completed-char');
            }
        });
        
        // 滚动到当前字符
        if (currentIndex >= 0) {
            const currentChar = this.container.querySelector(`[data-index="${currentIndex}"]`);
            if (currentChar) {
                this.scrollToElement(currentChar);
            }
        }
    }
    
    /**
     * 更新提示信息
     */
    updateHints(currentIndex, nextIndex, currentTime) {
        const currentHint = this.container.querySelector('#currentHint');
        const timingHint = this.container.querySelector('#timingHint');
        const upcomingHint = this.container.querySelector('#upcomingHint');
        
        if (currentIndex >= 0) {
            const char = this.charTimestamps[currentIndex].char;
            currentHint.textContent = `正在朗读: "${char}"`;
            
            const remainingTime = this.charTimestamps[currentIndex].end_time - currentTime;
            if (remainingTime > 0) {
                timingHint.textContent = `还有 ${remainingTime.toFixed(1)}秒`;
                timingHint.className = 'timing-hint';
            } else {
                timingHint.textContent = '时间已过，请继续';
                timingHint.className = 'timing-hint warning';
            }
        } else if (nextIndex >= 0) {
            const nextChar = this.charTimestamps[nextIndex].char;
            const waitTime = this.charTimestamps[nextIndex].start_time - currentTime;
            
            if (waitTime > 0) {
                currentHint.textContent = `准备朗读: "${nextChar}"`;
                timingHint.textContent = `${waitTime.toFixed(1)}秒后开始`;
                timingHint.className = 'timing-hint';
            } else {
                currentHint.textContent = `现在朗读: "${nextChar}"`;
                timingHint.textContent = '请立即开始';
                timingHint.className = 'timing-hint urgent';
            }
        } else {
            currentHint.textContent = '朗读完成！';
            timingHint.textContent = '您可以停止录音了';
            timingHint.className = 'timing-hint success';
        }
        
        // 更新即将朗读的字符提示
        this.updateUpcomingHint(upcomingHint, nextIndex);
    }
    
    /**
     * 更新即将朗读提示
     */
    updateUpcomingHint(element, startIndex) {
        if (!element || startIndex < 0 || startIndex >= this.charTimestamps.length) {
            if (element) element.textContent = '';
            return;
        }
        
        const upcomingChars = [];
        const maxShow = Math.min(this.guideConfig.showUpcomingCount, 
                               this.charTimestamps.length - startIndex);
        
        for (let i = 0; i < maxShow; i++) {
            const index = startIndex + i;
            if (index < this.charTimestamps.length) {
                upcomingChars.push(this.charTimestamps[index].char);
            }
        }
        
        if (upcomingChars.length > 0) {
            element.innerHTML = `即将朗读: <span class="upcoming-chars">${upcomingChars.join(' → ')}</span>`;
        } else {
            element.textContent = '';
        }
    }
    
    /**
     * 检查错过的字符（增强版，考虑反应时间和宽松窗口）
     */
    checkMissedCharacters(currentTime) {
        // 应用反应时间补偿
        const compensatedTime = currentTime + this.guideConfig.reactionTime;
        
        for (let i = 0; i < this.charTimestamps.length; i++) {
            const timestamp = this.charTimestamps[i];
            
            // 使用更宽松的错过判定：考虑反应时间 + 灵活窗口 + 错过阈值
            const missedDeadline = timestamp.end_time + 
                                 this.guideConfig.flexibleWindow / 2 + 
                                 this.missedThreshold;
            
            if (compensatedTime > missedDeadline && !this.userProgress[i]) {
                // 标记为错过
                this.markCharacterMissed(i);
                this.userProgress[i] = 'missed';
                this.stats.missedCount++;
                
                console.log(`字符错过: "${timestamp.char}" (索引: ${i}), 当前时间: ${currentTime.toFixed(2)}s, 补偿时间: ${compensatedTime.toFixed(2)}s, 截止时间: ${missedDeadline.toFixed(2)}s`);
                
                // 触发错过回调
                this.onCharacterMissed(i, timestamp.char);
                
                // 提供触觉反馈
                this.provideFeedback('missed');
            }
        }
    }
    
    /**
     * 标记字符为指定状态
     */
    markCharacterMissed(index) {
        const char = this.container.querySelector(`[data-index="${index}"]`);
        if (char) {
            char.classList.add('missed-char');
            
            // 添加动画效果
            char.style.animation = 'missedShake 0.5s ease-in-out';
            setTimeout(() => {
                if (char.style) {
                    char.style.animation = '';
                }
            }, 500);
        }
    }
    
    /**
     * 手动标记字符为正确
     */
    markCharacterCorrect(index, timing = 'ontime') {
        if (index >= 0 && index < this.userProgress.length) {
            this.userProgress[index] = timing === 'early' ? 'early' : 
                                    timing === 'late' ? 'late' : 'correct';
            
            if (timing === 'correct' || timing === 'ontime') {
                this.stats.correctCount++;
            } else if (timing === 'early') {
                this.stats.earlyCount++;
            } else if (timing === 'late') {
                this.stats.lateCount++;
            }
            
            const char = this.container.querySelector(`[data-index="${index}"]`);
            if (char) {
                char.classList.remove('current-char', 'pulse-highlight');
                char.classList.add(timing === 'early' ? 'early-char' : 
                                 timing === 'late' ? 'late-char' : 'correct-char');
                
                // 添加成功动画
                char.style.animation = 'correctPulse 0.3s ease-in-out';
                setTimeout(() => {
                    if (char.style) {
                        char.style.animation = '';
                    }
                }, 300);
            }
            
            // 提供成功反馈
            this.provideFeedback(timing);
        }
    }
    
    /**
     * 提供反馈（振动、声音等）
     */
    provideFeedback(type) {
        if (this.guideConfig.enableHapticFeedback && navigator.vibrate) {
            switch (type) {
                case 'correct':
                case 'ontime':
                    navigator.vibrate(50); // 短振动
                    break;
                case 'early':
                case 'late':
                    navigator.vibrate([50, 50, 50]); // 三次短振动
                    break;
                case 'missed':
                    navigator.vibrate(200); // 长振动
                    break;
            }
        }
        
        // 可以在这里添加音效播放等其他反馈
    }
    
    /**
     * 跳转到指定字符
     */
    jumpToCharacter(index) {
        if (index >= 0 && index < this.charTimestamps.length) {
            const targetTime = this.charTimestamps[index].start_time;
            const newRecordingTime = this.recordingStartTime + targetTime * 1000;
            this.recordingStartTime = newRecordingTime - targetTime * 1000;
            console.log(`跳转到字符 ${index}: ${this.charTimestamps[index].char}`);
        }
    }
    
    /**
     * 停止录音（真正的录音停止，不只是指导停止）
     */
    stopRecording() {
        console.log('从录音指导面板停止录音');
        
        // 停止指导
        this.stopGuide();
        
        // 显示重新录制按钮
        const restartBtn = this.container.querySelector('#restartRecordingBtn');
        if (restartBtn) {
            restartBtn.style.display = 'inline-block';
        }
        
        // 隐藏停止录音按钮
        const stopBtn = this.container.querySelector('#stopRecordingBtn');
        if (stopBtn) {
            stopBtn.style.display = 'none';
        }
        
        // 调用主页面的停止录音函数
        if (window.stopRecording && typeof window.stopRecording === 'function') {
            window.stopRecording();
        } else {
            console.warn('未找到全局stopRecording函数');
        }
        
        // 更新状态显示
        this.updateStatusAfterStop();
    }
    
    /**
     * 重新录制
     */
    restartRecording() {
        console.log('从录音指导面板重新录制');
        
        // 停止当前的录音指导
        this.stopGuide();
        
        // 保存当前的字符时间戳数据
        const savedCharTimestamps = this.charTimestamps;
        const savedGuideConfig = { ...this.guideConfig };
        
        // 重置状态
        this.isRecording = false;
        this.isInPreparation = false;
        this.currentCharIndex = 0;
        this.recordingStartTime = null;
        
        // 清理界面
        this.container.innerHTML = '';
        
        // 重新开始录音指导（包括倒计时），传入保存的数据
        setTimeout(() => {
            this.startRecordingGuide(savedCharTimestamps, savedGuideConfig);
        }, 100);
    }
    
    /**
     * 更新停止录音后的状态显示
     */
    updateStatusAfterStop() {
        // 更新录音状态显示
        const recordingText = this.container.querySelector('.recording-text');
        if (recordingText) {
            recordingText.textContent = '录音已停止';
        }
        
        // 更新录音图标
        const recordingIcon = this.container.querySelector('.recording-icon');
        if (recordingIcon) {
            recordingIcon.className = 'fas fa-stop recording-icon stopped';
        }
        
        // 更新提示信息
        const currentHint = this.container.querySelector('#currentHint');
        const timingHint = this.container.querySelector('#timingHint');
        
        if (currentHint) {
            currentHint.textContent = '录音已停止';
        }
        
        if (timingHint) {
            timingHint.textContent = '可以点击"重新录制"重新开始';
            timingHint.className = 'timing-hint info';
        }
    }
    
    /**
     * 重置按钮状态
     */
    resetButtonStates() {
        // 显示停止录音按钮，隐藏重新录制按钮
        const stopBtn = this.container.querySelector('#stopRecordingBtn');
        const restartBtn = this.container.querySelector('#restartRecordingBtn');
        
        if (stopBtn) {
            stopBtn.style.display = 'inline-block';
        }
        
        if (restartBtn) {
            restartBtn.style.display = 'none';
        }
        
        // 重置录音状态显示
        const recordingText = this.container.querySelector('.recording-text');
        const recordingIcon = this.container.querySelector('.recording-icon');
        
        if (recordingText) {
            recordingText.textContent = '录音指导中...';
        }
        
        if (recordingIcon) {
            recordingIcon.className = 'fas fa-microphone recording-icon';
        }
    }
    
    /**
     * 停止录音指导
     */
    stopGuide() {
        console.log('停止录音指导');
        this.isRecording = false;
        
        if (this.recordingTimer) {
            cancelAnimationFrame(this.recordingTimer);
        }
        
        this.stopVoiceDetection();
        
        // 计算最终统计
        this.calculateFinalStats();
        
        // 触发停止事件
        this.container.dispatchEvent(new CustomEvent('guidestopped', {
            detail: {
                progress: this.userProgress,
                stats: this.stats,
                duration: (Date.now() - this.recordingStartTime) / 1000
            }
        }));
    }
    
    /**
     * 更新计时器显示
     */
    updateTimerDisplay(currentTime) {
        const timerEl = this.container.querySelector('#recordingTimer');
        if (timerEl) {
            timerEl.textContent = this.formatTime(currentTime);
        }
    }
    
    /**
     * 更新进度显示
     */
    updateProgressDisplay() {
        const completedCount = this.userProgress.filter(p => p && p !== 'missed').length;
        const totalCount = this.charTimestamps.length;
        const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
        
        // 更新进度文本
        const progressText = this.container.querySelector('#progressText');
        if (progressText) {
            progressText.textContent = `${completedCount} / ${totalCount}`;
        }
        
        // 更新进度环
        this.updateProgressRing(progressPercent);
    }
    
    /**
     * 初始化进度环
     */
    initProgressRing() {
        const circle = this.container.querySelector('#progressRingCircle');
        if (circle) {
            const radius = circle.r.baseVal.value;
            const circumference = 2 * Math.PI * radius;
            
            circle.style.strokeDasharray = circumference;
            circle.style.strokeDashoffset = circumference;
        }
    }
    
    /**
     * 更新进度环
     */
    updateProgressRing(percent) {
        const circle = this.container.querySelector('#progressRingCircle');
        if (circle) {
            const radius = circle.r.baseVal.value;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (percent / 100) * circumference;
            
            circle.style.strokeDashoffset = offset;
        }
    }
    
    /**
     * 更新实时反馈
     */
    updateRealtimeFeedback() {
        const correctEl = this.container.querySelector('#correctCount');
        const missedEl = this.container.querySelector('#missedCount');
        const timingEl = this.container.querySelector('#timingScore');
        
        if (correctEl) {
            correctEl.textContent = this.stats.correctCount;
        }
        
        if (missedEl) {
            missedEl.textContent = this.stats.missedCount;
        }
        
        if (timingEl) {
            const totalProcessed = this.stats.correctCount + this.stats.missedCount + 
                                 this.stats.earlyCount + this.stats.lateCount;
            if (totalProcessed > 0) {
                const accuracy = (this.stats.correctCount / totalProcessed) * 100;
                timingEl.textContent = `${accuracy.toFixed(1)}%`;
                
                // 根据准确率设置颜色
                if (accuracy >= 90) {
                    timingEl.className = 'feedback-value timing-score excellent';
                } else if (accuracy >= 80) {
                    timingEl.className = 'feedback-value timing-score good';
                } else if (accuracy >= 70) {
                    timingEl.className = 'feedback-value timing-score fair';
                } else {
                    timingEl.className = 'feedback-value timing-score poor';
                }
            }
        }
    }
    
    /**
     * 切换设置面板
     */
    toggleSettings() {
        const settings = this.container.querySelector('#guideSettings');
        if (settings) {
            settings.classList.toggle('collapsed');
        }
    }
    
    /**
     * 初始化语音检测
     */
    initVoiceDetection() {
        if (!navigator.mediaDevices || !window.AudioContext) {
            console.warn('浏览器不支持语音检测功能');
            return;
        }
        
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.voiceDetector = new VoiceActivityDetector(stream);
                this.voiceDetector.onVoiceStart = () => {
                    this.lastVoiceTime = Date.now();
                    this.onVoiceDetected();
                };
                this.voiceDetector.start();
                console.log('语音检测已启动');
            })
            .catch(err => {
                console.warn('无法启动语音检测:', err);
            });
    }
    
    /**
     * 停止语音检测
     */
    stopVoiceDetection() {
        if (this.voiceDetector) {
            this.voiceDetector.stop();
            this.voiceDetector = null;
            console.log('语音检测已停止');
        }
    }
    
    /**
     * 语音检测到事件
     */
    onVoiceDetected() {
        const currentTime = (Date.now() - this.recordingStartTime) / 1000;
        
        // 找到应该说的字符
        for (let i = 0; i < this.charTimestamps.length; i++) {
            const timestamp = this.charTimestamps[i];
            
            if (!this.userProgress[i] && 
                currentTime >= timestamp.start_time - this.earlyThreshold &&
                currentTime <= timestamp.end_time + this.lateThreshold) {
                
                // 判断时机
                let timing = 'correct';
                if (currentTime < timestamp.start_time) {
                    timing = 'early';
                } else if (currentTime > timestamp.end_time) {
                    timing = 'late';
                }
                
                this.markCharacterCorrect(i, timing);
                break;
            }
        }
    }
    
    /**
     * 字符错过回调
     */
    onCharacterMissed(index, char) {
        console.log(`字符错过: ${char} (索引: ${index})`);
        
        // 可以在这里添加错过字符的处理逻辑
        // 例如记录到学习分析数据中
    }
    
    /**
     * 重置统计数据
     */
    resetStats() {
        this.stats = {
            correctCount: 0,
            missedCount: 0,
            earlyCount: 0,
            lateCount: 0,
            averageDelay: 0,
            totalDelay: 0
        };
    }
    
    /**
     * 计算最终统计
     */
    calculateFinalStats() {
        const totalProcessed = this.stats.correctCount + this.stats.missedCount + 
                             this.stats.earlyCount + this.stats.lateCount;
        
        if (totalProcessed > 0) {
            this.stats.accuracy = (this.stats.correctCount / totalProcessed) * 100;
            this.stats.completionRate = (totalProcessed / this.charTimestamps.length) * 100;
        }
        
        console.log('录音指导统计:', this.stats);
    }
    
    /**
     * 获取录音指导结果
     */
    getGuidanceResult() {
        return {
            progress: this.userProgress,
            stats: this.stats,
            charTimestamps: this.charTimestamps,
            duration: this.recordingStartTime ? (Date.now() - this.recordingStartTime) / 1000 : 0
        };
    }
}

/**
 * 简单的语音活动检测器
 */
class VoiceActivityDetector {
    constructor(stream) {
        this.stream = stream;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.microphone = this.audioContext.createMediaStreamSource(stream);
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        
        this.analyser.fftSize = 256;
        this.microphone.connect(this.analyser);
        
        this.threshold = 50; // 语音检测阈值
        this.isDetecting = false;
        
        // 回调函数
        this.onVoiceStart = null;
        this.onVoiceEnd = null;
    }
    
    start() {
        this.isDetecting = true;
        this.detect();
    }
    
    stop() {
        this.isDetecting = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
    
    detect() {
        if (!this.isDetecting) return;
        
        this.analyser.getByteFrequencyData(this.dataArray);
        
        // 计算音量
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            sum += this.dataArray[i];
        }
        const average = sum / this.dataArray.length;
        
        // 检测语音开始
        if (average > this.threshold && this.onVoiceStart) {
            this.onVoiceStart(average);
        }
        
        // 继续检测
        requestAnimationFrame(() => this.detect());
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        RecordingGuide,
        VoiceActivityDetector
    };
}
