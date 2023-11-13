from dataclasses import dataclass, field
from typing import Optional

from led_matrix.animation.abstract import AnimationSettings


@dataclass(kw_only=True)
class CronStructure:
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    week: Optional[str] = None
    day_of_week: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    second: Optional[str] = None


@dataclass(kw_only=True)
class ScheduleEntry:
    job_id: Optional[str] = None
    cron_structure: CronStructure = field(default_factory=CronStructure)
    animation_name: str
    animation_settings: AnimationSettings
