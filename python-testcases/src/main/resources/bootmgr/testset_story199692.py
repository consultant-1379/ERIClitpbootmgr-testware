"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2017
@author:    Laura Forbes
@summary:   TORF-199692
            Optimise puppet timer configuration to improve performance on
            larger systems and minimise occurrence of 'execution expired'
"""

from litp_generic_test import GenericTest, attr
import test_constants as const
from redhat_cmd_utils import RHCmdUtils


class Story199692(GenericTest):
    """
        Optimise puppet timer configuration to improve performance on
        larger systems and minimise occurrence of 'execution expired'
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story199692, self).setUp()

        self.rhcmd = RHCmdUtils()

        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.kickstart_erb =\
            const.LITP_PATH +\
            "etc/puppet/modules/cobbler/templates/kickstart.erb"
        self.cobbler_ks_path = "/var/lib/cobbler/kickstarts/"

    def tearDown(self):
        """ Runs after every single test """
        super(Story199692, self).tearDown()

    @attr('all', 'revert', 'story199692', 'story199692_tc07')
    def test_07_p_correct_values_in_kickstart_files(self):
        """
            @tms_id: torf_199692_tc07
            @tms_requirements_id: TORF-199692
            @tms_title: Kickstart Files On MS Have Correct Values
            @tms_description: Verify that the kickstart.erb file on the MS
                has the correct values for 'runinterval' and 'configtimeout'
                and the kickstart file for each node also has the correct
                values for these parameters.
            @tms_test_steps:
                @step: Grep the kickstart.erb file on the MS for 'runinterval'
                    and 'configtimeout' parameters. Assert that the
                    parameters are set to the correct values
                @result: Parameters are set to correct values
                @step: Grep the kickstart file for each node for 'runinterval'
                    and 'configtimeout' parameters. Assert that the parameters
                    are set to the correct values
                @result: Parameters are set to correct values
            @tms_test_precondition: None
            @tms_execution_type: Automated
        """
        # 'runinterval = 1800' should be in the kickstart file
        run_interval = "runinterval"
        run_interval_value = '1800'
        run_interval_expected = "{0} = {1}".format(
            run_interval, run_interval_value)

        # 'configtimeout = 1720' should be in the kickstart file
        config_timeout = "configtimeout"
        config_timeout_value = '1720'
        config_timeout_expected = "{0} = {1}".format(
            config_timeout, config_timeout_value)

        # Create grep command to find values in file
        cmd = self.rhcmd.get_grep_file_cmd(
            self.kickstart_erb, [run_interval, config_timeout])

        self.log('info', "1. Grep the kickstart.erb file on the MS "
                         "for 'runinterval' and 'configtimeout' parameters. "
                         "Assert that the parameters are set to "
                         "the correct values.")
        std_out, std_err, rc = self.run_command(
            self.ms_node, cmd, su_root=True)
        self.assertEqual(0, rc)
        self.assertEqual([], std_err)

        self.assertTrue(any(run_interval_expected in s for s in std_out),
                        "Expected '{0}' not found in {1} on {2}".format(
                            run_interval_expected,
                            self.kickstart_erb, self.ms_node))

        self.assertTrue(any(config_timeout_expected in s for s in std_out),
                        "Expected '{0}' not found in {1} on {2}".format(
                            config_timeout_expected,
                            self.kickstart_erb, self.ms_node))

        self.log('info', "2. Grep the kickstart file for each node "
                         "for 'runinterval' and 'configtimeout' parameters. "
                         "Assert that the parameters are set to "
                         "the correct values.")
        for node in self.mn_nodes:
            # Find the node's kickstart file on the MS
            node_ks_file = self.cobbler_ks_path + "{0}.ks".format(node)
            # Create grep command to find values in file
            cmd = self.rhcmd.get_grep_file_cmd(
                node_ks_file, [run_interval, config_timeout])

            std_out, std_err, rc = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual(0, rc)
            self.assertEqual([], std_err)

            self.assertTrue(any(run_interval_expected in s for s in std_out),
                            "Expected '{0}' not found in {1} on MS".format(
                                run_interval_expected, node_ks_file))

            self.assertTrue(any(config_timeout_expected in s for s in std_out),
                            "Expected '{0}' not found in {1} on MS".format(
                                config_timeout_expected, node_ks_file))
