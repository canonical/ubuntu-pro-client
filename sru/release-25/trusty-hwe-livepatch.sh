#!/bin/sh
set -x
# Manually deploy on a trusty lxc vm
CONTRACT_TOKEN=TOKEN
series=trusty
name=$series-uac

cat > install_hwe_kernel.sh << EOF
sudo apt-get -yq install --install-recommends linux-generic-lts-xenial xserver-xorg-core-lts-xenial xserver-xorg-lts-xenial xserver-xorg-video-all-lts-xenial xserver-xorg-input-all-lts-xenial libwayland-egl1-mesa-lts-xenial
EOF

cat > install_uac_from_master.sh << EOF
    sudo apt-get -yq install git make
    git clone https://github.com/canonical/ubuntu-advantage-client.git /tmp/uac
    cd /tmp/uac/
    sudo make deps
    sudo dpkg-buildpackage -us -uc
EOF

create_base_vm() {
    multipass delete $name
    multipass purge
    multipass launch $series --name $name
}

install_hwe_kernel() {
    multipass transfer install_hwe_kernel.sh $name:/tmp/
    multipass exec $name bash /tmp/install_hwe_kernel.sh
    multipass restart $name
    sleep 20

    kernel_version=$(multipass exec $name -- uname -r)

    if [[ "$kernel_version" == 4.4.0* ]] ; then
        echo "SUCCESS: kernel was successfully updated to HWE: $kernel_version"
    else
        echo "FAILURE: kernel was not updated to HWE: $kernel_version"
    fi
}

update_uaclient() {
    name_build=$series-uac-build
    pkg_name=ubuntu-advantage-tools_25.0_amd64.deb
    multipass launch $series --name $name_build
    multipass transfer install_uac_from_master.sh $name_build:/tmp/
    multipass exec $name_build bash /tmp/install_uac_from_master.sh
    multipass transfer $name_build:/tmp/$pkg_name /tmp/
    multipass transfer /tmp/$pkg_name $name:/tmp/
    multipass exec $name -- sudo apt-get remove ubuntu-advantage-tools --assume-yes
    multipass exec $name -- sudo dpkg -i /tmp/$pkg_name

    uac_version=$(multipass exec $name -- ua version)

    if [[ "$uac_version" == 25.0* ]] ; then
        echo "SUCCESS: uaclient was successfully updated to: $uac_version"
    else
        echo "FAILURE: uaclient was not updated"
    fi

    multipass delete $name_build
    multipass purge
}

check_livepatch_is_not_installed() {
    multipass exec $name -- which canonical-livepatch
    return_code=$(multipass exec $name -- echo $?)

    if [ "$return_code" = "1" ] ; then
        echo "SUCESS: canonical-livepatch is not found before enabling it"
    else
        echo "FAILURE: canonical-livepatch was found before enabling it"
    fi
}

attach_token_in_uaclient() {
    multipass exec $name -- sudo ua attach $CONTRACT_TOKEN
}

enable_livepatch() {
    multipass exec $name -- sudo ua enable livepatch
}

check_livepatch() {
    return_str=$(multipass exec $name -- sudo canonical-livepatch status | grep running)
    expected_str="  running: true"

    if [ "$return_str" = "$expected_str" ]; then
        echo "SUCCESS: livepatch was enabled and is running"
    else
        echo "FAILURE: livepatch is not running"
    fi
}


create_base_vm
install_hwe_kernel
update_uaclient
check_livepatch_is_not_installed
attach_token_in_uaclient
enable_livepatch
check_livepatch
