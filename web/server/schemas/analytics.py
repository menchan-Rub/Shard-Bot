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

class CommandStat(BaseModel):
    name: str
    count: int

class DailyActivity(BaseModel):
    date: str
    messages: int
    users: int

class GuildInfo(BaseModel):
    id: str
    name: str
    icon: str | None
    member_count: int
    owner_id: str

class GuildStatistics(BaseModel):
    message_count: int
    active_users: int
    top_commands: List[CommandStat]
    daily_activity: List[DailyActivity]

class GuildStats(BaseModel):
    guild_info: GuildInfo
    stats: GuildStatistics

    class Config:
        from_attributes = True 