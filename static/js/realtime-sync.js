/**
 * 实时文本同步组件
 * 实现音频播放时的实时字词高亮同步
 */
class RealtimeTextSync {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            highlightClass: 'highlight-current',
            upcomingClass: 'upcoming-char',
            completedClass: 'completed-char',
            animationDuration: 200,
            updateThrottle: 16, // 60 FPS
            ...options
        };
        
        this.charTimestamps = [];
        this.currentCharIndex = -1;
        this.audio = null;
        this.isPlaying = false;
        this.startTime = null;
        this.syncTimer = null;
        this.lastUpdateTime = 0;
        
        // 事件回调
        this.callbacks = {
            onCharacterChange: null,
            onSyncStart: null,
            onSyncPause: null,
            onSyncEnd: null
        };
    }
    
    /**
     * 加载文本和时间戳数据
     */
    loadText(text, charTimestamps) {
        console.log('加载文本同步数据:', text, charTimestamps);
        this.charTimestamps = charTimestamps || [];
        this.renderText(text);
        
        // 验证时间戳数据
        if (this.charTimestamps.length !== text.length) {
            console.warn('时间戳数量与文本长度不匹配:', this.charTimestamps.length, text.length);
        }
    }
    
    /**
     * 渲染可同步的文本界面
     */
    renderText(text) {
        const textHTML = Array.from(text).map((char, index) => {
            return `<span class="sync-char" data-index="${index}">${char}</span>`;
        }).join('');
        
        this.container.innerHTML = `
            <div class="sync-text-container">
                <div class="sync-text">${textHTML}</div>
                <div class="sync-progress">
                    <div class="progress-bar" id="syncProgressBar"></div>
                </div>
                <div class="sync-timer">
                    <span id="currentTime">00:00</span> / 
                    <span id="totalTime">00:00</span>
                </div>
                <div class="sync-controls">
                    <button class="btn btn-sm btn-outline-primary" id="syncPlayBtn">
                        <i class="fas fa-play"></i> 开始同步
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" id="syncPauseBtn" disabled>
                        <i class="fas fa-pause"></i> 暂停同步
                    </button>
                    <button class="btn btn-sm btn-outline-info" id="syncResetBtn">
                        <i class="fas fa-redo"></i> 重置
                    </button>
                </div>
            </div>
        `;
        
        // 绑定控制按钮事件
        this.bindControlEvents();
    }
    
    /**
     * 绑定控制按钮事件
     */
    bindControlEvents() {
        const playBtn = this.container.querySelector('#syncPlayBtn');
        const pauseBtn = this.container.querySelector('#syncPauseBtn');
        const resetBtn = this.container.querySelector('#syncResetBtn');
        
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                if (this.audio) {
                    this.audio.play();
                }
            });
        }
        
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => {
                if (this.audio) {
                    this.audio.pause();
                }
            });
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetSync();
            });
        }
    }
    
    /**
     * 开始音频文本同步
     */
    startSync(audioElement) {
        console.log('开始音频文本同步');
        this.audio = audioElement;
        this.startTime = Date.now();
        
        // 移除之前的事件监听器
        this.removeAudioListeners();
        
        // 添加音频事件监听器
        this.audio.addEventListener('play', this.onAudioPlay.bind(this));
        this.audio.addEventListener('pause', this.onAudioPause.bind(this));
        this.audio.addEventListener('timeupdate', this.onTimeUpdate.bind(this));
        this.audio.addEventListener('ended', this.onAudioEnd.bind(this));
        this.audio.addEventListener('seeked', this.onAudioSeeked.bind(this));
        
        // 初始化控制按钮状态
        this.updateControlButtons();
        
        // 触发同步开始回调
        if (this.callbacks.onSyncStart) {
            this.callbacks.onSyncStart();
        }
    }
    
    /**
     * 移除音频事件监听器
     */
    removeAudioListeners() {
        if (this.audio) {
            this.audio.removeEventListener('play', this.onAudioPlay.bind(this));
            this.audio.removeEventListener('pause', this.onAudioPause.bind(this));
            this.audio.removeEventListener('timeupdate', this.onTimeUpdate.bind(this));
            this.audio.removeEventListener('ended', this.onAudioEnd.bind(this));
            this.audio.removeEventListener('seeked', this.onAudioSeeked.bind(this));
        }
    }
    
    /**
     * 启动实时同步循环
     */
    startSyncLoop() {
        const sync = () => {
            if (this.isPlaying && this.audio) {
                const now = Date.now();
                
                // 节流更新，避免过度渲染
                if (now - this.lastUpdateTime >= this.options.updateThrottle) {
                    const currentTime = this.audio.currentTime;
                    this.updateHighlight(currentTime);
                    this.updateProgress(currentTime);
                    this.lastUpdateTime = now;
                }
            }
            
            if (this.isPlaying) {
                this.syncTimer = requestAnimationFrame(sync);
            }
        };
        
        sync();
    }
    
    /**
     * 更新字符高亮状态
     */
    updateHighlight(currentTime) {
        let newCurrentIndex = -1;
        
        // 找到当前时间对应的字符
        for (let i = 0; i < this.charTimestamps.length; i++) {
            const timestamp = this.charTimestamps[i];
            if (currentTime >= timestamp.start_time && currentTime < timestamp.end_time) {
                newCurrentIndex = i;
                break;
            }
        }
        
        // 更新高亮状态
        if (newCurrentIndex !== this.currentCharIndex) {
            this.highlightCharacter(newCurrentIndex);
            this.currentCharIndex = newCurrentIndex;
            
            // 触发字符变化事件
            this.onCharacterChange(newCurrentIndex);
        }
    }
    
    /**
     * 高亮指定字符
     */
    highlightCharacter(index) {
        // 清除所有高亮
        this.container.querySelectorAll('.sync-char').forEach((char, i) => {
            char.className = 'sync-char';
            
            if (i < index) {
                char.classList.add(this.options.completedClass);
            } else if (i === index) {
                char.classList.add(this.options.highlightClass);
            } else if (i === index + 1) {
                char.classList.add(this.options.upcomingClass);
            }
        });
        
        // 滚动到当前字符
        if (index >= 0) {
            const currentChar = this.container.querySelector(`[data-index="${index}"]`);
            if (currentChar) {
                this.scrollToElement(currentChar);
            }
        }
    }
    
    /**
     * 优化的滚动到元素
     */
    scrollToElement(element) {
        const rect = element.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();
        
        // 检查元素是否已经在可视区域内
        const isVisible = (
            rect.top >= containerRect.top &&
            rect.bottom <= containerRect.bottom &&
            rect.left >= containerRect.left &&
            rect.right <= containerRect.right
        );
        
        if (!isVisible) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'center'
            });
        }
    }
    
    /**
     * 更新进度条
     */
    updateProgress(currentTime) {
        const duration = this.audio.duration || 0;
        const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
        
        const progressBar = this.container.querySelector('#syncProgressBar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        // 更新时间显示
        const currentTimeEl = this.container.querySelector('#currentTime');
        const totalTimeEl = this.container.querySelector('#totalTime');
        
        if (currentTimeEl) {
            currentTimeEl.textContent = this.formatTime(currentTime);
        }
        if (totalTimeEl) {
            totalTimeEl.textContent = this.formatTime(duration);
        }
    }
    
    /**
     * 格式化时间显示
     */
    formatTime(seconds) {
        if (isNaN(seconds)) return '00:00';
        
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    /**
     * 更新控制按钮状态
     */
    updateControlButtons() {
        const playBtn = this.container.querySelector('#syncPlayBtn');
        const pauseBtn = this.container.querySelector('#syncPauseBtn');
        
        if (playBtn && pauseBtn) {
            if (this.isPlaying) {
                playBtn.disabled = true;
                pauseBtn.disabled = false;
            } else {
                playBtn.disabled = false;
                pauseBtn.disabled = true;
            }
        }
    }
    
    /**
     * 重置同步状态
     */
    resetSync() {
        console.log('重置同步状态');
        
        if (this.audio) {
            this.audio.currentTime = 0;
        }
        
        this.currentCharIndex = -1;
        this.highlightCharacter(-1);
        this.updateProgress(0);
    }
    
    /**
     * 字符变化回调
     */
    onCharacterChange(index) {
        if (index >= 0 && index < this.charTimestamps.length) {
            const char = this.charTimestamps[index].char;
            
            console.log(`当前字符: ${char} (索引: ${index})`);
            
            // 触发自定义事件
            this.container.dispatchEvent(new CustomEvent('characterchange', {
                detail: {
                    index: index,
                    character: char,
                    timestamp: this.charTimestamps[index]
                }
            }));
            
            // 调用回调函数
            if (this.callbacks.onCharacterChange) {
                this.callbacks.onCharacterChange(index, char, this.charTimestamps[index]);
            }
        }
    }
    
    /**
     * 音频播放事件
     */
    onAudioPlay() {
        console.log('音频开始播放');
        this.isPlaying = true;
        this.startSyncLoop();
        this.updateControlButtons();
        
        if (this.callbacks.onSyncStart) {
            this.callbacks.onSyncStart();
        }
    }
    
    /**
     * 音频暂停事件
     */
    onAudioPause() {
        console.log('音频暂停');
        this.isPlaying = false;
        if (this.syncTimer) {
            cancelAnimationFrame(this.syncTimer);
        }
        this.updateControlButtons();
        
        if (this.callbacks.onSyncPause) {
            this.callbacks.onSyncPause();
        }
    }
    
    /**
     * 音频结束事件
     */
    onAudioEnd() {
        console.log('音频播放结束');
        this.isPlaying = false;
        this.highlightCharacter(this.charTimestamps.length); // 全部完成
        this.updateControlButtons();
        
        if (this.callbacks.onSyncEnd) {
            this.callbacks.onSyncEnd();
        }
    }
    
    /**
     * 音频跳转事件
     */
    onAudioSeeked() {
        console.log('音频位置跳转');
        // 立即更新高亮位置
        if (this.audio) {
            this.updateHighlight(this.audio.currentTime);
            this.updateProgress(this.audio.currentTime);
        }
    }
    
    /**
     * 时间更新事件
     */
    onTimeUpdate() {
        // 这个事件处理在 startSyncLoop 中已经处理了
        // 这里保留接口以防需要额外处理
    }
    
    /**
     * 设置事件回调
     */
    setCallback(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
    }
    
    /**
     * 获取当前同步状态
     */
    getSyncStatus() {
        return {
            isPlaying: this.isPlaying,
            currentCharIndex: this.currentCharIndex,
            currentTime: this.audio ? this.audio.currentTime : 0,
            duration: this.audio ? this.audio.duration : 0,
            progress: this.audio && this.audio.duration ? 
                     (this.audio.currentTime / this.audio.duration) * 100 : 0
        };
    }
    
    /**
     * 销毁组件，清理资源
     */
    destroy() {
        console.log('销毁实时同步组件');
        
        // 停止同步循环
        this.isPlaying = false;
        if (this.syncTimer) {
            cancelAnimationFrame(this.syncTimer);
        }
        
        // 移除事件监听器
        this.removeAudioListeners();
        
        // 清理DOM引用
        this.container = null;
        this.charTimestamps = null;
        this.audio = null;
        this.callbacks = null;
    }
}

/**
 * 同步组件管理器
 * 管理多个同步组件实例
 */
class SyncComponentManager {
    constructor() {
        this.components = new Map();
        this.activeComponent = null;
    }
    
    /**
     * 创建同步组件
     */
    createComponent(id, container, options = {}) {
        const component = new RealtimeTextSync(container, options);
        this.components.set(id, component);
        return component;
    }
    
    /**
     * 获取组件
     */
    getComponent(id) {
        return this.components.get(id);
    }
    
    /**
     * 设置活动组件
     */
    setActiveComponent(id) {
        const component = this.components.get(id);
        if (component) {
            // 暂停其他组件
            if (this.activeComponent && this.activeComponent !== component) {
                this.activeComponent.isPlaying = false;
                if (this.activeComponent.syncTimer) {
                    cancelAnimationFrame(this.activeComponent.syncTimer);
                }
            }
            
            this.activeComponent = component;
            return true;
        }
        return false;
    }
    
    /**
     * 销毁组件
     */
    destroyComponent(id) {
        const component = this.components.get(id);
        if (component) {
            component.destroy();
            this.components.delete(id);
            
            if (this.activeComponent === component) {
                this.activeComponent = null;
            }
            return true;
        }
        return false;
    }
    
    /**
     * 销毁所有组件
     */
    destroyAll() {
        this.components.forEach((component, id) => {
            component.destroy();
        });
        this.components.clear();
        this.activeComponent = null;
    }
}

// 全局同步组件管理器
window.syncComponentManager = new SyncComponentManager();

// 导出类以便其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        RealtimeTextSync,
        SyncComponentManager
    };
}
