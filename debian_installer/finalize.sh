mkdir -p /etc/salt/minion.d/

# Add the master to point at to the machine
cat > /etc/salt/minion.d/master.conf << EOF
master: 192.168.1.1
master_finger: ba:42:e5:d8:e6:3f:ec:ff:a4:7b:c3:cd:24:74:2a:8b
EOF

echo 'startup_states: highstate' > /etc/salt/minion.d/startup.conf

# Update to Testing
cat > /etc/apt/sources.list <<EOF
deb http://linux-ftp.jf.intel.com/pub/mirrors/debian/ testing main
deb-src http://linux-ftp.jf.intel.com/pub/mirrors/debian/ testing main
EOF

apt-get update -y
for _ in `seq 3`; do
    DEBIAN_FRONTEND=noninteractive \
    APT_LISTCHANGES_FRONTEND=mail \
        apt-get -o Dpkg::Options::="--force-confdef" \
        --force-yes -fuy dist-upgrade
done

# Enable and disable some services
systemctl enable avahi-daemon salt-minion
systemctl disable saned hdparm
