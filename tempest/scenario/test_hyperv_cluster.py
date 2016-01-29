# Copyright 2016 Cloudbase Solutions SRL
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from oslo_log import log as logging

from tempest import config
from tempest import exceptions
from tempest.common.utils.windows import winrmclient
from tempest.scenario import manager
from tempest.scenario import utils as test_utils
from tempest import test

CONF = config.CONF

LOG = logging.getLogger(__name__)

class TestHyperVClusterBasic(manager.ScenarioTest):
    """Test suite for basic HyperV Cluster verification

    This is a test case that does the following operations:
     * Create a instance on a specific node
     * Reboot that host using host poweraction
     * Check that the instance host has changed
     * Terminate the instance
    """

    _host_key = 'OS-EXT-SRV-ATTR:host'

    credentials = ['primary', 'admin']

    @classmethod
    def setup_clients(cls):
        super(TestHyperVClusterBasic, cls).setup_clients()
        # Use admin client by default
        cls.manager = cls.admin_manager
        cls.admin_servers_client = cls.os_adm.servers_client

    def setUp(self):
        super(TestHyperVClusterBasic, self).setUp()
        self.win_user = CONF.hyperv.win_user
        self.win_pass = CONF.hyperv.win_pass

    def _get_server_host(self, server_id):
        server = (self.admin_servers_client.show_server(server_id)['server'])
        return server[self._host_key]

    def trigger_failover(self, host):
        client = winrmclient.WinrmClient(server_ip=host, username=self.win_user,
                                          password=self.win_pass)
        client.run_powershell('stop-service ClusSVC')

    def restore_server(self, host):
        client = winrmclient.WinrmClient(server_ip=host, username=self.win_user,
                                          password=self.win_pass)
        client.run_powershell('start-service ClusSVC')


    @test.idempotent_id('057e19cf-7360-48e6-972f-6e1491cd3d95')
    @test.services('compute', 'volume', 'image', 'network')
    def test_hyperv_cluster_scenario(self):
        image_id = self.glance_image_create()
        server_id = self.create_server(image_id=image_id,
                                       wait_until='ACTIVE',
                                       wait_on_delete=False)['id']
        server_host_original = self._get_server_host(server_id)
        self.trigger_failover(server_host_original)
        # sleep to give time for the machine to reach the new host
        time.sleep(30)
        server_host_new = self._get_server_host(server_id)

        self.assertNotEqual(server_host_original, server_host_new)

        self.addCleanup(self.restore_server, server_host_original)
