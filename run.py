import os
from waitress import serve
from suite import create_app

if __name__ == '__main__':
    app = create_app()
    host = os.getenv('APP_HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '8080'))
    print(f'Open http://{host}:{port} — Ctrl+C stops the application.', flush=True)
    serve(app, host=host, port=port, threads=8, channel_timeout=30)
