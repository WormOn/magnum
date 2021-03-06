# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import abc
from marathon import MarathonClient
from oslo_log import log as logging

from magnum.common import exception
from magnum.conductor import k8s_api as k8s
from magnum.i18n import _
from magnum.i18n import _LI
from magnum.i18n import _LW
from magnum import objects


LOG = logging.getLogger(__name__)


def get_scale_manager(context, osclient, cluster):
    manager = None
    coe = cluster.baymodel.coe
    if coe == 'kubernetes':
        manager = K8sScaleManager(context, osclient, cluster)
    elif coe == 'mesos':
        manager = MesosScaleManager(context, osclient, cluster)
    else:
        LOG.warning(_LW(
            "Currently only kubernetes and mesos cluster scale manager "
            "are available"))

    return manager


class ScaleManager(object):

    def __init__(self, context, osclient, cluster):
        self.context = context
        self.osclient = osclient
        self.old_cluster = objects.Cluster.get_by_uuid(context, cluster.uuid)
        self.new_cluster = cluster

    def get_removal_nodes(self, hosts_output):
        if not self._is_scale_down():
            return list()

        cluster = self.new_cluster
        stack = self.osclient.heat().stacks.get(cluster.stack_id)
        hosts = hosts_output.get_output_value(stack)
        if hosts is None:
            raise exception.MagnumException(_(
                "Output key '%(output_key)s' is missing from stack "
                "%(stack_id)s") % {'output_key': hosts_output.heat_output,
                                   'stack_id': stack.id})

        hosts_with_container = self._get_hosts_with_container(self.context,
                                                              cluster)
        hosts_no_container = list(set(hosts) - hosts_with_container)
        LOG.debug('List of hosts that has no container: %s',
                  str(hosts_no_container))

        num_of_removal = self._get_num_of_removal()
        if len(hosts_no_container) < num_of_removal:
            LOG.warning(_LW(
                "About to remove %(num_removal)d nodes, which is larger than "
                "the number of empty nodes (%(num_empty)d). %(num_non_empty)d "
                "non-empty nodes will be removed."), {
                    'num_removal': num_of_removal,
                    'num_empty': len(hosts_no_container),
                    'num_non_empty': num_of_removal - len(hosts_no_container)})

        hosts_to_remove = hosts_no_container[0:num_of_removal]
        LOG.info(_LI('Require removal of hosts: %s'), hosts_to_remove)

        return hosts_to_remove

    def _is_scale_down(self):
        return self.new_cluster.node_count < self.old_cluster.node_count

    def _get_num_of_removal(self):
        return self.old_cluster.node_count - self.new_cluster.node_count

    @abc.abstractmethod
    def _get_hosts_with_container(self, context, cluster):
        """Return the hosts with container running on them."""
        pass


class K8sScaleManager(ScaleManager):

    def __init__(self, context, osclient, cluster):
        super(K8sScaleManager, self).__init__(context, osclient, cluster)

    def _get_hosts_with_container(self, context, cluster):
        k8s_api = k8s.create_k8s_api(self.context, cluster)
        hosts = set()
        for pod in k8s_api.list_namespaced_pod(namespace='default').items:
            hosts.add(pod.spec.node_name)

        return hosts


class MesosScaleManager(ScaleManager):
    """When scaling a mesos cluster, MesosScaleManager will inspect the

    nodes and find out those with containers on them. Thus we can
    ask Heat to delete the nodes without containers. Note that this
    is a best effort basis -- Magnum doesn't have any synchronization
    with Marathon, so while Magnum is checking for the containers to
    choose nodes to remove, new containers can be deployed on the
    nodes to be removed.
    """

    def __init__(self, context, osclient, cluster):
        super(MesosScaleManager, self).__init__(context, osclient, cluster)

    def _get_hosts_with_container(self, context, cluster):
        marathon_client = MarathonClient(
            'http://' + cluster.api_address + ':8080')
        hosts = set()
        for task in marathon_client.list_tasks():
            hosts.add(task.host)

        return hosts
