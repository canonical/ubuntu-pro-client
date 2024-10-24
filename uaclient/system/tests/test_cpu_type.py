import mock
import pytest

from uaclient.system.cpu_type import (
    ArmCPUTypeCollector,
    BaseCPUTypeCollector,
    PPCCPUTypeCollector,
    S390CPUTypeCollector,
    X86CPUTypeCollector,
)


class ConcreteBaseCPUTypeCollector(BaseCPUTypeCollector):
    @classmethod
    def processor_match(cls, processor_type: str) -> bool:
        pass

    def collect(self):
        pass


class TestBaseCPUTypeCollector:
    @pytest.mark.parametrize(
        "cpu_info,re_pattern,expected_value",
        (
            (
                "test    : value\nid    : id\n\nvendor     : vendor_value",
                r"vendor\s+:\s+(?P<name>.+)",
                "vendor_value",
            ),
            (
                "test    : value\nid    : id\n\nvendor     : vendor    value  ",  # noqa
                r"vendor\s+:\s+(?P<name>.+)",
                "vendor value",
            ),
            (
                "test    : value\nid    : id\n\nvendor     : vendor_value",
                r"invalid\s+:\s+(?P<name>.+)",
                None,
            ),
        ),
    )
    def test_get_field_value(self, cpu_info, re_pattern, expected_value):
        collector = ConcreteBaseCPUTypeCollector()
        assert expected_value == collector._get_field_value(
            cpu_info, re_pattern
        )

    @pytest.mark.parametrize(
        "cpu_info,re_pattern,fallback_fields,expected_value",
        (
            (
                "test    : value\nid    : id\n\nvendor     : vendor_value",
                r"{}\s+:\s+(?P<name>.+)",
                ("test", "id"),
                "id:id; test:value",
            ),
            (
                "test    : value\nid    : id\n\nvendor     : vendor_value",
                r"{}\s+:\s+(?P<name>.+)",
                ("foo", "id"),
                "foo:; id:id",
            ),
        ),
    )
    def test_get_fallback_name(
        self, cpu_info, re_pattern, fallback_fields, expected_value
    ):
        collector = ConcreteBaseCPUTypeCollector()
        assert expected_value == collector._get_fallback_name(
            cpu_info, fallback_fields, re_pattern
        )


class TestX86CPUTypeCollector:
    CPU_INFO = (
        "bogomips        : 4199.88\n"
        "clflush size    : 64\n"
        "cache_alignment : 64\n"
        "address sizes   : 39 bits physical, 48 bits virtual\n"
        "\n"
        "processor          : 0\n"
        "vendor_id          : GenuineIntel\n"
        "cpu family         : 6\n"
        "model              : 142\n"
        "model name         : Test Intel 1\n"
        "stepping           : 10\n"
        "microcode          : 0xf4\n"
        "cpu MHz            : 1600.020\n"
        "cache size         : 8192 KB\n"
        "physical id        : 0\n"
        "siblings           : 8\n"
        "core id            : 0\n"
        "cpu cores          : 4\n"
        "apicid             : 0\n"
        "initial apicid     : 0\n"
        "fpu                : yes\n"
        "fpu_exception      : yes\n"
        "cpuid level        : 22\n"
        "wp                 : yes\n"
        "flags              : fpu vme de pse tsc msr pae mce cx8\n"
        "\n"
        "processor          : 1\n"
        "vendor_id          : GenuineIntel\n"
        "cpu family         : 6\n"
        "model              : 142\n"
        "model name         : Test Intel 2\n"
    )

    FALLBACK_CPU_INFO = (
        "bogomips        : 4199.88\n"
        "clflush size    : 64\n"
        "cache_alignment : 64\n"
        "address sizes   : 39 bits physical, 48 bits virtual\n"
        "\n"
        "processor          : 0\n"
        "vendor_id          : GenuineIntel\n"
        "cpu family         : 6\n"
        "model              : 142\n"
        "stepping           : 10\n"
        "microcode          : 0xf4\n"
        "cpu MHz            : 1600.020\n"
        "cache size         : 8192 KB\n"
        "physical id        : 0\n"
        "siblings           : 8\n"
        "core id            : 0\n"
        "cpu cores          : 4\n"
        "apicid             : 0\n"
        "initial apicid     : 0\n"
        "fpu                : yes\n"
        "fpu_exception      : yes\n"
        "cpuid level        : 22\n"
        "wp                 : yes\n"
        "flags              : fpu vme de pse tsc msr pae mce cx8\n"
        "\n"
        "processor          : 1\n"
        "vendor_id          : GenuineIntel\n"
        "cpu family         : 6\n"
        "model              : 142\n"
    )

    @pytest.mark.parametrize(
        "cpu_info,expected_value",
        (
            (
                CPU_INFO,
                "Test Intel 1",
            ),
            (
                FALLBACK_CPU_INFO,
                "cpu family:6; model:142; stepping:10; vendor_id:GenuineIntel",
            ),
        ),
    )
    @mock.patch("uaclient.system.load_file")
    def test_collect(self, m_load_file, cpu_info, expected_value):
        m_load_file.return_value = cpu_info
        collector = X86CPUTypeCollector()
        assert expected_value == collector.collect()


class TestPPCCPUTypeCollector:
    CPU_INFO = (
        "processor   : 0\n"
        "cpu         : POWER10\n"
        "clock       : 2800.000000MHz\n"
        "revision    : 2.0 (pvr 0080 0200)\n"
        "\n"
        "processor   : 1\n"
        "cpu         : TEST\n"
        "clock       : 2800.000000MHz\n"
        "revision    : 2.0 (pvr 0080 0200)\n"
    )

    @mock.patch("uaclient.system.load_file")
    def test_collect(self, m_load_file):
        m_load_file.return_value = self.CPU_INFO
        collector = PPCCPUTypeCollector()
        assert "POWER10" == collector.collect()


class TestS390CPUTypeCollector:
    CPU_INFO = (
        "Manufacturer:         IBM\n"
        "Type:                 2964\n"
        "Model:                400           N63\n"
        "Sequence Code:        00000000000B8F67\n"
        "Plant:                02\n"
        "Model Capacity:       400           00000000\n"
        "Capacity Adj. Ind.:   100\n"
        "Capacity Ch. Reason:  0\n"
        "Capacity Transient:   0\n"
        "Type 1 Percentage:    0\n"
        "Type 2 Percentage:    0\n"
        "Type 3 Percentage:    0\n"
        "Type 4 Percentage:    0\n"
        "Type 5 Percentage:    0\n"
    )

    @mock.patch("uaclient.system.load_file")
    def test_collect(self, m_load_file):
        m_load_file.return_value = self.CPU_INFO
        collector = S390CPUTypeCollector()
        assert "Model:400 N63; Type:2964" == collector.collect()


class TestArmCPUTypeCollector:
    CPU_INFO = "ARM CPU Type"
    FALLBACK_CPU_INFO = (
        "processor        : 0\n"
        "model name       : ARMv7 Processor rev 3 (v7l)\n"
        "BogoMIPS         : 144.00\n"
        "Features         : half thumb fastmult vfp edsp neon \n"
        "CPU implementer  : 0x41\n"
        "CPU architecture : 7\n"
        "CPU variant      : 0x0\n"
        "CPU part         : 0xd08\n"
        "CPU revision     : 3\n"
    )

    @mock.patch("uaclient.system.load_file")
    def test_collect(self, m_load_file):
        m_load_file.return_value = self.CPU_INFO
        collector = ArmCPUTypeCollector()
        assert self.CPU_INFO == collector.collect()

    @mock.patch("uaclient.system.load_file")
    def test_collect_fallback(self, m_load_file):
        m_load_file.side_effect = [
            FileNotFoundError(),
            self.FALLBACK_CPU_INFO,
        ]
        collector = ArmCPUTypeCollector()

        assert (
            "CPU architecture:7; CPU implementer:0x41; CPU part:0xd08; CPU revision:3; CPU variant:0x0"  # noqa
            == collector.collect()
        )
