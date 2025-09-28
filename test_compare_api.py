#!/usr/bin/env python3
"""
测试比对API的脚本
"""
import requests
import json
import urllib3
import ssl
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建自定义的SSL上下文
class CustomHTTPSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ALL:!DH')  # 禁用Diffie-Hellman密码套件
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

def test_compare_api():
    """测试比对API"""
    # 服务器地址
    url = "https://8.148.200.151:9999/api/compare"
    
    # 测试数据
    test_data = {
        "standard_file_id": "3b73bfaa-b06a-4910-b16e-ca55a0388626",  # 从temp目录中选择一个存在的文件
        "user_file_id": "0bb4fbc4-289c-47ac-981b-f2f900ef40c7",     # 尝试不同的用户音频文件
        "text": "今天天气很好"
    }
    
    print(f"测试比对API: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        # 创建会话并添加自定义HTTPS适配器
        session = requests.Session()
        session.mount('https://', CustomHTTPSAdapter())
        
        response = session.post(
            url, 
            json=test_data,
            headers={'Content-Type': 'application/json'},
            verify=False,  # 忽略SSL证书验证
            timeout=120    # 增加超时时间到120秒
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        except:
            print(f"响应文本: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_compare_api()
