rpm -Uvh perl-5.16.3-292.el7.x86_64.rpm --nodeps
rpm -Uvh perl-libs-5.16.3-292.el7.x86_64.rpm
rpm -Uvh perl-macros-5.16.3-292.el7.x86_64.rpm
rpm -Uvh perl-parent-0.225-244.el7.noarch.rpm
rpm -Uvh perl-Carp-1.26-244.el7.noarch.rpm --nodeps
rpm -Uvh perl-Exporter-5.68-3.el7.noarch.rpm
rpm -Uvh perl-constant-1.27-2.el7.noarch.rpm
rpm -Uvh perl-Time-Local-1.2300-2.el7.noarch.rpm
rpm -Uvh perl-HTTP-Tiny-0.033-3.el7.noarch.rpm
rpm -Uvh perl-Time-HiRes-1.9725-3.el7.x86_64.rpm
rpm -Uvh perl-threads-1.87-4.el7.x86_64.rpm
rpm -Uvh perl-Socket-2.010-4.el7.x86_64.rpm
rpm -Uvh perl-Text-ParseWords-3.29-4.el7.noarch.rpm
rpm -Uvh perl-Filter-1.49-3.el7.x86_64.rpm
rpm -Uvh perl-Pod-Escapes-1.04-292.el7.noarch.rpm
rpm -Uvh perl-Scalar-List-Utils-1.27-248.el7.x86_64.rpm
rpm -Uvh perl-Storable-2.45-3.el7.x86_64.rpm
rpm -Uvh perl-threads-shared-1.43-6.el7.x86_64.rpm
rpm -Uvh perl-PathTools-3.40-5.el7.x86_64.rpm
rpm -Uvh perl-File-Path-2.09-2.el7.noarch.rpm
rpm -Uvh perl-File-Temp-0.23.01-3.el7.noarch.rpm
rpm -Uvh perl-Pod-Usage-1.63-3.el7.noarch.rpm --nodeps
rpm -Uvh perl-Getopt-Long-2.40-2.el7.noarch.rpm
rpm -Uvh perl-Encode-2.51-7.el7.x86_64.rpm
rpm -Uvh perl-Getopt-Long-2.40-2.el7.noarch.rpm
rpm -Uvh perl-Pod-Simple-3.28-4.el7.noarch.rpm
rpm -Uvh perl-podlators-2.5.1-3.el7.noarch.rpm
rpm -Uvh perl-Pod-Perldoc-3.20-4.el7.noarch.rpm



wget http://www.tortall.net/projects/yasm/releases/yasm-1.3.0.tar.gz
tar -zxvf yasm-1.3.0.tar.gz
cd yasm-1.3.0
./configure;make;make install
wget http://www.ffmpeg.org/releases/ffmpeg-3.1.tar.gz
tar -xzvf ffmpeg-3.1.tar.gz
cd ffmpeg-3.1
./configure;make -j 4;make install
