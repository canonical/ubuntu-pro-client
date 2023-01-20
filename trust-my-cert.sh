set -x
name=$1
lxc file pull https-proxy-j/root/ca.crt .
lxc file push ./ca.crt $name/root/ca.crt
lxc exec $name -- cp ca.crt /usr/local/share/ca-certificates
lxc exec $name -- update-ca-certificates

