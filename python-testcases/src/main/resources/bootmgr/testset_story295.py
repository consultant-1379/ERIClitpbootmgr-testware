'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2013
@author:    Luke Murphy
@summary:   Integration test for system mount points
            Agile: EPIC-189, STORY-295
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
from storage_utils import StorageUtils

import os
import test_constants


class Story295(GenericTest):
    """As a system designer I want the cobbler plugin to generate
       kickstart information from file system layouts so that
       kickstarted systems have filesystems determined by the model.
    """

    def setUp(self):
        """init each testcase"""
        super(Story295, self).setUp()
        self.cli = CLIUtils()
        self.storage = StorageUtils()
        self.rhcmd = RHCmdUtils()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()

    def tearDown(self):
        """cleanup after each testcase"""
        super(Story295, self).tearDown()

    def get_storage_urls(self):
        """get system storage url"""
        storage_urls = self.find(
            self.ms_node, "/infrastructure", "storage-profile"
        )
        self.assertNotEqual([], storage_urls)
        return storage_urls

    def get_node_urls(self):
        """get system node urls"""
        node_urls = self.find(
            self.ms_node, "/deployments", "node"
        )
        self.assertNotEqual([], node_urls)
        return node_urls

    def _build_mount_points(self, url):
        """For a given url get mount point information and return a dict"""
        mounts = []

        # grab system urls
        fsys_urls = self.find(self.ms_node, url, "file-system", True)

        # get mounts points and sizes
        for fsys_url in fsys_urls:
            mount_info = {}
            # get all props under url
            props = self.get_props_from_url(self.ms_node, fsys_url)

            mount_info['fs_url'] = url
            mount_info['origin'] = props['mount_point']
            mount_info['size'] = props['size']

            # append dicts to list
            mounts.append(mount_info)

        return mounts

    def _match_mount_points(self, node_url):
        """
        Given a URL of a node, build a dict
        of the mount point information.
        """

        mount_points_list = self._build_mount_points(node_url + \
                                                     "/storage_profile")
        self.assertNotEqual([], mount_points_list)
        return mount_points_list

    def _get_info_from_snippet(self, snip_file, snip_file_dir):
        """Given a partition snippet file and it's directory, return
           'name' and 'size' of partitions that contain the line
            '--name' in 'snip_file'"""
        # setup grep params
        grep_file = os.path.join(snip_file_dir, snip_file)
        grep_name = r"\--name="

        # execute grep command
        cmd = RHCmdUtils().get_grep_file_cmd(grep_file, grep_name)
        std_out, std_err, exit_code = self.run_command(self.ms_node, cmd)
        self.assertNotEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, exit_code)

        partition_info = []
        for line in std_out:
            part_dict = {}
            # check for dynamic disk partitioning:
            split_index = 8 if '--grow' in line else 6
            ##Splits out the volume name and volume size values
            ##from the puppet snippet files
            part_dict['name'] = line.split()[4].split('=')[-1]
            part_dict['size'] = \
                line.split()[split_index].split('=')[-1].strip('"')
            part_dict['mount_point'] = line.split()[2]

            partition_info.append(part_dict)

        return partition_info

    def _get_device_mount_point(self, node, lv_path):
        """
            Return the mount point of a file system
            Ret value 32 means known but already mounted
        """
        cmd = "/bin/mount " + lv_path
        out, err, ret_code = self.run_command(node, cmd, su_root=True)

        self.assertNotEqual([], out)
        self.assertEqual([], err)
        if ret_code == 32:
            if self.is_text_in_list('already', out):
                mount_point = out[-1].split()[-1]
                self.log("info", "Returning mount point '{0}'"
                         .format(mount_point))
                return mount_point

        self.log("info", "Mount error")
        return None

    @attr('all', 'revert', 'story295', '295_01',
          'story487446', 'story487446_tc01')
    def test_01_p_cobbler_mount_points(self):
        """
        @tms_id: litpcds_295_tc01
        @tms_requirements_id: LITPCDS-295, TORF-487446
        @tms_title: cobbler_mount_points
        @tms_description:
            Test to ensure that the mount points and sizes defined in the LITP
            model are being used by cobbler and match the points/sizes on
            created nodes
            TORF-487446: ensure that /boot partition size on each
                         peer node is 1gb
        @tms_test_steps:
            @step: Compare the mount point in the model with the actual mount
                point for every node
            @result: Mount points match
            @step: Compare the size of the volume with the one in the model for
            every node
            @result: Sizes match
            @step: check /boot partition size on each peer node
            @result: /boot partition size is 1gb
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. get all node urls
        node_urls = self.find(self.ms_node, "/deployments", "node", "True")

        # 2. For each node, ie. iterate through node urls
        for node_url in node_urls:
            node = self.get_node_filename_from_url(self.ms_node, node_url)

            # get model_mount_points info for current node
            model_mount_points = self._match_mount_points(node_url)

            # 3. get node filename via node_url
            node_fname = self.get_node_filename_from_url(
                self.ms_node, node_url
            )

            # 4. get lvscan output
            lv_out, std_err, return_code = self.run_command(
                node_fname, "/sbin/lvscan", su_root=True
            )
            self.assertNotEqual([], lv_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, return_code)

            # 5. compare lvscan output from managed node and
            # info stored in model

            # get lvscan output ( list containing dict(s) )
            lv_out_list = self.storage.parse_lvscan_stdout(lv_out)

            for lv_dict in lv_out_list:
                lv_dict['mnt_pt'] = self._get_device_mount_point(
                    node, lv_dict['origin']
                )

            for model_mount_dict in model_mount_points:
                if model_mount_dict['origin'] != 'swap':
                    mount_found = False
                    mount_size_found = False
                    for lv_dict in lv_out_list:

                        lv_mount = lv_dict['mnt_pt']

                        if model_mount_dict['origin'] == lv_mount:
                            mount_found = True

                            # Get size firstly from model
                            # Then from lvscan output
                            model_size = model_mount_dict['size']
                            lv_size = lv_dict[self.storage.vol_size]

                            # mount sizes are in gigabytes
                            if 'G' in model_size and 'GiB' in lv_size:
                                mount_size = \
                                    model_mount_dict['size'].split('G')[0]
                                model_size = lv_dict[
                                    self.storage.vol_size
                                ].split('G')[0]

                            # mount sizes are in megabytes
                            if 'M' in model_size and 'MiB' in lv_size:
                                mount_size = \
                                    model_mount_dict['size'].split('M')[0]
                                model_size = lv_dict[
                                    self.storage.vol_size
                                ].split('M')[0]

                            try:
                                # example - '16' in '16.00' || '2' in '2.00'
                                if mount_size in model_size:
                                    mount_size_found = True

                            except UnboundLocalError:
                                # unable to match sizes
                                self.log(
                                    "error",
                                    "Mount point sizes could not be matched"
                                )

                    # assert we got matches
                    self.assertTrue(mount_found,
                                    "Mount mismatch No match for {0}"
                                    .format(lv_mount))

                    self.assertTrue(mount_size_found, "Mount size mismatch")

            # 6. get /boot partition size from 'parted' command output
            cmd = "/usr/sbin/parted -l | awk '$NF==\"boot\"{print $4}'"
            boot_size, _, _ = self.run_command(node_fname, cmd, su_root=True,
                                               default_asserts=True)

            # assert /boot partition size is 1GB
            self.assertEquals("1049MB", boot_size[0],
                              "/boot partition size is {0}".format(boot_size))

    @attr('all', 'revert', 'story295', '295_02')
    def test_02_p_kickstart_snippets(self):
        """
        @tms_id: litpcds_295_tc02
        @tms_requirements_id: LITPCDS-295
        @tms_title: kickstart_snippets
        @tms_description:
            Verify that the kickstart snippet files have been created for the
            nodes in the cluster
            NOTE: also verifies LITPCDS-13441
        @tms_test_steps:
            @step: Verify that the kickstart snippet files exists on the nodes
            @result: The kickstart files exist
            @step: Compare the mount point of the volume with the one in the
            kickstart for every node
            @result: mount points match
            @step: Compare the size of the volume with the one in the
            kickstart for every node
            @result: sizes match
            @step: Verify that the kickstart files have the permission 644 set
            in the ms
            @result: kickstart permissions are 644
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        for node_url in self.get_node_urls():
            # 2. Get mount point info for current node
            mount_points = self._match_mount_points(node_url)

            # 3. Get node hostname via node_url
            node_name = self.get_props_from_url(
                self.ms_node, node_url, "hostname"
            )
            self.assertTrue(
                node_name is not "",
                """Expected a node hostname,
                   but got the empty string!"""
            )

            # 4. Check existence of snippet file,
            grep_snippet = node_name + ".ks.partition.snippet"
            grep_dir = test_constants.COBBLER_SNIPPETS_DIR
            cmd = RHCmdUtils().get_grep_file_cmd(
                grep_dir, [grep_snippet], file_access_cmd="ls"
            )

            std_out, std_err, exit_code = self.run_command(
                self.ms_node, cmd
            )
            # Verify that snippet file exists
            self.assertNotEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, exit_code)

            # 5. Got snippet file for current node, now get dict
            # of info from grepping the snippet file
            snippet_file = std_out[0]
            snippet_list = self._get_info_from_snippet(
                snippet_file, grep_dir
            )

            # 6. compare information in mount_points (model)
            # with information found in snippet_dict (snippet file)
            for mount_dict, snippet_dict in zip(mount_points, snippet_list):
                point_found = False
                size_match_found = False

                # match points
                if mount_dict['origin'] == snippet_dict['mount_point']:
                    self.log("info", "Model FS mount {0} = Snippet file FS {1}"
                             .format(mount_dict['origin'],
                             snippet_dict['mount_point']))
                    point_found = True

                    ##This checks that the same units are used for both lvscan
                    ##and as stated in the tree
                    if 'G' in mount_dict['size']:
                        # grab size in gigabytes
                        mount_size = mount_dict['size'].split('G')[0]

                        # assert that snippet_dict size is in Gigabytes
                        self.assertTrue(
                            len(snippet_dict['size']) >= 4,
                            "Size mismatch from snippet file"
                        )

                    elif 'M' in mount_dict['size']:
                        # grab size in megabytes
                        mount_size = mount_dict['size'].split('M')[0]

                        # assert that snippet_dict size is in Megabytes
                        self.assertTrue(
                            len(snippet_dict['size']) <= 3,
                            "Size mismatch from snippet file"
                        )

                    # assert we parsed it correctly
                    self.assertNotEqual("", mount_size)

                    if mount_size in snippet_dict['size']:
                        # matched size
                        size_match_found = True
                else:
                    self.log("info", "{0} != {1}".format(
                        mount_dict['origin'],
                        snippet_dict['mount_point']))

                # assert we got matches
                self.assertTrue(point_found, "Failed to match points for {0}"
                                .format(mount_dict['origin']))
                self.assertTrue(size_match_found, "Failed to match sizes")

        # LITPCDS-13441
        # Verify kickstart snippets have right permissions '644'
        cmd_permissions = "/usr/bin/stat -c \"%a %n\" {0}/*".format(
                                        test_constants.COBBLER_SNIPPETS_DIR)

        permissions, _, _ = self.run_command(self.ms_node, cmd_permissions,
                                             default_asserts=True)
        wrong_permissions = list()
        for permission in permissions:
            if "644" not in permission:
                wrong_permissions.append(permission)
        for snippet in wrong_permissions:
            permmission, snippet_file = snippet.split(" ")
            self.log('error',
                    "Snippet '{0}'' with wrong permissions '{1}'".format(
                                                    snippet_file, permmission))

        self.assertTrue([] == wrong_permissions)
