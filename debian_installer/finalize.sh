# Copyright (C) Intel Corp.  2014.  All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE COPYRIGHT OWNER(S) AND/OR ITS SUPPLIERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#  **********************************************************************/
#  * Authors:
#  *   Dylan Baker <dylanx.c.baker@intel.com>
#  **********************************************************************/

mkdir -p /etc/salt/minion.d/

# Add the master to point at to the machine
cat > /etc/salt/minion.d/master.conf << EOF
master: 192.168.1.1
master_finger: 1f:69:bc:a8:31:0f:c5:75:17:bc:4f:d6:9e:ab:35:fb:f1:11:19:52:ee:63:27:7f:e8:4b:b1:59:8d:d3:cb:82
EOF

echo 'startup_states: highstate' > /etc/salt/minion.d/startup.conf

# Add our nfs mount to fstab
echo 'otc-mesa-android.local:/srv/jenkins       /mnt/jenkins    nfs     _netdev,auto,async,comment=systemd.automount        0       0' >> /etc/fstab

# Create a systemd .network file for the network interfac
name=$(ip addr show scope link up | grep -v DOWN | grep UP | awk '{print $2}' | sed 's@:@@')

mkdir -p /etc/systemd/network

cat > "/etc/systemd/network/${name}.network" << EOF
[Match]
Name=${name}

[Network]
DHCP=yes
EOF

# setup resolve for systemd-resolved
rm /etc/resolv.conf
ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf

# Remove interfaces to keep debian's interfaces from coming up as well as systemd
rm /etc/network/interfaces

# Copy the loader from ${EFI}/debian/grubx64.efi to ${EFI}/boot/bootx64.efi
# This is a work-around for broken EFI implementations.
mkdir -p /boot/efi/EFI/boot/
cp /boot/efi/EFI/debian/grubx64.efi /boot/efi/EFI/boot/bootx64.efi

# Enable and disable some services
systemctl enable systemd-networkd systemd-resolved avahi-daemon salt-minion
systemctl disable networking
