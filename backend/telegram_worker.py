import os
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
import tempfile
import json
import uuid
from backend.clickhouse_util import get_clickhouse_client
from backend.parsing_utils import extract_and_parse
import asyncio
import re

# Telegram API credentials
api_id = int(os.getenv('TG_API_ID', '24451053'))
api_hash = os.getenv('TG_API_HASH', '53c5b47488d256696d17fee1ab8c82c7')
session_name = os.getenv('TG_SESSION', 'session_name')
target_channels = [
    int(os.getenv('TG_CHANNEL_ID', '-1001711284206')),
    -1001585778611,
]
WORKER_COUNT = int(os.getenv('TG_WORKER_COUNT', 4))

worker_status = {
    'running': False,
    'last_checked': None,
    'last_file': None,
    'inserted_leaks': 0,
    'errors': []
}

def get_worker_status():
    return worker_status

def get_last_msg_id_file(channel_id):
    return f'last_message_id_{channel_id}.txt'

def load_last_message_id(channel_id):
    fname = get_last_msg_id_file(channel_id)
    try:
        with open(fname, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_last_message_id(channel_id, msg_id):
    fname = get_last_msg_id_file(channel_id)
    with open(fname, 'w') as f:
        f.write(str(msg_id))

async def file_worker(queue):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        message, file_path, password = item
        try:
            print(f"[Parsing] Started: {file_path}")
            leaks = extract_and_parse(file_path, password=password)
            print(f"[Parsing] Finished: {file_path}")
            if leaks:
                print(f"[Parsing] Found {len(leaks)} leaks in: {file_path}")
                base_name = os.path.basename(file_path)
                json_name = f"{os.path.splitext(base_name)[0]}_{message.id}.json"
                json_path = os.path.join('uploads', json_name)
                with open(json_path, 'w', encoding='utf-8') as jf:
                    json.dump(leaks, jf, indent=2, ensure_ascii=False)

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
                print(f"[DB] Inserted {len(clickhouse_data)} leaks from {file_path}")
            else:
                print(f"[Parsing] No leaks found in: {file_path}")
        except Exception as e:
            print(f"[ERROR] {file_path}: {e}")
            worker_status['errors'].append(f"Error processing {file_path}: {e}")
        finally:
            os.remove(file_path)
            queue.task_done()

async def process_channel(target, client):
    try:
        print(f"[DEBUG] Getting channel entity for {target}...")
        channel = await client.get_entity(target)
        print(f"[INFO] Downloading from: {getattr(channel, 'title', str(target))} (ID: {getattr(channel, 'id', str(target))})")
    except Exception as e:
        print(f"[ERROR] Failed to get channel {target}: {e}")
        import traceback
        traceback.print_exc()
        return

    queue = asyncio.Queue()
    workers = [asyncio.create_task(file_worker(queue)) for _ in range(WORKER_COUNT)]

    last_msg_id = load_last_message_id(getattr(channel, 'id', str(target)))
    total_files = 0
    max_msg_id = last_msg_id
    print(f"[DEBUG] Counting files in channel {getattr(channel, 'title', str(target))}...")
    async for message in client.iter_messages(channel):
        if message.id > last_msg_id and message.media and isinstance(message.media, MessageMediaDocument):
            total_files += 1

    print(f"[INFO] Found {total_files} new files in {getattr(channel, 'title', str(target))}.")
    processed = 0
    async for message in client.iter_messages(channel):
        if message.id > last_msg_id and message.media and isinstance(message.media, MessageMediaDocument):
            file_name = message.file.name if hasattr(message, 'file') and hasattr(message.file, 'name') else 'unknown'
            processed += 1
            print(f"[INFO] Downloading file {processed} of {total_files} from {getattr(channel, 'title', str(target))}: {file_name}")
            password = None
            if message.message:
                pw_match = re.search(r'Password[:：]?\s*([@\w\d_\-]+)', message.message, re.IGNORECASE)
                if pw_match:
                    password = pw_match.group(1)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                file_path = await message.download_media(file=tmp.name)
                print(f"[INFO] Downloaded: {file_path}")
                worker_status['last_file'] = file_path
                await queue.put((message, file_path, password))
            if message.id > max_msg_id:
                max_msg_id = message.id

    print(f"[DEBUG] All files queued for channel {getattr(channel, 'title', str(target))}.")
    for _ in range(WORKER_COUNT):
        await queue.put(None)
    await queue.join()
    for w in workers:
        await w
    save_last_message_id(getattr(channel, 'id', str(target)), max_msg_id)
    print(f"[DEBUG] Finished processing channel {getattr(channel, 'title', str(target))}.")

async def run_telegram_worker():
    print("[Telegram Worker] Worker started!")
    worker_status['running'] = True
    worker_status['last_checked'] = str(datetime.utcnow())
    worker_status['inserted_leaks'] = 0
    worker_status['errors'] = []

    client = TelegramClient(session_name, api_id, api_hash)
    print("[DEBUG] Awaiting client.start()...")
    await client.start()
    print("[DEBUG] Logged in to Telegram.")
    print(f"[DEBUG] Target channels: {target_channels}")

    channel_tasks = [asyncio.create_task(process_channel(target, client)) for target in target_channels]
    await asyncio.gather(*channel_tasks)

    await client.disconnect()
    worker_status['running'] = False
    worker_status['last_checked'] = str(datetime.utcnow())
    print("All downloads and insertions complete.")
