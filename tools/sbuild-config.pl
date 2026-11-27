$chroot_mode = 'unshare';
$unshare_mmdebstrap_keep_tarball = 1;
$unshare_tmpdir_template = '/var/tmp/tmp.sbuild.XXXXXXXXXX';
$unshare_mmdebstrap_extra_args = [
    '*' => ['--components=main,universe'],
    # The development release needs dependencies from its proposed pocket.
    # Tenacious is the current development release; update this block when it
    # changes. The mirror is archive.ubuntu.com, so this only works on amd64 and
    # i386 hosts. Keep the release as APT's default so proposed is used only when
    # required by the package dependency resolver.
    'tenacious' => [
        '--setup-hook=echo "deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu tenacious-proposed main universe" > "$1"/etc/apt/sources.list.d/proposed.list',
        '--aptopt=APT::Default-Release "tenacious";',
    ],
];
1;
