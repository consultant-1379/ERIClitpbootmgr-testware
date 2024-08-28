'''
COPYRIGHT Ericsson 2021
The copyright to the computer program(s) herein is the property of
Ericssont Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2021
@author:    Xindi Qiu
@summary:   TORF-489029
            Integration test to verify vxrsyncd service is running
            on a different port than 8989
'''
import re
from litp_generic_test import GenericTest, attr
from test_constants import NETSTAT_PATH, GREP_PATH
from redhat_cmd_utils import RHCmdUtils


class Story489029(GenericTest):
    """
    verify the vxrsyncd service is running on a different port than 8989 (Pos)
    Test to verify that when RHEL7 is installed on
    peer nodes then vxrsyncd service is running on
    a different port than 8989, i.e. 8999
    """
    def setUp(self):
        """
        Description:
            Runs before every single test.
        Actions:

            1. Call the super class setup method.
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        super(Story489029, self).setUp()
        self.managed_nodes = self.get_managed_node_filenames()
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """
        Description:
            Run after each test and performs the following:
        Actions:
            1. Cleanup after test if global results value has been used
            2. Call the superclass teardown method
        Results:
            Items used in the test are cleaned up and the
            super class prints out end test diagnostics
        """
        super(Story489029, self).tearDown()

    @attr('all', 'revert', 'story489029', 'story489029_tc01')
    def test_01_p_validate_service_on_different_port(self):
        """
        @tms_id: torf_489029_tc01
        @tms_requirements_id: TORF-489029
        @tms_title: validate_service_on_different_node
        @tms_description:
            Verify that vxryncd.service(VVR process) on nodes
            to run on a different port
        @tms_test_steps:
            @step: Check that vxrsyncd service is running on node
            @result: The vxrsyncd service is running on the node
            @step: Verify that the service is not running on port 8989
            @result: The vxrsyncd service not running on port 8989
            @step: Verify that the service is running on port 8999
            @result: The vxrsyncd service is running on the port 8999
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', '1. Check that vxryncd service is running on nodes')
        for node in self.managed_nodes:

            service_status = self.rhcmd.get_systemctl_status_cmd('vxrsyncd')
            service_stat, _, _ = self.run_command(
                node, service_status, default_asserts=True)
            self.assertNotEqual(None, re.search(
                r".active.\(running\)", str(service_stat)))
            self.log('info', '2. assert that vxrsyncd '
                             'service is not running on the port 8989')
            service_port = "{0} -nplt | {1} 8989".format(
                NETSTAT_PATH, GREP_PATH)
            service_in_port, std_err, return_code = self.run_command(
                node, service_port, su_root=True)
            self.assertEqual([], service_in_port)
            self.assertEqual([], std_err)
            self.assertEqual(1, return_code)

            self.log('info', '3. assert that vxrsyncd '
                             'service is running on the port 8999')
            service_port = "{0} -nplt | {1} 8999".format(
                NETSTAT_PATH, GREP_PATH)
            service_in_port, _, _ = self.run_command(
                node, service_port, su_root=True, default_asserts=True)
            self.assertTrue(
                self.is_text_in_list_regex(
                    r".\.vxrsyncd$",
                    service_in_port),
                "vxryncd service is not running on node")
