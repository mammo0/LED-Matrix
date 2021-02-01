from animation.abstract import _AnimationSettingsStructure
from common.structure import TypedStructure, Structure


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
    CRON_STRUCTURE = CronStructure()
    ANIMATION_SETTINGS = _AnimationSettingsStructure()

    @staticmethod
    def as_recursive_dict(self_obj):
        self_dict = dict(self_obj)
        for k, v in self_dict.items():
            if isinstance(v, Structure):
                self_dict[k] = ScheduleEntry.as_recursive_dict(v)

        return self_dict
