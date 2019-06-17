# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class Usage(Model):
    """ARM usage.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar id: Resource ID.
    :vartype id: str
    :ivar name: Resource name.
    :vartype name: ~azure.mgmt.sql.models.Name
    :ivar type: Resource type.
    :vartype type: str
    :ivar unit: Usage unit.
    :vartype unit: str
    :ivar current_value: Usage current value.
    :vartype current_value: int
    :ivar limit: Usage limit.
    :vartype limit: int
    :ivar requested_limit: Usage requested limit.
    :vartype requested_limit: int
    """

    _validation = {
        'id': {'readonly': True},
        'name': {'readonly': True},
        'type': {'readonly': True},
        'unit': {'readonly': True},
        'current_value': {'readonly': True},
        'limit': {'readonly': True},
        'requested_limit': {'readonly': True},
    }

    _attribute_map = {
        'id': {'key': 'id', 'type': 'str'},
        'name': {'key': 'name', 'type': 'Name'},
        'type': {'key': 'type', 'type': 'str'},
        'unit': {'key': 'unit', 'type': 'str'},
        'current_value': {'key': 'currentValue', 'type': 'int'},
        'limit': {'key': 'limit', 'type': 'int'},
        'requested_limit': {'key': 'requestedLimit', 'type': 'int'},
    }

    def __init__(self, **kwargs):
        super(Usage, self).__init__(**kwargs)
        self.id = None
        self.name = None
        self.type = None
        self.unit = None
        self.current_value = None
        self.limit = None
        self.requested_limit = None
