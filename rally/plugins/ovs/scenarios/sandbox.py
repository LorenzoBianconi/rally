#
# Created on Jan 28, 2016
#
# @author: lhuang8
#

import sys
import netaddr

from rally import exceptions
from rally.plugins.ovs import scenario
from rally.task import atomic

from rally.common import objects

from ..deployment.engines import get_script
from netaddr.ip import IPRange
from ..consts import ResourceType


class SandboxScenario(scenario.OvsScenario):


    def _add_controller_resource(self, deployment, controller_cidr):
        dep = objects.Deployment.get(deployment)
        resources = dep.get_resources(type=ResourceType.CONTROLLER)
        if resources == None:
            dep.add_resource(provider_name=deployment,
                            type=ResourceType.CONTROLLER,
                            info={"ip":controller_cidr.split('/')[0],
                                  "deployment_name":deployment})
            return

        resources[0].update({"info": {"ip":controller_cidr.split('/')[0],
                                        "deployment_name":deployment}})
        resources[0].save()



    def _create_controller(self, dep_name, controller_cidr, net_dev):

        cmd = "./ovs-sandbox.sh --controller --ovn \
                            --controller-ip %s --device %s;" % \
                            (controller_cidr, net_dev)
        ssh = self.controller_client()
        ssh.run(cmd, stdout=sys.stdout, stderr=sys.stderr)

        self._add_controller_resource(dep_name, controller_cidr)



    """
        @param farm_dep  A name or uuid of farm deployment
        @param sandboxes A list of sandboxes' name
    """
    def _add_sandbox_resource(self, farm_dep, sandboxes):
        dep = objects.Deployment.get(farm_dep)
        res = dep.get_resources(type=ResourceType.SANDBOXES)[0]

        info = res["info"]
        sandbox_set = set(info["sandboxes"])
        sandbox_set |= set(sandboxes)


        for i in sandbox_set:
            if sandboxes.has_key(i):
                continue
            sandboxes[i] = info["sandboxes"][i]


        info["sandboxes"] = sandboxes
        res.update({"info": info})
        res.save()


    @atomic.action_timer("sandbox.create_sandbox")
    def _do_create_sandbox(self, ssh, cmds):
        ssh.run("\n".join(cmds), stdout=sys.stdout, stderr=sys.stderr);


    def _create_sandbox(self, sandbox_create_args):
        """
        :param sandbox_create_args from task config file
        """

        print("create sandbox")

        amount = sandbox_create_args.get("amount", 1)
        batch = sandbox_create_args.get("batch", 1)

        farm = sandbox_create_args.get("farm")
        controller_ip = self.context["controller"]["ip"]

        start_cidr = sandbox_create_args.get("start_cidr")
        net_dev = sandbox_create_args.get("net_dev", "eth0")
        tag = sandbox_create_args.get("tag", "")

        if controller_ip == None:
            raise exceptions.NoSuchConfigField(name="controller_ip")

        sandbox_cidr = netaddr.IPNetwork(start_cidr)
        end_ip = sandbox_cidr.ip + amount
        if not end_ip in sandbox_cidr:
            message = _("Network %s's size is not big enough for %d sandboxes.")
            raise exceptions.InvalidConfigException(
                        message  % (start_cidr, amount))


        sandbox_hosts = netaddr.iter_iprange(sandbox_cidr.ip, sandbox_cidr.last)

        ssh = self.farm_clients(farm)


        sandboxes = {}
        batch_left = min(batch, amount)
        i = 0
        while i < amount:

            i += batch_left
            host_ip_list = []
            while batch_left > 0:
                host_ip_list.append(str(sandbox_hosts.next()))
                batch_left -= 1

            cmds = []
            for host_ip in host_ip_list:
                cmd = "./ovs-sandbox.sh --ovn --controller-ip %s \
                             --host-ip %s/%d --device %s" % \
                         (controller_ip, host_ip, sandbox_cidr.prefixlen,
                                net_dev)
                cmds.append(cmd)

                sandboxes["sandbox-%s" % host_ip] = tag

            self._do_create_sandbox(ssh, cmds)


            batch_left = min(batch, amount - i)
            if batch_left <= 0:
                break;

        self._add_sandbox_resource(farm, sandboxes)

    @atomic.action_timer("sandbox.delete_sandbox")
    def _delete_sandbox(self, sandbox):
        print("delete sandbox")
        pass





