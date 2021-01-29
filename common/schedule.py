from animation.abstract import AnimationSettingsStructure
from common.structure import InitializableStructure, Structure


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

    @staticmethod
    def as_recursive_dict(self_obj):
        self_dict = dict(self_obj)
        for k, v in self_dict.items():
            if isinstance(v, Structure):
                self_dict[k] = ScheduleEntry.as_recursive_dict(v)

        return self_dict
