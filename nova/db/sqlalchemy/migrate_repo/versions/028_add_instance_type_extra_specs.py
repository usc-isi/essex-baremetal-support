# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 University of Southern California
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

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy import MetaData, String, Table
from nova import log as logging
from nova import db
from nova import context

LOG = logging.getLogger(__name__)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine;
    # bind migrate_engine to your metadata
    meta = MetaData()
    meta.bind = migrate_engine

    # load tables for fk
    instance_types = Table('instance_types', meta, autoload=True)

    #
    # New Tables
    #
    instance_type_extra_specs_table = Table('instance_type_extra_specs', meta,
            Column('created_at', DateTime(timezone=False)),
            Column('updated_at', DateTime(timezone=False)),
            Column('deleted_at', DateTime(timezone=False)),
            Column('deleted', Boolean(create_constraint=True, name=None)),
            Column('id', Integer(), primary_key=True, nullable=False),
            Column('instance_type_id',
                   Integer(),
                   ForeignKey('instance_types.id'),
                   nullable=False),
            Column('key',
                   String(length=255, convert_unicode=False,
                          assert_unicode=None,
                          unicode_error=None, _warn_on_bytestring=False)),
            Column('value',
                   String(length=255, convert_unicode=False,
                          assert_unicode=None,
                          unicode_error=None, _warn_on_bytestring=False)))

    for table in (instance_type_extra_specs_table, ):
        try:
            table.create()
            #
            instance_type_rows = list(instance_types.select().execute())
            for instance_type in instance_type_rows:
                id = instance_type.id
                name = instance_type.name
                if (name == 'm1.tiny') or \
                   (name == 'm1.small') or \
                   (name == 'm1.medium') or \
                   (name == 'm1.large') or \
                   (name == 'm1.xlarge'):
                    extra_specs = {}
                elif (name == 'cg1.small'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 1')
                elif (name == 'cg1.medium'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 2')
                elif (name == 'cg1.large'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 3')
                elif (name == 'cg1.xlarge'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 4')
                elif (name == 'cg1.2xlarge'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 4')
                elif (name == 'cg1.4xlarge'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      gpu_arch='s== fermi',
                                      gpus='= 4')
                elif (name == 'sh1.small') or  \
                     (name == 'sh1.medium') or \
                     (name == 'sh1.large') or \
                     (name == 'sh1.xlarge') or \
                     (name == 'sh1.2xlarge') or \
                     (name == 'sh1.4xlarge') or \
                     (name == 'sh1.8xlarge') or \
                     (name == 'sh1.16xlarge') or \
                     (name == 'sh1.32xlarge'):
                    extra_specs = dict(
                                      cpu_arch='s== x86_64',
                                      system_type='s== UV')
                elif (name == 'tp64.8x8'):
                    extra_specs = dict(
                                      #cpu_arch='s== tilepro64')
                                      cpu_arch='s== tilepro64',
                                      vcores='= 64',
                                      hypervisor_type='s== tilera_hv',
                                      baremetal_driver='s== tilera')

                db.api.instance_type_extra_specs_update_or_create(
                                          context.get_admin_context(),
                                          id,
                                          extra_specs)
        except Exception:
            LOG.info(repr(table))
            LOG.exception('Exception while creating table')
            raise


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = MetaData()
    meta.bind = migrate_engine

    # load tables for fk
    instance_types = Table('instance_types', meta, autoload=True)

    instance_type_extra_specs_table = Table('instance_type_extra_specs',
                                            meta,
                                            autoload=True)
    for table in (instance_type_extra_specs_table, ):
        table.drop()
