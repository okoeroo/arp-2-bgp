#!/usr/bin/env python
# Copyright (c) 2011 Nikhef. All rights reserved.
# Author: Oscar Koeroo <okoeroo (at) nikhef (dot) nl>
# BSD Licence

import subprocess, os, sys
from subprocess import Popen, PIPE, STDOUT
import array
import ConfigParser
#import Tac, PyClient


dry_run          = False
run_in_test_mode = False

if run_in_test_mode:
    use_shell         = "/bin/sh"
    cmd_showconnected = "./test.sh"
    cmd_showinBGP     = "./test2.sh"
else:
    use_shell         = "/usr/bin/Cli"
    cmd_showconnected = "show ip arp"
    cmd_showinBGP     = "show run | include network"


class Arp2Bgp(object):
    table_ip_link = []
    table_in_bgp  = []
    table_bgp_add = None
    table_bgp_del = None
    include_interfaces        = None
    include_vlans             = None
    include_vlan_on_interface = None
    exclude_interfaces        = None
    exclude_vlans             = None
    exclude_vlan_on_interface = None
    defaults_selection        = 'ignore'  # Could be 'add', 'ignore' or 'remove'
    as_number                 = None

    def sendCmdOnCli(self, table_cmds=[]):
        if table_cmds == []:
            return None

        # Start up the Cli
        p = subprocess.Popen([use_shell], stdout=PIPE, stdin=PIPE, stderr=STDOUT)

        if run_in_test_mode:
            p.stdin.write('echo ena\n')
            for cmd in table_cmds:
                p.stdin.write('echo ' + cmd + '\n')
        else:
            if dry_run:
                print "ena"
            p.stdin.write('ena\n')
            for cmd in table_cmds:
                if dry_run:
                    print cmd
                p.stdin.write(cmd + '\n')

        my_stdout = p.communicate()[0]

        p.stdout.close()
        p.stdin.close()
        if p.wait() != 0:
            print "There were some errors"

        return my_stdout

    def __init__(self, conffile="/etc/arp-2-bgp.conf"):
        # The 'show run' command requires administrative privileges (aka root) to work
        if not run_in_test_mode:
            if os.geteuid() != 0:
                print "Error: You must use this tool with administrative privileges for it do do its business"
                sys.exit(1)

        # Read configuration file, if available
        self.load_configuration(conffile)

        # Read ARP information combined with active link/Vlan allocation
        self.load_ip_and_link_info()

        # Read current BGP table
        self.load_current_bgp_table()

    def load_configuration(self, conffile):
        # Open config file for exclusion rules.
        # Without a config file the script will sync all entries from the ARP table into BGP
        config = ConfigParser.RawConfigParser()
        self.use_config = False
        if conffile:
            try:
                try:
                    config.read(conffile)
                except:
                    print "Error in configuration file: Syntax error. Please fix the configuration file to be a proper .ini style config file"
                    sys.exit(1)

                if config.has_section('excludes'):
                    if config.has_option('excludes', 'interfaces'):
                        self.exclude_interfaces         = config.get("excludes", 'interfaces').replace(' ','').split(',')
                    if config.has_option('excludes', 'vlans'):
                        self.exclude_vlans              = config.get("excludes", 'vlans').replace(' ','').split(',')
                    if config.has_option('excludes', 'vlan_on_interface'):
                        self.exclude_vlan_on_interface = config.get("excludes", 'vlan_on_interface').replace(' ','').split(',')

                if config.has_section('includes'):
                    if config.has_option('includes', 'interfaces'):
                        self.include_interfaces         = config.get("includes", 'interfaces').replace(' ','').split(',')
                    if config.has_option('includes', 'vlans'):
                        self.include_vlans              = config.get("includes", 'vlans').replace(' ','').split(',')
                    if config.has_option('includes', 'vlan_on_interface'):
                        self.include_vlan_on_interface  = config.get("includes", 'vlan_on_interface').replace(' ','').split(',')

                if config.has_section('defaults'):
                    if config.has_option('defaults', 'selection'):
                        self.defaults_selection         = config.get("defaults", 'selection').replace(' ','')

                        if not (self.defaults_selection == 'add' or self.defaults_selection == 'ignore' or self.defaults_selection == 'remove'):
                            print "Error in configuration file: In section 'defaults' the 'selection' must be of the value 'add', 'ignore' or 'remove'"
                            raise

                    if config.has_option('defaults', 'asnumber'):
                        self.defaults_asnumber         = config.get("defaults", 'asnumber').replace(' ','')

                        if not self.defaults_asnumber.isdigit():
                            print "Error in configuration file: In section 'defaults' the 'asnumber' fails to be a number. Please use: asnumber = 1234"
                            raise
                    else:
                        print "Error in configuration file: In section 'defaults' the 'asnumber' option is missing. Please use: asnumber = 1234"
                        raise
                else:
                    print "Error in configuration file: Section 'defaults' is missing. Please add: [defaults]"
                    raise

                self.use_config = True
            except:
                sys.exit(1)

    def load_ip_and_link_info(self):
        # Get the arp table output

        # Get command output from the shell
        table_cmds = []
        table_cmds.append(cmd_showconnected)
        stdout = self.sendCmdOnCli(table_cmds)

        skipFirst = True
        for line in stdout.split('\n'):
            if skipFirst == True:
                skipFirst = False
                continue

            row = {}
            try:
                row['ip'] = line.split()[0]
            except:
                continue

            # The final part of the line holds the Ethernet device names and Vlans an IP was active on.
            # Must assume this list to be infinit for device names and the number of Vlans.
            # Key word substring matches:
            #     Vlan<number>
            #     Ethernet<device number>
            #     not learned
            num_link_elements = len(line.split()) - 3
            for i in xrange(num_link_elements):
                elem = line.split()[i + 3]
                elem = elem.rstrip(',')

                # Filter 'not learned'
                if elem.startswith('not'):
                    continue
                if elem.startswith('learned'):
                    continue

                # Separate the Vlans
                if elem.startswith('Vlan'):
                    if not 'vlans' in row:
                        row['vlans'] = []
                    row['vlans'].append(elem)

                # The rest must be aggregated links, ethernet or management interfaces
                else:
                    if not 'interfaces' in row:
                        row['interfaces'] = []
                    row['interfaces'].append(elem)

            # Add row to table
            self.table_ip_link.append(row)

    def load_current_bgp_table(self):
        # Get command output from the shell
        table_cmds = []
        table_cmds.append(cmd_showinBGP)
        stdout = self.sendCmdOnCli(table_cmds)

        for line in stdout.split('\n'):
            row = {}
            try:
                ip_subnet = line.split()[1]
            except:
                continue

            if ip_subnet.endswith('/32'):
                row['ip']   = ip_subnet.split('/')[0]
                row['mask'] = '/32'

            self.table_in_bgp.append(row)

    def use_configuration(self):
        return self.use_config

    def evaluate(self):
        self.filter_list()

    def is_vlan_included(self, ip_link):
        if 'vlans' in ip_link and self.include_vlans != None:
            if set(ip_link['vlans']) & set(self.include_vlans):
                return True
        return False

    def is_vlan_excluded(self, ip_link):
        if 'vlans' in ip_link and self.exclude_vlans != None:
            if set(ip_link['vlans']) & set(self.exclude_vlans):
                return True
        return False

    def is_interface_included(self, ip_link):
        if 'interfaces' in ip_link and self.include_interfaces != None:
            if set(ip_link['interfaces']) & set(self.include_interfaces):
                return True
        return False

    def is_interface_excluded(self, ip_link):
        if 'interfaces' in ip_link and self.exclude_interfaces != None:
            if set(ip_link['interfaces']) & set(self.exclude_interfaces):
                return True
        return False

    def is_vlan_on_interface_included(self, ip_link):
        if 'interfaces' in ip_link and 'vlans' in ip_link and self.include_vlan_on_interface != None:
            for vlan in ip_link['vlans']:
                for iface in ip_link['interfaces']:
                    for incl_vlan_on_iface in self.include_vlan_on_interface:
                        # Split Vlan<x>+Interface<y>
                        incl_iface = incl_vlan_on_iface.split('+')[0]
                        incl_vlan  = incl_vlan_on_iface.split('+')[1]

                        if iface == incl_iface and vlan == incl_vlan:
                            return True

                        # Split nterface<y>+Vlan<x>
                        incl_iface = incl_vlan_on_iface.split('+')[1]
                        incl_vlan  = incl_vlan_on_iface.split('+')[0]

                        if iface == incl_iface and vlan == incl_vlan:
                            return True
        return False

    def is_vlan_on_interface_excluded(self, ip_link):
        if 'interfaces' in ip_link and 'vlans' in ip_link and self.exclude_vlan_on_interface != None:
            for vlan in ip_link['vlans']:
                for iface in ip_link['interfaces']:
                    for excl_vlan_on_iface in self.exclude_vlan_on_interface:
                        # Split Vlan<x>+Interface<y>
                        excl_iface = excl_vlan_on_iface.split('+')[0]
                        excl_vlan  = excl_vlan_on_iface.split('+')[1]

                        if iface == excl_iface and vlan == excl_vlan:
                            return True

                        # Split Interface<y>+Vlan<x>
                        excl_iface = excl_vlan_on_iface.split('+')[1]
                        excl_vlan  = excl_vlan_on_iface.split('+')[0]

                        if iface == excl_iface and vlan == excl_vlan:
                            return True
        return False

    def get_filter_list(self):
        # Do we use a configuration file?
        if not self.use_configuration():
#            print "No config file"
            return self.table_ip_link

        table_ip_link_filtered = []

        # Walk the list and filter which IP addresses need to be ignored, based on the configured Vlan and network device filter rules.
        for ip_link in self.table_ip_link:
            # Inclusion rules
            if self.is_vlan_included(ip_link):
                table_ip_link_filtered.append(ip_link)
                continue
            if self.is_interface_included(ip_link):
                table_ip_link_filtered.append(ip_link)
                continue
            if self.is_vlan_on_interface_included(ip_link):
                table_ip_link_filtered.append(ip_link)
                continue

            # Exclusion rules
            if self.is_vlan_excluded(ip_link):
                continue
            if self.is_interface_excluded(ip_link):
                continue
            if self.is_vlan_on_interface_excluded(ip_link):
                continue

            # Steered by configuration defaults.selection
            if self.defaults_selection == 'add':
                table_ip_link_filtered.append(ip_link)
            elif self.defaults_selection == 'remove':
                continue

#        print "Filtered table is:"
#        print table_ip_link_filtered
#        print "End list"

        return table_ip_link_filtered

    def get_table_bgp_add(self):
        self.table_bgp_add = []
        filtered_table_ip_link = self.get_filter_list()

        for ip_link in filtered_table_ip_link:
            if 'ip' in ip_link:
                # When a match is found, the IP is in the BGP
                found = False
                for in_bgp in self.table_in_bgp:
                    if 'ip' in in_bgp:
                        if ip_link['ip'] == in_bgp['ip']:
                            found = True
                            break;
                # When no match is found, the IP needs to be added in BGP
                if not found:
                    self.table_bgp_add.append(ip_link)

        return self.table_bgp_add

    def get_table_bgp_del(self):
        self.table_bgp_del = []
        filtered_table_ip_link = self.get_filter_list()

        # is IP in the table_in_bgp in table_ip_link ? OK, nothing to do : Add to the table_bgp_del (for removal from BGP)
        for in_bgp in self.table_in_bgp:
            if 'ip' in in_bgp:
                found = False
                for ip_link in filtered_table_ip_link:
                    if 'ip' in ip_link:
                        if ip_link['ip'] == in_bgp['ip']:
                            found = True
                            break;

                # Without a match in the other table, this entry needs to be removed
                if not found:
                    self.table_bgp_del.append(in_bgp)

        return self.table_bgp_del

    def get_build_cmd_table_to_reconfigure_bgp(self):
        table_bgp_add = self.get_table_bgp_add()
        table_bgp_del = self.get_table_bgp_del()

        table_cmds = []

        if (table_bgp_add != []) or (table_bgp_del != []):
            table_cmds.append("conf t")
            table_cmds.append("router bgp %s" % self.defaults_asnumber)

        if table_bgp_add != None:
            for ip_link_bgp in table_bgp_add:
                if 'ip' in ip_link_bgp:
                    mask = '/32'
                    table_cmds.append("network %s%s" % (ip_link_bgp['ip'], mask))

        if table_bgp_del != None:
            for ip_link_bgp in table_bgp_del:
                if 'ip' in ip_link_bgp:
                    mask = '/32'
                    table_cmds.append("no network %s%s" % (ip_link_bgp['ip'], mask))

        return table_cmds

    def print_reconfigure_bgp(self):
        table_cmds = self.get_build_cmd_table_to_reconfigure_bgp()

        print "ena"
        for cmd in table_cmds:
            print cmd

    def reconfigure_bgp(self):
        # Construct commands list and execute it
        if dry_run:
            self.print_reconfigure_bgp()
        else:
            return self.sendCmdOnCli(self.get_build_cmd_table_to_reconfigure_bgp())


############### MAIN ##############
if __name__ == "__main__":
    if len(sys.argv) > 1:
        a2b = Arp2Bgp(sys.argv[1])
    else:
        a2b = Arp2Bgp()

    if run_in_test_mode:
        print "To append to the BGP list"
        print a2b.get_table_bgp_add()
        print "To delete from the BGP list"
        print a2b.get_table_bgp_del()

        print "xxxxxxxxxxxxxxxxxxxx"
        print "xxx ReConfig BGP xxx"
        print "xxxxxxxxxxxxxxxxxxxx"
        print a2b.reconfigure_bgp()
        print "xxxxxxxxxxxxxxxxxxxx"
    else:
        if dry_run:
            print "To append to the BGP list"
            print a2b.get_table_bgp_add()
            print "To delete from the BGP list"
            print a2b.get_table_bgp_del()

    a2b.reconfigure_bgp()
