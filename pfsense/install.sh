echo "NOTICE:"
echo "This is going to install the custom RADIUS server for the captive portal"
echo "and run it in screen. We assume it is being run on a FreeBSD pfSense box."
echo
sleep 3
pkg_add -r python
pkg_add -r py26-setuptools
pkg_add -r screen
rehash
fetch http://pypi.python.org/packages/source/p/pyrad/pyrad-1.1.tar.gz
tar -zxvf pyrad-1.1.tar.gz
cd pyrad-1.1
python setup.py install
mkdir -p /home/captiveportal
cd /home/captiveportal
fetch https://github.com/progrium/hd-captiveportal/raw/master/pfsense/dictionary
fetch https://github.com/progrium/hd-captiveportal/raw/master/pfsense/bridge.py
screen python bridge.py