from threading import Event


class EventWithUnsetSignal(Event):
    def clear(self) -> None:
        with self._cond:  # type: ignore
            # copied from parent class
            self._flag = False
            # after the flag is cleared notify any threads that have called 'wait_unset'
            self._cond.notify_all()  # type: ignore

    def wait_unset(self, timeout: float | None=None) -> bool:
        """Block until the internal flag is false.

        If the internal flag is false on entry, return immediately. Otherwise,
        block until another thread calls clear() to set the flag to false, or until
        the optional timeout occurs.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        This method returns the internal flag on exit, so it will always return
        False except if a timeout is given and the operation times out.

        """
        with self._cond:  # type: ignore
            signaled: bool = self._flag
            if signaled:
                self._cond.wait_for(lambda: not self._flag, timeout=timeout)  # type: ignore
                signaled = self._flag
            return signaled
