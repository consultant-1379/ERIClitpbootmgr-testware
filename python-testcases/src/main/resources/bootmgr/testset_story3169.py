'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2014
@author:    mboyer
@summary:   Integration test for LVM root VG awareness in BootMgr
            Agile: LITPCDS-3169
'''

import os.path
import re

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
from storage_utils import StorageUtils
from test_constants import COBBLER_SNIPPETS_DIR, PLAN_TASKS_SUCCESS


class Story3169(GenericTest):

    '''
    As a Product Designer, I want logic in the bootmanager, so that the correct
    disk is used for the OS installation when multiple disks are configured for
    the node
    '''
    story = "litpcds_3169"

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story3169, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()
        self.storage = StorageUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        super(Story3169, self).tearDown()

    @staticmethod
    def _extract_mounts_for_vgs_in_snippet_files(mount_points, snippet_lines):
        """Extract mount points that are used in snippet files for
        creating root volume group.
        """
        snippet_vgs = set([sn['volume_group'] for sn in snippet_lines])
        mount_points = [mp for mp in mount_points
                         if mp['volume_group'] in snippet_vgs]
        return mount_points

    @staticmethod
    def _size_in_mbytes(size_string):
        """Extract size in megabytes from various human readable
        forms.

        Examples: size_string can be 200M or 300.00 GiB
        """
        pattern = r'^\s*(?P<size>[1-9][.0-9]*)\s*(?P<unit>[MGT](iB)?)\s*$'
        regexp = re.compile(pattern)
        match = regexp.search(size_string)
        if match:
            parts = match.groupdict()
            if parts:
                if 'size' in parts.keys() and 'unit' in parts.keys():
                    size = int(float(parts['size']))
                    unit = parts['unit'][0]
                    if unit == 'M':
                        pass  # no change
                    elif unit == 'G':
                        size *= 1024
                    elif unit == 'T':
                        size *= 1024 * 1024

        return size

    def get_info_from_snippet(self, snip_file, snip_file_dir):
        """Given a partition snippet file and it's directory, return
        'name' and 'size' of partitions that contain the line
            '--name' in 'snip_file'"""
        # setup grep params
        grep_file = os.path.join(snip_file_dir, snip_file)
        grep_name = r"\--name="

        # execute grep command
        cmd = RHCmdUtils().get_grep_file_cmd(grep_file, grep_name)
        std_out, std_err, exit_code = self.run_command(self.test_ms, cmd)
        self.assertNotEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, exit_code)

        partition_info = []
        for line in std_out:
            part_dict = {}
            # Splits out the volume name and volume size values
            # from the puppet snippet files
            part_dict['name'] = line.split()[4].split('=')[-1]
            part_dict['size'] = line.split()[6].split('"')[0].split('=')[-1]
            part_dict['volume_group'] = line.split()[5].split('=')[1]

            partition_info.append(part_dict)

        return partition_info

    def match_mount_points(self, node_url):
        """given a url of a node, match it's storage profile to a
        profile in the model. If the profile exists in the model
        build a dict of the resulting mount point information """
        mount_points_list = []

        # get storage profile names from node urls
        node_storage_url = node_url + "/storage_profile"
        prof_url = self.execute_show_data_cmd(self.test_ms, node_storage_url,
            "inherited from")

        mount_points_list = self.build_mount_points(prof_url)
        self.assertNotEqual([], mount_points_list)

        return mount_points_list

    def build_mount_points(self, url):
        """for a given url get mount point information and return a dict"""
        mounts = []

        # grab system urls
        fsys_urls = self.find(self.test_ms, url, "file-system", True)

        # get mounts points and sizes
        for fsys_url in fsys_urls:
            mount_info = {}

            # get all props under url
            props = self.get_props_from_url(self.test_ms, fsys_url)

            # get parent volume_group
            vg_url = "/".join(fsys_url.split("/")[:-2])
            vg_props = self.get_props_from_url(self.test_ms, vg_url)

            # store in dicts

            # mount_info['origin'] = props['mount_point']
            mount_info['origin'] = fsys_url.split("/")[-1]
            mount_info['size'] = props['size']
            mount_info['volume_group'] = vg_props['volume_group_name']
            mount_info['vg_id'] = vg_url.split('/')[-1]
            mounts.append(mount_info)

        return mounts

    def get_node_urls(self):
        """get system node urls"""
        node_urls = self.find(self.test_ms, "/deployments", "node")
        return node_urls

    @attr('all', 'revert', 'story3169', '3169_01')
    def test_01_p_check_root_vg_used(self):
        """
        @tms_id: litpcds_3169_tc01
        @tms_requirements_id: LITPCDS-3169
        @tms_title: check_root_vg_used
        @tms_description:
            Test that when a node is installed (with two VGs in the model)
            that the root_vg is used and other disks are ignored.
            Checks the kickstart file to see which VG has been picked.
        @tms_test_steps:
            @step: Add a storage profile with two volume groups (one root one
            none root)
            @result: Storage profiles added
            @step: Create a new node in the model with the just created storage
            profiles
            @result: New node definition added
            @step: create/run_plan
            @result: plan is running
            @step: Wait for kickstart snippet task to finish
            @result: kickstart snippet task succeeds and kickstart snippet is
            created
            @step: stop plan
            @result: plan is in stopped state
            @step: Verify kickstart snippet
            @result: The volume group used in the kickstart snippet
                is the one with the root volume
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        storage_profiles = self.find(self.test_ms, "/infrastructure",
                "storage-profile-base", rtn_type_children=False)[0]

        # 1. Create a storage profile with 2 VGs
        sp_path = os.path.join(storage_profiles, self.story + "_test1")
        self.execute_cli_create_cmd(self.test_ms, sp_path, "storage-profile")

        vg_a = os.path.join(sp_path, "volume_groups", "vg_A")
        self.execute_cli_create_cmd(self.test_ms, vg_a, "volume-group",
                "volume_group_name=root_vg")

        root_fs = os.path.join(vg_a, "file_systems", "root")
        self.execute_cli_create_cmd(self.test_ms, root_fs, "file-system",
                "type='ext4' mount_point='/' size='16G'")

        swap_fs = os.path.join(vg_a, "file_systems", "swap")
        self.execute_cli_create_cmd(self.test_ms, swap_fs, "file-system",
                "type='swap' mount_point='swap' size='2G'")

        root_pd = os.path.join(vg_a, "physical_devices", "root_pd")
        self.execute_cli_create_cmd(self.test_ms, root_pd, "physical-device",
                "device_name=hd_test0")

        # 2. Now create a non-root VG
        vg_b = os.path.join(sp_path, "volume_groups", "vg_B")
        self.execute_cli_create_cmd(self.test_ms, vg_b, "volume-group",
                "volume_group_name=data_vg")

        app1_fs = os.path.join(vg_b, "file_systems", "appdata")
        self.execute_cli_create_cmd(self.test_ms, app1_fs, "file-system",
                "type='ext4' mount_point='/opt/foo' size='16G'")

        app2_fs = os.path.join(vg_b, "file_systems", "appstorage")
        self.execute_cli_create_cmd(self.test_ms, app2_fs, "file-system",
                "type='ext4' mount_point='/opt/bar' size='2G'")

        root_pd = os.path.join(vg_b, "physical_devices", "app_pd")
        self.execute_cli_create_cmd(self.test_ms, root_pd, "physical-device",
                "device_name=hd_test1")

        # 3. Reuse an existing item of type system (or whose type *extends*
        #  system) in a brand new node definition
        test_node_name = "node" + self.story + "_1"
        systems_url = self.find(self.test_ms,
                                "/infrastructure",
                                "system",
                                False)[0]
        system_url = systems_url + "/system_" + self.story

        test_node_hostname = self.story.replace("_", "-")
        cmds = self.get_create_node_deploy_cmds(self.test_ms,
                test_node_name,
                hostname=test_node_hostname,
                system_path=system_url,
                system_type="system", create_system=True)
        result = self.run_commands(self.test_ms, cmds)
        self.assertEqual([], self.get_stderr(result))

        # 4. Make sure the node's system has disk items with names that match
        # its storage profile
        for cmd in cmds:
            if "/infrastructure" in cmd and "-t system" in cmd:
                test_system = self.cli.get_command_url(cmd)
                break

        extant_disk = self.find(self.test_ms, test_system, "disk")[0]
        self.execute_cli_update_cmd(self.test_ms, extant_disk,
                props='name=hd_test0')

        # 5. Add 2nd disk to this system
        second_disk = os.path.join(test_system, "disks", "test_disk")
        second_disk_props = "name=hd_test1 size=40G uuid=2nd"
        self.execute_cli_create_cmd(self.test_ms, second_disk,
                                    "disk", second_disk_props)

        testnode_url = None
        nodes_path = self.find(self.test_ms, "/deployments", "node")
        for node in nodes_path:
            if test_node_name == node.split("/")[-1]:
                testnode_url = node
                break
        self.assertFalse(testnode_url is None)

        sp_link_url = testnode_url + "/storage_profile"
        self.execute_cli_remove_cmd(self.test_ms, sp_link_url)

        self.execute_cli_inherit_cmd(self.test_ms, sp_link_url, sp_path)

        #self.log("info", self.get_props_from_url(self.test_ms,
        #        os.path.join(testnode_url, "network-profile")))
        self.execute_cli_createplan_cmd(self.test_ms)

        # 6. Run plan until task is finished
        self.execute_cli_runplan_cmd(self.test_ms)

        task_desc = 'Create "RHEL7" partition kickstart snippet for node "*"'
        task_success = self.wait_for_task_state(self.test_ms, task_desc,
            PLAN_TASKS_SUCCESS)
        self.assertTrue(task_success, "The task {0} did not succeed".format(
            task_desc))

        self.stop_plan_if_running(self.test_ms)

        # 7. Inspect snippet
        snip_file = test_node_hostname + ".ks.partition.snippet"
        partition_info = self.get_info_from_snippet(snip_file,
            COBBLER_SNIPPETS_DIR)
        mounts = self.match_mount_points(testnode_url)

        # 8. Find root vg in the model
        root_vg = set([mount['volume_group'] for mount in mounts
                       if mount['origin'] == 'root'])
        # 9. Find vg used in snippet
        snippet_vg = set([sn['volume_group'] for sn in partition_info])

        self.assertEqual(root_vg, snippet_vg)
