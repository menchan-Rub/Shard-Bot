from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

class StatsOverview(BaseModel):
    total_servers: int
    total_users: int
    total_commands: int
    active_users: int

    class Config:
        from_attributes = True

class TimeSeriesData(BaseModel):
    timestamp: datetime
    value: int

class AnalyticsData(BaseModel):
    command_usage: List[TimeSeriesData]
    user_growth: List[TimeSeriesData]
    server_growth: List[TimeSeriesData]
    popular_commands: Dict[str, int]

    class Config:
        from_attributes = True 