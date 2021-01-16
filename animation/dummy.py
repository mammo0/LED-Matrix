from animation.abstract import AbstractAnimation, AbstractAnimationController


class DummyAnimation(AbstractAnimation):
    def animate(self):
        # do nothing and wait until the animation is stopped
        self._stop_event.wait()


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
