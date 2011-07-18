#!/usr/bin/env python

from distutils.core import setup


name="arp-2-bgp"
version="0.0.2"
description="Based on Arp information announce routes to a particular host using BGP"
keywords = 'arista networks switch arp bgp BGP'
author="Oscar Koeroo"
author_email="okoeroo@nikhef.nl"
url="https://github.com/okoeroo/arp-2-bgp"
data_files=[  ('/mnt/flash/eos.sysconfig/arp-2-bgp', ['arp2bgp/arp-2-bgp.conf']),
              ('/etc/cron.d',                        ['arp2bgp/arp-2-bgp.cron']),
              ('/usr/bin',                           ['arp2bgp/arp-2-bgp.py'])
           ]
options = {'bdist_rpm':{'post_install' : 'package_scripts/post_install',
                      'post_uninstall' : 'package_scripts/post_uninstall'}}
long_description=open('README').read()


setup(
    name=name + "-arista",
    version=version,
    description=description,
    keywords=keywords,
    author=author,
    author_email=author_email,
    url=url,
    data_files=data_files,
    options=options,
    long_description=long_description
)

