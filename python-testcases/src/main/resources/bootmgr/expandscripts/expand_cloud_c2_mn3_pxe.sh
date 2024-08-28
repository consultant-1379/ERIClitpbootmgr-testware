#!/bin/bash
#
# TORF-169048:
#    test_12_p_litp_expansion_install.IT:
#    Description: With an already up and running LITP environment (MS and node1 deployed),
#    using a LITP plan: expand the cluster to add a node2, and add new cluster with two nodes
#    (node3 and node4), both clusters using pxe boot.
#
#    This script is expanding cluster c2 with node3.
#

if [ "$#" -lt 1 ]; then
    echo -e "Usage:\n  $0 <CLUSTER_SPEC_FILE>" >&2
    exit 1
fi

cluster_file="$1"
source "$cluster_file"


set -x
function litp(){
    command litp "$@" 2>&1
    retval=( $(echo "$?") )
    if [ $retval -ne 0 ]
    then
        exit 1
    fi
}



for (( i=2; i<3; i++ )); do
    # DISK CREATION FOR SYSTEMS - PEER NODES
    litp create -p /infrastructure/systems/sys$(($i+2)) -t blade -o system_name="${node_expansion_sysname[$i]}"
    # DISK SETUP
    litp create -p /infrastructure/systems/sys$(($i+2))/disks/disk0 -t disk -o name=sda size=40G bootable=true uuid="${node_expansion_disk_uuid[$i]}"
    # BMC SETUP FOR PXE BOOTING BLADES
    litp create -p /infrastructure/systems/sys$(($i+2))/bmc -t bmc -o username=no-user password_key=key-for-user ipaddress=${node_expansion_ip[$i]}
done

# INDIVIDUAL NODE SETUP
for (( i=2; i<3; i++ )); do
    # GATEWAY SETUP FOR NODE

    # HOSTNAME SETUP
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1)) -t node -o hostname="${node_expansion_hostname[$i]}"

    # INHERIT SYSTEM SETUP FROM ABOVE
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/system -s /infrastructure/systems/sys$(($i+2))

    # CREATE OS PROFILE
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/os -s /software/profiles/os_prof1

    # CREATE STORAGE PROFILE
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/storage_profile -s /infrastructure/storage/storage_profiles/profile_1

    # INHERIT SPECIFIC SOFTWARE ITEMS
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/items/ntp1 -s /software/items/ntp1
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/items/java -s /software/items/jdk
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/items/dovecot -s /software/items/dovecot

    # LOG ROTATE RULES FOR THE NODE
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/logrotate -t logrotate-rule-config
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/logrotate/rules/messages -t logrotate-rule -o name="syslog" \
        path="/var/log/messages,/var/log/cron,/var/log/maillog,/var/log/secure,/var/log/spooler" size=10M rotate=50 copytruncate=true \
        sharedscripts=true postrotate="/bin/kill -HUP \`cat /var/run/syslogd.pid 2> /dev/null\` 2> /dev/null || true"

    ##### NETWORK SETUP FOR EACH NIC #####

    # GATEWAY SETUP FOR NODE
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/routes/traffic2_gw -s /infrastructure/networking/routes/traffic2_gw

    # BOND ETH0, ETH7
    litp create -t bond -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/b0 -o device_name=bondmgmt network_name=mgmt miimon=100 ipaddress="${node_expansion_ip[$i]}" \
        ipv6address="${node_expansion_ipv6_00[$i]}"
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if0 -t eth -o device_name=eth0 macaddress="${node_expansion_eth0_mac[$i]}" master=bondmgmt
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if7 -t eth -o device_name=eth7 macaddress="${node_expansion_eth7_mac[$i]}" master=bondmgmt

    # PXE-BOOT DEVICE
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if1 -t eth -o device_name=eth1 macaddress="${node_expansion_eth1_mac[$i]}" pxe_boot_only=true

    # HEARTBEAT NETWORK SETUP
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if2 -t eth -o device_name=eth2 macaddress="${node_expansion_eth2_mac[$i]}" network_name=hb1
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if3 -t eth -o device_name=eth3 macaddress="${node_expansion_eth3_mac[$i]}" network_name=hb2

    # TRAFFIC NETWORKS
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if4 -t eth -o device_name=eth4 macaddress="${node_expansion_eth4_mac[$i]}" network_name='traffic1' \
        ipaddress="${node_expansion_ip_2[$i]}"
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if5 -t eth -o device_name=eth5 macaddress="${node_expansion_eth5_mac[$i]}" network_name='traffic2' \
        ipaddress="${node_expansion_ip_3[$i]}"

    # DHCP NETWORKS
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/if6 -t eth -o bridge='br6' device_name=eth6 macaddress="${node_expansion_eth6_mac[$i]}"
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/network_interfaces/br6 -t bridge -o device_name='br6' forwarding_delay=4 network_name=dhcp_network \
        ipaddress="${dhcp_expansion_ip_1[$i]}"

    # ROUTE SETUP
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/routes/r1 -s /infrastructure/networking/routes/r1
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/routes/r2_ipv6 -s /infrastructure/networking/routes/default_ipv6

    # CREATE FIREWALL SETUP FOR NODES
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init -t firewall-node-config
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_nfsudp -t firewall-rule -o name='011 nfsudp' dport=111,2049,4001 proto=udp
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_nfstcp -t firewall-rule -o name='001 nfstcp' dport=111,2049,4001,12987 proto=tcp
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_icmp_ip6 -t firewall-rule -o name='101 icmpipv6' proto="ipv6-icmp"
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_dhcpudp -t firewall-rule  -o name="400 dhcp" proto="udp" dport=67 provider=iptables
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_dhcpsynctcp -t firewall-rule  -o name="401 dhcpsync" proto="tcp" dport=647 provider=iptables
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_dnstcp -t firewall-rule -o name='200 dnstcp' dport=53 proto=tcp
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/fw_config_init/rules/fw_dnsudp -t firewall-rule -o name='053 dnsudp' dport=53 proto=udp

    # MANAGED SFS MOUNTS
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/file_systems/mfs2 -s /infrastructure/storage/nfs_mounts/mount2

    # SYSCTRL PARAMS FOR NODES
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/init_config -t sysparam-node-config
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/init_config/params/sysctrl_01 -t sysparam -o key="net.ipv4.tcp_wmem" value="4096 65536 16777215"

    # DNS SETUP FOR NODES
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/dns_client -t dns-client -o search=ammeonvpn.com,exampleone.com,exampletwo.com,examplethree.com,examplefour.com,examplefive.com
    litp create -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/configs/dns_client/nameservers/init_name_server -t nameserver -o ipaddress=10.44.86.212 position=1

    # NODE SERVICES
    litp inherit -p /deployments/d1/clusters/c2/nodes/n$(($i+1))/services/sentinel -s /software/services/sentinel

done
