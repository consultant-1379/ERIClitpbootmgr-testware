"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2017
@author:    Boyan Mihovski
@summary:   Integration Tests
            Agile: TORF-169048
"""
import test_constants
from litp_generic_test import GenericTest, attr
from vcs_utils import VCSUtils
from xml_utils import XMLUtils
from lxml import etree
PXE_BOOT_DEV = "eth1"
LITP_PXE_BOOT_IF = "if1"
MGMT_BOND_NAME = "bondmgmt"
MGMT_BOND_SLAVE_1 = "eth0"
MGMT_BOND_SLAVE_2 = "eth7"
FIRST_CLUSTER_ID = "c1"
SECOND_CLUSTER_ID = "c2"
NETSTAT_NIC_MONITOR_STRATEGY = "default_nic_monitor=netstat"
MII_NIC_MONITOR_STRATEGY = "default_nic_monitor=mii"


class Story169048(GenericTest):
    """
    TORF-169048:
    AC1: I can PXE boot a server using the designated network interface
    AC2: Once the PXE boot is completed, I should see that the IP received in
     the PXE boot DHCP request is no longer plumbed on that interface but on a
      designated bond interface
    AC3: I should see that upgrade is unaffected
    AC4: I should be able to expand the cluster
    """

    def setUp(self):
        super(Story169048, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.vcs = VCSUtils()
        self.xml = XMLUtils()

    def tearDown(self):
        super(Story169048, self).tearDown()

    def xml_validate(self, node_url, file_name):
        """
        Description:
        checks that ie xml file created is valid
        """

        # XML TEST ARTIFACT

        # EXPORT CREATED PROFILE ITEM
        network_url = "{0}/network_interfaces".format(node_url)
        self.execute_cli_export_cmd(self.test_ms, network_url, file_name)

        # run xml file and assert that it passes
        cmd = self.xml.get_validate_xml_file_cmd(file_name)
        stdout, stderr, exit_code = self.run_command(self.test_ms, cmd)
        self.assertNotEqual([], stdout)
        self.assertEqual(0, exit_code)
        self.assertEqual([], stderr)
        # check pxe_boot_only value
        root = etree.fromstring(''.join(stdout))
        self.assertEqual('true',
                         root.xpath(".//*[@id='{0}']/pxe_boot_only/text()".
                                    format(LITP_PXE_BOOT_IF))[0])
        # check ipaddress value is not present when pxe_boot_only is set
        self.assertEqual([], root.xpath(".//*[@id='{0}']/ipaddress/text()".
                                        format(LITP_PXE_BOOT_IF)))

    def chk_intf_ip_conf_on_node(self, node_to_check, dev_name, ipaddr):
        """
        Description:
            Function to query the multicast options values which is set
            in the ifcfg file of the specified Network Interface.
            Verify IPADDR applied from ifcfg file only for mgmt bond interface.
        Args:
            node_to_check (str): Hostname of node to be verified.
            dev_name (str): suffix file name of the ifcfg file.
            ipaddr (str): IP address value to be searched for.
        """
        filepath = test_constants.NETWORK_SCRIPTS_DIR + \
            '/ifcfg-{0}'.format(dev_name)
        stdout = self.get_file_contents(node_to_check, filepath)
        ip_line = 'IPADDR="{0}"'.format(ipaddr)
        if dev_name == MGMT_BOND_NAME:
            self.assertTrue(self.is_text_in_list(ip_line, stdout),
                            'IPADDR property should be present.')
        else:
            self.assertFalse(self.is_text_in_list(ip_line, stdout),
                             'IPADDR property should not be present.')

    def check_mii_state(self, node, exp_state):
        """
        Method to run vcs command on node and check state of Mii attribute
        Args:
            node (str): Specifies the location of the Service Group to
                perform Mii check on.
            exp_state (str): 1 or 0 state of Mii attribute for service group
              resources
        """
        if node == 'node2':
            cmd = self.vcs.get_hagrp_resource_list_cmd('Grp_NIC_' +
                                                       FIRST_CLUSTER_ID +
                                                       '_' + PXE_BOOT_DEV)
        else:
            cmd = self.vcs.get_hagrp_resource_list_cmd('Grp_NIC_' +
                                                       SECOND_CLUSTER_ID +
                                                       '_' + PXE_BOOT_DEV)

        stdout = self.run_command(node, cmd, su_root=True,
                                  default_asserts=True)

        cmd = self.vcs.get_hares_cmd('-value {0} Mii'
                                     .format(stdout[0][0]))

        stdout = self.run_command(node, cmd, su_root=True,
                                  default_asserts=True)
        self.assertEqual(stdout[0][0], exp_state)

    def check_ssh_connectivity(self, node, ip_to_check):
        """
        Function to test TCP/IP layer 4 connectivity using ssh port.
        Args:
            node (str): Hostname of node from where the check is executed.
            ip_to_check (str): IP address assigned to the bond.
        """
        stdout = self.run_command(node, 'echo "QUIT" | nc -w 5 {0} 22'.
                                  format(ip_to_check), default_asserts=True)
        self.assertTrue(self.is_text_in_list('OpenSSH_', stdout[0]),
                        'The IP address is not reachable')

    def check_nodes_mco(self, nodes):
        """
        Function to check expanded nodes are reachable.
        Args:
            nodes(list): Hostname of node to be verified.
        """
        for node in nodes:
            stdout, _, _ = self.run_command(self.test_ms,
                                            '/usr/bin/mco ping -I ' + node)
            self.assertTrue(self.is_text_in_list('1 replies max:', stdout))

    def setup_default_passwds(self, nodes):
        """
        Function to set the passwords on expanded node.
        Args:
            nodes(list): Hostname of node to be setup.
        """
        for node in nodes:
            self.assertTrue(self.set_pws_new_node(self.test_ms, node),
                            'Failed to set password')

    @attr('all', 'revert', 'torf169048', 'torf169048_tc12', 'expansion')
    def test_12_p_litp_expansion_install(self):
        """
        @tms_id:
            torf_169048_tc12
        @tms_requirements_id:
            TORF-169048
        @tms_title:
            Expand the cluster pxe boot.
        @tms_description:
            With a pre-deployed litp environment (MS and 1 node).
            Expand the current deployment to add a new cluster with two nodes
             and an additional node to the current cluster.
            And both clusters using pxe boot.
        @tms_test_steps:
        @step: Ensure the llthosts fact from node1 is available to Puppet
               server
        @result: Facts are available
        @step: Expand the existing cluster by 1 node
             (with default_nic_monitor to netstat) and create a new cluster
             of 2 nodes (with default_nic_monitor to mii).
        @result: The plan is successful.
        @step: Ensure the connectivity on TCP/IP layer 4 level and check
             ifcfg files.
        @result: The connection response is successful and ifcfg files
             are correct.
        @step: Validate the generated xml after model export.
        @result: The generated xml has correct structure.
        @step: Ensure vcs clusters pxe boot device mii value is correct.
        @result: VCS clusters ha-res mii value is equal to 1.
        @step: Update vcs cluster c1 default_nic_monitor to mii, and vcs
             cluster c2 default_nic_monitor to netstat.
        @result: The plan is successful.
        @step: Ensure vcs clusters pxe boot device mii value is correct.
        @result: VCS clusters ha-res mii value is equal to 1.
        @step: Update pxe_boot_only to false, and assign an IP address, network
            and vcs_network_host to all of pxe_boot_only interfaces per cluster
        @result: The plan is successful.
        @step: Ensure vcs cluster c1 pxe boot device mii value is correct.
        @result: VCS ha-res mii value is equal to 1.
        @step: Ensure vcs cluster c2 pxe boot devices mii value is correct.
        @result: VCS ha-res mii value is equal to 0.
        @step: Ensure the connectivity on TCP/IP layer 4.
        @result:  The connection responses are successful.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        if not self.is_puppet_synched('node1', self.test_ms, 'llthosts'):
            self.log('info', 'The \"llthosts\" fact for node1 is not available'
                    ' to the Puppet server. Triggering a Puppet run and'
                    ' waiting until it completes')
            self.wait_full_puppet_run(self.test_ms)

        self.log('info', '# 1. Expand the existing cluster by 1 node and '
                 ' create a new cluster of 2 nodes.')
        # We create a list of the nodes we will be adding. Note if using a
        # script name which contains 'mn2' you should use node2. If using a
        # script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append('node2')
        nodes_to_expand.append('node3')
        nodes_to_expand.append('node4')
        # Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments', 'cluster',
                                    False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' + \
                'cluster_id=1043 ' + MII_NIC_MONITOR_STRATEGY
        self.execute_cli_create_cmd(self.test_ms, cluster_collect + '/' +
                                    SECOND_CLUSTER_ID, 'vcs-cluster', props,
                                    add_to_cleanup=False)
        # Execute the expand script for expanding cluster 2 with
        # node3 and node4 and adds node2 to cluster 1
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c1_mn2_pxe.sh',
                                   cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn3_pxe.sh',
                                   cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn4_pxe.sh',
                                   cluster_filename='192.168.0.42_4node.sh')
        # Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)
        self.check_nodes_mco(nodes_to_expand)
        self.setup_default_passwds(nodes_to_expand)
        self.log('info', '# 2. Ensure the connectivity on TCP/IP '
                 'layer 4 level and check ifcfg files.')
        hosts_ip = dict()
        nodes_url = self.find(self.test_ms, '/deployments', 'node')
        for node_url in nodes_url:
            inf_url = self.find(self.test_ms, node_url, 'bond',
                                assert_not_empty=False)
            if inf_url:
                node_vpath = \
                    self.get_node_filename_from_url(self.test_ms, node_url)
                node_hostname = \
                    self.get_node_att(node_vpath, 'hostname')
                # Check bonds are created for expanded nodes
                self.assertTrue(self.is_text_in_list(node_hostname,
                                                     nodes_to_expand))
                if_ip4 = self.get_props_from_url(self.test_ms, inf_url[0],
                                                 'ipaddress')
                hosts_ip[node_hostname] = if_ip4
                self.log('info', '# 3. Validate the generated xml after '
                         'model export.')
                self.xml_validate(node_url,
                                  'xml_expected_story169048' +
                                  node_hostname + '.xml')
            else:
                node_vpath = \
                    self.get_node_filename_from_url(self.test_ms, node_url)
                node_hostname = \
                    self.get_node_att(node_vpath, 'hostname')
                # Check nodes without bonds are not including expanded nodes
                self.assertFalse(self.is_text_in_list(node_hostname,
                                                      nodes_to_expand))
        for host, ip4 in hosts_ip.iteritems():
            self.chk_intf_ip_conf_on_node(host, MGMT_BOND_NAME, ip4)
            self.check_ssh_connectivity(host, ip4)
            self.chk_intf_ip_conf_on_node(host, MGMT_BOND_SLAVE_1, ip4)
            self.chk_intf_ip_conf_on_node(host, MGMT_BOND_SLAVE_2, ip4)
            self.chk_intf_ip_conf_on_node(host, PXE_BOOT_DEV, ip4)
        self.log('info', '# 4. Ensure vcs clusters pxe boot device mii value'
                 ' is correct.')
        self.check_mii_state('node2', exp_state='1')
        self.check_mii_state('node3', exp_state='1')
        self.check_mii_state('node4', exp_state='1')
        self.log('info', '# 5. Update vcs cluster c1 default_nic_monitor to '
                 'mii, and vcs cluster c2 default_nic_monitor to netstat.')
        self.execute_cli_update_cmd(self.test_ms, cluster_collect + '/' +
                                    FIRST_CLUSTER_ID, MII_NIC_MONITOR_STRATEGY)
        self.execute_cli_update_cmd(self.test_ms, cluster_collect + '/' +
                                    SECOND_CLUSTER_ID,
                                    NETSTAT_NIC_MONITOR_STRATEGY)
        timeout_mins = 5
        self.run_and_check_plan(self.test_ms, test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)
        self.log('info', '# 6. Ensure vcs clusters pxe boot device mii value'
                 ' is correct.')
        self.check_mii_state('node2', exp_state='1')
        self.check_mii_state('node3', exp_state='1')
        self.check_mii_state('node4', exp_state='1')
        self.log('info', '# 7. Update pxe_boot_only to false, and assign an '
                 'IP address, network and vcs_network_host to all of '
                 'pxe_boot_only interfaces per cluster.')
        # GET NETWORKS PATH
        networks_path = self.find(self.test_ms, '/infrastructure',
                                  'network', False)[0]
        # CREATE TEST NETWORK
        network_url = networks_path + '/test_pxe'
        props = 'name=test_pxe subnet=10.10.10.0/24'
        self.execute_cli_create_cmd(self.test_ms, network_url,
                                    'network', props)
        eth_props = 'network_name=test_pxe pxe_boot_only=false \
            ipaddress=10.10.10.'
        used_vcs_hosts = list()
        ips_to_check = list()
        ip_host = 0
        for node_url in nodes_url:
            inf_url = self.find(self.test_ms, node_url, 'bond',
                                assert_not_empty=False)
            if inf_url:
                ip_host += 1
                ips_to_check.append(ip_host)
                if_url = node_url + '/network_interfaces/' + LITP_PXE_BOOT_IF
                self.execute_cli_update_cmd(self.test_ms, if_url, eth_props +
                                            str(ip_host))
                vcs_clust_url = node_url.rsplit('/', 2)[0] + '/network_hosts/'
                vcs_hst_props = 'network_name=test_pxe ip=10.10.10.' + \
                    str(ip_host)
                vcs_host_url = vcs_clust_url + LITP_PXE_BOOT_IF
                if self.is_text_in_list(vcs_host_url, used_vcs_hosts):
                    vcs_host_url = vcs_host_url + str(ip_host)
                self.execute_cli_create_cmd(self.test_ms, vcs_host_url,
                                            'vcs-network-host', vcs_hst_props)
                used_vcs_hosts.append(vcs_host_url)
        timeout_mins = 5
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)
        self.log('info', '# 8. Ensure vcs cluster c1 pxe boot device mii value'
                 ' is correct.')
        self.check_mii_state('node2', exp_state='0')
        self.log('info', '# 9. Ensure vcs cluster c2 pxe boot device mii value'
                 ' is correct.')
        self.check_mii_state('node3', exp_state='0')
        self.check_mii_state('node4', exp_state='0')
        self.log('info', '# 10. Ensure the connectivity on TCP/IP layer 4.')
        for node, ip_addr in zip(nodes_to_expand, ips_to_check):
            self.check_ssh_connectivity(node, '10.10.10.' + str(ip_addr))
