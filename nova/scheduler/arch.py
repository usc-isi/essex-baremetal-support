# Copyright (c) 2010 Openstack, LLC.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""
Archtecture Scheduler implementation
"""

import random
import string
from nova import db
from nova import flags
from nova import exception
from nova.openstack.common import cfg
from nova.scheduler import driver
from nova import utils

from nova import log as logging

LOG = logging.getLogger('nova.scheduler.ArchitectureScheduler')


ArchetectureScheduler_opts = [
    cfg.IntOpt('max_cores',
               default=16,
               help='maximum number of instance cores to allow per host'),
    cfg.IntOpt('max_gigabytes',
               default=10000,
               help='maximum number of volume gigabytes to allow per host'),
    cfg.IntOpt('max_networks',
               default=1000,
               help='maximum number of networks to allow per host'),
    cfg.BoolOpt('skip_isolated_core_check',
                default=True,
                help='Allow overcommitting vcpus on isolated hosts'),
    ]

FLAGS = flags.FLAGS
#FLAGS.add_options(ArchetectureScheduler_opts)
FLAGS.register_opts(ArchetectureScheduler_opts)


class ArchitectureScheduler(driver.Scheduler):
    """Implements Scheduler as a random node selector."""

    def hosts_up_with_arch(self, context, topic, request_spec):
#    def hosts_up_with_arch(self, context, topic, instance_id):

        """Figure out what is requested
        """
        LOG.debug(_("## req: %s"), request_spec)
        instance_type = request_spec['instance_type']
        LOG.debug(_("## it: %s"), instance_type)
#        instance = db.instance_get(context, instance_id)

#        LOG.debug(_("## instance %s"), instance)
#        LOG.debug(_("## instance.id %s"), instance.id)
#        LOG.debug(_("## instance.cpu_arch %s"), instance.cpu_arch)

        services = db.service_get_all_by_topic(context.elevated(), topic)
        LOG.debug(_("## services %s"), services)

        hosts = []

        # from instance table
        wanted_vcpus = instance_type['vcpus']
        wanted_memory_mb = instance_type['memory_mb']
        wanted_root_gb = instance_type['root_gb']
        instance_id = instance_type['id']

        LOG.debug(_("## wanted-vcpus=%s"), wanted_vcpus)
        LOG.debug(_("## wanted-memory=%s"), wanted_memory_mb)
        LOG.debug(_("## wanted-hard=%s"), wanted_root_gb)
        LOG.debug(_("## instance_id=%s"), instance_id)

        # from instance_metadata table
#        instance_meta = db.instance_metadata_get(context, instance_id)
#        LOG.debug(_("## inst-meta=%s"), instance_meta)

        # from instance_type_extra_specs table
#        instance_extra = db.instance_type_extra_specs_get( \
        instance_meta = db.instance_type_extra_specs_get( \
            context, instance_id)
        LOG.debug(_("## inst-meta=%s"), instance_meta)

        # combine to inatance_meta
#        instance_meta.update(instance_extra)
#        LOG.debug(_("## new inst meta=%s"), instance_meta)

        try:
            wanted_cpu_arch = instance_meta['cpu_arch']
        except:
            wanted_cpu_arch = None

        LOG.debug(_("## wanted-cpu-arch=%s"), wanted_cpu_arch)

        """Get capability from zone_manager and match cpu_arch and others
        """
        cap = self.zone_manager.get_hosts_capabilities(context)

        for host, host_dict_cap in cap.iteritems():
            LOG.debug(_("## host=%s"), host)
            for service_name_cap, service_dict_cap in \
                host_dict_cap.iteritems():
                if (service_name_cap != 'compute'):
                    continue

                resource_cap = {}
                for cap, value in service_dict_cap.iteritems():
                    if type(value) is int:  # value is int
                        resource_cap[cap] = value

                    elif (type(value) is not str) and \
                         (type(value) is not unicode):
                        continue

                    # string and one value
                    elif value.find(':') == -1 and value.find(',') == -1:
                        try:
                            resource_cap[cap] = int(value)
                        except:
                            resource_cap[cap] = value

                    # complex; multi-level key-value pairs.
                    # example: cpu_info = { "vendor":"intel", features=
                    #  ["dia", "est"], toplogy={"core":4, "thread":1}}
                    # only the lowest key-value pair is recorded. So, in the
                    # previous eample, the final dict is:
                    #   resource["vendor"] = "intel",
                    #   resource["features"] = "dia, est",
                    #   resource["core"] = "4",
                    #   resource["thread"] = "1",
                    # No key is availabel for cpu_info and topology
                    else:  # decompose capability
                        new_key = ''
                        new_val = ''
                        splitted = value.split(',')
                        for pair in splitted:
                            if pair.find(':') != -1:  # key:value pair
                                if len(new_key) != 0:
                                    try:
                                        resource_cap[new_key] = int(new_val)
                                    except:
                                        resource_cap[new_key] = new_val
                                nspl = pair.split(':')
                                right = nspl[-2].rfind('"', 0, len(nspl[-2]))
                                left = nspl[-2].rfind('"', 0, right)
                                new_key = nspl[-2][left + 1: right]
                                right = nspl[-1].rfind('"', 0, len(nspl[-1]))
                                left = nspl[-1].rfind('"', 0, right)
                                new_val = nspl[-1][left + 1: right]
                            else:  # value only
                                right = pair.rfind('"', 0, len(pair))
                                left = pair.rfind('"', 0, right)
                                if right != -1 and left != -1:
                                    new_val += "," + pair[left + 1:right]
                                else:
                                    new_val += ", " + pair
                        try:
                            resource_cap[new_key] = int(new_val)
                        except:
                            resource_cap[new_key] = new_val

                # if the same architecture is found
                if ((wanted_cpu_arch is None) \
                    or (wanted_cpu_arch == resource_cap['cpu_arch'])):

                    # basic requirements from instance_type
                    LOG.debug(_("## *** wanted arch found: <%s> ***"),
                        wanted_cpu_arch)
                    LOG.debug(_("## cap vcpus = <%s>"),
                        int(resource_cap['vcpus']) \
                        - int(resource_cap['vcpus_used']))
                    LOG.debug(_("## cap memory_mb = <%s>"),
                        resource_cap['host_memory_free'])

                    if wanted_vcpus > (int(resource_cap['vcpus']) \
                        - int(resource_cap['vcpus_used'])) \
                    or wanted_memory_mb > \
                       int(resource_cap['host_memory_free']) \
                    or wanted_root_gb > (int(resource_cap['disk_total']) \
                        - int(resource_cap['disk_used'])):

                        flag_different = 1
                    else:
                        flag_different = 0

                    # extra requirements from instance_type_extra_spec
                    # or instance_metadata table

                    for kkey in instance_meta:
                        try:
                            if(flag_different == 0):
                                wanted_value = instance_meta[kkey]
                                LOG.debug(_("## wanted-key=%s"), kkey)
                                LOG.debug(_("## wanted-value=%s"), \
                                    wanted_value)
                                if (wanted_value is not None):
                                    flag_different = 1
                                    if (resource_cap[kkey] is None):
                                        LOG.debug(_("## cap is None"))
                                    elif type(resource_cap[kkey]) is int:
                                        LOG.debug(_("## offered(int)=%s"), \
                                            resource_cap[kkey])
                                        if int(wanted_value) <= \
                                            resource_cap[kkey]:

                                            LOG.debug(_("## found"))
                                            flag_different = 0
                                        else:
                                            LOG.debug(_("**not found"))
                                    else:
                                        # get wanted list first
                                        wanted = wanted_value.split(',')

                                        # get provided list now
                                        if resource_cap[kkey].find(',') == -1:
                                            offered = [resource_cap[kkey]]
                                        else:
                                            offered = resource_cap[kkey]. \
                                                split(',')

                                        LOG.debug(_("## offered(str)=%s"), \
                                                offered)

                                        # check if the required are provided
                                        flag_different = 0
                                        for want in wanted:
                                            found = 0
                                            for item in offered:
                                                if(want == item):
                                                    found = 1
                                                    break
                                            if found == 0:
                                                flag_different = 1
                                                LOG.debug(_("**not found"))
                                                break
                                            else:
                                                LOG.debug(_("## found"))
                        except:
                            pass

                    if (flag_different == 0):
                        LOG.debug(_("##\t***** found  **********="))
                        hosts.append(host)
                    else:
                        LOG.debug(_("##\t***** not found  **********="))

        LOG.debug(_("## hosts = %s"), hosts)
        return hosts

    def _schedule(self, context, topic, request_spec, **_kwargs):
        """Picks a host that is up at random in selected
        arch (if defined).
        """
        #instance_id = _kwargs.get('instance_id')
#        request_spec = _kwargs.get('request_spec')
#        instance_type = request_spec['instance_type']

        hosts = self.hosts_up_with_arch(context, topic, request_spec)
        return hosts[int(random.random() * len(hosts))]

    def schedule_create_volume(self, context, volume_id, *_args, **_kwargs):
        """Picks a host that is up and has the fewest volumes."""
        elevated = context.elevated()

        volume_ref = db.volume_get(context, volume_id)
        availability_zone = volume_ref.get('availability_zone')

        zone, host = None, None
        if availability_zone:
            zone, _x, host = availability_zone.partition(':')
        if host and context.is_admin:
            service = db.service_get_by_args(elevated, host, 'nova-volume')
            if not utils.service_is_up(service):
                raise exception.WillNotSchedule(host=host)
            driver.cast_to_volume_host(context, host, 'create_volume',
                    volume_id=volume_id, **_kwargs)
            return None

        results = db.service_get_all_volume_sorted(elevated)
        if zone:
            results = [(service, gigs) for (service, gigs) in results
                       if service['availability_zone'] == zone]
        for result in results:
            (service, volume_gigabytes) = result
            if volume_gigabytes + volume_ref['size'] > FLAGS.max_gigabytes:
                msg = _("All hosts have too many gigabytes")
                raise exception.NoValidHost(reason=msg)
            if utils.service_is_up(service):
                driver.cast_to_volume_host(context, service['host'],
                        'create_volume', volume_id=volume_id, **_kwargs)
                return None
        msg = _("Is the appropriate service running?")
        raise exception.NoValidHost(reason=msg)

    def schedule_run_instance(self, context, request_spec, *_args, **kwargs):
        """Create and run an instance or instances"""

        elevated = context.elevated()
        num_instances = request_spec.get('num_instances', 1)
        instances = []
        for num in xrange(num_instances):
            host = self._schedule(context, 'compute', request_spec, **kwargs)
            instance = self.create_instance_db_entry(elevated, request_spec)
            driver.cast_to_compute_host(context, host,
                    'run_instance', instance_uuid=instance['uuid'], **kwargs)
            instances.append(driver.encode_instance(instance))

        return instances

    def update_service_capabilities(self, service_name, host, capabilities):
        """Process a capability update from a service node."""
        self.zone_manager.update_service_capabilities(service_name,
                host, capabilities)
