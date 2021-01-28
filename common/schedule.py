from animation.abstract import AnimationSettingsStructure
from common.structure import InitializableStructure


class CronStructure(InitializableStructure):
    YEAR = None
    MONTH = None
    DAY = None
    WEEK = None
    DAY_OF_WEEK = None
    HOUR = None
    MINUTE = None
    SECOND = None


class ScheduleEntry(InitializableStructure):
    JOB_ID = None
    CRON_STRUCTURE = CronStructure()
    ANIMATION_SETTINGS = AnimationSettingsStructure()
