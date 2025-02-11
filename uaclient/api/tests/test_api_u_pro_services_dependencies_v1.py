import mock

from uaclient import messages
from uaclient.api.u.pro.services.dependencies.v1 import (
    DependenciesResult,
    Reason,
    ServiceWithDependencies,
    ServiceWithReason,
    _dependencies,
)


class TestServicesDependenciesV1:
    def test_dependencies(self):
        assert _dependencies(cfg=mock.MagicMock()) == DependenciesResult(
            services=[
                ServiceWithDependencies(
                    name="anbox-cloud", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="cc-eal", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="cis", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="esm-apps", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="esm-infra", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="fips",
                    incompatible_with=[
                        ServiceWithReason(
                            name="livepatch",
                            reason=Reason(
                                code=messages.LIVEPATCH_INVALIDATES_FIPS.name,
                                title=messages.LIVEPATCH_INVALIDATES_FIPS.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="fips-updates",
                            reason=Reason(
                                code=messages.FIPS_UPDATES_INVALIDATES_FIPS.name,  # noqa: E501
                                title=messages.FIPS_UPDATES_INVALIDATES_FIPS.msg,  # noqa: E501
                            ),
                        ),
                        ServiceWithReason(
                            name="realtime-kernel",
                            reason=Reason(
                                code=messages.REALTIME_FIPS_INCOMPATIBLE.name,
                                title=messages.REALTIME_FIPS_INCOMPATIBLE.msg,
                            ),
                        ),
                    ],
                    depends_on=[],
                ),
                ServiceWithDependencies(
                    name="fips-updates",
                    incompatible_with=[
                        ServiceWithReason(
                            name="fips",
                            reason=Reason(
                                code=messages.FIPS_INVALIDATES_FIPS_UPDATES.name,  # noqa: E501
                                title=messages.FIPS_INVALIDATES_FIPS_UPDATES.msg,  # noqa: E501
                            ),
                        ),
                        ServiceWithReason(
                            name="realtime-kernel",
                            reason=Reason(
                                code=messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE.name,  # noqa: E501
                                title=messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE.msg,  # noqa: E501
                            ),
                        ),
                    ],
                    depends_on=[],
                ),
                ServiceWithDependencies(
                    name="fips-preview",
                    incompatible_with=[
                        ServiceWithReason(
                            name="livepatch",
                            reason=Reason(
                                code=messages.LIVEPATCH_INVALIDATES_FIPS.name,
                                title=messages.LIVEPATCH_INVALIDATES_FIPS.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="fips-updates",
                            reason=Reason(
                                code=messages.FIPS_UPDATES_INVALIDATES_FIPS.name,  # noqa: E501
                                title=messages.FIPS_UPDATES_INVALIDATES_FIPS.msg,  # noqa: E501
                            ),
                        ),
                        ServiceWithReason(
                            name="realtime-kernel",
                            reason=Reason(
                                code=messages.REALTIME_FIPS_INCOMPATIBLE.name,
                                title=messages.REALTIME_FIPS_INCOMPATIBLE.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="fips",
                            reason=Reason(
                                code=messages.FIPS_INVALIDATES_FIPS_UPDATES.name,  # noqa: E501
                                title=messages.FIPS_INVALIDATES_FIPS_UPDATES.msg,  # noqa: E501
                            ),
                        ),
                    ],
                    depends_on=[],
                ),
                ServiceWithDependencies(
                    name="landscape", incompatible_with=[], depends_on=[]
                ),
                ServiceWithDependencies(
                    name="livepatch",
                    incompatible_with=[
                        ServiceWithReason(
                            name="fips",
                            reason=Reason(
                                code=messages.LIVEPATCH_INVALIDATES_FIPS.name,
                                title=messages.LIVEPATCH_INVALIDATES_FIPS.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="realtime-kernel",
                            reason=Reason(
                                code=messages.REALTIME_LIVEPATCH_INCOMPATIBLE.name,  # noqa: E501
                                title=messages.REALTIME_LIVEPATCH_INCOMPATIBLE.msg,  # noqa: E501
                            ),
                        ),
                    ],
                    depends_on=[],
                ),
                ServiceWithDependencies(
                    name="realtime-kernel",
                    incompatible_with=[
                        ServiceWithReason(
                            name="fips",
                            reason=Reason(
                                code=messages.REALTIME_FIPS_INCOMPATIBLE.name,
                                title=messages.REALTIME_FIPS_INCOMPATIBLE.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="fips-updates",
                            reason=Reason(
                                code=messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE.name,  # noqa: E501
                                title=messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE.msg,  # noqa: E501
                            ),
                        ),
                        ServiceWithReason(
                            name="livepatch",
                            reason=Reason(
                                code=messages.REALTIME_LIVEPATCH_INCOMPATIBLE.name,  # noqa: E501
                                title=messages.REALTIME_LIVEPATCH_INCOMPATIBLE.msg,  # noqa: E501
                            ),
                        ),
                    ],
                    depends_on=[],
                ),
                ServiceWithDependencies(
                    name="ros",
                    incompatible_with=[],
                    depends_on=[
                        ServiceWithReason(
                            name="esm-infra",
                            reason=Reason(
                                code=messages.ROS_REQUIRES_ESM.name,
                                title=messages.ROS_REQUIRES_ESM.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="esm-apps",
                            reason=Reason(
                                code=messages.ROS_REQUIRES_ESM.name,
                                title=messages.ROS_REQUIRES_ESM.msg,
                            ),
                        ),
                    ],
                ),
                ServiceWithDependencies(
                    name="ros-updates",
                    incompatible_with=[],
                    depends_on=[
                        ServiceWithReason(
                            name="esm-infra",
                            reason=Reason(
                                code=messages.ROS_REQUIRES_ESM.name,
                                title=messages.ROS_REQUIRES_ESM.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="esm-apps",
                            reason=Reason(
                                code=messages.ROS_REQUIRES_ESM.name,
                                title=messages.ROS_REQUIRES_ESM.msg,
                            ),
                        ),
                        ServiceWithReason(
                            name="ros",
                            reason=Reason(
                                code=messages.ROS_UPDATES_REQUIRES_ROS.name,
                                title=messages.ROS_UPDATES_REQUIRES_ROS.msg,
                            ),
                        ),
                    ],
                ),
            ]
        )
