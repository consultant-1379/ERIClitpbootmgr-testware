"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2015
@author:    eslakal
@summary:   Tests for volmgr with dmp. Stories:
            LITPCDS-4016
"""
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils


class Story4016(GenericTest):
    """
    LITPCDS-4016:
        As a LITP User, I want Symantec DMP to be the only multipather
        used in a node that is member of an sfha cluster
    """

    def setUp(self):
        """Run before every test """
        super(Story4016, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()

    def _get_all_vcs_clusters(self):
        """Get urls of all items of type vcs-cluster
        Returns:
        list
        """
        return self.find(self.ms_node, '/deployments', 'vcs-cluster')

    def _get_sfha_clusters(self):
        """Get only clusters of type vcs_cluster and
        property: cluster_type=sfha
        Returns:
        list
        """
        sfha_clusters_urls = []

        for url in self._get_all_vcs_clusters():
            cl_type = self.get_props_from_url(self.ms_node, url,
                                              'cluster_type')
            if cl_type == 'sfha':
                sfha_clusters_urls.append(url)
        return sfha_clusters_urls

    def _get_sfha_nodes_urls(self):
        """Get urls of all nodes in all sfha clusters
        Returns:
        list
        """
        nodes_urls = []
        for cl_url in self._get_sfha_clusters():
            nodes_urls.extend(self.find(self.ms_node, cl_url, "node"))
        return nodes_urls

    def _get_sfha_nodes_filenames(self):
        """Get all filenames of all nodes in all sfha clusters
        Returns
        list
        """
        nodes_filenames = []
        for url in self._get_sfha_nodes_urls():
            filename = self.get_node_filename_from_url(self.ms_node, url)
            nodes_filenames.append(filename)
        return nodes_filenames

    def tearDown(self):
        """Run after every test"""
        super(Story4016, self).tearDown()

    @attr('all', 'revert', 'story4016', 'story4016_tc01')
    def test_01_p_validate_multipath(self):
        """
        @tms_id: litpcds_4016_tc01
        @tms_requirements_id: LITPCDS-4016
        @tms_title: validate_multipath
        @tms_description:
             Validates that multipath is not installed/loaded.
        @tms_test_steps:
            @step: Get multipathd service state
            @result: multipathd service is not running on any node
            @step: Check whether multipath packages are installed
            @result: multipath packages are not installed on any node
            @step: List the loaded kernel modules
            @result: multipath module is not loaded on any node
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1.
        service_cmd = self.rhc.get_systemctl_is_active_cmd("multipathd")
        packages = ['device-mapper-multipath', 'device-mapper-multipath-libs']

        for node in self._get_sfha_nodes_filenames():
            # 1a) verify that multipathd service is not running,
            out, err, r_code = self.run_command(node, service_cmd,
                                                su_root=True)
            self.assertEqual([], err)
            self.assertEqual(3, r_code)
            self.assertEqual(['unknown'], out, "multipathd is not unknown as "
                                               "expected on {0}".format(node))

            # 1b) multipath rpms are not installed
            pkg_cmd = self.rhc.check_pkg_installed(packages)
            out, err, r_code = self.run_command(node, pkg_cmd,
                                                su_root=True)
            self.assertEqual([], err)
            self.assertEqual(1, r_code)
            self.assertEqual([], out)

            # 1c) also the multipath kernel module is not loaded
            mod_cmd = '/sbin/lsmod | grep multipath'
            out, err, r_code = self.run_command(node, mod_cmd,
                                                su_root=True)
            self.assertEqual([], err)
            self.assertEqual(1, r_code)
            self.assertEqual([], out)

    @attr('all', 'revert', 'story4016', 'story4016_tc02')
    def test_02_p_validate_devices_under_dmp(self):
        """
        @tms_id: litpcds_4016_tc02
        @tms_requirements_id: LITPCDS-4016
        @tms_title: validate_devices_under_dmp
        @tms_description:
             Validates that symantec dmp is used
        @tms_test_steps:
            @step: Run pvs grep for dmp
            @result: dmp devices exist
            @step: Run pvs grep for everything excluding dmp
            @result: There are no other lvm devices except dmp
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. Run  pvs command and get all devices matching /dev/vx/dmp/
        dmp_devices_cmd = '/sbin/pvs --noheadings' \
                          ' | grep /dev/vx/dmp/'

        for node in self._get_sfha_nodes_filenames():
            dmp_devices, err, r_code = self.run_command(node, dmp_devices_cmd,
                                                        su_root=True)
            self.assertEqual([], err)
            self.assertEqual(0, r_code)
            self.assertTrue(dmp_devices)

        # 2. Verify that there are no other lvm devices
        other_devices_cmd_ = '/sbin/pvs --noheadings' \
                             ' | grep -v /dev/vx/dmp/'

        for node in self._get_sfha_nodes_filenames():
            other_devices, err, r_code = self.run_command(node,
                                                          other_devices_cmd_,
                                                          su_root=True)
            self.assertEqual([], err)
            self.assertEqual(1, r_code)
            self.assertFalse(other_devices)
