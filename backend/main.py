from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from backend.clickhouse_util import get_clickhouse_client
from backend.models import UploadResponse, SearchRequest, SearchResponse, LeakEntry
import os
import uuid
from datetime import datetime
import shutil
import tempfile
import json
import zipfile
import rarfile
import py7zr
import aiofiles
import re
from typing import List
from backend.telegram_worker import run_telegram_worker, get_worker_status
import asyncio
from backend.parsing_utils import parse_leaks_from_text, parse_leaks_from_json, extract_and_parse
import time

app = FastAPI(title="Leak Parser API", description="API for parsing and searching password leaks.", version="1.0.0")

@app.on_event("startup")
async def start_telegram_worker():
    print("[FastAPI] Starting Telegram worker in background...")
    asyncio.create_task(run_telegram_worker())

@app.get("/health")
def health_check():
    try:
        client = get_clickhouse_client()
        client.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/worker-status")
def worker_status():
    return get_worker_status()

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    # Allow multiple file types
    allowed_exts = {'.txt', '.json', '.zip', '.rar', '.7z', '.xlsx', '.xls', '.csv'}
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"File type {suffix} not allowed.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        with open(temp_path, 'wb') as out:
            shutil.copyfileobj(file.file, out)
    # Parse leaks
    leaks = extract_and_parse(temp_path)
    os.remove(temp_path)
    if not leaks:
        raise HTTPException(status_code=400, detail="No leaks found in file.")
    # Insert into ClickHouse, avoiding duplicates
    client = get_clickhouse_client()
    now = datetime.utcnow()
    clickhouse_data = []
    for leak in leaks:
        software = leak.get('software', '')
        url = leak.get('url', '')
        username = leak.get('username', '')
        password = leak.get('password', '')
        exists = client.execute(
            "SELECT count() FROM Leaked_DB WHERE software=%(software)s AND url=%(url)s AND username=%(username)s AND password=%(password)s",
            {'software': software, 'url': url, 'username': username, 'password': password}
        )[0][0]
        if exists:
            continue  # Skip duplicate
        clickhouse_data.append({
            'id': str(uuid.uuid4()),
            'software': software,
            'url': url,
            'username': username,
            'password': password,
            'date': now,
            **{k: v for k, v in leak.items() if k not in ['software', 'url', 'username', 'password']}
        })
    if not clickhouse_data:
        # Still save the parsed leaks as JSON for download
        json_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        os.makedirs(json_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file.filename))[0]
        json_name = f"{base_name}.json"
        json_path = os.path.join(json_dir, json_name)
        # Handle duplicate file names
        if os.path.exists(json_path):
            json_name = f"{base_name}_{int(time.time())}.json"
            json_path = os.path.join(json_dir, json_name)
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(leaks, jf, indent=2)
        return {"inserted_rows": 0, "details": [], "json_file": f"/uploads/{json_name}"}
    # Ensure columns
    table_columns = set(row[0] for row in client.execute(f"DESCRIBE TABLE Leaked_DB"))
    all_columns = set()
    for row in clickhouse_data:
        all_columns.update(row.keys())
    for col in all_columns - table_columns:
        if col != 'id':
            client.execute(f"ALTER TABLE Leaked_DB ADD COLUMN IF NOT EXISTS {col} String")
    all_columns = list(all_columns)
    insert_data = []
    for row in clickhouse_data:
        insert_data.append(tuple(row.get(col, '') if col != 'date' else row.get(col) for col in all_columns))
    client.execute(
        f"INSERT INTO Leaked_DB ({', '.join(all_columns)}) VALUES",
        insert_data
    )
    # Save the parsed leaks as JSON for download
    json_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    os.makedirs(json_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file.filename))[0]
    json_name = f"{base_name}.json"
    json_path = os.path.join(json_dir, json_name)
    if os.path.exists(json_path):
        json_name = f"{base_name}_{int(time.time())}.json"
        json_path = os.path.join(json_dir, json_name)
    with open(json_path, 'w', encoding='utf-8') as jf:
        json.dump(clickhouse_data, jf, indent=2, default=str)
    return {"inserted_rows": len(clickhouse_data), "details": [LeakEntry(**row) for row in clickhouse_data], "json_file": f"/uploads/{json_name}"}

from difflib import SequenceMatcher

def fuzzy_match(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

@app.post("/search", response_model=SearchResponse)
async def search_leaks(request: SearchRequest):
    query = request.query.strip()
    if not query:
        return SearchResponse(results=[])
    client = get_clickhouse_client()
    columns = [row[0] for row in client.execute(f"DESCRIBE TABLE Leaked_DB")]
    # Get all rows (limit for demo, optimize for production)
    results = client.execute(f"SELECT {', '.join(columns)} FROM Leaked_DB LIMIT 10000")
    formatted = [dict(zip(columns, row)) for row in results]
    # Fuzzy filter
    filtered = []
    for row in formatted:
        # Convert id to string if it's not already
        if 'id' in row and not isinstance(row['id'], str):
            row['id'] = str(row['id'])
        if 'username' in row and fuzzy_match(row['username'], query) > 0.6:
            filtered.append(LeakEntry(**row))
        elif 'url' in row and fuzzy_match(row['url'], query) > 0.6:
            filtered.append(LeakEntry(**row))
        elif 'password' in row and fuzzy_match(row['password'], query) > 0.6:
            filtered.append(LeakEntry(**row))
    return SearchResponse(results=filtered)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=True) 