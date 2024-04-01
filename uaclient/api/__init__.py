import abc
import logging
from typing import Optional

# setup null handler for all API endpoints
logging.getLogger("ubuntupro").addHandler(logging.NullHandler())


class AbstractProgress(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def progress(
        self,
        *,
        total_steps: int,
        done_steps: int,
        previous_step_message: Optional[str],
        current_step_message: Optional[str]
    ):
        pass


class NullProgress(AbstractProgress):
    def progress(
        self,
        *,
        total_steps: int,
        done_steps: int,
        previous_step_message: Optional[str],
        current_step_message: Optional[str]
    ):
        pass


class ProgressWrapper:
    def __init__(self, progress_object: Optional[AbstractProgress] = None):
        if progress_object is not None:
            self.progress_object = progress_object
        else:
            self.progress_object = NullProgress()
        self.done_steps = 0
        self.total_steps = -1
        self.previous_step_message = None  # type: Optional[str]

    def progress(self, message: str):
        self.progress_object.progress(
            total_steps=self.total_steps,
            done_steps=self.done_steps,
            previous_step_message=self.previous_step_message,
            current_step_message=message,
        )
        self.previous_step_message = message
        self.done_steps += 1

    def finish(self):
        self.done_steps = self.total_steps
        self.progress_object.progress(
            total_steps=self.total_steps,
            done_steps=self.done_steps,
            previous_step_message=self.previous_step_message,
            current_step_message=None,
        )

    def emit(self, event: str, payload=None):
        """
        This is our secret event system. We use it internally to insert prompts
        and extra messages in the middle of operations at certain points.
        We don't consider this stable enough to expose to the public API.
        """
        if hasattr(self.progress_object, "_on_event"):
            self.progress_object._on_event(event, payload)

    def is_interactive(self) -> bool:
        if hasattr(self.progress_object, "is_interactive"):
            return self.progress_object.is_interactive
        else:
            return False
