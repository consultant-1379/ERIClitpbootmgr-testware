'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2013
@author:    Luke Murphy
@summary:   LITPCDS-588
            As an Administrator I want a default LITP user in
            peer nodes so I can login remotely without
            using root account

            LITPCDS-11626
            Default user password expire date set to "never"
'''

from litp_generic_test import GenericTest, attr
import re


class Story588(GenericTest):
    """
        LITPCDS-588
        As an Administrator I want a default LITP user in
        peer nodes so I can login remotely without
        using root account

        LITPCDS-11626
        Default password expire date set to "never"
    """
    def setUp(self):
        """init each testcase"""
        super(Story588, self).setUp()
        self.litp_default_user = "litp-admin"
        self.all_nodes = ([self.get_management_node_filename()] +
                           self.get_managed_node_filenames())

    def tearDown(self):
        """cleanup after each testcase"""
        super(Story588, self).tearDown()

    def get_user_groups(self, node):
        """
        Description:
            Get the list of groups a user belongs to
        Args:
            node (str): The node to run the command on
        Returns:
            lst. of groups the user belongs to
        """
        cmd = '/usr/bin/groups'
        stdout = self.run_command(node, cmd,
                                  default_asserts=True)[0][0]
        user_groups = ((stdout.split(': '))[0]).split(' ')

        return user_groups

    @attr('all', 'revert', 'story588', 'story588_tc01', 'cdb_priority1')
    def test_01_n_admin_user_deployment(self):
        """
        @tms_id: litpcds_588_tc01
        @tms_requirements_id: LITPCDS-588
        @tms_title: admin_user_deployment
        @tms_description:
            Ensure that the litp-admin user has been deployed
            successfully to the nodes
        @tms_test_steps:
            @step: Verify groups for user litp-admin on MS and MNs
            @result: litp-admin has two groups on MS and one group on MNs
            @result: litp-admin's groups are litp-admin and celery on the MS
                     and litp-admin only on the MNs
            @step: Verify litp-admin's home directory
            @result: litp-admin's home directory has been created
            @step: Verify litp-admin sudo access
            @result: litp-admin does not have sudo access
            @step: Verify litp-admin's uid
            @result: litp-admin's uid is different from root's uid
            @step: Verify litp-admin's umask
            @result: litp-admin's umask is different from root's umask
            @step: Verify litp-admin's default access privileges
            @result: litp-admin cannot read /root
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        for node in self.all_nodes:

            # 1. run 'groups' command as 'litp_user'
            groups = self.get_user_groups(node)

            # 2. assert that 'litp-admin' is in two groups only on the MS
            # and one group only on the MNs

            expected_group_len = 1

            if node is self.all_nodes[0]:
                expected_group_len = 3

            group_len = len(groups)

            self.assertTrue(
                group_len == expected_group_len,
                "found incorrect number of groups - %s" % group_len
            )

            # 3. assert that 'litp-admin' is in 'litp-admin' group
            self.assertTrue(
                self.litp_default_user in groups,
                "expected group 'litp-admin', got %s" % groups[0]
            )

            # 4. assert that the 'litp-admin' home dir is present
            litp_path = "/home/litp-admin"
            self.assertTrue(
                self.remote_path_exists(node, litp_path, expect_file=False),
                "/home/litp-admin does not exist!"
            )

            # 5. assert that litp-admin does not have sudo access
            sudo_cmd = "sudo pvdisplay"
            expected_out = "litp-admin is not in the sudoers file"
            std_out, std_err, exit_code = self.run_command(
                node, sudo_cmd, sudo="True"
            )
            # assert expected values
            self.assertNotEqual([], std_out)
            self.assertTrue(
                self.is_text_in_list(expected_out, std_out),
                "litp-admin has sudo access!"
            )
            self.assertEqual([], std_err)
            self.assertEqual(1, exit_code)

            # 6. assert that litp-admin does not have root uid
            # assert that litp-admin does not have root uid
            uid_cmd = "id -u"

            # get root uid
            root_uid, std_err, return_code = self.run_command(
                node, uid_cmd, su_root=True
            )
            self.assertNotEqual([], root_uid)
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

            # get litp-admin uid
            litp_admin_uid, std_err, return_code = self.run_command(
                node, uid_cmd
            )
            self.assertNotEqual([], litp_admin_uid)
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

            # assert uids are not equal
            self.assertNotEqual(litp_admin_uid, root_uid)

            # 7. assert litp-admin does not have root umask
            # assert that root umask is not the same as litp-admin umask
            umask_cmd = "umask"

            # get litp-admin umask
            litp_admin_umask, std_err, return_code = self.run_command(
                node, umask_cmd
            )
            self.assertNotEqual([], litp_admin_uid)
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

            root_umask, std_err, return_code = self.run_command(
                node, "umask", su_root=True
            )
            self.assertNotEqual([], root_umask)
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

            # assert umask is not equal to root's
            self.assertNotEqual(litp_admin_umask, root_umask)

            # 8. assert default access privileges by running 'ls /root'
            std_out, std_err, return_code = self.run_command(
                node, "ls /root"
            )
            self.assertEqual([], std_out)
            self.assertNotEqual([], std_err)
            self.assertNotEqual(0, return_code)

    @attr('all', 'revert', 'story588', 'story588_tc03', 'cdb_priority1')
    def test_03_p_default_access_allowed(self):
        """
        @tms_id: litpcds_588_tc03
        @tms_requirements_id: LITPCDS-588
        @tms_title: default_access_allowed
        @tms_description:
            Confirm litp-admin has
            default access privileges for its home dir
        @tms_test_steps:
            @step: list $HOME as user litp-admin for all nodes
            @result: litp-admin can access $HOME
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. run 'ls' command
        for node in self.all_nodes:
            _, std_err, return_code = self.run_command(node, "ls $HOME")

            # in case the litp-admin home directory is not empty
            # we don't assert that standard out is not empty, as
            # long as we get a valid return code and no error
            # we know we have default privileges
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

    @attr('all', 'revert', 'story588', 'story588_tc04')
    def test_04_p_password_expiry(self):
        """
        @tms_id: litpcds_588_tc04
        @tms_requirements_id: LITPCDS-588, LITPCDS-11626
        @tms_title: password_expiry
        @tms_description:
            Confirm that users' password expiry
            policy is set to "never expire" on MS and peer nodes
        @tms_test_steps:
            @step: Verify root's password expiry for all nodes
            @result: root's password never expires
            @step: Verify litp-admin's password expiry for all nodes
            @result: litp-admin's password never expires
            @step: Create a new user for all nodes
            @result: new user created
            @step: Verify new user's password expiry for all nodes
            @result: new user's password never expires
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_message = 'Password expires : never'
        users = ['root', self.litp_default_user, 'newuser']

        self.log('info',
        '1. Verify password expiry policy for users "root" and "litp-admin" '
            'and a newly created user')
        for node in self.all_nodes:
            try:
                self.log('info',
                'a. Create a new user')
                cmd = '/usr/sbin/useradd {0}'.format(users[-1])
                out, _, _ = self.run_command(node, cmd, su_root=True,
                                                    default_asserts=True)
                self.assertEqual([], out)

                self.log('info',
                'b. Check that password expire policy is set correctly')
                for user in users:
                    cmd = 'chage --list {0}'.format(user)
                    out, _, _ = self.run_command(node, cmd, su_root=True,
                                                    default_asserts=True)
                    msg_found = False
                    for line in out:
                        line = re.sub('\t+', ' ', line)
                        if line == expected_message:
                            msg_found = True
                    self.assertTrue(msg_found,
                    '\nPassword for user "{0}" on "{1}" not set to never '
                    'expire\nCURRENT PASSWORD SETTING\n{2}'
                    .format(user, node, '\n'.join(out)))
            finally:
                self.log('info',
                    'FINALLY c. Remove newly created user')
                cmd = '/usr/sbin/userdel -r {0}'.format(users[-1])
                out, _, _ = self.run_command(node, cmd, su_root=True,
                                                    default_asserts=True)
                self.assertEqual([], out)
