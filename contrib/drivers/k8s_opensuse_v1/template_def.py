# Copyright 2016 Rackspace Inc. All rights reserved.
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

import os

import magnum.conf
from magnum.drivers.common import k8s_template_def

CONF = magnum.conf.CONF


class JeOSK8sTemplateDefinition(k8s_template_def.K8sTemplateDefinition):
    """Kubernetes template for openSUSE/SLES JeOS VM."""

    provides = [
        {'server_type': 'vm',
         'os': 'opensuse',
         'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(JeOSK8sTemplateDefinition, self).__init__()
        self.add_parameter('docker_volume_size',
                           cluster_template_attr='docker_volume_size')
        self.add_output('kube_minions',
                        cluster_attr='node_addresses')
        self.add_output('kube_masters',
                        cluster_attr='master_addresses')

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant

        return super(JeOSK8sTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')
