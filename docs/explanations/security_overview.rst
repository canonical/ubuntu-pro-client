.. _security_overview:

Security Overview
*****************************

Ubuntu Pro Client (``pro``) attaches an Ubuntu machine to an Ubuntu Pro
subscription and enables the services that the subscription includes. This
page describes the security properties of ``pro`` itself. For how ``pro``
helps you fix vulnerabilities in installed packages, see
:ref:`index_security`.

System overview
===============

.. mermaid::

   flowchart LR
     subgraph host["Ubuntu machine"]
       admin["root"]
       user["Unprivileged users"]
       pro["Ubuntu Pro Client"]
       machine["Client machine"]
       admin -- "all commands" --> pro
       user -- "read-only commands" --> pro
       pro -- "configures" --> machine
     end
     contracts["Contract server<br/>(contracts.canonical.com)"]
     services["Pro-enabled services"]
     pro -- "HTTPS" --> contracts
     machine --> services

The system has four parts:

Ubuntu Pro Client
   An agent on the client machine. It gets the machine's entitlements and
   credentials from the contract server, and uses them to configure the
   client machine for each Pro-enabled service.

Client machine
   The Ubuntu machine where ``pro`` is installed. Its own software, such as
   APT and the Livepatch client, connects to the Pro-enabled services.

Contract server
   ``contracts.canonical.com``. It checks the tokens that ``pro`` sends,
   tells ``pro`` which services the machine can use, and receives the data
   described in :ref:`what-data-is-collected`.

Pro-enabled services
   The back ends that the client machine uses after ``pro`` enables a
   service:

   * **Ubuntu Pro APT repositories** (``esm.ubuntu.com``) serve the packages
     for ``anbox-cloud``, ``cc-eal``, ``cis`` and ``usg``, ``esm-apps``,
     ``esm-infra``, ``esm-apps-legacy``, ``esm-infra-legacy``, ``fips``,
     ``fips-updates``, ``fips-preview``, ``realtime-kernel``, ``ros``, and
     ``ros-updates``.
   * **Snap Store** serves the snaps that some services need, such as the
     Livepatch client.
   * **Livepatch server** serves kernel livepatches to the Livepatch client.
   * **Landscape server** is the Landscape SaaS or self-hosted server that
     the Landscape client registers with.

The system has three trust boundaries:

* **Root and unprivileged users.** Only root can run commands that
  change the state of ``pro``: ``attach``, ``auto-attach``, ``detach``,
  ``enable``, ``disable``, ``refresh``, ``config set``, ``config unset``,
  and ``fix`` without ``--dry-run``. Unprivileged users can run read-only
  commands such as ``pro status`` and ``pro security-status``.
* **The client machine and the contract server.** ``pro`` connects to the
  contract server over HTTPS and sends a bearer token with each request.
  After the machine is attached, this token is the machine token.
* **The client machine and the Pro-enabled services.** APT authenticates to
  the Ubuntu Pro APT repositories with credentials that ``pro`` stores on
  the machine. ``pro`` gives the Livepatch client a token when it enables
  Livepatch. For Landscape, ``pro`` passes the ``landscape-config`` options
  that root provides. See :ref:`network_requirements` for the endpoints.

Security controls
-----------------

Root-only commands
   Commands that change the machine check that they run as root. This stops
   unprivileged users from attaching, detaching, or changing services.

Root-only secret files
   ``pro`` stores the machine token in
   ``/var/lib/ubuntu-advantage/private/`` (directory mode ``0700``, files
   mode ``0600``). It stores APT repository credentials in
   ``/etc/apt/auth.conf.d/90ubuntu-advantage`` (mode ``0600``). This stops
   unprivileged users from reading credentials. The world-readable copy of
   the machine token file, ``/var/lib/ubuntu-advantage/machine-token.json``,
   does not contain the machine token.

Log redaction
   ``pro`` removes tokens and other known secrets from log entries before
   it writes them. ``pro collect-logs`` also redacts the files it collects.
   This stops secrets from leaking through logs and bug reports.

TLS certificate verification
   ``pro`` uses HTTPS for Canonical services and verifies server certificates
   against the system's trusted CA certificates. This stops an attacker on
   the network from impersonating Canonical services.

Signed APT repositories
   APT verifies packages from Ubuntu Pro repositories with Canonical signing
   keys that the ``ubuntu-pro-client`` package installs. This stops APT from
   installing tampered packages.

Confined network services
   ``apt-news.service`` and ``esm-cache.service`` download and parse data
   from the network. They run under AppArmor profiles and with a reduced set
   of Linux capabilities. This limits what an attacker can do through a
   malicious response.

Risks
=====

Token disclosure
   A person who has your Ubuntu Pro token can attach machines to your
   subscription and use its services. Treat the token as a secret. See
   :ref:`pro_token_and_machine_usage`.

Disabled security services
   If you disable ``esm-infra``, ``esm-apps``, or ``livepatch``, the machine
   stops receiving the security updates that those services provide.

Security of data
================

Data sent to Canonical
   See :ref:`what-data-is-collected`.

Data stored on the machine
   ``pro`` stores the following data:

   * ``/var/lib/ubuntu-advantage/``: machine token, contract information,
     configuration, and state.
   * ``/etc/apt/auth.conf.d/90ubuntu-advantage``: APT repository credentials.
   * ``/var/log/ubuntu-advantage*.log``: logs. Logrotate rotates them
     monthly and keeps 6 rotations.
   * ``~/.cache/ubuntu-pro/ubuntu-pro.log``: logs from commands that an
     unprivileged user runs.

Data deletion
   ``pro detach`` disables all services, removes their APT credentials, and
   deletes the machine token and state files.

   ``apt purge ubuntu-pro-client`` deletes ``/var/lib/ubuntu-advantage/``,
   the APT credentials file, the logs in ``/var/log``, and the Pro signing
   keys in ``/etc/apt/trusted.gpg.d/``. It does not delete log files in
   user home directories.

Cryptography
   ``pro`` uses TLS for connections to Canonical services. APT uses
   GPG signatures to verify packages from Ubuntu Pro repositories.

Security support
================

``ubuntu-pro-client`` is a package in the Ubuntu archive. For the Ubuntu
releases that ``pro`` supports, see :ref:`support_matrix`. For the support
period of each release, see the `Ubuntu release cycle`_.

.. _Ubuntu release cycle: https://ubuntu.com/about/release-cycle
