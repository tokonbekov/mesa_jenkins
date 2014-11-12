#!/bin/bash
# Run a few commands in the target system after the install

# Enables render-nodes as needed by gbm and disables the software_cmd_parser
sed -i -e 's!GRUB_CMDLINE_LINUX=""!GRUB_CMDLINE_LINUX="drm.rnodes=1 i915.enable_cmd_parser=0"!g' /etc/default/grub

# Replace wheezy with sid in the sources.list file, then updates to sid, the
# does a dist-upgrade to sid in a fully non-interactive way
cat > /etc/apt/sources.list << EOF
deb http://linux-ftp.jf.intel.com/pub/mirrors/debian/ sid main
deb-src http://linux-ftp.jf.intel.com/pub/mirrors/debian/ sid main
EOF

apt-get update -y
DEBIAN_FRONTEND=noninteractive \
APT_LISTCHANGES_FRONTEND=mail \
	apt-get -o Dpkg::Options::="--force-confdef" \
	--force-yes -fuy dist-upgrade

# systemd-sysv requires '--force-yes' to be installed without supervision, it
# cannot be isntalled in package select. It also must be installed after the sid
# update has happened since it doesn't seem possible to automate in wheezy
apt-get install -y --force-yes systemd-sysv

# install additional packages. Many of these are i386 dev packages that cannot
# be co-installed with the amd64 versions in debian stale but can on sid
apt-get install -y --force-yes \
	libdrm2 libdrm2:i386 \
	freeglut3 freeglut3:i386 \
	gcc-4.9-base gcc-4.9-base:i386 \
	libc6 libc6:i386 \
	libc6-dev libc6-dev:i386\
	libegl1-mesa libegl1-mesa:i386 \
	libegl1-mesa-dev \
	libelf-dev libelf-dev:i386 \
	libexpat1-dev libexpat1-dev:i386 \
	libffi-dev libffi-dev:i386 \
	libffi6 libffi6:i386 \
	libffi-dev \
	libgbm1 libgbm1:i386 \
	libgbm-dev \
	libgcc1 libgcc1:i386 \
	libgl1-mesa-dev \
	libgl1-mesa-dri libgl1-mesa-dri:i386 \
	libgl1-mesa-glx libgl1-mesa-glx:i386 \
	libegl1-mesa libegl1-mesa:i386 \
	libegl1-mesa-drivers libegl1-mesa-drivers:i386 \
	libglapi-mesa \
	libglu1-mesa libglu1-mesa:i386 \
	libglu1-mesa-dev \
	libllvm3.4 libllvm3.4:i386 \
	libpciaccess-dev libpciaccess-dev:i386 \
	libpciaccess0 libpciaccess0:i386 \
	libpthread-stubs0-dev \
	libtinfo-dev libtinfo-dev:i386 \
	libudev-dev libudev-dev:i386 \
	libvdpau-dev libvdpau-dev:i386 \
	libx11-dev libx11-dev:i386 \
	libx11-xcb-dev libx11-xcb-dev:i386 \
	libxcb-dri2-0-dev libxcb-dri2-0-dev:i386 \
	libxcb-dri3-dev libxcb-dri3-dev:i386 \
	libxcb-glx0-dev libxcb-glx0-dev:i386 \
	libxcb-present-dev libxcb-present-dev:i386 \
	libxcb-randr0-dev libxcb-randr0-dev:i386 \
	libxcb-sync-dev libxcb-sync-dev:i386 \
	libxcb-xfixes0-dev libxcb-xfixes0-dev:i386 \
	libxdamage-dev libxdamage-dev:i386 \
	libxext-dev libxext-dev:i386 \
	libxfixes-dev libxfixes-dev:i386 \
	libxrender1 libxrender1:i386 \
	libxshmfence-dev libxshmfence-dev:i386 \
	libxxf86vm-dev libxxf86vm-dev:i386 \
	linux-libc-dev linux-libc-dev:i386 \
	x11proto-dri2-dev \
	x11proto-dri3-dev \
	x11proto-gl-dev \
	x11proto-present-dev \

# Disable the pc-spkr module
echo 'blacklist pcspkr' > /etc/modprobe.d/pcspkr.conf

# Enable and disable some services
systemctl enable ntp avahi-daemon
systemctl disable saned hdparm

# Create a wrapper for git that uses tsocks to get through the proxy
[[ -z '/usr/local/bin' ]] && mkdir -p /usr/local/bin
cat > /usr/local/bin/git <<EOF
#!/bin/bash

/usr/bin/tsocks /usr/bin/git \$*
EOF

# make it executable
chmod +x /usr/local/bin/git

# Add our nfs mount to fstab
echo 'otc-gfxtest-01.jf.intel.com:/srv/jenkins       /mnt/jenkins    nfs     defaults,comment=systemd.automount        0       0' >> /etc/fstab

# Create the jenkins directory
mkdir /mnt/jenkins
chmod 0666 /mnt/jenkins

# Write a tsocks configuration
cat > /etc/tsocks.conf <<EOF
local = 192.168.0.0/255.255.255.0
local = 134.134.0.0/255.255.0.0
local = 10.0.0.0/255.0.0.0
server = 10.7.211.16
server_type = 5
server_port = 1080
EOF

# Symlink some i386 dev packages.
# This works around debian bugs
for x in libEGL libGLU libgbm libGL libwayland-client libwayland-egl; do
	ln -s "/usr/lib/i386-linux-gnu/${x}.so.1" "/usr/lib/i386-linux-gnu/${x}.so"
done

# Modify the ntp server to use the local mirror, not the debian mirrors
sed -i -e 's!^server!#server!g' /etc/ntp.conf
sed -i -e 's!#server ntp.your-provider.example!server amr.corp.intel.com!g' /etc/ntp.conf

# use ntp to set the clock, force it to sync regardless
systemctl stop ntp
ntpd -gq

# Configure the cache size for the jenkins user
su jenkins -c 'ccache -M 10G'

echo -e "jenkins\tALL=(ALL:ALL) /sbin/reboot, NOPASSWD: /sbin/reboot\n" >> /etc/sudoers
