#!/usr/bin/env python3
"""
High-Speed HTTP Streaming Server with Zero-Copy Linux Kernel sendfile support.
"""
import os
import sys
import shutil
import socket
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = Path(__file__).resolve().parent.parent
srv_http_dir = str(BASE_DIR / 'srv' / 'http')

class FastHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=srv_http_dir, **kwargs)

    def copyfile(self, source, outputfile):
        """Zero-copy kernel sendfile streaming for maximum network wire throughput."""
        try:
            in_fd = source.fileno()
            out_fd = outputfile.fileno()
            file_size = os.fstat(in_fd).st_size
            try:
                self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
            except Exception:
                pass
            offset = 0
            while offset < file_size:
                sent = os.sendfile(out_fd, in_fd, offset, 16 * 1024 * 1024)
                if sent == 0:
                    break
                offset += sent
            return
        except Exception:
            pass
        shutil.copyfileobj(source, outputfile, length=1024 * 1024)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(('0.0.0.0', port), FastHandler)
    server.serve_forever()
