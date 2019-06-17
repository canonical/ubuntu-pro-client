# Using multipass For Development

This is a document outlining how one developer has configured their
system to enable the easy use of multipass for UA client development.
It is intended to be used as a reference point for other developers to
build their own workflows, rather than as a single, mandated workflow.

## Create cloud-config for instance configuration

This is the cloud-config that I use (stored in
`~/rc/multipass-cloud-config`):

```yaml
#cloud-config
apt:
  http_proxy: http://10.76.88.1:3142
  https_proxy: "DIRECT"
apt_http_proxy: http://10.76.88.1:3142  # support trusty
apt_https_proxy: "DIRECT"
packages:
  - equivs
  - git
  - libpython3-dev
  - libffi-dev
  - sshfs  # for `multipass mount`; save time by installing it ourselves
  - ubuntu-dev-tools
  - virtualenvwrapper
runcmd:
  # The expectation is that we will mount our local development repo in to the
  # VM, but to install the build-deps at launch time we clone the public repo
  # temporarily
  - 'git clone https://github.com/CanonicalLtd/ubuntu-advantage-client /var/tmp/uac'
  - 'mk-build-deps -t "apt-get --no-install-recommends --yes" -r -i /var/tmp/uac/debian/control'
  - 'rm -rf /var/tmp/uac'
  - 'echo alias pytest=py.test-3 >> /home/multipass/.bashrc'
ssh_import_id:
  - daniel-thewatkins
```

## Create an alias to launch multipass instances

Adding these lines to my `.aliases` file (which is source'd by my
`.zshrc`) means I can launch a multipass VM ready for development with
a single command:

```sh
alias mpl="multipass launch --cloud-init ~/rc/multipass-cloud-config"

uamultipass() {
    SERIES="$1"
    if [ -z "$SERIES" ]; then
        echo "needs argument"
        return 1
    fi
    name="$SERIES-$(date +%y%m%d-%H%M)"
    mpl -n "$name" $SERIES

    while ! multipass exec "$name" -- test -e /run/cloud-init/result.json; do
        sleep 5
    done

    multipass mount /home/daniel/dev/ubuntu-advantage-client $name:/home/multipass/ubuntu-advantage-client
}
```
