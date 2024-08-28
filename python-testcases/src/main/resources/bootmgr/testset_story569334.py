"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2022
@author:    Karen Flannery
@summary:   TORF-569334: As a LITP user, I want to retain previous
            PXE boot logs

"""
import test_constants
from litp_generic_test import GenericTest, attr


class Story569334(GenericTest):
    """
    TORF-569334:
    As a LITP user, I want to retain previous PXE boot logs
    When PXE boot a node
    If there are previous PXE log files
    Then the previous log files are retained
    And the new log files are written to a different directory
    So that I can maintain a history of PXE boots
    """

    def setUp(self):
        super(Story569334, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.node_paths = self.find(self.ms_node, "/deployments",
                                    "node")

    def tearDown(self):
        super(Story569334, self).tearDown()

    @attr('all', 'revert', 'torf569334', 'torf569334_tc01', 'expansion')
    def test_01_p_verify_cobbler_backup_folder(self):
        """
        @tms_id: torf_569334_tc01
        @tms_requirements_id: TORF-569334
        @tms_title: Verify cobbler backup folder
        @tms_description:
            Test to verify cobbler backup folders are generated when a
            node is PXE booted
        @tms_test_steps:
        @step: Check there are no backup folder present
        @result: No backup folders are present
        @step: Create dummy backup folder for test purposes to be
               overwritten on next PXE boot
        @result: dummy backup folder is created
        @step: Take a copy of "current" cobbler files for node1 to
               compare with the backup folder after PXE boot
        @result: node1 logs are coped to /tmp/cobbler_logs/
        @step: Execute prepare_restore on node1 and node3, create and
               run plan
        @result: Plan completes successfully
        @step: Verify backup folder are generated for node1 and node3
               and not for node2 and node4
        @result: backup folder exists for node1 and node3 and not for
                 node2 and node4
        @step: Verify that the backup folders contain all the logs
        @result: All logs are found
        @step: Verify that node1 dummy backup folder has been
                overwritten
        @result: node1 dummy backup folder has been overwritten
        @step: Compare node1 backup logs against those copied to
               /tmp/cobbler_logs/
        @result: All logs are the same
        @tms_test_precondition: deployment is expanded to 4 nodes
        @tms_execution_type: Automated
        """

        peer_nodes = self.get_managed_node_filenames()
        cobbler_dir = "/var/log/cobbler/anamon/"
        cobbler_backup_dir = "/var/log/cobbler/anamon.backup/"
        awk_cmd = " | awk '{print $9}'"
        list_cobbler_logs_cmd = "{0} -lh {1}{2}/ {3}"
        list_backup_logs_cmd = "{0} -lh {1}{2}*/{2} {3}"
        tmp_dir = "/tmp/cobbler_logs/"

        self.log("info", "#1. Verify that no backup exists")
        for node in peer_nodes:
            backup_exists = self.remote_path_exists(self.ms_node, "{0}{1}*/".
                                            format(cobbler_backup_dir,
                                                   node), expect_file=False)
            self.assertFalse(backup_exists, "backup found/not expected")

        self.log("info", "#2. Create dummy backup folder to verify it's "
                         "overwritten by next PXE boot")
        mkdir_cmd = "{0} -p {1}{2}.dummy/".format(test_constants.MKDIR_PATH,
                                            cobbler_backup_dir, peer_nodes[0])
        self.run_command(self.ms_node, mkdir_cmd, su_root=True,
                         default_asserts=True)

        copy_cmd = "cp -r {0}{1}/ {2}{1}.dummy/".format(cobbler_dir,
                                                        peer_nodes[0],
                                                        cobbler_backup_dir)
        self.run_command(self.ms_node, copy_cmd, su_root=True,
                         default_asserts=True)

        self.log("info", "#3. Take a copy of node1 logs for compare after "
                         "PXE boot")
        mkdir_cmd = "{0} -p {1}".format(test_constants.MKDIR_PATH, tmp_dir)
        self.run_command(self.ms_node, mkdir_cmd, su_root=True,
                         default_asserts=True)

        copy_cmd = "cp {0}{1}/* {2}".format(cobbler_dir, peer_nodes[0],
                                            tmp_dir)
        self.run_command(self.ms_node, copy_cmd, su_root=True,
                         default_asserts=True)

        self.log('info', "#4. Execute prepare_restore on node1 and node3 "
                         "followed by create_plan/run_plan.")
        self.execute_cli_prepare_restore_cmd(self.ms_node, " -p {0}".format(
            self.node_paths[0]))
        self.execute_cli_prepare_restore_cmd(self.ms_node, " -p {0}".format(
            self.node_paths[2]))
        self.run_and_check_plan(self.ms_node, test_constants.PLAN_COMPLETE,
                                plan_timeout_mins=60)
        self.log("info", "run plan complete")

        self.log("info", "#5. Verify backup folders exist for node1 and node3 "
                         "and do not exist for node2 and node4")
        for node in peer_nodes:
            backup_exists = self.remote_path_exists(self.ms_node, "{0}{1}*/"
                                                    .format(cobbler_backup_dir,
                                                            node),
                                                    expect_file=False)

            if peer_nodes[0] in node or peer_nodes[2] in node:
                self.assertTrue(backup_exists)
                self.log("info", "#6. Verify backup folders contain the same "
                                 "logs as cobbler folder")
                list_cobbler_logs = self.run_command(self.ms_node,
                                         list_cobbler_logs_cmd.format(
                                             test_constants.LS_PATH,
                                                cobbler_dir, node, awk_cmd),
                                             su_root=True,
                                             default_asserts=True)
                list_backup_logs = self.run_command(self.ms_node,
                                            list_backup_logs_cmd.format(
                                                test_constants.LS_PATH,
                                                cobbler_backup_dir, node,
                                                awk_cmd),
                                            su_root=True,
                                            default_asserts=True)
                self.assertEqual(list_cobbler_logs, list_backup_logs,
                         "All files were not copied on '{0}'".format(node))
            else:
                self.assertFalse(backup_exists)

        self.log("info", "#7. Verify dummy backup folder doesn't exist")
        grep_cmd = "{0} {1} | {2} dummy".format(test_constants.LS_PATH,
                                                cobbler_backup_dir,
                                                test_constants.GREP_PATH)
        grep_out = self.run_command(self.ms_node, grep_cmd, su_root=True)
        self.assertNotEqual(["node1.dummy"], grep_out[0],
                            "dummy backup folder was found")

        self.log("info", "#8. Verify file contents are the same")
        list_of_logs = self.run_command(self.ms_node, list_backup_logs_cmd.
                                        format(test_constants.LS_PATH,
                                   cobbler_backup_dir, peer_nodes[0], awk_cmd),
                                        su_root=True)
        for log in list_of_logs[0]:
            cmp_cmd = "cmp {0}{1}*/{1}/{2} {3}{2}".format(cobbler_backup_dir,
                                                  peer_nodes[0], log, tmp_dir)
            cmp_out = self.run_command(self.ms_node, cmp_cmd, su_root=True)
            self.assertEqual([], cmp_out[0],
                             "Log file '{0}' is not the same as expected"
                             .format(log))
