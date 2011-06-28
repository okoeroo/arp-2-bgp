#!/usr/bin/env python

from distutils.core import setup

setup(
    name="arp-2-bgp",
    version="0.0.1",
    description="Based on Arp information announce routes to a particular host using BGP",
    keywords = 'arista networks switch arp bgp BGP',
    author="Oscar Koeroo",
    author_email="okoeroo@nikhef.nl",
    url="https://github.com/okoeroo/arp-2-bgp",
    packages=["arp2bgp"],
    data_files=[  ('/etc', ['arp2bgp/arp-2-bgp.conf']),
                  ('/etc/cron.d', ['arp2bgp/arp-2-bgp.cron'])
               ],
    options = {'bdist_rpm':{'post_install' : 'package_scripts/post_install',
                            'post_uninstall' : 'package_scripts/post_uninstall'}},
    long_description=open('README').read()
)

