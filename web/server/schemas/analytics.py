from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

class StatsOverview(BaseModel):
    total_servers: int
    total_users: int
    total_commands: int
    commands_today: int
    new_users_today: int
    active_servers: int

    class Config:
        from_attributes = True

class TimeSeriesData(BaseModel):
    timestamp: datetime
    value: int

class AnalyticsData(BaseModel):
    date: str
    commands: int
    users: int

    class Config:
        from_attributes = True 