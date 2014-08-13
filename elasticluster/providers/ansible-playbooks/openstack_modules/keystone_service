#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: keystone_service
short_description: Manage OpenStack Identity (keystone) service endpoints
requirements: [ python-keystoneclinet ]
examples:
    - code: 'keystone_service: name=keystone type=identity description="Keystone Identity Service" publicurl=http://192.168.206.130:5000/v2.0 internalurl=http://192.168.206.130:5000/v2.0 adminurl=http://192.168.206.130:35357/v2.0'
    - code: 'keystone_service: name=glance type=image description="Glance Identity Service" url=http://192.168.206.130:9292'
author: Lorin Hochstein
'''

try:
    from keystoneclient.v2_0 import client
except ImportError:
    keystoneclient_found = False
else:
    keystoneclient_found = True

import traceback


def authenticate(endpoint, token, login_user, login_password):
    """Return a keystone client object"""

    if token:
        return client.Client(endpoint=endpoint, token=token)
    else:
        return client.Client(endpoint=endpoint, username=login_user,
                             password=login_password)


def get_service(keystone, name):
    """ Retrieve a service by name """
    services = [x for x in keystone.services.list() if x.name == name]
    count = len(services)
    if count == 0:
        raise KeyError("No keystone services with name %s" % name)
    elif count > 1:
        raise ValueError("%d services with name %s" % (count, name))
    else:
        return services[0]


def get_endpoint(keystone, name):
    """ Retrieve a service endpoint by name """
    service = get_service(keystone, name)
    endpoints = [x for x in keystone.endpoints.list()
                   if x.service_id == service.id]
    count = len(endpoints)
    if count == 0:
        raise KeyError("No keystone endpoints with service name %s" % name)
    elif count > 1:
        raise ValueError("%d endpoints with service name %s" % (count, name))
    else:
        return endpoints[0]


def ensure_service_present(keystone, name, service_type, description,
                           check_mode):
    """ Ensure the service is present and has the right values

        Returns a pair, where the first element is a boolean that indicates
        a state change, and the second element is the service uuid, or None
        if running in check mode"""
    service = None
    try:
        service = get_service(keystone, name)
    except:
        # Service doesn't exist yet, we'll need to create one
        pass
    else:
        # See if it matches exactly
        if service.name == name and \
           service.type == service_type and \
           service.description == description:

            # Same, no changes needed
            return (False, service.id)

    # At this point, we know we will need to make a change
    if check_mode:
        return (True, None)

    if service is None:
        service = keystone.services.create(name=name,
                                           service_type=service_type,
                                           description=description)
        return (True, service.id)
    else:
        msg = "keystone v2 API doesn't support updating services"
        raise ValueError(msg)


def ensure_endpoint_present(keystone, name, public_url, internal_url,
                             admin_url, region, check_mode):
    """ Ensure the service endpoint is present and have the right values

        Assumes the service object has already been created at this point"""

    service = get_service(keystone, name)
    endpoint = None
    try:
        endpoint = get_endpoint(keystone, name)
    except:
        # Endpoint doesn't exist yet, we'll need to create one
        pass
    else:
        # See if it matches
        if endpoint.publicurl == public_url and \
           endpoint.adminurl == admin_url and \
           endpoint.internalurl == internal_url and \
           endpoint.region == region:

            # Same, no changes needed
            return (False, endpoint.id)

    # At this point, we know we will need to make a change
    if check_mode:
        return (True, None)

    if endpoint is None:
        endpoint = keystone.endpoints.create(region=region,
                                             service_id=service.id,
                                             publicurl=public_url,
                                             adminurl=admin_url,
                                             internalurl=internal_url)
        return (True, endpoint.id)
    else:
        msg = "keystone v2 API doesn't support updating endpoints"
        raise ValueError(msg)


def ensure_service_absent(keystone, name, check_mode):
    """ Ensure the service is absent"""

    raise NotImplementedError()

def ensure_endpoint_absent(keystone, name, check_mode):
    """ Ensure the service endpoint """
    raise NotImplementedError()


def dispatch(keystone, name, service_type, description, public_url,
             internal_url, admin_url, region, state, check_mode):

    if state == 'present':
        (service_changed, service_id) = ensure_service_present(keystone,
                                                              name,
                                                              service_type,
                                                              description,
                                                              check_mode)

        (endpoint_changed, endpoint_id) = ensure_endpoint_present(
            keystone,
            name,
            public_url,
            internal_url,
            admin_url,
            region,
            check_mode)
        return dict(changed=service_changed or endpoint_changed,
                    service_id=service_id,
                    endpoint_id=endpoint_id)
    elif state == 'absent':
        endpoint_changed = ensure_endpoint_absent(keystone, name, check_mode)
        service_changed = ensure_service_absent(keystone, name, check_mode)
        return dict(changed=service_changed or endpoint_changed)
    else:
        raise ValueError("Code should never reach here")



def main():

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True),
            type=dict(required=True),
            description=dict(required=False),
            public_url=dict(required=True, aliases=['url', 'publicurl']),
            internal_url=dict(required=False, aliases=['internalurl']),
            admin_url=dict(required=False, aliases=['adminurl']),
            region=dict(required=True),
            state=dict(default='present', choices=['present', 'absent']),
            endpoint=dict(required=False,
                          default="http://127.0.0.1:35357/v2.0"),
            token=dict(required=False),
            login_user=dict(required=False),
            login_password=dict(required=False)
        ),
        supports_check_mode=True,
        mutually_exclusive=[['token', 'login_user'],
                            ['token', 'login_password']]
    )

    endpoint = module.params['endpoint']
    token = module.params['token']
    login_user = module.params['login_user']
    login_password = module.params['login_password']

    name = module.params['name']
    service_type = module.params['type']
    description = module.params['description']
    public_url = module.params['public_url']
    internal_url = module.params['internal_url']
    if internal_url is None:
        internal_url = public_url
    admin_url = module.params['admin_url']
    if admin_url is None:
        admin_url = public_url
    region = module.params['region']
    state = module.params['state']

    keystone = authenticate(endpoint, token, login_user, login_password)
    check_mode = module.check_mode

    try:
        d = dispatch(keystone, name, service_type, description,
                     public_url, internal_url, admin_url, region, state,
                     check_mode)
    except Exception:
        if check_mode:
            # If we have a failure in check mode
            module.exit_json(changed=True,
                             msg="exception: %s" % traceback.format_exc())
        else:
            module.fail_json(msg=traceback.format_exc())
    else:
        module.exit_json(**d)


# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
