from common.structure import TypedStructure


class CronStructure(TypedStructure):
    YEAR = None
    MONTH = None
    DAY = None
    WEEK = None
    DAY_OF_WEEK = None
    HOUR = None
    MINUTE = None
    SECOND = None


class ScheduleEntry(TypedStructure):
    JOB_ID = None
    CRON_STRUCTURE = CronStructure
    ANIMATION_SETTINGS = None
