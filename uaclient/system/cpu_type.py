import abc
import logging
import re
from typing import Dict, List, Type  # noqa: F401

from uaclient import exceptions, system, util

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class BaseCPUTypeCollector(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def processor_match(cls, processor_type: str) -> bool:
        pass

    @abc.abstractmethod
    def collect(self):
        pass

    def _get_field_value(self, cpu_info: str, re_pattern):
        re_match = re.search(
            re_pattern,
            cpu_info,
        )

        if re_match:
            match_groups = re_match.groupdict()
            return re.sub(r"\s{2,}", " ", match_groups["name"].strip())

        return None

    def _cpu_type_stringify(self, fallback_dict: Dict[str, str]):
        return "; ".join(
            [
                "{}:{}".format(key, value)
                for key, value in sorted(fallback_dict.items())
            ]
        )

    def _get_fallback_name(
        self,
        cpu_info,
        fallback_fields,
        re_pattern,
    ):
        return self._cpu_type_stringify(
            fallback_dict={
                field: self._get_field_value(
                    cpu_info=cpu_info,
                    re_pattern=re_pattern.format(field),
                )
                or ""
                for field in fallback_fields
            }
        )


class X86CPUTypeCollector(BaseCPUTypeCollector):
    CPU_TYPE_FILE = "/proc/cpuinfo"
    CPU_TYPE_REGEX_PATTERN = r"{}\s+:\s+(?P<name>.+)"

    @classmethod
    def processor_match(cls, processor_type: str) -> bool:
        return (
            processor_type == "amd64"
            or processor_type == "i386"
            or processor_type == "i686"
        )

    def collect(self):
        cpu_info = system.load_file(self.CPU_TYPE_FILE)
        model_name = self._get_field_value(
            cpu_info=cpu_info,
            re_pattern=self.CPU_TYPE_REGEX_PATTERN.format("model name"),
        )

        if model_name:
            return model_name

        # start backup plan if model name is not present in the data
        return self._get_fallback_name(
            cpu_info=cpu_info,
            fallback_fields=("vendor_id", "cpu family", "model", "stepping"),
            re_pattern=self.CPU_TYPE_REGEX_PATTERN,
        )


class PPCCPUTypeCollector(BaseCPUTypeCollector):
    CPU_TYPE_FILE = "/proc/cpuinfo"
    CPU_TYPE_REGEX_PATTERN = r"{}\s+:\s+(?P<name>.+)"

    @classmethod
    def processor_match(cls, processor_type: str) -> bool:
        return processor_type.startswith("ppc")

    def collect(self):
        cpu_info = system.load_file(self.CPU_TYPE_FILE)
        return self._get_field_value(
            cpu_info=cpu_info,
            re_pattern=self.CPU_TYPE_REGEX_PATTERN.format("cpu"),
        )


class S390CPUTypeCollector(BaseCPUTypeCollector):
    CPU_TYPE_FILE = "/proc/sysinfo"
    CPU_TYPE_REGEX_PATTERN = r"{}:\s+(?P<name>.+)"

    @classmethod
    def processor_match(cls, processor_type: str) -> bool:
        return processor_type.startswith("s390")

    def collect(self):
        cpu_info = system.load_file(self.CPU_TYPE_FILE)
        cpu_type = (
            self._get_field_value(
                cpu_info=cpu_info,
                re_pattern=self.CPU_TYPE_REGEX_PATTERN.format("Type"),
            )
            or ""
        )
        cpu_model = (
            self._get_field_value(
                cpu_info=cpu_info,
                re_pattern=self.CPU_TYPE_REGEX_PATTERN.format("Model"),
            )
            or ""
        )

        return self._cpu_type_stringify({"Type": cpu_type, "Model": cpu_model})


class ArmCPUTypeCollector(BaseCPUTypeCollector):
    CPU_TYPE_FILE = "/sys/firmware/devicetree/base/model"
    CPU_FALLBACK_FILE = "/proc/cpuinfo"
    CPU_TYPE_REGEX_PATTERN = r"{}\s+:\s*(?P<name>.+)"

    @classmethod
    def processor_match(cls, processor_type: str) -> bool:
        return processor_type.startswith("arm") or processor_type.startswith(
            "aarm"
        )

    def collect(self):
        try:
            return system.load_file(self.CPU_TYPE_FILE)
        except FileNotFoundError:
            pass

        # start backup plan if devicetree file not present
        fallback_cpu_info = system.load_file(self.CPU_FALLBACK_FILE)
        return self._get_fallback_name(
            cpu_info=fallback_cpu_info,
            fallback_fields=(
                "CPU implementer",
                "CPU architecture",
                "CPU variant",
                "CPU part",
                "CPU revision",
            ),
            re_pattern=self.CPU_TYPE_REGEX_PATTERN,
        )


COLLECTOR_CLASSES = [
    X86CPUTypeCollector,
    PPCCPUTypeCollector,
    S390CPUTypeCollector,
    ArmCPUTypeCollector,
]  # type: List[Type[BaseCPUTypeCollector]]


def cpu_type_collector_factory(processor_type: str):
    for collector_cls in COLLECTOR_CLASSES:
        if collector_cls.processor_match(processor_type):
            return collector_cls()
    raise exceptions.UnknownProcessorType(processor_type=processor_type)


def get_cpu_type():
    processor_type = system.get_dpkg_arch()

    try:
        return cpu_type_collector_factory(processor_type).collect()
    except exceptions.UnknownProcessorType as e:
        LOG.debug(str(e))
        return "unknown_cpu_type"
