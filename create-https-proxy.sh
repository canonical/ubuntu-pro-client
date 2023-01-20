set -x

lxc launch ubuntu-daily:jammy https-proxy-j
DOMAIN=https-proxy-j.lxd

lxc exec https-proxy-j -- apt update
lxc exec https-proxy-j -- apt upgrade -y
lxc exec https-proxy-j -- sudo apt-get install openssl libssl-dev ssl-cert squid-openssl -y
lxc exec https-proxy-j -- openssl req -newkey rsa:4096 -x509 -sha256 -days 3650 -nodes -out ca.crt -keyout ca.key -subj "/C=CN/ST=BJ/O=STS/CN=CA"
lxc exec https-proxy-j -- openssl genrsa -out $DOMAIN.key
lxc exec https-proxy-j -- openssl req -new -key $DOMAIN.key -out $DOMAIN.csr -subj "/C=CN/ST=BJ/O=STS/CN=$DOMAIN"
lxc exec https-proxy-j -- openssl x509 -req -in $DOMAIN.csr -out $DOMAIN.crt -sha256 -CA ca.crt -CAkey ca.key -CAcreateserial -days 3650
lxc file push ./squid.conf https-proxy-j/etc/squid/squid.conf
lxc exec https-proxy-j -- systemctl restart squid
