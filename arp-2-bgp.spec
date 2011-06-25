Summary: BGP announce hosts based on current arp table entries
Name: arp-2-bgp
Version: 0.0.1
Release: 1%{?dist}
Vendor: Nikhef
License: BSD
Group: Applications/System
URL: https://github.com/okoeroo/arp-2-bgp
Source0: https://github.com/okoeroo/%{name}.git
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
#BuildRequires: python
Requires: python

%description

This script will read the arp table output to collect the connected
IP addresses to the switch. This information needs to be made
available to another (layer-3) switch using BGP. This feature is
makes it possible to use multiple switches to implement a layer-2
network, while each of them connecting to another (set of) switches,
based on layer-3 routing.
This solution makes it possible to re-route traffic over another
switch in the layer-2 domain to the neighbouring switch based on its
layer-3 link. The net-result will be an aggregation possibility of
saturating both Layer-3 links by the traffic of either layer-2
connected switches.


%prep
%setup -q

#%build

#%configure

#make

%install
rm -rf $RPM_BUILD_ROOT

install -d $RPM_BUILD_ROOT/persist/nikhef/arp-2-bgp
install -pm 0644 arp-2-bgp.py $RPM_BUILD_ROOT/nikhef/arp-2-bgp/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%doc AUTHORS LICENSE README
%config(noreplace) /persist/nikhef/arp-2-bgp.conf


%changelog
* Sun Jun 25 2011 Oscar Koeroo <okoeroo@nikhef.nl> 0.0.1

