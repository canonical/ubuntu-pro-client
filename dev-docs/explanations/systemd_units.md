# Mechanisms for auto-attaching Ubuntu Pro Cloud instances

> **Note**
> This document explains the systemd units that attempt to auto-attach in various scenarios. If you're interested in how auto-attach itself works, see [How auto-attach works](./how_auto_attach_works.md).

There are three methods by which a cloud instance may auto-attach to become Ubuntu Pro.

1. On boot auto-attach for known Pro cloud instances.
2. Upgrade-in-place for non-Pro instances that get modified via the Cloud platform to entitle them to become Ubuntu Pro (only on GCP for now)
3. Retry auto-attach in case of failures

(1) is handled by a systemd unit (`ua-auto-attach.service`) delivered by a separate package called `ubuntu-advantage-pro`. This package is only installed on Ubuntu Pro Cloud images. In this way, an instance launched from an Ubuntu Pro Cloud image knows that it needs to auto-attach.

(2) and (3) are both handled in a systemd unit (`ubuntu-advantage.service`) that is present on all Ubuntu machines (including non-Pro).

Below is a flow chart intended to describe how all of these methods and systemd units interact.

```mermaid
graph TD;
    %% nodes
    %%%% decisions
    is_pro{Is -pro installed?}
    auto_outcome{Success?}
    is_attached{Attached?}
    should_run_daemon{on GCP? or retry flag set?}
    is_gcp{GCP?}
    is_retry{retry flag set?}
    is_gcp_pro{Pro license detected?}
    daemon_attach_outcome{Success?}
    daemon_attach_outcome2{Success?}

    %%%% actions
    auto_attach[/Try to Attach/]
    trigger_retry[/Create Retry Flag File/]
    trigger_retry2[/Create Retry Flag File/]
    poll_gcp[/Poll for GCP Pro license/]
    daemon_attach[/Try to Attach/]
    daemon_attach2[/Try to Attach/]
    wait[/Wait a while/]
    
    %%%% systemd units
    auto(ua-auto-attach.service)
    daemon(ubuntu-advantage.service)

    %%%% states
    done([End])


    %% arrows
    is_pro--Yes-->auto
    auto-->auto_attach
    subgraph ua-auto-attach.service blocks boot
        auto_attach-->auto_outcome
        auto_outcome--No-->trigger_retry
    end

    is_pro--No-->is_attached
    trigger_retry-->is_attached
    auto_outcome--Yes-->is_attached
    is_attached--No-->should_run_daemon
    is_attached--Yes-->done
    should_run_daemon--No-->done
    should_run_daemon--Yes-->daemon

    daemon-->is_gcp
    subgraph ubuntu-advantage.service
        is_gcp--Yes-->poll_gcp
        subgraph poll for pro license
            poll_gcp-->is_gcp_pro
            is_gcp_pro--No-->poll_gcp
            is_gcp_pro--Yes-->daemon_attach
            daemon_attach-->daemon_attach_outcome
            daemon_attach_outcome--No-->trigger_retry2
        end
        trigger_retry2-->is_retry
        is_gcp--No-->is_retry
        is_retry--Yes-->daemon_attach2
        subgraph retry auto-attach
            daemon_attach2-->daemon_attach_outcome2
            daemon_attach_outcome2--No-->wait
        end
        wait-->daemon_attach2
    end

    daemon_attach_outcome--Yes-->done
    is_retry--No-->done
    daemon_attach_outcome2--Yes-->done
    daemon_attach_outcome2--Failed for a month-->done
```
