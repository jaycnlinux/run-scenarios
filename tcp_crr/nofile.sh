echo "fs.nr_open=50000000"  >> /etc/sysctl.conf
echo "fs.file-max=50000000" >> /etc/sysctl.conf
echo "* soft nofile 50000000" >> /etc/security/limits.conf
echo "* hard nofile 50000000" >> /etc/security/limits.conf
