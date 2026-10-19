$chroot_mode = 'unshare';
$unshare_tmpdir_template = '/var/tmp/tmp.sbuild.XXXXXXXXXX';
$unshare_mmdebstrap_extra_args = [
    '*' => ['--components=main,universe'],
    # The development release needs dependencies from its proposed pocket.
    # Stonking is the current development release; update this block when it
    # changes. Keep the release as APT's default so proposed is used only when
    # required by the package dependency resolver.
    'stonking' => [
        '--include=ca-certificates',
        '--setup-hook=echo "deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://snapshot.ubuntu.com/ubuntu stonking-proposed main universe" > "$1"/etc/apt/sources.list.d/proposed.list',
        '--aptopt=APT::Default-Release "stonking";',
    ],
];
1;
