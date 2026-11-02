"""Behave plugins that keep reruns from hiding failures.

``run_behave_with_retries.py`` reruns only what behave's rerun file lists, so
everything that failed or never ran must be in it, or the run must not be
retried. Behave loads these classes by module path (``--format`` and
``--runner``); the ``behave`` tox env puts this directory on ``PYTHONPATH``
for that. Only behave imports this module.
"""

import os

from behave.formatter.rerun import RerunFormatter
from behave.runner import Runner


class FeatureRerunFormatter(RerunFormatter):
    """Rerun formatter that also lists failed features without failed
    scenarios.

    Behave's built-in ``rerun`` formatter lists only failing scenarios. When
    a feature-level hook such as ``before_feature`` fails, behave marks the
    feature as failed but never runs its scenarios. Listing the feature by
    its own location makes the next run execute the whole feature again.
    """

    name = "feature_rerun"
    description = (
        "Emits locations of failing scenarios, and of failed features "
        "that have no failing scenario"
    )

    def eof(self):
        feature = self.current_feature
        if (
            feature
            and feature.status.has_failed()
            and not any(
                scenario.status.has_failed()
                for scenario in feature.walk_scenarios()
            )
        ):
            self.failed_scenarios.append(feature)
        super().eof()


class AbortAwareRunner(Runner):
    """Runner that removes the rerun file when behave aborted.

    When a hook raises ``SystemExit`` or ``KeyboardInterrupt``, behave stops
    running features, so the rerun file lists only what ran before the abort.
    Without the file, the helper fails instead of retrying that subset.
    """

    def run_model(self, features=None):
        failed = super().run_model(features)
        if self.aborted:
            for formatter in self.formatters:
                if isinstance(formatter, FeatureRerunFormatter):
                    rerun_file = formatter.stream_opener.name
                    if rerun_file and os.path.exists(rerun_file):
                        os.remove(rerun_file)
        return failed
