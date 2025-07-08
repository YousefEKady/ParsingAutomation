import os
import re
import json
import zipfile
import rarfile
import py7zr
from typing import List
import pandas as pd
from difflib import get_close_matches
import shutil
import asyncio

def parse_leaks_from_text(text: str) -> List[dict]:
    leak_pattern = re.compile(
        r"SOFT:\s*(?P<software>.+?)\s*\n(?:URL|HOST):\s*(?P<url>.+?)\s*\nUSER:\s*(?P<username>.+?)\s*\nPASS:\s*(?P<password>.+?)(?:\n|$)",
        re.DOTALL | re.IGNORECASE
    )
    leaks = []
    for match in leak_pattern.finditer(text):
        leaks.append(match.groupdict())
    return leaks

def parse_leaks_from_json(data: str) -> List[dict]:
    try:
        items = json.loads(data)
        if isinstance(items, list):
            return items
    except Exception:
        pass
    return []

def fuzzy_column(columns, targets, cutoff=0.4):
    columns_lower = [c.lower() for c in columns]
    for target in targets:
        match = get_close_matches(target, columns_lower, n=1, cutoff=cutoff)
        if match:
            return columns[columns_lower.index(match[0])]
        for col in columns:
            if target in col.lower():
                return col
    return None

def detect_email_column(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(r'@', na=False).sum() > 0:
            return col
    return None

def parse_leaks_from_table(df) -> List[dict]:
    leaks = []
    columns = list(df.columns)
    software_col = fuzzy_column(columns, ['software', 'soft', 'app', 'browser', 'platform', 'source'])
    url_col = fuzzy_column(columns, ['url', 'host', 'website', 'site', 'link', 'profile_url', 'profile'])
    username_col = fuzzy_column(columns, ['username', 'user', 'login', 'email', 'mail', 'account', 'name'])
    password_col = fuzzy_column(columns, ['password', 'pass', 'pwd', 'hash', 'pwd_hash'])

    if not username_col:
        username_col = detect_email_column(df)

    for _, row in df.iterrows():
        leak = {}
        for col in columns:
            leak[col] = row.get(col, '')
        leak['software'] = row.get(software_col, 'LinkedIn') if software_col else 'LinkedIn'
        leak['url'] = row.get(url_col, '') if url_col else ''
        leak['username'] = row.get(username_col, '') if username_col else ''
        leak['password'] = row.get(password_col, '') if password_col else ''
        non_empty = sum(1 for v in leak.values() if str(v).strip())
        if non_empty >= 2:
            leaks.append(leak)
    return leaks

def parse_leaks_from_excel(file_path: str) -> List[dict]:
    try:
        df = pd.read_excel(file_path)
        return parse_leaks_from_table(df)
    except Exception:
        return []

def parse_leaks_from_csv(file_path: str) -> List[dict]:
    try:
        df = pd.read_csv(file_path)
        return parse_leaks_from_table(df)
    except Exception:
        return []

def parse_leaks_from_custom_blocks(text: str) -> List[dict]:
    block_pattern = re.compile(
        r"URL:\s*(?P<url>.+?)\s*\nUsername:\s*(?P<username>.+?)\s*\nPassword:\s*(?P<password>.+?)\s*\nApplication:\s*(?P<software>.+?)\s*\n=+",
        re.DOTALL | re.IGNORECASE
    )
    leaks = []
    for match in block_pattern.finditer(text):
        leaks.append(match.groupdict())
    return leaks

def _parse_file_by_ext(file_path: str) -> List[dict]:
    leaks = []
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".json":
        with open(file_path, 'r', encoding='utf-8') as f:
            leaks.extend(parse_leaks_from_json(f.read()))
    elif ext in [".xlsx", ".xls"]:
        leaks.extend(parse_leaks_from_excel(file_path))
    elif ext == ".csv":
        leaks.extend(parse_leaks_from_csv(file_path))
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                leaks.extend(parse_leaks_from_text(content))
                leaks.extend(parse_leaks_from_custom_blocks(content))
        except Exception:
            pass
    return leaks

async def _parse_file_async(file_path: str) -> List[dict]:
    return _parse_file_by_ext(file_path)

async def extract_and_parse(file_path: str, password: str = None) -> List[dict]:
    leaks = []
    ext = os.path.splitext(file_path)[1].lower()
    temp_dir = None
    try:
        if ext in [".zip", ".rar", ".7z"]:
            temp_dir = tempfile.mkdtemp()
            if ext == ".zip":
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(temp_dir)
            elif ext == ".rar":
                try:
                    with rarfile.RarFile(file_path, pwd=password.encode() if password else None) as rf:
                        rf.extractall(temp_dir)
                except rarfile.RarWrongPassword:
                    print(f"Wrong password for RAR file: {file_path}")
                    return []
                except Exception as e:
                    print(f"Error extracting RAR file {file_path}: {e}")
                    return []
            elif ext == ".7z":
                with py7zr.SevenZipFile(file_path, mode='r') as z:
                    z.extractall(path=temp_dir)

            tasks = []
            for root, dirs, files in os.walk(temp_dir):
                for name in files:
                    fpath = os.path.join(root, name)
                    tasks.append(_parse_file_async(fpath))

            results = await asyncio.gather(*tasks)
            for r in results:
                leaks.extend(r)

        else:
            leaks.extend(_parse_file_by_ext(file_path))

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    return leaks
