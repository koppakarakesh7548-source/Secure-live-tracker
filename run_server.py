import os
import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wsgi import application
from waitress import serve

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    print("=" * 60, flush=True)
    print("  SECURE LIVE TRACKER — Production WSGI Server (Waitress)", flush=True)
    print(f"  Status: Active", flush=True)
    print(f"  Local URL:  http://{host}:{port}", flush=True)
    print(f"  Admin URL:  http://{host}:{port}/login", flush=True)
    print("=" * 60, flush=True)
    serve(application, host=host, port=port, threads=8)
