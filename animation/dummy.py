from animation.abstract import AbstractAnimation, AbstractAnimationController,\
    _AnimationSettingsStructure


class DummySettings(_AnimationSettingsStructure):
    pass


class DummyAnimation(AbstractAnimation):
    def render_next_frame(self):
        # do nothing here, but continue
        return True

    def display_frame(self, frame):
        # check stop and pause event
        if not (self._stop_event.is_set() or
                self._pause_event.is_set()):
            self._frame_queue.put(frame)


class DummyController(AbstractAnimationController):
    @property
    def animation_class(self):
        return DummyAnimation

    @property
    def animation_variants(self):
        return None

    @property
    def animation_parameters(self):
        return None

    @property
    def default_animation_settings(self):
        return DummySettings

    @property
    def is_repeat_supported(self):
        return False

    def display_frame(self, frame):
        """
        This method is special and only available in the Dummy animation.
        It allows direct access to the frame queue.
        @param frame: This frame gets directly added to the frame queue if the animation is running.
        """
        if self.is_running:
            self.__animation_thread.display_frame(frame)
