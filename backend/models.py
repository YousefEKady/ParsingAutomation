from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class LeakEntry(BaseModel):
    id: Optional[str]
    software: Optional[str]
    url: Optional[str]
    username: Optional[str]
    password: Optional[str]
    date: Optional[datetime]
    extra: Optional[Dict[str, str]] = None

class UploadResponse(BaseModel):
    inserted_rows: int
    details: Optional[List[LeakEntry]]

class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    results: List[LeakEntry] 