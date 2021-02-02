import calendar
from datetime import datetime
from enum import Enum

from bottle import template, static_file, request, redirect
import bottle

from common import RESOURCES_DIR
from common.bottle import BottleCBVMeta, get, post
from common.color import Color
from common.config import Config
from common.schedule import ScheduleEntry, CronStructure
from common.wsgi import CustomWSGIRefServer


# change bottle template path
HTTP_RESOURCES_DIR = RESOURCES_DIR / "http"
bottle.TEMPLATE_PATH = [(HTTP_RESOURCES_DIR / "templates").resolve()]


CRON_DICT = {
    "year": [
                {"value": i,
                 "text": i} for i in range(datetime.now().year, datetime.now().year + 11)
            ],
    "month": [
                {"value": i,
                 "text": calendar.month_name[i]} for i in range(1, 13)
             ],
    "day": [
                {"value": i,
                 "text": i} for i in range(1, 32)
           ],
    "week": [
                {"value": i,
                 "text": i} for i in range(1, 54)
            ],
    "day_of_week": [
                        {"value": i,
                         "text": calendar.day_name[i]} for i in range(0, 7)
                    ],
    "hour": [
                {"value": i,
                 "text": i} for i in range(0, 24)
            ],
    "minute": [
                {"value": i,
                 "text": i} for i in range(0, 60)
              ],
    "second": [
                {"value": i,
                 "text": i} for i in range(0, 60)
              ],
}


class SettingsTabs(Enum):
    main = "Main"
    default_animation = "Default Animation"
    schedule_table = "Schedule Table"


class Input():
    def __init__(self, value):
        self.__type = "text"
        self.__value = value
        self.__step = "1"

        if isinstance(value, bool):
            self.__type = "checkbox"
        elif isinstance(value, int):
            self.__type = "number"
        elif isinstance(value, float):
            self.__type = "number"
            self.__step = "any"
        elif isinstance(value, Color):
            self.__type = "color"
            self.__value = value.hex_value

    @property
    def type(self):
        return self.__type

    @property
    def value(self):
        return self.__value

    @property
    def step(self):
        return self.__step


class HttpServer(metaclass=BottleCBVMeta):
    def __init__(self, main_app):
        self.__main_app = main_app

        self.__js_dir = HTTP_RESOURCES_DIR / "js"
        self.__css_dir = HTTP_RESOURCES_DIR / "css"
        self.__fonts_dir = HTTP_RESOURCES_DIR / "fonts"

        port = self.__main_app.config.get(Config.MAIN.HttpServerPort)
        host = self.__main_app.config.get(Config.MAIN.HttpServerInterfaceIP)

        self.__wsgi_server = CustomWSGIRefServer(host=host, port=port, quiet=True)

    def start(self):
        self.__wsgi_server.start()

    def stop(self):
        self.__wsgi_server.stop()

    def __show_settings(self, tab=SettingsTabs.main):
        return template("settings",
                        active_tab=tab,
                        # provide the main config
                        config=self.__main_app.config,
                        # except the brightness value should be always actual
                        current_brightness=self.__main_app.get_brightness(),
                        # provide the animations
                        animations=self.__main_app.available_animations,
                        default_animation_name=self.__main_app.config.get(Config.DEFAULTANIMATION.Animation),
                        # the scheduled ones
                        schedule_table=self.__main_app.scheduled_animations)

    def __parse_animation_form(self, form):
        animation_name = form.get("selected_animation_name")

        animation_obj = self.__main_app.available_animations[animation_name]

        # create new instance of the animation settings
        animation_settings = animation_obj.default_animation_settings()
        animation_settings.animation_name = animation_name

        # variant
        if animation_obj.animation_variants is not None:
            new_default_animation_variant = form.get(animation_name + "_variant_value")
            animation_settings.variant = new_default_animation_variant

        # parameter
        if animation_obj.animation_parameters is not None:
            new_parameter = {}
            for p_name, parameter in animation_obj.animation_parameters:
                # special treatment for bool values, because if not checked, None is returned, otherwise 'on'
                if isinstance(parameter, bool):
                    new_parameter[p_name] = form.get(animation_name +
                                                     "_parameter_" +
                                                     p_name +
                                                     "_value",
                                                     default=False, type=bool)
                else:
                    new_parameter[p_name] = form.get(animation_name +
                                                     "_parameter_" +
                                                     p_name +
                                                     "_value")

            animation_settings.parameter = new_parameter

        # repeat
        if animation_obj.is_repeat_supported:
            new_default_animation_repeat = form.get(animation_name + "_repeat_value")
            animation_settings.repeat = int(new_default_animation_repeat)

        return animation_settings

    def __parse_cron_form(self, form):
        cron_structure = CronStructure()
        for category in CRON_DICT.keys():
            selected_values = form.get("cron_%s_select_value" % category)

            # validate values
            try:
                [int(val) for val in selected_values.split(",")]
            except Exception:
                continue

            setattr(cron_structure, category.upper(), selected_values)

        entry = ScheduleEntry()
        entry.CRON_STRUCTURE = cron_structure
        entry.ANIMATION_SETTINGS = self.__parse_animation_form(form)

        return entry

    @get("/")
    def index(self):
        return template("index",
                        animations=self.__main_app.available_animations,
                        current_animation_name=self.__main_app.get_current_animation_name())

    @post("/")
    def start_new_animation(self):
        new_animation_settings = self.__parse_animation_form(request.forms)
        self.__main_app.start_animation(animation_settings=new_animation_settings,
                                        # wait until the new animation runs
                                        blocking=True)

        redirect("/")

    @post("/schedule/new")
    def new_schedule_entry(self):
        temp_schedule_entry = ScheduleEntry()
        temp_schedule_entry.ANIMATION_SETTINGS = self.__parse_animation_form(request.forms)

        return template("schedule/entry",
                        animations=self.__main_app.available_animations,
                        entry=temp_schedule_entry)

    @post("/schedule/create")
    def create_schedule_entry(self):
        schedule_entry = self.__parse_cron_form(request.forms)

        # schedule the animation
        self.__main_app.schedule_animation(schedule_entry.CRON_STRUCTURE,
                                           schedule_entry.ANIMATION_SETTINGS)

        redirect("/settings/" + SettingsTabs.schedule_table.name)

    @get("/schedule/edit/<job_id>")
    def edit_schedule_entry(self, job_id):
        table = self.__main_app.scheduled_animations
        for row in table:
            if row.JOB_ID == job_id:
                return template("schedule/entry",
                                animations=self.__main_app.available_animations,
                                entry=row,
                                is_modify=True)

        # show table if no corresponding job could be found
        redirect("/settings/" + SettingsTabs.schedule_table.name)

    @post("/schedule/edit/<job_id>")
    def modify_schedule_entry(self, job_id):
        schedule_entry = self.__parse_cron_form(request.forms)
        schedule_entry.JOB_ID = job_id

        self.__main_app.modify_scheduled_animation(schedule_entry)

        redirect("/settings/" + SettingsTabs.schedule_table.name)

    @get("/schedule/delete/<job_id>")
    def delete_schedule_entry(self, job_id):
        self.__main_app.remove_scheduled_animation(job_id)

        # redirect back to the schedule table
        redirect("/settings/" + SettingsTabs.schedule_table.name)

    @get("/stop-animation")
    def stop_current_animation(self):
        self.__main_app.stop_animation(blocking=True)
        redirect("/")

    @get("/settings")
    def settings(self):
        return self.__show_settings()

    @get("/settings/<tab>")
    def settings_with_pane(self, tab):
        return self.__show_settings(SettingsTabs[tab])

    @post("/settings/<tab>")
    def save_settings(self, tab):
        if SettingsTabs[tab] == SettingsTabs.main:
            brightness = request.forms.get("brightness_value")
            # special treatment for bool values, because if not checked, None is returned, otherwise 'on'
            enable_rest = request.forms.get("enable_rest", default=False, type=bool)
            enable_tpm2net = request.forms.get("enable_tpm2net", default=False, type=bool)

            # save the settings
            self.__main_app.config.set(Config.MAIN.Brightness, brightness)
            self.__main_app.config.set(Config.MAIN.RestServer, enable_rest)
            self.__main_app.config.set(Config.MAIN.TPM2NetServer, enable_tpm2net)
        elif SettingsTabs[tab] == SettingsTabs.default_animation:
            new_default_animation_settings = self.__parse_animation_form(request.forms)

            self.__main_app.config.set(Config.DEFAULTANIMATION.Animation, new_default_animation_settings.animation_name)

            # variant
            self.__main_app.config.set(Config.DEFAULTANIMATION.Variant, new_default_animation_settings.variant)

            # parameter
            self.__main_app.config.set(Config.DEFAULTANIMATION.Parameter,
                                       new_default_animation_settings.parameter)

            # repeat
            self.__main_app.config.set(Config.DEFAULTANIMATION.Repeat, new_default_animation_settings.repeat)

        self.__main_app.config.save()

        # reload the application
        self.__main_app.reload()

        # reload the page
        redirect("/settings/" + tab)

    @get("/settings/reset/<tab>")
    def reset_settings(self, tab):
        # reset the brightness value
        self.__main_app.set_brightness(self.__main_app.config.get(Config.MAIN.Brightness))

        # for all other values a simple reload should be sufficient
        redirect("/settings/" + tab)

    @post("/settings/preview_brightness")
    def set_brightness(self):
        value = request.forms.get("brightness_value")
        self.__main_app.set_brightness(int(value))

    @get("/js/<file_name:path>")
    def load_js(self, file_name):
        return static_file(file_name, root=self.__js_dir, mimetype="text/javascript")

    @get("/css/<file_name:path>")
    def load_css(self, file_name):
        return static_file(file_name, root=self.__css_dir, mimetype="text/css")

    @get("/fonts/<file_name:path>")
    def load_font(self, file_name):
        return static_file(file_name, root=self.__fonts_dir)
