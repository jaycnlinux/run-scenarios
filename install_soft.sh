yum -y install unzip gcc gcc-c++ epel-release
wget --no-check-certificate https://github.com/HewlettPackard/netperf/archive/netperf-2.7.0.zip -O netperf-2.7.0.zip
unzip netperf-2.7.0.zip
cd netperf-netperf-2.7.0/
./configure && make && make install
cd
yum -y install memcached libmemcached
yum -y install qperf
yum -y install nginx
