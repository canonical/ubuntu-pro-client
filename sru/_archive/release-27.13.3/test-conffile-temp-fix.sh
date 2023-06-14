#!/bin/bash
set -e

function install_old_version {
    name=$1
    series=$2
    old_version=$3
    PACKAGE=ubuntu-advantage-tools
    ARCH=amd64
    echo -e "\n-------------------------------------------"
    echo "** installing $old_version"
    echo "-------------------------------------------"
    package_url=$(curl -s https://launchpad.net/ubuntu/$series/$ARCH/$PACKAGE/$old_version | grep -o "http://launchpadlibrarian.net/.*/${PACKAGE}_${old_version}_${ARCH}.deb")
    lxc exec $name -- wget -nv -O ua.deb $package_url
    lxc exec $name -- dpkg -i ./ua.deb
    lxc exec $name -- apt-cache policy ubuntu-advantage-tools
    echo "-------------------------------------------"
}

function upgrade_to_proposed {
    name=$1
    echo -e "\n-------------------------------------------"
    echo "** upgrading to 27.13.3 from proposed - VERIFY NO CONFFILE PROMPT"
    echo "-------------------------------------------"
    lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
    lxc exec $name -- apt-get update > /dev/null
    lxc exec $name -- apt-get install ubuntu-advantage-tools
    lxc exec $name -- apt-cache policy ubuntu-advantage-tools
    echo "-------------------------------------------"
}


function test_normal_upgrade {
    series=$1
    old_version=$2
    echo -e "\n\n###########################################"
    echo "## $series normal upgrade from $old_version to 27.13.3"
    echo "###########################################"
    name=$(echo $series-$old_version | tr .~ -)

    echo -e "\n-------------------------------------------"
    echo "** launching container"
    echo "-------------------------------------------"
    lxc launch -q ubuntu-daily:$series $name
    sleep 5
    lxc exec $name -- apt-get update > /dev/null
    lxc exec $name -- apt-get install debsums -y > /dev/null
    echo "-------------------------------------------"

    install_old_version $name $series $old_version

    upgrade_to_proposed $name

    echo -e "\n-------------------------------------------"
    echo "** Show uaclient.conf"
    echo "-------------------------------------------"
    lxc exec $name -- cat /etc/ubuntu-advantage/uaclient.conf
    echo "-------------------------------------------"
    echo -e "\n-------------------------------------------"
    echo "** debsums - VERIFY ALL OK"
    echo "-------------------------------------------"
    lxc exec $name -- debsums -e ubuntu-advantage-tools
    echo "-------------------------------------------"

    lxc delete --force $name
    echo "###########################################"
}

function test_apt_news_false_upgrade {
    series=$1
    old_version=$2
    echo -e "\n\n###########################################"
    echo "## $series apt_news=false upgrade from $old_version to 27.13.3"
    echo "###########################################"
    name=$(echo $series-$old_version | tr .~ -)

    echo -e "\n-------------------------------------------"
    echo "** launching container"
    echo "-------------------------------------------"
    lxc launch -q ubuntu-daily:$series $name
    sleep 5
    lxc exec $name -- apt-get update > /dev/null
    echo "-------------------------------------------"

    install_old_version $name $series $old_version

    echo -e "\n-------------------------------------------"
    echo "** pro config set apt_news=false"
    echo "-------------------------------------------"
    lxc exec $name -- pro config set apt_news=false
    echo "-------------------------------------------"
    echo -e "\n-------------------------------------------"
    echo "** Show uaclient.conf"
    echo "-------------------------------------------"
    lxc exec $name -- cat /etc/ubuntu-advantage/uaclient.conf
    echo "-------------------------------------------"

    upgrade_to_proposed $name

    echo -e "\n-------------------------------------------"
    echo "** Show uaclient.conf"
    echo "-------------------------------------------"
    lxc exec $name -- cat /etc/ubuntu-advantage/uaclient.conf
    echo "-------------------------------------------"

    lxc delete --force $name
    echo "###########################################"
}

function test_apt_news_true_upgrade {
    series=$1
    old_version=$2
    echo -e "\n\n###########################################"
    echo "## $series apt_news=true upgrade from $old_version to 27.13.3"
    echo "###########################################"
    name=$(echo $series-$old_version | tr .~ -)

    echo -e "\n-------------------------------------------"
    echo "** launching container"
    echo "-------------------------------------------"
    lxc launch -q ubuntu-daily:$series $name
    sleep 5
    lxc exec $name -- apt-get update > /dev/null
    lxc exec $name -- apt-get install debsums -y > /dev/null
    echo "-------------------------------------------"

    install_old_version $name $series $old_version

    echo -e "\n-------------------------------------------"
    echo "** pro config set apt_news=true"
    echo "-------------------------------------------"
    lxc exec $name -- pro config set apt_news=true
    echo "-------------------------------------------"
    echo -e "\n-------------------------------------------"
    echo "** Show uaclient.conf"
    echo "-------------------------------------------"
    lxc exec $name -- cat /etc/ubuntu-advantage/uaclient.conf
    echo "-------------------------------------------"

    upgrade_to_proposed $name

    echo -e "\n-------------------------------------------"
    echo "** Show uaclient.conf"
    echo "-------------------------------------------"
    lxc exec $name -- cat /etc/ubuntu-advantage/uaclient.conf
    echo "-------------------------------------------"
    echo -e "\n-------------------------------------------"
    echo "** debsums - VERIFY ALL OK"
    echo "-------------------------------------------"
    lxc exec $name -- debsums -e ubuntu-advantage-tools
    echo "-------------------------------------------"

    lxc delete --force $name
    echo "###########################################"
}


# xenial
test_normal_upgrade         xenial 27.11.3~16.04.1
test_normal_upgrade         xenial 27.12~16.04.1
test_normal_upgrade         xenial 27.13.1~16.04.1
test_normal_upgrade         xenial 27.13.2~16.04.1
test_apt_news_false_upgrade xenial 27.11.3~16.04.1
test_apt_news_false_upgrade xenial 27.12~16.04.1
test_apt_news_false_upgrade xenial 27.13.1~16.04.1
test_apt_news_false_upgrade xenial 27.13.2~16.04.1
test_apt_news_true_upgrade  xenial 27.11.3~16.04.1
test_apt_news_true_upgrade  xenial 27.12~16.04.1
test_apt_news_true_upgrade  xenial 27.13.1~16.04.1
test_apt_news_true_upgrade  xenial 27.13.2~16.04.1
# bionic
test_normal_upgrade         bionic 27.11.3~18.04.1
test_normal_upgrade         bionic 27.12~18.04.1
test_normal_upgrade         bionic 27.13.1~18.04.1
test_normal_upgrade         bionic 27.13.2~18.04.1
test_apt_news_false_upgrade bionic 27.11.3~18.04.1
test_apt_news_false_upgrade bionic 27.12~18.04.1
test_apt_news_false_upgrade bionic 27.13.1~18.04.1
test_apt_news_false_upgrade bionic 27.13.2~18.04.1
test_apt_news_true_upgrade  bionic 27.11.3~18.04.1
test_apt_news_true_upgrade  bionic 27.12~18.04.1
test_apt_news_true_upgrade  bionic 27.13.1~18.04.1
test_apt_news_true_upgrade  bionic 27.13.2~18.04.1
# focal
test_normal_upgrade         focal 27.11.3~20.04.1
test_normal_upgrade         focal 27.12~20.04.1
test_normal_upgrade         focal 27.13.1~20.04.1
test_normal_upgrade         focal 27.13.2~20.04.1
test_apt_news_false_upgrade focal 27.11.3~20.04.1
test_apt_news_false_upgrade focal 27.12~20.04.1
test_apt_news_false_upgrade focal 27.13.1~20.04.1
test_apt_news_false_upgrade focal 27.13.2~20.04.1
test_apt_news_true_upgrade  focal 27.11.3~20.04.1
test_apt_news_true_upgrade  focal 27.12~20.04.1
test_apt_news_true_upgrade  focal 27.13.1~20.04.1
test_apt_news_true_upgrade  focal 27.13.2~20.04.1
# jammy
test_normal_upgrade         jammy 27.11.3~22.04.1
test_normal_upgrade         jammy 27.12~22.04.1
test_normal_upgrade         jammy 27.13.1~22.04.1
test_normal_upgrade         jammy 27.13.2~22.04.1
test_apt_news_false_upgrade jammy 27.11.3~22.04.1
test_apt_news_false_upgrade jammy 27.12~22.04.1
test_apt_news_false_upgrade jammy 27.13.1~22.04.1
test_apt_news_false_upgrade jammy 27.13.2~22.04.1
test_apt_news_true_upgrade  jammy 27.11.3~22.04.1
test_apt_news_true_upgrade  jammy 27.12~22.04.1
test_apt_news_true_upgrade  jammy 27.13.1~22.04.1
test_apt_news_true_upgrade  jammy 27.13.2~22.04.1
# kinetic
test_normal_upgrade         kinetic 27.11.3~22.10.1
test_normal_upgrade         kinetic 27.12~22.10.1
test_normal_upgrade         kinetic 27.13.1~22.10.1
test_normal_upgrade         kinetic 27.13.2~22.10.1
test_apt_news_false_upgrade kinetic 27.11.3~22.10.1
test_apt_news_false_upgrade kinetic 27.12~22.10.1
test_apt_news_false_upgrade kinetic 27.13.1~22.10.1
test_apt_news_false_upgrade kinetic 27.13.2~22.10.1
test_apt_news_true_upgrade  kinetic 27.11.3~22.10.1
test_apt_news_true_upgrade  kinetic 27.12~22.10.1
test_apt_news_true_upgrade  kinetic 27.13.1~22.10.1
test_apt_news_true_upgrade  kinetic 27.13.2~22.10.1
