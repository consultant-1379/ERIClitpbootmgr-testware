"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Sep 2017
@author:    Pat Bohan
@summary:   TORF-216461
            As a LITP user I want xinetd service running only when needed
            (PXE booting) so that my deployment is more secure
"""
from re import findall, MULTILINE

from litp_generic_test import GenericTest, attr
import test_constants as const
import time


class Story216461(GenericTest):
    """
        Optimise puppet timer configuration to improve performance on
        larger systems and minimise occurrence of 'execution expired'
    """

    UDEV_NET_RULES = '/etc/udev/rules.d/70-persistent-net.rules'

    def setUp(self):
        """ Runs before every single test """
        super(Story216461, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()

    def tearDown(self):
        """ Runs after every single test """
        super(Story216461, self).tearDown()

    def assert_udev_rules(self):
        """
         Verify 1 udev net rule is generated on each node and the rule is
          defined with the correct mac address.
        """
        for node in self.find(self.ms_node, "/deployments", "node"):
            hostname = self.get_node_filename_from_url(self.ms_node, node)
            rules, _, _ = self.run_command(
                    hostname, "cat {0}".format(Story216461.UDEV_NET_RULES),
                    default_asserts=True)
            self.assertNotEqual([], rules,
                                msg='Expected output from command, got none!')

            rules = '\n'.join(rules)
            found = findall(r'^SUBSYSTEM.*(ATTR\{address\}==\".*?\").*',
                            rules, flags=MULTILINE)
            # only one SUBSYSTEM rule should be found
            self.assertEqual(
                    1, len(found), msg='Expected 1 SUBSYSTEM entry in {0} on '
                                       'node {1}, got {2}'.format(
                            Story216461.UDEV_NET_RULES, hostname, len(found)))

            nets = self.get_node_network_devices(self.ms_node, node)
            udev_mac = nets['eth0']['macaddress']
            # verify the udev rule on the node is usng the correct macaddress
            self.assertEqual('ATTR{{address}}=="{0}"'.format(udev_mac),
                             found[0], msg='Expected MAC address {0}, '
                                           'found {1}'.format(udev_mac,
                                                              found[0]))

    @attr('all', 'revert', 'story216461', 'story216461_tc01', 'TORF-294553')
    def test_01_p_prepare_restore(self):
        """
            @tms_id: torf_216461_tc01
            @tms_requirements_id: TORF-216461, TORF-294553
            @tms_title: prepare_restore
            @tms_description: Verify that the xientd service is not in state
                              running outside the execution of a plan which
                              contains a PXE boot task
            @tms_test_steps:
                @step: Execute service xientd status
                @result: status should be stopped
                @step: Execute litp prepare_restore
                       Execute litp create_plan
                       Execute litp run_plan
                @result: Plan executes successfully
                @step: Execute service xientd status
                @result: status should be stopped
                @step: Execute shutdown -r now on the LMS.
                       When LMS reboots, execute service xinetd status
                @result: status should be stopped
                @step: Check udev nic rules
                @result: Only one nic udev rule is generated on a node.
            @tms_test_precondition: None
            @tms_execution_type: Automated
        """
        self.log('info', "1. Verify that the service "
                         "xinetd on the MS is not running.")

        _, _, rc = self.get_service_status(self.ms_node, 'xinetd',
                                           assert_running=False)
        self.assertNotEqual(0, rc)

        self.log('info', "2. Execute prepare_restore followed "
                         "by create_plan/run_plan.")
        _, _, rc = self.execute_cli_prepare_restore_cmd(self.ms_node)
        self.run_and_check_plan(self.ms_node, const.PLAN_COMPLETE,
                                plan_timeout_mins=35)

        self.log('info', "3. Verify that the service "
                         "xinetd on the MS is not running.")
        _, _, rc = self.get_service_status(self.ms_node, 'xinetd',
                                           assert_running=False)
        self.assertNotEqual(0, rc)

        self.log('info', "4. Reboot the MS and ensure "
                         "that xinedt isn't running.")
        cmd = const.REBOOT_PATH
        self.run_command(self.ms_node, cmd, su_root=True)
        time.sleep(30)
        self.wait_for_node_up(self.ms_node, timeout_mins=5, wait_for_litp=True)
        _, _, rc = self.get_service_status(self.ms_node, 'xinetd',
                                           assert_running=False)
        self.assertNotEqual(0, rc)

        # Set passwords on rebooted nodes
        for node in self.mn_nodes:
            cmd = "sed -i '/{0}/d' {1}/known_hosts".format(
                node, const.SSH_KEYS_FOLDER)
            _, _, rc = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, rc)

            self.assertTrue(self.set_pws_new_node(self.ms_node, node),
                            "Failed to set password on node {0}.".format(node))

            # Run command on node to ensure correct password has been set
            _, _, rc = self.run_command(node, 'hostname')
            self.assertEqual(0, rc)

        self.log('info', "5. Checking nic udev rules.")
        self.assert_udev_rules()
