# Copyright 2015 Rackspace Inc. All rights reserved.
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

import mock
from oslo_config import cfg

from magnum.common import exception
from magnum.conductor import template_definition as tdef
from magnum.tests import base


class TemplateDefinitionTestCase(base.TestCase):

    @mock.patch.object(tdef, 'iter_entry_points')
    def test_load_entry_points(self, mock_iter_entry_points):
        mock_entry_point = mock.MagicMock()
        mock_entry_points = [mock_entry_point]
        mock_iter_entry_points.return_value = mock_entry_points.__iter__()

        entry_points = tdef.TemplateDefinition.load_entry_points()

        for (expected_entry_point,
             (actual_entry_point, loaded_cls)) in zip(mock_entry_points,
                                                      entry_points):
            self.assertEqual(expected_entry_point, actual_entry_point)
            expected_entry_point.load.assert_called_once_with(require=False)

    def test_get_template_definitions(self):
        defs = tdef.TemplateDefinition.get_template_definitions()

        vm_atomic_k8s = defs[('vm', 'fedora-atomic', 'kubernetes')]
        vm_coreos_k8s = defs[('vm', 'coreos', 'kubernetes')]

        self.assertEqual(len(vm_atomic_k8s), 1)
        self.assertEqual(vm_atomic_k8s['magnum_vm_atomic_k8s'],
                         tdef.AtomicK8sTemplateDefinition)
        self.assertEqual(len(vm_coreos_k8s), 1)
        self.assertEqual(vm_coreos_k8s['magnum_vm_coreos_k8s'],
                         tdef.CoreOSK8sTemplateDefinition)

    def test_get_vm_atomic_kubernetes_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition('vm',
                                             'fedora-atomic', 'kubernetes')

        self.assertIsInstance(definition,
                              tdef.AtomicK8sTemplateDefinition)

    def test_get_vm_coreos_kubernetes_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition('vm',
                                                    'coreos', 'kubernetes')

        self.assertIsInstance(definition,
                              tdef.CoreOSK8sTemplateDefinition)

    def test_get_definition_not_supported(self):
        self.assertRaises(exception.BayTypeNotSupported,
                          tdef.TemplateDefinition.get_template_definition,
                          'vm', 'not_supported', 'kubernetes')

    def test_get_definition_not_enabled(self):
        cfg.CONF.set_override('enabled_definitions',
                              ['magnum_vm_atomic_k8s'],
                              group='bay')
        self.assertRaises(exception.BayTypeNotEnabled,
                          tdef.TemplateDefinition.get_template_definition,
                          'vm', 'coreos', 'kubernetes')

    def test_required_param_not_set(self):
        param = tdef.ParameterMapping('test', baymodel_attr='test',
                                      required=True)
        mock_baymodel = mock.MagicMock()
        mock_baymodel.test = None

        self.assertRaises(exception.RequiredParameterNotProvided,
                          param.set_param, {}, mock_baymodel, None)
