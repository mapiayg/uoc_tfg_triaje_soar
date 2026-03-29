# run.py
import os
from dotenv import load_dotenv
from src.listener import app

load_dotenv()

if __name__ == '__main__':
    port = int(os.getenv('LISTENER_PORT', 5000))
    print(f'[SOAR] Listener arrancado en http://0.0.0.0:{port}')
    print(f'[SOAR] Health check: http://localhost:{port}/health')
    print(f'[SOAR] Webhook endpoint: http://localhost:{port}/webhook')
    app.run(host='0.0.0.0', port=port, debug=False)
