#!/usr/bin/env python3
"""
Portfolio Admin Server
Usage: python3 admin-server.py
Then open: http://localhost:3000/admin.html
"""

import http.server
import json
import os
import io

PORT = 3000
DIR = os.path.dirname(os.path.abspath(__file__))

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_POST(self):
        if self.path == '/api/save-projects':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                with open(os.path.join(DIR, 'projects.json'), 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                self._json_response(200, {'ok': True})
            except Exception as e:
                self._json_response(500, {'error': str(e)})

        elif self.path == '/api/upload-media':
            try:
                content_type = self.headers.get('Content-Type', '')
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)

                # Parse multipart manually (no cgi module needed)
                boundary = content_type.split('boundary=')[1].encode()
                parts = body.split(b'--' + boundary)

                file_data = None
                dest_path = None

                for part in parts:
                    if b'name="file"' in part:
                        # Extract file content after \r\n\r\n
                        header_end = part.find(b'\r\n\r\n')
                        if header_end != -1:
                            file_data = part[header_end + 4:].rstrip(b'\r\n--')
                    elif b'name="path"' in part:
                        header_end = part.find(b'\r\n\r\n')
                        if header_end != -1:
                            dest_path = part[header_end + 4:].rstrip(b'\r\n--').decode().strip()

                if not file_data or not dest_path:
                    self._json_response(400, {'error': 'Missing file or path'})
                    return

                full_path = os.path.normpath(os.path.join(DIR, dest_path))
                if not full_path.startswith(DIR):
                    self._json_response(403, {'error': 'Path outside project'})
                    return

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(file_data)
                self._json_response(200, {'ok': True, 'path': dest_path})
            except Exception as e:
                self._json_response(500, {'error': str(e)})
        elif self.path == '/api/commit':
            import subprocess
            try:
                subprocess.run(['git', 'add', 'projects.json'], cwd=DIR, check=True)
                subprocess.run(['git', 'commit', '-m', 'Update projects (admin tool)'], cwd=DIR, check=True)
                self._json_response(200, {'ok': True})
            except subprocess.CalledProcessError as e:
                self._json_response(200, {'ok': False, 'message': 'Nothing to commit or git error'})
            except Exception as e:
                self._json_response(500, {'error': str(e)})

        elif self.path == '/api/boats-lock':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            lock_file = os.path.join(DIR, '.boats-locked')
            if body.get('locked'):
                open(lock_file, 'w').write('1')
            else:
                if os.path.exists(lock_file): os.remove(lock_file)
            self._json_response(200, {'ok': True, 'locked': body.get('locked')})

        elif self.path == '/api/boats-lock-status':
            locked = os.path.exists(os.path.join(DIR, '.boats-locked'))
            self._json_response(200, {'locked': locked})

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/api/boats-lock-status':
            locked = os.path.exists(os.path.join(DIR, '.boats-locked'))
            self._json_response(200, {'locked': locked})
        else:
            super().do_GET()

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def end_headers(self):
        # Disable caching so work.html always gets fresh projects.json
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

import webbrowser
import threading

print(f'Portfolio Admin Server running at http://localhost:{PORT}')
print(f'Admin tool: http://localhost:{PORT}/admin.html')
print(f'Boats admin: http://localhost:{PORT}/admin-boats.html')
print(f'Serving from: {DIR}')
print('Press Ctrl+C to stop.\n')

threading.Timer(0.5, lambda: webbrowser.open(f'http://localhost:{PORT}/admin.html')).start()
http.server.HTTPServer(('', PORT), AdminHandler).serve_forever()
