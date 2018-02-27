# Copyright 2018 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ddt
import mock

from rally_ovs.plugins.ovs.scenarios import ovn_network
from tests.unit import test


@ddt.ddt
class OvnNetworkTestCase(test.ScenarioTestCase):

    @ddt.data(
        { "network_create_args" : {} },
        { "network_create_args" : { "amount" : 1 } },
        { "network_create_args" : { "amount" : 5 } },
    )
    @ddt.unpack
    def test_create_and_bind_ports(self,
                                   network_create_args):
        context = {
            "ovn_multihost" : {
                "controller" : {},
                "farms" : {},
                "install_method" : {},
            },
            "sandboxes" : mock.Mock(),
        }
        ports_per_network = mock.Mock()
        port_create_args = mock.Mock()
        port_bind_args = mock.Mock()

        num_nets = network_create_args.get("amount", 0)
        nets = [mock.Mock() for _ in range(num_nets)]
        port_sets = [mock.Mock() for _ in range(num_nets)]

        scenario = ovn_network.OvnNetwork(context)
        scenario._create_networks = mock.Mock(return_value=nets)
        scenario._create_lports = mock.Mock(side_effect=port_sets)
        scenario._bind_ports = mock.Mock()

        scenario.create_and_bind_ports(network_create_args=network_create_args,
                                       port_create_args=port_create_args,
                                       ports_per_network=ports_per_network,
                                       port_bind_args=port_bind_args)

        scenario._create_networks.assert_called_once_with(
            network_create_args)
        scenario._create_lports.assert_has_calls(
            [mock.call(n, port_create_args, ports_per_network) for n in nets])
        scenario._bind_ports.assert_has_calls(
            [mock.call(p, context["sandboxes"], port_bind_args) for p in port_sets])
