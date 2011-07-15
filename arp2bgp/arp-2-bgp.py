#!/usr/bin/env python
# Copyright (c) 2011 Nikhef. All rights reserved.
# Author: Oscar Koeroo <okoeroo (at) nikhef (dot) nl>
# BSD Licence

import subprocess, os, sys, re
from subprocess import Popen, PIPE, STDOUT
import array
import ConfigParser
#import Tac, PyClient


run_test_mode    = True
fake_output_path = '/Users/okoeroo/dvl/scripts/arista/arp-2-bgp'


use_shell         = "/usr/bin/Cli"
cmd_showconnected = "show ip arp"
cmd_showinBGP     = "show run | include network"


#############  Helper functions   ##############
class AristaGenericHelpers(object):
    def decompose_DeviceAndNumber(self, str):
        if str:
            try:
                combo = {}

                number = re.search('[0-9]+', str).group(0).lower()
                device = re.search('[a-zA-Z]+', str).group(0).lower()

                combo[device] = number
                return combo
            except:
                print "Error in decompose_DeviceAndNumber: Parse error: %s" % str
                return None
        else:
            print "Error in decompose_DeviceAndNumber: No input"
            return None


# Register the switch cli commands and associate output files to it for test
# data. This makes easier testing
class AristaTestData(object):
    run_test_mode_fake_output_path = ''
    faked_cmds = [
                  {'command': 'show ip arp', 'faked_output': 'show_ip_arp.out'},
                  {'command': 'show run | include network', 'faked_output': 'show_run_include_network.out'}
                 ]
    def __init__(self, faked_output_path='/tmp'):
        self.run_test_mode_fake_output_path = faked_output_path

    def run_command_faked(self, cmd=""):
        if len(cmd) == 0:
            return ""

        for faked_cmd in self.faked_cmds:
            if faked_cmd['command'] == cmd:
                output = open (self.run_test_mode_fake_output_path + '/' + faked_cmd['faked_output'], "r").read()
                return output
        return ""


class AristaProcessor(object):
    table_cmds = []
    run_in_test_mode = False

    def __init__(self, test_mode=False, test_output_path=''):
        self.run_in_test_mode = test_mode
        if test_mode:
            self.atd = AristaTestData(test_output_path)

        # The 'show run' command requires administrative privileges (aka root) to work
        if not test_mode:
            if os.geteuid() != 0:
                print "Error: You must use this tool with administrative privileges for it to do its business"
                sys.exit(1)

    def sendCmdOnCli(self, table_cmds=[]):
        if table_cmds == []:
            return None

        # Running in Test mode?
        if not self.run_in_test_mode:
            # Start on the Switch Cli
            p = subprocess.Popen([use_shell], stdout=PIPE, stdin=PIPE, stderr=STDOUT)

            p.stdin.write('ena\n')
            for cmd in table_cmds:
                p.stdin.write(cmd + '\n')

            my_stdout = p.communicate()[0]

            p.stdout.close()
            p.stdin.close()
            if p.wait() != 0:
                print "There were some errors"

            return my_stdout
        else:
            # Run test mode
            print "--xxx  Running in Test Mode xxx---"
            print "ena"
            multi_cmd_output = ""
            for cmd in table_cmds:
                print cmd
                multi_cmd_output += self.atd.run_command_faked(cmd)
            print "--xxxx Output in Test Mode xxxx---"
            print multi_cmd_output
            print "--xxxx Output in Test Mode xxxx---"
            print "--xxx  Running in Test Mode xxx---"
            return multi_cmd_output


class Arp2BgpConfiguration(object):
    include_interfaces        = None
    include_vlans             = None
    include_vlan_on_interface = []
    exclude_interfaces        = None
    exclude_vlans             = None
    exclude_vlan_on_interface = []
    defaults_selection        = 'ignore'  # Could be 'add', 'ignore' or 'remove'
    as_number                 = None

    def __init__(self, conffile='/etc/arp-2-bgp.conf'):
        try:
            self.load_configuration(conffile)
        except:
            sys.exit(1)

    def construct_vlan_on_interface(self, configline):
        vlan_on_interface = []

        tmp_list = configline
        for tmp in tmp_list:
            # Split Vlan<x>+Interface<y>
            elem0 = tmp.split('+')[0]
            elem1 = tmp.split('+')[1]

            if elem0 and elem1:
                combo = []
                elem0_combo = {}
                elem1_combo = {}

                # Split the Device and its Number: "Vlan66" and "Ethernet42" -> [{'Vlan': '66'}, {'Ethernet': '42'}]
                elem0_combo = AristaGenericHelpers().decompose_DeviceAndNumber(elem0)
                elem1_combo = AristaGenericHelpers().decompose_DeviceAndNumber(elem1)
                combo.append(elem0_combo)
                combo.append(elem1_combo)

                vlan_on_interface.append(combo)
        return vlan_on_interface

    def load_configuration(self, conffile):
        # Open config file for inclusion/exclusion rules.
        # Without a config file the script will sync all entries from the ARP table into BGP
        config = ConfigParser.RawConfigParser()
        self.use_config = False
        if not os.path.exists(conffile):
            print "Could not open the configuration file \'%s\'" % conffile
            raise

        try:
            try:
                config.read(conffile)
            except:
                print "Error in configuration file: Syntax error. Please fix the configuration file to be a proper .ini style config file"
                raise

            if config.has_section('excludes'):
                if config.has_option('excludes', 'interfaces'):
                    self.exclude_interfaces         = config.get("excludes", 'interfaces').replace(' ','').split(',')
                if config.has_option('excludes', 'vlans'):
                    self.exclude_vlans              = config.get("excludes", 'vlans').replace(' ','').split(',')
                if config.has_option('excludes', 'vlan_on_interface'):
                    tmp_list = config.get("excludes", 'vlan_on_interface').replace(' ','').split(',')
                    self.exclude_vlan_on_interface = self.construct_vlan_on_interface(tmp_list)

            if config.has_section('includes'):
                if config.has_option('includes', 'interfaces'):
                    self.include_interfaces         = config.get("includes", 'interfaces').replace(' ','').split(',')
                if config.has_option('includes', 'vlans'):
                    self.include_vlans              = config.get("includes", 'vlans').replace(' ','').split(',')
                if config.has_option('includes', 'vlan_on_interface'):
                    tmp_list = config.get("includes", 'vlan_on_interface').replace(' ','').split(',')
                    self.include_vlan_on_interface = self.construct_vlan_on_interface(tmp_list)

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
            raise

    def is_vlan_included(self, vlan):
        if self.include_vlans != None and vlan in set(self.include_vlans):
            return True
        else:
            return False

    def is_vlan_excluded(self, ip_link):
        if self.exclude_vlans != None and vlan in set(self.exclude_vlans):
            return True
        else:
            return False

    def is_interface_included(self, iface):
        if self.include_vlans != None and iface in set(self.include_interfaces):
            return True
        else:
            return False

    def is_interface_excluded(self, ip_link):
        if self.exclude_vlans != None and iface in set(self.exclude_interfaces):
            return True
        else:
            return False

    def is_vlan_on_interface_included(self, vlan, iface):
        if self.include_vlan_on_interface != None:
            for incl_vlan_on_iface in self.include_vlan_on_interface:
                if incl_vlan_on_iface['vlan'] and incl_vlan_on_iface['iface']:
                    return True
        return False

    def is_vlan_on_interface_excluded(self, vlan, iface):
        if self.exclude_vlan_on_interface != None:
            for excl_vlan_on_iface in self.exclude_vlan_on_interface:
                if excl_vlan_on_iface['vlan'] and excl_vlan_on_iface['iface']:
                    return True
        return False


class AristaConnectedHost(object):
    def __init__(self, ip_or_mac, type='ip'):
        self.MAC = ''
        self.ip = ''

        if type == 'ip':
            self.ip = ip_or_mac
        elif type.lower() == 'mac':
            self.MAC = ip_or_mac
        else:
            print "Error in AristaConnectedHost().__init__: Unknown type specified, got \"%s\"" % type
            raise

    def add_mac(self, mac):
        self.MAC = mac

    def add_ip(self, ip):
        self.ip = ip

    def print_me(self):
        print "    Host ip:  %s  MAC %s " % (self.ip, self.MAC)


class AristaDevice(object):
    # Connector
#    dev_name   = '' # 'Ethernet' or 'Management'
#    dev_number = '' # 0, for Ethernet0
#    dev_MACs   = []
#    dev_IPs    = []

    def __init__(self, devicename):
        self.dev_name   = '' # 'Ethernet' or 'Management'
        self.dev_number = '' # 0, for Ethernet0
        self.dev_MACs   = []
        self.dev_IPs    = []

        if devicename and len(devicename) > 1:
            try:
                number = re.search('[0-9]+', devicename).group(0)
                device = re.search('[a-zA-Z]+', devicename).group(0)
            except:
                print "Error in AristaSwitchState().add_device(): Couldn't parse input, got \"devicename\"" % devicename
                raise

        self.dev_name   = device
        self.dev_number = number

    def add_mac(self, mac):
        self.dev_MACs.append(mac)

    def add_ip(self, ip):
        self.dev_IPs.append(ip)

    def compare(self, devicename):
        if devicename and len(devicename) > 1:
            try:
                number = re.search('[0-9]+', devicename).group(0)
                device = re.search('[a-zA-Z]+', devicename).group(0)
            except:
                print "Error in AristaSwitchState().compare(): Couldn't parse input, got \"devicename\"" % devicename
                raise

        # Compare the devicename with the registered build
        if number == self.dev_number and device == self.dev_name:
            return True
        else:
            return False

    def print_me(self):
        print "    Device: %s%s" % (self.dev_name, self.dev_number)

    def get_devicename(self):
        return self.dev_name + self.dev_number


class AristaVlan(object):
    vlan_prefix = 'Vlan'
#    vlan_number = None
#    connected_hosts = []
#    active_on_device = []

    def __init__(self, vlan):
        self.connected_hosts  = []
        self.active_on_device = []
        vlan_number           = None

        # In the event that you need to specify a non-tagged Vlan
        if vlan == None:
            self.vlan_number = None
        else:
            # Parse tag number from the Vlan string
            try:
                number = re.search('[0-9]+', vlan).group(0)
            except:
                print "Error in AristaVlan.__init__: Parse error in string \"%s\"" % vlan
                raise
            self.vlan_number = number

    def get_vlan(self):
        if self.vlan_number == None:
            return ''
        else:
            return self.vlan_prefix + self.vlan_number

    def add_host(self, host, type='ip'):
        h = AristaConnectedHost(host, type)
        self.connected_hosts.append(h)

    def add_active_on_device(self, devicename):
        dev = AristaDevice(devicename)
        self.active_on_device.append(dev)

    def compare(self, vlan):
        if vlan == None and self.vlan_number == None:
            return True

        v = str(vlan).lower()
        if v.startswith('vlan'):
            try:
                number = re.search('[0-9]+', vlan).group(0)
            except:
                print "Error in AristaVlan.__init__: Parse error in string \"%s\"" % vlan
                return False

            if self.vlan_number == number:
                return True
        # Just fail
        return False

    def print_me(self):
        if self.vlan_number == None:
            print "Untagged"
        else:
            print "Vlan%s" % self.vlan_number

        for ch in self.connected_hosts:
            ch.print_me()

        for ad in self.active_on_device:
            ad.print_me()


class AristaRoute(object):
    def __init__(self, route):
        self.network = ''
        self.mask    = ''

        self.network = route.split('/')[0]
        self.mask    = route.split('/')[1]
        return

    def compare(self, route):
        if route and len(route) > 1:
            network = route.split('/')[0]
            mask    = route.split('/')[1]
            if network == self.network and mask == self.mask:
                return True
        # Just fail
        return False

    def print_me(self):
        print "Route: %s/%s" % (self.network, self.mask)


class AristaSwitchState(object):
    def __init__(self, aristaproc=None):
        self.vlans = []
        self.routes = []

        if not aristaproc:
            raise

        # Install the AristaProcessor object - Used to execute commands on the switch Cli
        self.ap = aristaproc

    def print_state(self):
        for vlan in self.vlans:
            vlan.print_me()

        for route in self.routes:
            route.print_me()

    def add_hostip_to_vlan(self, ip, vlan):
        if not ip and len(ip) == 0:
            print "Error in AristaSwitchState().add_hostip_to_vlan(): Function needs a host IP, got \'ip: %s\'" % ip
            raise

        # Search existing Vlans
        for v in self.vlans:
            if v.compare(vlan):
                v.add_host(ip, 'ip')
                return

        # If Vlan doesn't exist, create it
        v = AristaVlan(vlan)
        v.add_host(ip, 'ip')
        self.vlans.append(v)

    def add_device_to_vlan(self, devicename, vlan):
        if not devicename and len(devicename) == 0:
            print "Error in AristaSwitchState().add_device_to_vlan(): Function needs a device device name and vlan, got \'device: %s\'" % devicename
            raise

        # Search existing Vlans
        for v in self.vlans:
            if v.compare(vlan):
                v.add_active_on_device(devicename)
                return
        # If Vlan doesn't exist, create it
        v = AristaVlan(vlan)
        v.add_active_on_device(devicename)
        self.vlans.append(v)

    def add_route(self, route):
        route = AristaRoute(route)
        self.routes.append(route)

    def load_current_bgp_table(self):
        # Get command output from the shell
        table_cmds = []
        table_cmds.append(cmd_showinBGP)
        stdout = self.ap.sendCmdOnCli(table_cmds)

        for line in stdout.split('\n'):
            row = {}
            try:
                # Line looks like: "    network 1.2.3.4/32"
                ip_subnet = line.split()[1]
            except:
                continue

            self.add_route(ip_subnet)

    def load_ip_and_link_info(self):
        # Get the arp table output

        # Get command output from the shell
        table_cmds = []
        table_cmds.append(cmd_showconnected)
        stdout = self.ap.sendCmdOnCli(table_cmds)

        skipFirst = True
        for line in stdout.split('\n'):
            if skipFirst == True:
                skipFirst = False
                continue

            row = {}
            try:
                # Got an IP address from the arp table
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
                    # Remember the vlan name
                    row['vlans'].append(elem)



                # The rest must be aggregated links, ethernet or management interfaces
                else:
                    if not 'interfaces' in row:
                        row['interfaces'] = []
                    # Remember the interface name
                    row['interfaces'].append(elem)

            # Add row to table
            # Based on a Vlan
            if 'vlans' in row:
                for v in row['vlans']:
                    self.add_hostip_to_vlan(row['ip'], v)

                    if 'interfaces' in row:
                        for i in row['interfaces']:
                            self.add_device_to_vlan(i, v)
            # Based on an untagged interface
            else:
                self.add_hostip_to_vlan(row['ip'], None)
                if 'interfaces' in row:
                    for i in row['interfaces']:
                        # Add host (based on IP) to the special Vlan 'None' which
                        # indicates that this is detected on an untagged link

                        self.add_device_to_vlan(i, None)


class Arp2Bgp(object):
    def __init__(self, conffile="/etc/arp-2-bgp.conf", test_mode=False, fake_output_path=''):
        self.test_mode = test_mode

        # Install the AristaProcessor object - Used to execute commands on the switch Cli
        self.ap = AristaProcessor(test_mode, fake_output_path)

        # Initialize switch state
        self.aristaswitchstate = AristaSwitchState(self.ap)
        # Load current BGP table
        self.aristaswitchstate.load_current_bgp_table()
        # Read ARP information combined with active link/Vlan allocation
        self.aristaswitchstate.load_ip_and_link_info()

        # Read configuration file, if available
        self.a2bconfig = Arp2BgpConfiguration(conffile)

        if self.test_mode:
            print "Current SwitchState:"
            self.aristaswitchstate.print_state()

    # Construct a table with the example content:
    # ip addr | vlan (| ethernet device)
    def get_input_as_filtered_arp_table(self):
        table_filtered_arp_input = []

        for vlan in self.aristaswitchstate.vlans:
            if self.a2bconfig.is_vlan_excluded(vlan.get_vlan()):
                continue
            if self.a2bconfig.is_vlan_included(vlan.get_vlan()):
                for host in vlan.connected_hosts:
                    tuple = {}
                    tuple['ip'] = host.ip
                    tuple['vlan'] = vlan.get_vlan()
                    table_filtered_arp_input.append(tuple)
        return table_filtered_arp_input

    # Only concider /32 routes (direct host routes)
    def get_input_as_filtered_bgp_table(self):
        table_filtered_bgp_input = []

        for route in self.aristaswitchstate.routes:
            if route.mask == '32':
                tuple = {}
                tuple['network'] = route.network
                tuple['mask']    = route.mask
                table_filtered_bgp_input.append(tuple)
        return table_filtered_bgp_input

    def get_table_bgp_add(self):
        filtered_table_host = self.get_input_as_filtered_arp_table()
        filtered_table_bgp  = self.get_input_as_filtered_bgp_table()

        table_bgp_add = []
        # Walk through the connected hosts, and list the once that are not advertised
        for host in filtered_table_host:
            found = False
            for route in filtered_table_bgp:
                # If a host is already configured as a /32 route, ignore it
                if route['network'] == host['ip']:
                    found = True
            # If a host is not configured as a /32 route, must be added
            if not found:
                tuple = {}
                tuple['ip']   = host['ip']
                tuple['vlan'] = host['vlan']
                table_bgp_add.append(tuple)
        return table_bgp_add

    def get_table_bgp_del(self):
        filtered_table_host = self.get_input_as_filtered_arp_table()
        filtered_table_bgp  = self.get_input_as_filtered_bgp_table()

        table_bgp_del = []
        # Walk through the /32 routes, and list those that are listed as route, but are not in the connected list
        for route in filtered_table_bgp:
            found = False
                # If a host is already configured as a /32 route, ignore it
            for host in filtered_table_host:
                if route['network'] == host['ip']:
                    found = True
            # If a /32 network is announced, but the host left -> remove the entry
            if not found:
                tuple = {}
                tuple['ip']   = route['network']
                # tuple['vlan'] = route['vlan']
                table_bgp_del.append(tuple)
        return table_bgp_del

    def get_build_cmd_table_to_reconfigure_bgp(self):
        table_cmds = []

        table_bgp_add = self.get_table_bgp_add()
        table_bgp_del = self.get_table_bgp_del()

        if self.test_mode:
            print "Addition from static route announcement:"
            for i in table_bgp_add:
                print "    " + i['ip'] + " vlan: " + i['vlan']
            print "Deletion from static route announcement:"
            for i in table_bgp_del:
                print "    " + i['ip']
                # print "    " + i['ip'] + " vlan: " + i['vlan']

        if (table_bgp_add == []) and (table_bgp_del == []):
            if self.test_mode:
                print "Nothing to add and nothing to remove"
            return table_cmds

        table_cmds.append("conf t")
        # table_cmds.append("router bgp %s" % self.defaults_asnumber)

        if table_bgp_add != None:
            for ip_link_bgp in table_bgp_add:
                if 'ip' in ip_link_bgp:
                    mask = '/32'
                    table_cmds.append("ip route %s%s vlan %s" % (ip_link_bgp['ip'], mask, ip_link_bgp['vlan']))

        if table_bgp_del != None:
            for ip_link_bgp in table_bgp_del:
                if 'ip' in ip_link_bgp:
                    mask = '/32'
                    table_cmds.append("no ip route %s%s" % (ip_link_bgp['ip'], mask))
                    # table_cmds.append("no ip route %s%s vlan %s" % (ip_link_bgp['ip'], mask, ip_link_bgp['vlans']))

        return table_cmds

    def print_reconfigure_bgp(self):
        table_cmds = self.get_build_cmd_table_to_reconfigure_bgp()

        print "ena"
        for cmd in table_cmds:
            print cmd

    def reconfigure_bgp(self):
        # Construct commands list and execute it
        return self.ap.sendCmdOnCli(self.get_build_cmd_table_to_reconfigure_bgp())


############### MAIN ##############
if __name__ == "__main__":
    if len(sys.argv) > 1:
        a2b = Arp2Bgp(sys.argv[1], run_test_mode, fake_output_path)
    else:
        a2b = Arp2Bgp(run_test_mode, fake_output_path)

    if run_test_mode:
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
        a2b.reconfigure_bgp()

