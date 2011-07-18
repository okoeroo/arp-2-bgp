#!/bin/sh

### Website: https://github.com/okoeroo/arp-2-bgp
### Author:  Oscar Koeroo <okoeroo@nikhef.nl>


EOS_RC_PATH="${EOS_RC_PATH:=/mnt/flash}"
EOS_RC_D="eos.rc.d"
EOS_SYSCONF_DIR="${EOS_RC_PATH}/eos.sysconfig"

A2B_NAME="arp-2-bgp"
A2B_SCRIPT="arp-2-bgp.sh"
A2B_CONF="arp-2-bgp.conf"
A2B_PERSIST_CONF_PATH="${EOS_SYSCONF_DIR}/${A2B_NAME}/${A2B_CONF}"
A2B_CONF_PATH="/etc/${A2B_CONF}"



ln -s ${A2B_PERSIST_CONF_PATH} ${A2B_CONF_PATH}

