# -*- coding: utf-8 -*-
"""
Web界面模块 - Flask后端API
提供音高曲线比对系统的Web服务
"""
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
import os
import uuid
import time
from datetime import datetime
import json
import traceback

# 导入系统模块
from config import Config
from tts_module import TTSManager
from pitch_comparison import PitchComparator
from scoring_algorithm import ScoringSystem, DetailedAnalyzer
from visualization import PitchVisualization

# 导入数值处理
import numpy as np

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 启用跨域支持
CORS(app)

def safe_json_serialize(obj):
    """安全的JSON序列化，处理NaN和inf值"""
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return safe_json_serialize(obj.tolist())
    else:
        return obj

# 初始化系统组件
tts_manager = None
comparator = None
scoring_system = None
analyzer = None
visualizer = None

def init_system():
    """初始化系统组件"""
    global tts_manager, comparator, scoring_system, analyzer, visualizer
    
    try:
        print("正在初始化系统组件...")
        
        # 创建必要目录
        Config.create_directories()
        
        # 初始化各个模块
        tts_manager = TTSManager()
        comparator = PitchComparator()
        scoring_system = ScoringSystem()
        analyzer = DetailedAnalyzer()
        visualizer = PitchVisualization()
        
        print("✓ 系统初始化完成")
        return True
        
    except Exception as e:
        print(f"✗ 系统初始化失败: {e}")
        traceback.print_exc()
        return False

# 路由定义

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/tts/engines', methods=['GET'])
def get_tts_engines():
    """获取可用的TTS引擎列表"""
    try:
        engines = tts_manager.get_available_engines() if tts_manager else []
        return jsonify({
            'success': True,
            'engines': engines
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tts/generate', methods=['POST'])
def generate_standard_audio():
    """生成标准发音音频"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要合成的文本'
            }), 400
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"standard_{file_id}.wav"
        output_path = os.path.join(Config.TEMP_FOLDER, filename)
        
        # 调用TTS生成音频
        success = tts_manager.generate_standard_audio(text, output_path)
        
        if success:
            # 提取音高信息
            pitch_data = comparator.extractor.extract_pitch(output_path)
            
            # 安全计算音高统计
            pitch_values = pitch_data.get('pitch_values', [0])
            if len(pitch_values) > 0 and not all(np.isnan(pitch_values)):
                mean_pitch = float(np.nanmean(pitch_values))
            else:
                mean_pitch = 0.0
            
            pitch_info = {
                'duration': pitch_data.get('duration', 0),
                'valid_ratio': pitch_data.get('valid_ratio', 0),
                'mean_pitch': mean_pitch
            }
            
            return jsonify({
                'success': True,
                'audio_url': url_for('serve_temp_file', filename=filename),
                'file_id': file_id,
                'pitch_info': safe_json_serialize(pitch_info)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'TTS生成失败，请检查网络连接或TTS配置'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/audio/upload', methods=['POST'])
def upload_user_audio():
    """上传用户录音"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': '请上传音频文件'
            }), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"user_{file_id}_temp{file_extension}"
        temp_filepath = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
        
        # 先保存临时文件
        file.save(temp_filepath)
        
        # 目标WAV文件路径
        wav_filename = f"user_{file_id}.wav"
        wav_filepath = os.path.join(Config.UPLOAD_FOLDER, wav_filename)
        
        # 使用ffmpeg转换为WAV格式
        try:
            import subprocess
            result = subprocess.run([
                'ffmpeg', '-i', temp_filepath, 
                '-acodec', 'pcm_s16le', 
                '-ar', '16000', 
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                wav_filepath
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"ffmpeg转换失败: {result.stderr}")
                # 如果转换失败，尝试直接使用原文件
                import shutil
                shutil.move(temp_filepath, wav_filepath)
            else:
                print(f"音频格式转换成功: {temp_filename} -> {wav_filename}")
                # 删除临时文件
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                    
        except Exception as e:
            print(f"音频转换过程出错: {e}")
            # 转换失败时使用原文件
            import shutil
            if os.path.exists(temp_filepath):
                shutil.move(temp_filepath, wav_filepath)
        
        # 使用转换后的WAV文件路径
        filepath = wav_filepath
        filename = wav_filename
        
        # 提取音高信息
        pitch_data = comparator.extractor.extract_pitch(filepath)
        
        # 安全计算平均音高
        pitch_values = pitch_data.get('pitch_values', [])
        valid_pitches = [p for p in pitch_values if p > 0]
        mean_pitch = np.mean(valid_pitches) if valid_pitches else 0.0
        
        return safe_json_serialize({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'pitch_info': {
                'duration': pitch_data.get('duration', 0),
                'valid_ratio': pitch_data.get('valid_ratio', 0),
                'mean_pitch': mean_pitch
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件上传失败: {str(e)}'
        }), 500

@app.route('/api/compare', methods=['POST'])
def compare_audio():
    """比较音频并生成评分"""
    try:
        data = request.get_json()
        print(f"收到比较请求数据: {data}")
        
        if not data:
            print("错误: 请求体为空")
            return jsonify({
                'success': False,
                'error': '请求体为空'
            }), 400
            
        standard_file_id = data.get('standard_file_id')
        user_file_id = data.get('user_file_id')
        text = data.get('text', '')
        
        print(f"standard_file_id: {standard_file_id}, user_file_id: {user_file_id}")
        
        if not standard_file_id or not user_file_id:
            return jsonify({
                'success': False,
                'error': f'缺少音频文件ID (standard: {standard_file_id}, user: {user_file_id})'
            }), 400
        
        # 构建文件路径
        standard_path = os.path.join(Config.TEMP_FOLDER, f"standard_{standard_file_id}.wav")
        user_path = os.path.join(Config.UPLOAD_FOLDER, f"user_{user_file_id}.wav")
        
        if not os.path.exists(standard_path):
            return jsonify({
                'success': False,
                'error': '标准音频文件不存在'
            }), 404
        
        if not os.path.exists(user_path):
            return jsonify({
                'success': False,
                'error': '用户音频文件不存在'
            }), 404
        
        # 进行音高比较
        print(f"开始比较音频: {standard_path} vs {user_path}")
        comparison_result = comparator.compare_pitch_curves(standard_path, user_path)
        
        if 'error' in comparison_result:
            return jsonify({
                'success': False,
                'error': comparison_result['error']
            }), 400
        
        # 计算评分
        score_result = scoring_system.calculate_score(comparison_result)
        
        # 详细分析
        detailed_analysis = analyzer.analyze_pitch_details(comparison_result)
        
        # 生成可视化图表
        chart_filename = f"comparison_{user_file_id}_{int(time.time())}.png"
        chart_path = os.path.join(Config.OUTPUT_FOLDER, chart_filename)
        
        chart_success = visualizer.plot_pitch_comparison(
            comparison_result, score_result, chart_path
        )
        
        # 准备返回数据，使用安全序列化
        result = {
            'success': True,
            'score': safe_json_serialize(score_result),
            'analysis': safe_json_serialize(detailed_analysis),
            'text': text,
            'timestamp': datetime.now().isoformat(),
            'chart_url': url_for('serve_output_file', filename=chart_filename) if chart_success else None
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"比较失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'比较失败: {str(e)}'
        }), 500

@app.route('/api/pitch/extract', methods=['POST'])
def extract_pitch():
    """提取单个音频的音高信息"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        file_type = data.get('type', 'user')  # 'user' or 'standard'
        
        if not file_id:
            return jsonify({
                'success': False,
                'error': '缺少文件ID'
            }), 400
        
        # 构建文件路径
        if file_type == 'standard':
            file_path = os.path.join(Config.TEMP_FOLDER, f"standard_{file_id}.wav")
        else:
            user_files = [f for f in os.listdir(Config.UPLOAD_FOLDER) if f.startswith(f"user_{file_id}")]
            if not user_files:
                return jsonify({
                    'success': False,
                    'error': '文件不存在'
                }), 404
            file_path = os.path.join(Config.UPLOAD_FOLDER, user_files[0])
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 提取音高
        pitch_data = comparator.extractor.extract_pitch(file_path)
        
        # 生成单独的音高图
        chart_filename = f"pitch_{file_type}_{file_id}_{int(time.time())}.png"
        chart_path = os.path.join(Config.OUTPUT_FOLDER, chart_filename)
        
        title = "标准发音音高曲线" if file_type == 'standard' else "用户发音音高曲线"
        chart_success = visualizer.plot_individual_pitch(pitch_data, chart_path, title)
        
        # 安全计算音高统计
        pitch_values = pitch_data.get('pitch_values', [0])
        if len(pitch_values) > 0 and not all(np.isnan(pitch_values)):
            mean_pitch = float(np.nanmean(pitch_values))
            pitch_range = float(np.nanmax(pitch_values) - np.nanmin(pitch_values))
        else:
            mean_pitch = 0.0
            pitch_range = 0.0
        
        pitch_data_safe = {
            'duration': pitch_data.get('duration', 0),
            'valid_ratio': pitch_data.get('valid_ratio', 0),
            'mean_pitch': mean_pitch,
            'pitch_range': pitch_range
        }
        
        return jsonify({
            'success': True,
            'pitch_data': safe_json_serialize(pitch_data_safe),
            'chart_url': url_for('serve_output_file', filename=chart_filename) if chart_success else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'音高提取失败: {str(e)}'
        }), 500

@app.route('/temp/<filename>')
def serve_temp_file(filename):
    """提供临时文件访问"""
    try:
        return send_file(os.path.join(Config.TEMP_FOLDER, filename))
    except Exception:
        return "File not found", 404

@app.route('/output/<filename>')
def serve_output_file(filename):
    """提供输出文件访问"""
    try:
        return send_file(os.path.join(Config.OUTPUT_FOLDER, filename))
    except Exception:
        return "File not found", 404

@app.route('/upload/<filename>')
def serve_upload_file(filename):
    """提供上传文件访问"""
    try:
        return send_file(os.path.join(Config.UPLOAD_FOLDER, filename))
    except Exception:
        return "File not found", 404

@app.route('/api/system/status')
def system_status():
    """获取系统状态"""
    return jsonify({
        'success': True,
        'status': {
            'tts_available': tts_manager is not None,
            'tts_engines': tts_manager.get_available_engines() if tts_manager else [],
            'system_ready': all([tts_manager, comparator, scoring_system, visualizer])
        }
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'error': '文件太大，请上传小于16MB的音频文件'
    }), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500

# 创建静态文件目录和模板目录
def create_web_directories():
    """创建Web应用所需的目录"""
    directories = ['templates', 'static', 'static/css', 'static/js', 'static/images']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

if __name__ == '__main__':
    # 创建Web目录
    create_web_directories()
    
    # 初始化系统
    if init_system():
        print("🚀 启动Web服务器...")
        print(f"访问地址: http://localhost:{Config.PORT}")
        
        # 启动Flask应用
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.DEBUG,
            threaded=True
        )
    else:
        print("❌ 系统初始化失败，无法启动Web服务器")
        exit(1)
