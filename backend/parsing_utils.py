import os
import re
import json
import zipfile
import rarfile
import py7zr
from typing import List
import pandas as pd
from difflib import get_close_matches

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
    # Lower cutoff, try partial/inclusion matches
    columns_lower = [c.lower() for c in columns]
    for target in targets:
        # Fuzzy match
        match = get_close_matches(target, columns_lower, n=1, cutoff=cutoff)
        if match:
            return columns[columns_lower.index(match[0])]
        # Partial/inclusion match
        for col in columns:
            if target in col.lower():
                return col
    return None

def detect_email_column(df):
    # Try to find a column with email-like values
    for col in df.columns:
        if df[col].astype(str).str.contains(r'@', na=False).sum() > 0:
            return col
    return None

def parse_leaks_from_table(df) -> List[dict]:
    leaks = []
    columns = list(df.columns)
    columns_lower = [c.lower() for c in columns]
    software_col = fuzzy_column(columns, ['software', 'soft', 'app', 'browser', 'platform', 'source'])
    url_col = fuzzy_column(columns, ['url', 'host', 'website', 'site', 'link', 'profile_url', 'profile'])
    username_col = fuzzy_column(columns, ['username', 'user', 'login', 'email', 'mail', 'account', 'name'])
    password_col = fuzzy_column(columns, ['password', 'pass', 'pwd', 'hash', 'pwd_hash'])
    # If username_col not found, try to detect email column by value
    if not username_col:
        username_col = detect_email_column(df)
    for _, row in df.iterrows():
        leak = {}
        # Always save all columns
        for col in columns:
            leak[col] = row.get(col, '')
        # Try to map standard fields for searchability
        leak['software'] = row.get(software_col, 'LinkedIn') if software_col else 'LinkedIn'
        leak['url'] = row.get(url_col, '') if url_col else ''
        leak['username'] = row.get(username_col, '') if username_col else ''
        leak['password'] = row.get(password_col, '') if password_col else ''
        # Accept if at least two non-empty fields (to avoid empty rows)
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
    # Matches blocks like:
    # URL: ...\nUsername: ...\nPassword: ...\nApplication: ...\n===============
    block_pattern = re.compile(
        r"URL:\s*(?P<url>.+?)\s*\nUsername:\s*(?P<username>.+?)\s*\nPassword:\s*(?P<password>.+?)\s*\nApplication:\s*(?P<software>.+?)\s*\n=+",
        re.DOTALL | re.IGNORECASE
    )
    leaks = []
    for match in block_pattern.finditer(text):
        leak = match.groupdict()
        leaks.append(leak)
    return leaks

def extract_and_parse(file_path: str) -> List[dict]:
    leaks = []
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".zip":
        with zipfile.ZipFile(file_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    content = f.read().decode(errors='ignore')
                    if name.endswith('.json'):
                        leaks.extend(parse_leaks_from_json(content))
                    else:
                        leaks.extend(parse_leaks_from_text(content))
                        leaks.extend(parse_leaks_from_custom_blocks(content))
    elif ext == ".rar":
        with rarfile.RarFile(file_path) as rf:
            for name in rf.namelist():
                with rf.open(name) as f:
                    content = f.read().decode(errors='ignore')
                    if name.endswith('.json'):
                        leaks.extend(parse_leaks_from_json(content))
                    else:
                        leaks.extend(parse_leaks_from_text(content))
                        leaks.extend(parse_leaks_from_custom_blocks(content))
    elif ext == ".7z":
        with py7zr.SevenZipFile(file_path, mode='r') as z:
            for name, bio in z.readall().items():
                content = bio.read().decode(errors='ignore')
                if name.endswith('.json'):
                    leaks.extend(parse_leaks_from_json(content))
                else:
                    leaks.extend(parse_leaks_from_text(content))
                    leaks.extend(parse_leaks_from_custom_blocks(content))
    elif ext == ".json":
        with open(file_path, 'r', encoding='utf-8') as f:
            leaks.extend(parse_leaks_from_json(f.read()))
    elif ext in [".xlsx", ".xls"]:
        leaks.extend(parse_leaks_from_excel(file_path))
    elif ext == ".csv":
        leaks.extend(parse_leaks_from_csv(file_path))
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            leaks.extend(parse_leaks_from_text(content))
            leaks.extend(parse_leaks_from_custom_blocks(content))
    return leaks 