# -*- coding: utf-8 -*-
"""
WebSocket实时同步模块
提供音频-文本实时同步的WebSocket服务
"""
import time
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
import traceback

class RealtimeSyncManager:
    """实时同步管理器"""
    
    def __init__(self):
        self.active_sessions = {}  # 活动同步会话
        self.sync_data = {}        # 同步数据缓存
        self.user_connections = {} # 用户连接映射
        
    def create_session(self, session_id: str, text: str, char_timestamps: List[Dict], 
                      user_id: str = None) -> bool:
        """
        创建同步会话
        :param session_id: 会话ID
        :param text: 同步文本
        :param char_timestamps: 字符时间戳列表
        :param user_id: 用户ID（可选）
        :return: 是否创建成功
        """
        try:
            session_data = {
                'session_id': session_id,
                'text': text,
                'char_timestamps': char_timestamps,
                'user_id': user_id,
                'start_time': None,
                'current_position': 0,
                'current_char_index': -1,
                'status': 'ready',
                'created_at': datetime.now(),
                'participants': [],
                'sync_events': []
            }
            
            self.active_sessions[session_id] = session_data
            print(f"创建同步会话: {session_id} (文本: {text[:10]}...)")
            return True
            
        except Exception as e:
            print(f"创建同步会话失败: {e}")
            return False
    
    def start_session(self, session_id: str) -> bool:
        """
        开始同步会话
        :param session_id: 会话ID
        :return: 是否启动成功
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['start_time'] = time.time()
            session['status'] = 'playing'
            
            # 记录启动事件
            self._add_sync_event(session_id, 'session_started', {
                'start_time': session['start_time']
            })
            
            print(f"启动同步会话: {session_id}")
            return True
        return False
    
    def pause_session(self, session_id: str) -> bool:
        """暂停同步会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['status'] = 'paused'
            session['pause_time'] = time.time()
            
            self._add_sync_event(session_id, 'session_paused', {
                'pause_time': session['pause_time']
            })
            
            print(f"暂停同步会话: {session_id}")
            return True
        return False
    
    def resume_session(self, session_id: str) -> bool:
        """恢复同步会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # 补偿暂停时间
            if 'pause_time' in session and session['start_time']:
                pause_duration = time.time() - session['pause_time']
                session['start_time'] += pause_duration
            
            session['status'] = 'playing'
            
            self._add_sync_event(session_id, 'session_resumed', {
                'resume_time': time.time()
            })
            
            print(f"恢复同步会话: {session_id}")
            return True
        return False
    
    def stop_session(self, session_id: str) -> bool:
        """停止同步会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['status'] = 'stopped'
            session['end_time'] = time.time()
            
            self._add_sync_event(session_id, 'session_stopped', {
                'end_time': session['end_time']
            })
            
            print(f"停止同步会话: {session_id}")
            return True
        return False
    
    def update_position(self, session_id: str, current_time: float, 
                       source: str = 'client') -> Optional[Dict]:
        """
        更新播放位置
        :param session_id: 会话ID
        :param current_time: 当前播放时间
        :param source: 更新源 ('client', 'server')
        :return: 位置信息
        """
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        session['current_position'] = current_time
        session['last_update'] = time.time()
        
        # 计算当前字符索引
        current_char_index = -1
        for i, timestamp in enumerate(session['char_timestamps']):
            if (current_time >= timestamp.get('start_time', 0) and 
                current_time < timestamp.get('end_time', float('inf'))):
                current_char_index = i
                break
        
        # 检查字符变化
        if current_char_index != session['current_char_index']:
            session['current_char_index'] = current_char_index
            
            # 记录字符变化事件
            self._add_sync_event(session_id, 'character_changed', {
                'char_index': current_char_index,
                'current_time': current_time,
                'char': session['char_timestamps'][current_char_index]['char'] if current_char_index >= 0 else None
            })
        
        # 计算进度
        total_duration = session['char_timestamps'][-1].get('end_time', 0) if session['char_timestamps'] else 0
        progress = (current_time / total_duration * 100) if total_duration > 0 else 0
        
        position_info = {
            'session_id': session_id,
            'current_char_index': current_char_index,
            'current_time': current_time,
            'progress': min(100, max(0, progress)),
            'status': session['status'],
            'source': source,
            'timestamp': time.time()
        }
        
        return position_info
    
    def add_participant(self, session_id: str, user_id: str, socket_id: str) -> bool:
        """添加会话参与者"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # 检查是否已经是参与者
            existing = next((p for p in session['participants'] if p['user_id'] == user_id), None)
            if existing:
                existing['socket_id'] = socket_id
                existing['last_active'] = time.time()
            else:
                session['participants'].append({
                    'user_id': user_id,
                    'socket_id': socket_id,
                    'joined_at': time.time(),
                    'last_active': time.time()
                })
            
            print(f"用户 {user_id} 加入会话 {session_id}")
            return True
        return False
    
    def remove_participant(self, session_id: str, user_id: str) -> bool:
        """移除会话参与者"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['participants'] = [p for p in session['participants'] if p['user_id'] != user_id]
            print(f"用户 {user_id} 离开会话 {session_id}")
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """获取所有活动会话ID"""
        return list(self.active_sessions.keys())
    
    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            print(f"清理会话: {session_id}")
            return True
        return False
    
    def _add_sync_event(self, session_id: str, event_type: str, event_data: Dict):
        """添加同步事件记录"""
        if session_id in self.active_sessions:
            event = {
                'type': event_type,
                'data': event_data,
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat()
            }
            self.active_sessions[session_id]['sync_events'].append(event)
            
            # 限制事件数量，避免内存泄漏
            if len(self.active_sessions[session_id]['sync_events']) > 1000:
                self.active_sessions[session_id]['sync_events'] = \
                    self.active_sessions[session_id]['sync_events'][-500:]

# 创建全局同步管理器实例
sync_manager = RealtimeSyncManager()

def init_socketio(app):
    """初始化SocketIO"""
    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
    
    @socketio.on('connect')
    def on_connect():
        """客户端连接事件"""
        client_id = request.sid
        user_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        
        print(f"客户端连接: {client_id} (IP: {user_ip})")
        
        # 发送连接确认
        emit('connected', {
            'client_id': client_id,
            'timestamp': time.time(),
            'message': '连接成功'
        })
    
    @socketio.on('disconnect')
    def on_disconnect():
        """客户端断开连接事件"""
        client_id = request.sid
        print(f"客户端断开连接: {client_id}")
        
        # 从所有会话中移除该客户端
        for session_id in list(sync_manager.active_sessions.keys()):
            session = sync_manager.active_sessions[session_id]
            session['participants'] = [
                p for p in session['participants'] 
                if p.get('socket_id') != client_id
            ]
    
    @socketio.on('join_sync')
    def on_join_sync(data):
        """加入同步会话"""
        try:
            session_id = data.get('session_id')
            user_id = data.get('user_id', request.sid)
            
            if not session_id:
                emit('error', {'message': '缺少session_id'})
                return
            
            # 加入房间
            join_room(session_id)
            
            # 添加到会话参与者
            sync_manager.add_participant(session_id, user_id, request.sid)
            
            # 获取会话信息
            session = sync_manager.get_session(session_id)
            
            if session:
                emit('sync_joined', {
                    'session_id': session_id,
                    'user_id': user_id,
                    'text': session['text'],
                    'char_timestamps': session['char_timestamps'],
                    'current_position': session['current_position'],
                    'current_char_index': session['current_char_index'],
                    'status': session['status']
                })
                
                # 通知其他参与者
                emit('participant_joined', {
                    'user_id': user_id,
                    'participants_count': len(session['participants'])
                }, room=session_id, include_self=False)
                
                print(f"用户 {user_id} 加入同步会话 {session_id}")
            else:
                emit('error', {'message': '会话不存在'})
                
        except Exception as e:
            print(f"加入同步会话错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('leave_sync')
    def on_leave_sync(data):
        """离开同步会话"""
        try:
            session_id = data.get('session_id')
            user_id = data.get('user_id', request.sid)
            
            if session_id:
                # 离开房间
                leave_room(session_id)
                
                # 从会话中移除参与者
                sync_manager.remove_participant(session_id, user_id)
                
                # 通知其他参与者
                emit('participant_left', {
                    'user_id': user_id
                }, room=session_id)
                
                emit('sync_left', {'session_id': session_id})
                print(f"用户 {user_id} 离开同步会话 {session_id}")
                
        except Exception as e:
            print(f"离开同步会话错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('create_sync')
    def on_create_sync(data):
        """创建同步会话"""
        try:
            text = data.get('text', '')
            char_timestamps = data.get('char_timestamps', [])
            user_id = data.get('user_id', request.sid)
            
            if not text or not char_timestamps:
                emit('error', {'message': '缺少文本或时间戳数据'})
                return
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 创建会话
            success = sync_manager.create_session(session_id, text, char_timestamps, user_id)
            
            if success:
                # 自动加入会话
                join_room(session_id)
                sync_manager.add_participant(session_id, user_id, request.sid)
                
                emit('sync_created', {
                    'session_id': session_id,
                    'text': text,
                    'char_timestamps': char_timestamps,
                    'creator': user_id
                })
                
                print(f"创建同步会话: {session_id}")
            else:
                emit('error', {'message': '创建会话失败'})
                
        except Exception as e:
            print(f"创建同步会话错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('start_sync')
    def on_start_sync(data):
        """开始同步"""
        try:
            session_id = data.get('session_id')
            
            if not session_id:
                emit('error', {'message': '缺少session_id'})
                return
            
            success = sync_manager.start_session(session_id)
            
            if success:
                session = sync_manager.get_session(session_id)
                
                # 通知所有参与者开始同步
                socketio.emit('sync_started', {
                    'session_id': session_id,
                    'start_time': session['start_time'],
                    'text': session['text'],
                    'char_timestamps': session['char_timestamps']
                }, room=session_id)
                
                print(f"开始同步会话: {session_id}")
            else:
                emit('error', {'message': '启动同步失败'})
                
        except Exception as e:
            print(f"开始同步错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('pause_sync')
    def on_pause_sync(data):
        """暂停同步"""
        try:
            session_id = data.get('session_id')
            
            success = sync_manager.pause_session(session_id)
            
            if success:
                socketio.emit('sync_paused', {
                    'session_id': session_id,
                    'pause_time': time.time()
                }, room=session_id)
                
                print(f"暂停同步会话: {session_id}")
                
        except Exception as e:
            print(f"暂停同步错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('resume_sync')
    def on_resume_sync(data):
        """恢复同步"""
        try:
            session_id = data.get('session_id')
            
            success = sync_manager.resume_session(session_id)
            
            if success:
                session = sync_manager.get_session(session_id)
                
                socketio.emit('sync_resumed', {
                    'session_id': session_id,
                    'resume_time': time.time(),
                    'adjusted_start_time': session['start_time']
                }, room=session_id)
                
                print(f"恢复同步会话: {session_id}")
                
        except Exception as e:
            print(f"恢复同步错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('sync_position')
    def on_sync_position(data):
        """同步位置更新"""
        try:
            session_id = data.get('session_id')
            current_time = data.get('current_time', 0)
            user_id = data.get('user_id', request.sid)
            
            # 更新位置
            position_info = sync_manager.update_position(session_id, current_time, 'client')
            
            if position_info:
                # 广播位置更新（排除发送者）
                emit('position_update', position_info, room=session_id, include_self=False)
                
                # 如果字符发生变化，发送特殊事件
                if 'character_changed' in [e['type'] for e in sync_manager.get_session(session_id)['sync_events'][-5:]]:
                    emit('character_changed', {
                        'session_id': session_id,
                        'char_index': position_info['current_char_index'],
                        'current_time': current_time
                    }, room=session_id)
                
        except Exception as e:
            print(f"同步位置更新错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('stop_sync')
    def on_stop_sync(data):
        """停止同步"""
        try:
            session_id = data.get('session_id')
            
            success = sync_manager.stop_session(session_id)
            
            if success:
                session = sync_manager.get_session(session_id)
                
                socketio.emit('sync_stopped', {
                    'session_id': session_id,
                    'end_time': session.get('end_time'),
                    'duration': session.get('end_time', 0) - session.get('start_time', 0) if session.get('start_time') else 0
                }, room=session_id)
                
                print(f"停止同步会话: {session_id}")
                
        except Exception as e:
            print(f"停止同步错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('get_session_info')
    def on_get_session_info(data):
        """获取会话信息"""
        try:
            session_id = data.get('session_id')
            session = sync_manager.get_session(session_id)
            
            if session:
                emit('session_info', {
                    'session_id': session_id,
                    'text': session['text'],
                    'status': session['status'],
                    'participants_count': len(session['participants']),
                    'current_position': session['current_position'],
                    'current_char_index': session['current_char_index'],
                    'created_at': session['created_at'].isoformat()
                })
            else:
                emit('error', {'message': '会话不存在'})
                
        except Exception as e:
            print(f"获取会话信息错误: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('ping')
    def on_ping():
        """心跳检测"""
        emit('pong', {'timestamp': time.time()})
    
    return socketio

# 使用示例
if __name__ == '__main__':
    from flask import Flask
    
    app = Flask(__name__)
    socketio = init_socketio(app)
    
    print("WebSocket同步服务器启动")
    print("测试地址: http://localhost:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
