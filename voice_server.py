#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""语音匹配服务端 - 打开浏览器 http://localhost:8765 即可使用"""
import json, re, sys, io, os, time, tempfile, webbrowser, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.chdir('E:/claude')
print(' 预热引擎...')
from voice_matcher import match, generate
_ = match('预热')
print(' 引擎就绪')

from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8765
CACHE = {}

class API(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open('voice_asr.html', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/status':
            self.send_json({'status':'ok','templates':183})
        else:
            self.send_json({'error':'not found'}, 404)

    def do_POST(self):
        if self.path == '/api/match':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            text = data.get('text', '')

            # 缓存命中（同一句话不重复算）
            if text in CACHE:
                result = CACHE[text]
            else:
                top5, locked = match(text)
                result = {
                    'top5': [{'rid':m['rid'],'discname':m['discname'],
                              'discgroup':m['discgroup'],'score':m['score']} for m in top5],
                    'locked': None
                }
                if locked:
                    r = generate(locked)
                    result['locked'] = {
                        'rid':r['rid'],'discname':r['discname'],'discgroup':r['discgroup'],
                        'tpl_hint':r['tpl_hint'],'suggestion':r['suggestion'],
                        'full_report':r['full_report'],'confidence':r['confidence']
                    }
                CACHE[text] = result
                if len(CACHE) > 200:
                    CACHE.clear()

            self.send_json(result)
        else:
            self.send_json({'error':'not found'}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, fmt, *args):
        pass

# 自动打开浏览器
import threading as t
t.Thread(target=lambda:(time.sleep(1.5),webbrowser.open(f'http://localhost:{PORT}')),daemon=True).start()

print('')
print('  超声语音报告系统')
print('  启动成功！')
print(f'')
print(f'  浏览器自动打开: http://localhost:{PORT}')
print(f'')
print(f'  功能：')
print(f'    - 按住说话，松开识别')
print(f'    - 一边说一边出结果（实时）')
print(f'    - 超85%自动锁定，生成完整报告')
print(f'')
print(f'  按 Ctrl+C 停止')
print()

HTTPServer(('0.0.0.0', PORT), API).serve_forever()
