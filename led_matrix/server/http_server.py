from __future__ import annotations

import calendar
from dataclasses import Field, replace
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, cast

import bottle
from bottle import (FileUpload, FormsDict, HTTPResponse, redirect, request,
                    static_file, template)

from led_matrix import STATIC_RESOURCES_DIR
from led_matrix.animation.abstract import (AbstractAnimationController,
                                           AnimationParameterTypes,
                                           AnimationSettings, AnimationVariant)
from led_matrix.common.bottle import BottleCBVMeta, get, post
from led_matrix.common.color import Color
from led_matrix.common.log import LOG
from led_matrix.common.schedule import CronStructure, ScheduleEntry
from led_matrix.common.wsgi import CustomWSGIRefServer
from led_matrix.config.types import ColorTemp

if TYPE_CHECKING:
    from led_matrix.main import MainController


CRON_DICT: dict[str, list[dict[str, int | str]]] = {
    "second": [
                {"value": i,
                 "text": i} for i in range(0, 60)
              ],
    "minute": [
                {"value": i,
                 "text": i} for i in range(0, 60)
              ],
    "hour": [
                {"value": i,
                 "text": i} for i in range(0, 24)
            ],
    "day_of_week": [
                        {"value": i,
                         "text": calendar.day_name[i]} for i in range(0, 7)
                    ],
    "week": [
                {"value": i,
                 "text": i} for i in range(1, 54)
            ],
    "day": [
                {"value": i,
                 "text": i} for i in range(1, 32)
           ],
    "month": [
                {"value": i,
                 "text": calendar.month_name[i]} for i in range(1, 13)
             ],
    "year": [
                {"value": i,
                 "text": i} for i in range(datetime.now().year, datetime.now().year + 11)
            ],
}


def get_cron_selector_pattern(cron_category: str) -> str:
    valid_numbers: list[str] = [str(item["value"]) for item in CRON_DICT[cron_category]]

    return ("^"                                      # noqa, BOS
            "(?!"                                    # Validate no dups
                ".*"
                "("                                  # (1 start)
                    "\\b"
                   f"(?:{'|'.join(valid_numbers)})"  # number range
                    "\\b"
                ")"                                  # (1 end)
                ".*"
                "\\b\\1\\b"
            ")"
           f"(?:{'|'.join(valid_numbers)})"          # Unrolled-loop, match 1 to many numb's
            "(?:"                                    # in the number range
                ","
               f"(?:{'|'.join(valid_numbers)})"
            ")*"
            "$")                                     # EOS


class SettingsTabs(Enum):
    """
    This class is ALSO used in led_matrix/static_res/http/templates/settings.tpl
    """
    MAIN = "Main"
    DEFAULT_ANIMATION = "Default Animation"
    VARIANT_UPLOAD = "Upload Variants"


class Input:
    """
    This class is ONLY used in led_matrix/static_res/http/templates/animation/settings.tpl
    """
    def __init__(self, value: AnimationParameterTypes) -> None:
        self.__input_type: str = "text"
        self.__value: AnimationParameterTypes = value
        self.__step: str = "1"

        if isinstance(value, bool):
            self.__input_type = "checkbox"
        elif isinstance(value, int):
            self.__input_type = "number"
        elif isinstance(value, float):
            self.__input_type = "number"
            self.__step = "any"
        elif isinstance(value, Color):
            self.__input_type = "color"
            self.__value = value.hex_value

    @property
    def input_type(self) -> str:
        return self.__input_type

    @property
    def value(self) -> AnimationParameterTypes:
        return self.__value

    @property
    def step(self) -> str:
        return self.__step


class HttpServer(metaclass=BottleCBVMeta):
    def __init__(self, main_app: MainController) -> None:
        self.__main_app: MainController = main_app

        self.__log: Logger = LOG.create(HttpServer.__name__)

        http_res_dir: Path = STATIC_RESOURCES_DIR / "http"
        self.__js_dir: Path = http_res_dir / "js"
        self.__css_dir: Path = http_res_dir / "css"
        self.__fonts_dir: Path = http_res_dir / "fonts"
        bottle.TEMPLATE_PATH = [(http_res_dir / "templates").resolve()]

        self.__port: int = self.__main_app.config.main.http_server_port
        self.__host: IPv4Address | IPv6Address = self.__main_app.config.main.http_server_listen_ip

        self.__wsgi_server: CustomWSGIRefServer = CustomWSGIRefServer(host=str(self.__host),
                                                                      port=self.__port,
                                                                      quiet=True)

    def start(self) -> None:
        self.__wsgi_server.start()

        self.__log.info("Listening on http://%s:%d",
                        self.__host, self.__port)

    def stop(self) -> None:
        self.__wsgi_server.stop()

        self.__log.info("Server stopped")

    def __get_form(self) -> FormsDict:
        form: FormsDict = cast(FormsDict, request.forms)

        # get unicode strings
        return form.decode()  # pylint: disable=maybe-no-member

    def __get_files(self) -> FormsDict:
        files: FormsDict = cast(FormsDict, request.files)

        return files.decode()  # pylint: disable=maybe-no-member

    def __show_settings(self, tab: SettingsTabs=SettingsTabs.MAIN) -> str:
        """
        led_matrix/static_res/http/templates/settings.tpl
        """
        return template("settings",
                        active_tab=tab,
                        # provide the main config
                        config=self.__main_app.config,
                        # provide the animations
                        animation_controllers=self.__main_app.all_animation_controllers)

    def __parse_animation_form(self, form: FormsDict) -> tuple[str, AnimationSettings]:
        """
        led_matrix/static_res/http/templates/animation/settings.tpl
        """
        animation_name: str | None = form.get("selected_animation_name")

        if animation_name is not None:
            animation_controller: AbstractAnimationController = (
                self.__main_app.all_animation_controllers[animation_name]
            )

            # create new instance of the animation settings
            animation_settings: AnimationSettings = animation_controller.default_settings

            # variant
            if animation_controller.variant_enum is not None:
                new_default_animation_variant_name: str | None = form.get(animation_name + "_variant_value",
                                                                          default=None)

                if new_default_animation_variant_name is not None:
                    animation_settings.variant = animation_controller.variant_enum[new_default_animation_variant_name]

            # parameter
            if animation_settings.parameter is not None:
                new_parameters: dict[str, AnimationParameterTypes] = {}

                field: Field
                for field, _ in animation_settings.parameter.iterate_fields():
                    # special treatment for bool values, because if not checked, None is returned, otherwise 'on'
                    if field.type == bool:
                        new_parameters[field.name] = form.get(animation_name +
                                                              "_parameter_" +
                                                              field.name +
                                                              "_value",
                                                              default=False, type=bool)
                    else:
                        new_parameters[field.name] = form.get(
                            animation_name + "_parameter_" + field.name + "_value",
                            default=getattr(animation_settings.parameter, field.name),
                            type=field.type
                        )

                animation_settings.parameter = replace(animation_settings.parameter, **new_parameters)

            # repeat
            if animation_controller.is_repeat_supported:
                animation_settings.repeat = form.get(animation_name + "_repeat_value",
                                                     default=animation_controller.default_settings.repeat,
                                                     type=int)

            return (animation_name, animation_settings)

        # this should not happen
        raise KeyError("The animation name was empty!")

    def __parse_cron_form(self, form: FormsDict, job_id: str | None=None) -> ScheduleEntry:
        """
        led_matrix/static_res/http/templates/schedule/entry.tpl
        """
        cron_structure: dict[str, str | None] = {}
        for category in CRON_DICT:
            selected_values: str | None = form.get(f"cron_{category}_select_value",
                                                   default=None)

            if selected_values is None:
                cron_structure[category] = None
                continue

            # validate values
            try:
                [int(val) for val in selected_values.split(",")]
            except ValueError:
                selected_values = None

            cron_structure[category] = selected_values

        a_name:str
        a_settings: AnimationSettings
        a_name, a_settings = self.__parse_animation_form(form)

        return ScheduleEntry(job_id=job_id,
                             cron_structure=CronStructure(year=cron_structure["year"],
                                                          month=cron_structure["month"],
                                                          day=cron_structure["day"],
                                                          week=cron_structure["week"],
                                                          day_of_week=cron_structure["day_of_week"],
                                                          hour=cron_structure["hour"],
                                                          minute=cron_structure["minute"],
                                                          second=cron_structure["second"]),
                             animation_name=a_name,
                             animation_settings=a_settings)

    @get("/")
    def index(self) -> str:
        """
        led_matrix/static_res/http/templates/index.tpl
        """
        return template("index",
                        animation_controllers=self.__main_app.all_animation_controllers,
                        current_animation_name=self.__main_app.current_animation_name)

    @post("/")
    def start_new_animation(self) -> None:
        a_name:str
        a_settings: AnimationSettings
        a_name, a_settings = self.__parse_animation_form(self.__get_form())

        self.__main_app.start_animation(animation_name=a_name,
                                        animation_settings=a_settings,
                                        # wait until the new animation runs
                                        block_until_started=True)

        redirect("/")

    @get("/schedule")
    def schedule_table(self) -> str:
        """
        led_matrix/static_res/http/templates/schedule/table.tpl
        """
        return template("schedule/table",
                        schedule_table=self.__main_app.scheduled_animations)

    @post("/schedule/new")
    def new_schedule_entry(self) -> str:
        """
        led_matrix/static_res/http/templates/schedule/entry.tpl
        """
        a_name:str
        a_settings: AnimationSettings
        a_name, a_settings = self.__parse_animation_form(self.__get_form())

        temp_schedule_entry = ScheduleEntry(animation_name=a_name,
                                            animation_settings=a_settings)

        return template("schedule/entry",
                        animation_controllers=self.__main_app.all_animation_controllers,
                        entry=temp_schedule_entry)

    @post("/schedule/create")
    def create_schedule_entry(self) -> None:
        schedule_entry: ScheduleEntry = self.__parse_cron_form(self.__get_form())

        # schedule the animation
        self.__main_app.schedule_animation(entry=schedule_entry)

        redirect("/schedule")

    @get("/schedule/edit/<job_id>")
    def edit_schedule_entry(self, job_id: str) -> str | None:
        table: list[ScheduleEntry] = self.__main_app.scheduled_animations
        for entry in table:
            if entry.job_id == job_id:
                return template("schedule/entry",
                                animation_controllers=self.__main_app.all_animation_controllers,
                                entry=entry,
                                is_modify=True)

        # show table if no corresponding job could be found
        redirect("/schedule")

    @post("/schedule/edit/<job_id>")
    def modify_schedule_entry(self, job_id: str) -> None:
        self.__main_app.modify_scheduled_animation(self.__parse_cron_form(self.__get_form(),
                                                                          job_id=job_id))

        redirect("/schedule")

    @get("/schedule/delete/<job_id>")
    def delete_schedule_entry(self, job_id: str) -> None:
        self.__main_app.remove_scheduled_animation(job_id)

        # redirect back to the schedule table
        redirect("/schedule")

    @get("/stop-animation")
    def stop_current_animation(self) -> None:
        self.__main_app.stop_animation(blocking=True)
        redirect("/")

    @get("/settings")
    def settings(self) -> str:
        return self.__show_settings()

    @get("/settings/<tab>")
    def settings_with_pane(self, tab: str) -> str:
        return self.__show_settings(SettingsTabs[tab.upper()])

    @post("/settings/<tab>")
    def save_settings(self, tab: str) -> None:
        form: FormsDict = self.__get_form()

        if SettingsTabs[tab.upper()] == SettingsTabs.MAIN:
            # get the day and night brightness and color temperature values
            day_brightness: int = form.get("day_brightness_value", type=int,
                                           default=self.__main_app.config.main.day_brightness)
            day_color_temp: ColorTemp = ColorTemp[form.get("day_color_temp_value", type=str,
                                                           default=self.__main_app.config.main.day_color_temp.name)]

            night_brightness: int
            night_color_temp: ColorTemp
            if form.get("setting_night_brightness_enabled_value", default=False, type=bool):
                night_brightness = form.get("night_brightness_value", type=int,
                                            default=self.__main_app.config.main.night_brightness)
                night_color_temp = ColorTemp[form.get("night_color_temp_value", type=str,
                                                      default=self.__main_app.config.main.night_color_temp.name)]
            else:
                night_brightness = -1
                night_color_temp = self.__main_app.config.main.night_color_temp

            # apply both
            self.__main_app.config.main.day_brightness = day_brightness
            self.__main_app.config.main.day_color_temp = day_color_temp
            self.__main_app.config.main.night_brightness = night_brightness
            self.__main_app.config.main.night_color_temp = night_color_temp
            self.__main_app.apply_day_night()

            # special treatment for bool values, because if not checked, None is returned, otherwise 'on'
            enable_tpm2net: bool = form.get("enable_tpm2net", default=False, type=bool)

            # save the settings
            self.__main_app.config.main.day_brightness = day_brightness
            self.__main_app.config.main.night_brightness = night_brightness
            self.__main_app.config.main.tpm2net_server = enable_tpm2net
        elif SettingsTabs[tab.upper()] == SettingsTabs.DEFAULT_ANIMATION:
            new_default_an: str
            new_default_as: AnimationSettings
            new_default_an, new_default_as = self.__parse_animation_form(form)

            self.__main_app.config.default_animation.animation_name = new_default_an

            # variant
            self.__main_app.config.set_default_animation_variant(new_default_as.variant)

            # parameter
            self.__main_app.config.set_default_animation_parameter(new_default_as.parameter)

            # repeat
            self.__main_app.config.default_animation.repeat = new_default_as.repeat

        self.__main_app.config.save()

        # reload the application
        self.__main_app.reload()

        # reload the page
        redirect(f"/settings/{tab}")

    @get("/settings/reset/<tab>")
    def reset_settings(self, tab: str) -> None:
        # reset the brightness value
        self.__main_app.apply_day_night()

        # for all other values a simple reload should be sufficient
        redirect(f"/settings/{tab}")

    @post("/settings/preview_brightness")
    def set_brightness(self) -> None:
        form: FormsDict = self.__get_form()

        value: int = form.get("preview_brightness_value", type=int,
                              default=-1)
        if value > -1:
            self.__main_app.preview_brightness(value)

    @post("/settings/preview_color_temp")
    def set_color_temp(self) -> None:
        form: FormsDict = self.__get_form()

        value: str | None = form.get("preview_color_temp_value", type=str,
                                     default=None)
        if value is not None:
            self.__main_app.preview_color_temp(ColorTemp[value])

    @get(f"/settings/{SettingsTabs.VARIANT_UPLOAD.name.lower()}/<animation_name>/delete/<variant_name>")
    def delete_variant(self, animation_name: str, variant_name: str) -> None:
        animation: AbstractAnimationController = self.__main_app.all_animation_controllers[animation_name]
        if animation.variant_enum is not None:
            variant: AnimationVariant = animation.variant_enum[variant_name]

            # remove a scheduled animation if it's variant gets deleted
            scheduled_animation: ScheduleEntry
            for scheduled_animation in self.__main_app.scheduled_animations:
                if scheduled_animation.animation_name == animation_name:
                    scheduled_variant: AnimationVariant | None = scheduled_animation.animation_settings.variant

                    if (
                        scheduled_variant is not None and
                        scheduled_variant == variant and
                        scheduled_animation.job_id is not None
                    ):
                        self.__main_app.remove_scheduled_animation(scheduled_animation.job_id)

            animation.remove_dynamic_variant(variant)

        redirect(f"/settings/{SettingsTabs.VARIANT_UPLOAD.name.lower()}?show_animation={animation_name}")

    @post(f"/settings/{SettingsTabs.VARIANT_UPLOAD.name.lower()}/<animation_name>/upload")
    def upload_variant(self, animation_name: str) -> None:
        uploaded_file: FileUpload | None = self.__get_files().get(f"variant_upload_{animation_name}_value")

        if uploaded_file is not None:
            animation: AbstractAnimationController = self.__main_app.all_animation_controllers[animation_name]

            animation.add_dynamic_variant(file_name=uploaded_file.filename,
                                          file_content=uploaded_file.file)

        #TODO: error handling

        redirect(f"/settings/{SettingsTabs.VARIANT_UPLOAD.name.lower()}?show_animation={animation_name}")

    @get("/js/<file_name:path>")
    def load_js(self, file_name: str) -> HTTPResponse:
        return static_file(filename=file_name,
                           root=self.__js_dir,
                           mimetype="text/javascript")

    @get("/css/<file_name:path>")
    def load_css(self, file_name: str) -> HTTPResponse:
        return static_file(filename=file_name,
                           root=self.__css_dir,
                           mimetype="text/css")

    @get("/fonts/<file_name:path>")
    def load_font(self, file_name: str) -> HTTPResponse:
        return static_file(filename=file_name,
                           root=self.__fonts_dir)
