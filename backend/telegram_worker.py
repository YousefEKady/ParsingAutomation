import os
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
import tempfile
import zipfile
import rarfile
import py7zr
import json
import uuid
from backend.clickhouse_util import get_clickhouse_client
from backend.parsing_utils import parse_leaks_from_text, parse_leaks_from_json, extract_and_parse

# Telegram API credentials (replace with your own or use env vars)
api_id = os.getenv('TG_API_ID', '24451053')
api_hash = os.getenv('TG_API_HASH', '53c5b47488d256696d17fee1ab8c82c7')
session_name = os.getenv('TG_SESSION', 'session_name')
target_channel_id = int(os.getenv('TG_CHANNEL_ID', '-1001711284206'))

worker_status = {
    'running': False,
    'last_checked': None,
    'last_file': None,
    'inserted_leaks': 0,
    'errors': []
}

def get_worker_status():
    return worker_status

async def run_telegram_worker():
    print("[Telegram Worker] Worker started!")
    worker_status['running'] = True
    worker_status['last_checked'] = str(datetime.utcnow())
    worker_status['inserted_leaks'] = 0
    worker_status['errors'] = []
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("Logged in to Telegram.")
    try:
        channel = await client.get_entity(target_channel_id)
        print(f"Downloading from: {channel.title} (ID: {target_channel_id})")
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get channel: {error_msg}")
        # Only add to worker_status['errors'] if not PeerChannel not found
        if 'PeerChannel' not in error_msg:
            worker_status['errors'].append(f"Failed to get channel: {error_msg}")
        worker_status['running'] = False
        await client.disconnect()
        return
    messages_by_day = {}
    async for message in client.iter_messages(channel):
        if message.media and isinstance(message.media, MessageMediaDocument):
            date_folder = message.date.strftime('%Y-%m-%d')
            if date_folder not in messages_by_day:
                messages_by_day[date_folder] = []
            messages_by_day[date_folder].append(message)
    print(f"Found {sum(len(msgs) for msgs in messages_by_day.values())} files.")
    for date_folder, messages in messages_by_day.items():
        for message in messages:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                file_path = await message.download_media(file=tmp.name)
                print(f"Downloaded: {file_path}")
                worker_status['last_file'] = file_path
                leaks = extract_and_parse(file_path)
                os.remove(file_path)
                if not leaks:
                    print(f"No leaks found in {file_path}")
                    continue
                # Insert into ClickHouse
                client_db = get_clickhouse_client()
                now = datetime.utcnow()
                clickhouse_data = []
                for leak in leaks:
                    clickhouse_data.append({
                        'id': str(uuid.uuid4()),
                        'software': leak.get('software', ''),
                        'url': leak.get('url', ''),
                        'username': leak.get('username', ''),
                        'password': leak.get('password', ''),
                        'date': now,
                        **{k: v for k, v in leak.items() if k not in ['software', 'url', 'username', 'password']}
                    })
                table_columns = set(row[0] for row in client_db.execute(f"DESCRIBE TABLE Leaked_DB"))
                all_columns = set()
                for row in clickhouse_data:
                    all_columns.update(row.keys())
                for col in all_columns - table_columns:
                    if col != 'id':
                        client_db.execute(f"ALTER TABLE Leaked_DB ADD COLUMN IF NOT EXISTS {col} String")
                all_columns = list(all_columns)
                insert_data = []
                for row in clickhouse_data:
                    insert_data.append(tuple(row.get(col, '') if col != 'date' else row.get(col) for col in all_columns))
                client_db.execute(
                    f"INSERT INTO Leaked_DB ({', '.join(all_columns)}) VALUES",
                    insert_data
                )
                worker_status['inserted_leaks'] += len(clickhouse_data)
                print(f"Inserted {len(clickhouse_data)} leaks from {file_path}")
    await client.disconnect()
    worker_status['running'] = False
    worker_status['last_checked'] = str(datetime.utcnow())
    print("All downloads and insertions complete.") 