$chroot_mode = 'unshare';
$unshare_mmdebstrap_keep_tarball = 1;
$unshare_tmpdir_template = '/var/tmp/tmp.sbuild.XXXXXXXXXX';
$unshare_mmdebstrap_extra_args = [
    '*' => ['--components=main,universe'],
];
1;
