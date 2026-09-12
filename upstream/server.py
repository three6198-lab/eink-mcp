"""
Optional remote push server for E-Ink BLE Writer.
Allows updating display content remotely via HTTP API.

Usage:
    pip install fastapi uvicorn
    python server.py

API:
    GET  /api/latest   - Get current content
    POST /api/letter   - Update content (JSON: {text, date})
    GET  /api/version  - Check for updates (returns updated_at)
    GET  /               - Serve the web frontend
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json, os, datetime

app = FastAPI()

DATA_FILE = 'latest_letter.json'

class Note(BaseModel):
    text: str = ''
    date: Optional[str] = None

@app.get('/api/latest')
def get_latest():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {'text': 'Hello, World!', 'date': datetime.date.today().isoformat()}

@app.post('/api/letter')
def update_note(note: Note):
    data = note.model_dump()
    if not data.get('date'):
        data['date'] = datetime.date.today().isoformat()
    data['updated_at'] = datetime.datetime.now().isoformat()
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False)
    return {'status': 'ok', 'data': data}

@app.get('/api/version')
def get_version():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            d = json.load(f)
            return {'updated_at': d.get('updated_at', '')}
    return {'updated_at': ''}

@app.get('/')
def index():
    return FileResponse('eink-ble-writer.html')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8905)