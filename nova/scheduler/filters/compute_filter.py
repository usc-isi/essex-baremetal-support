# Copyright (c) 2011 OpenStack, LLC.
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

import operator

from nova import log as logging
from nova.scheduler import filters
from nova import utils
from types import *


LOG = logging.getLogger(__name__)


class ComputeFilter(filters.BaseHostFilter):
    """HostFilter hard-coded to work with InstanceType records."""

    def _satisfies_extra_specs(self, capabilities, instance_type):
        """Check that the capabilities provided by the compute service
        satisfy the extra specs associated with the instance type"""
        if 'extra_specs' not in instance_type:
            return True

        # Now, it can do various operations:
        #   =, s==, s!=, s>=, s>, s<=, s<, <in>, <or>, ==, !=, >=, <=
        op_methods = {'=': lambda x, y: (float(x) >= float(y)),
                      '=+': lambda x, y: (float(x) >= float(y)),
                      '=-': lambda x, y: (float(x) >= float(y)),
                      '<in>': lambda x, y: (x.find(y) != -1),
                      '==': lambda x, y: (float(x) == float(y)),
                      '==+': lambda x, y: (float(x) == float(y)),
                      '==-': lambda x, y: (float(x) == float(y)),
                      '!=': lambda x, y: (float(x) != float(y)),
                      '!=+': lambda x, y: (float(x) != float(y)),
                      '!=-': lambda x, y: (float(x) != float(y)),
                      '>=': lambda x, y: (float(x) >= float(y)),
                      '>=+': lambda x, y: (float(x) >= float(y)),
                      '>=-': lambda x, y: (float(x) >= float(y)),
                      '<=': lambda x, y: (float(x) <= float(y)),
                      '<=+': lambda x, y: (float(x) <= float(y)),
                      '<=-': lambda x, y: (float(x) <= float(y)),
                      's==': lambda x, y: operator.eq(x, y),
                      's!=': lambda x, y: operator.ne(x, y),
                      's<': lambda x, y: operator.lt(x, y),
                      's<=': lambda x, y: operator.le(x, y),
                      's>': lambda x, y: operator.gt(x, y),
                      's>=': lambda x, y: operator.ge(x, y)}

        cap_extra_specs = capabilities.get('instance_type_extra_specs', None)
        for key, req in instance_type['extra_specs'].iteritems():
            cap = cap_extra_specs.get(key, None)
            if cap == None:
                return False
            if (type(req) == BooleanType or type(req) == IntType or
                type(req) == LongType or type(req) == FloatType):
                    if cap != req:
                        return False
            else:
                words = req.split()
                if len(words) == 1:
                    if cap != req:
                        return False
                else:
                    op = words[0]
                    method = op_methods.get(op)
                    new_req = words[1]
                    for i in range(2, len(words)):
                        new_req += words[i]

                    if op == '<or>':  # Ex: <or> v1 <or> v2 <or> v3
                        found = 0
                        for idx in range(1, len(words), 2):
                            if words[idx] == cap:
                                found = 1
                                break
                        if found == 0:
                            return False
                    elif method:
                        if method(cap, new_req) == False:
                            return False
                    else:
                        if cap != req:
                            return False
        return True

    def host_passes(self, host_state, filter_properties):
        """Return a list of hosts that can create instance_type."""
        instance_type = filter_properties.get('instance_type')
        if host_state.topic != 'compute' or not instance_type:
            return True
        capabilities = host_state.capabilities
        service = host_state.service

        if not utils.service_is_up(service) or service['disabled']:
            LOG.debug(_("%(host_state)s is disabled or has not been "
                    "heard from in a while"), locals())
            return False
        if not capabilities.get("enabled", True):
            LOG.debug(_("%(host_state)s is disabled via capabs"), locals())
            return False
        if not self._satisfies_extra_specs(capabilities, instance_type):
            LOG.debug(_("%(host_state)s fails instance_type extra_specs "
                    "requirements"), locals())
            return False
        return True
