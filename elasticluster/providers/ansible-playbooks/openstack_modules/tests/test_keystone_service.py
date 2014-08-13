import keystone_service
import mock
from nose.tools import assert_equal, assert_list_equal, assert_is_none
from nose import SkipTest


def setup():
    keystone = mock.MagicMock()
    service = mock.Mock(id="b6a7ff03f2574cd9b5c7c61186e0d781",
                        type="identity",
                        description="Keystone Identity Service")
    # Can't set <name> field in mock in initializer
    service.name = "keystone"
    keystone.services.list = mock.Mock(return_value=[service])
    endpoint = mock.Mock(id="600759628a214eb7b3acde39b1e85180",
                         service_id="b6a7ff03f2574cd9b5c7c61186e0d781",
                         publicurl="http://192.168.206.130:5000/v2.0",
                         internalurl="http://192.168.206.130:5000/v2.0",
                         adminurl="http://192.168.206.130:35357/v2.0",
                         region="RegionOne")
    keystone.endpoints.list = mock.Mock(return_value=[endpoint])
    return keystone


@mock.patch('keystone_service.ensure_endpoint_absent')
@mock.patch('keystone_service.ensure_service_absent')
@mock.patch('keystone_service.ensure_endpoint_present')
@mock.patch('keystone_service.ensure_service_present')
def test_dispatch_service_present(mock_ensure_service_present,
                                  mock_ensure_endpoint_present,
                                  mock_ensure_service_absent,
                                  mock_ensure_endpoint_absent):
    """ Dispatch: service present """
    # Setup
    mock_ensure_service_present.return_value = (True, None)
    mock_ensure_endpoint_present.return_value = (True, None)
    manager = mock.MagicMock()
    manager.attach_mock(mock_ensure_service_present, 'ensure_service_present')
    manager.attach_mock(mock_ensure_service_absent, 'ensure_service_absent')
    manager.attach_mock(mock_ensure_endpoint_present,
                        'ensure_endpoint_present')
    manager.attach_mock(mock_ensure_endpoint_absent,
                        'ensure_endpoint_absent')

    keystone = setup()
    name = "keystone"
    service_type = "identity"
    description = "Keystone Identity Service"
    state = "present"
    public_url = "http://192.168.206.130:5000/v2.0"
    internal_url = "http://192.168.206.130:5000/v2.0"
    admin_url = "http://192.168.206.130:35357/v2.0"
    region = "RegionOne"
    check_mode = False

    # Code under test
    keystone_service.dispatch(keystone, name, service_type, description,
            public_url, internal_url, admin_url, region, state, check_mode)

    expected_calls = [mock.call.ensure_service_present(keystone, name,
                                                       service_type,
                                                       description,
                                                       check_mode),
                      mock.call.ensure_endpoint_present(keystone, name,
                                                         public_url,
                                                         internal_url,
                                                         admin_url,
                                                         region,
                                                         check_mode)]

    assert_equal(manager.mock_calls, expected_calls)


@mock.patch('keystone_service.ensure_endpoint_absent')
@mock.patch('keystone_service.ensure_service_absent')
@mock.patch('keystone_service.ensure_endpoint_present')
@mock.patch('keystone_service.ensure_service_present')
def test_dispatch_service_absent(mock_ensure_service_present,
                                  mock_ensure_endpoint_present,
                                  mock_ensure_service_absent,
                                  mock_ensure_endpoint_absent):
    """ Dispatch: service absent """
    # Setup
    mock_ensure_service_absent.return_value = True
    mock_ensure_endpoint_absent.return_value = True
    manager = mock.MagicMock()
    manager.attach_mock(mock_ensure_service_present, 'ensure_service_present')
    manager.attach_mock(mock_ensure_service_absent, 'ensure_service_absent')
    manager.attach_mock(mock_ensure_endpoint_present,
                        'ensure_endpoint_present')
    manager.attach_mock(mock_ensure_endpoint_absent,
                        'ensure_endpoint_absent')

    keystone = setup()
    name = "keystone"
    service_type = "identity"
    description = "Keystone Identity Service"
    region = "RegionOne"
    state = "absent"
    public_url = "http://192.168.206.130:5000/v2.0"
    internal_url = "http://192.168.206.130:5000/v2.0"
    admin_url = "http://192.168.206.130:35357/v2.0"
    check_mode = False

    # Code under test
    keystone_service.dispatch(keystone, name, service_type, description,
            public_url, internal_url, admin_url, region, state, check_mode)

    expected_calls = [
        mock.call.ensure_endpoint_absent(keystone, name, check_mode),
        mock.call.ensure_service_absent(keystone, name, check_mode)
    ]

    assert_list_equal(manager.mock_calls, expected_calls)


def test_ensure_service_present_when_present():
    """ ensure_services_present when the service is present"""
    # Setup
    keystone = setup()
    name = "keystone"
    service_type = "identity"
    description = "Keystone Identity Service"
    check_mode = False

    # Code under test
    (changed, id) = keystone_service.ensure_service_present(keystone, name,
                        service_type, description, check_mode)

    # Assertions
    assert not changed
    assert_equal(id, "b6a7ff03f2574cd9b5c7c61186e0d781")

def test_ensure_service_present_when_present_check():
    """ ensure_services_present when the service is present, check mode"""
    # Setup
    keystone = setup()
    name = "keystone"
    service_type = "identity"
    description = "Keystone Identity Service"
    check_mode = True

    # Code under test
    (changed, id) = keystone_service.ensure_service_present(keystone, name,
                        service_type, description, check_mode)

    # Assertions
    assert not changed
    assert_equal(id, "b6a7ff03f2574cd9b5c7c61186e0d781")


def test_ensure_service_present_when_absent():
    """ ensure_services_present when the service is absent"""
    # Setup
    keystone = setup()
    service = mock.Mock(id="a7ebed35051147d4abbe2ee049eeb346")
    keystone.services.create = mock.Mock(return_value=service)
    name = "nova"
    service_type = "compute"
    description = "Compute Service"
    check_mode = False

    # Code under test
    (changed, id) = keystone_service.ensure_service_present(keystone, name,
                        service_type, description, check_mode)

    # Assertions
    assert changed
    assert_equal(id, "a7ebed35051147d4abbe2ee049eeb346")
    keystone.services.create.assert_called_with(name=name,
                                                service_type=service_type,
                                                description=description)


def test_ensure_service_present_when_absent_check():
    """ ensure_services_present when the service is absent, check mode"""
    # Setup
    keystone = setup()
    service = mock.Mock(id="a7ebed35051147d4abbe2ee049eeb346")
    keystone.services.create = mock.Mock(return_value=service)
    name = "nova"
    service_type = "compute"
    description = "Compute Service"
    check_mode = True

    # Code under test
    (changed, id) = keystone_service.ensure_service_present(keystone, name,
                        service_type, description, check_mode)

    # Assertions
    assert changed
    assert_equal(id, None)
    assert not keystone.services.create.called


def test_get_endpoint_present():
    """ get_endpoint when endpoint is present """
    keystone = setup()

    endpoint = keystone_service.get_endpoint(keystone, "keystone")

    assert_equal(endpoint.id, "600759628a214eb7b3acde39b1e85180")


def test_ensure_endpoint_present_when_present():
    """ ensure_endpoint_present when the endpoint is present """
    # Setup
    keystone = setup()
    name = "keystone"
    public_url = "http://192.168.206.130:5000/v2.0"
    internal_url = "http://192.168.206.130:5000/v2.0"
    admin_url = "http://192.168.206.130:35357/v2.0"
    region = "RegionOne"
    check_mode = False

    # Code under test
    (changed, id) = keystone_service.ensure_endpoint_present(keystone, name,
                        public_url, internal_url, admin_url, region,
                        check_mode)

    # Assertions
    assert not changed
    assert_equal(id, "600759628a214eb7b3acde39b1e85180")


def test_ensure_endpoint_present_when_present_check():
    """ ensure_endpoint_present when the endpoint is present, check mode"""
    # Setup
    keystone = setup()
    name = "keystone"
    public_url = "http://192.168.206.130:5000/v2.0"
    internal_url = "http://192.168.206.130:5000/v2.0"
    admin_url = "http://192.168.206.130:35357/v2.0"
    region = "RegionOne"
    check_mode = True

    # Code under test
    (changed, id) = keystone_service.ensure_endpoint_present(keystone, name,
                        public_url, internal_url, admin_url, region, check_mode)

    # Assertions
    assert not changed
    assert_equal(id, "600759628a214eb7b3acde39b1e85180")


def test_ensure_endpoint_present_when_absent():
    """ ensure_endpoint_present when the endpoint is absent """
    # Setup
    keystone = setup()
    # Mock out the endpoints create
    endpoint = mock.Mock(id="622386d836b14fd986d9cec7504d208a",
                 publicurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
                 internalurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
                 adminurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
                 region="RegionOne")

    keystone.endpoints.create = mock.Mock(return_value=endpoint)

    # We need to add a service, but not an endpoint
    service = mock.Mock(id="0ad62de6cfe044c7a77ad3a7f2851b5d",
                        type="compute",
                        description="Compute Service")
    service.name = "nova"
    keystone.services.list.return_value.append(service)

    name = "nova"
    public_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    internal_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    admin_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    region = "RegionOne"
    check_mode = False

    # Code under test
    (changed, id) = keystone_service.ensure_endpoint_present(keystone, name,
                        public_url, internal_url, admin_url, region,
                        check_mode)

    # Assertions
    assert changed
    assert_equal(id, "622386d836b14fd986d9cec7504d208a")
    keystone.endpoints.create.assert_called_with(
        service_id="0ad62de6cfe044c7a77ad3a7f2851b5d",
         publicurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
         internalurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
         adminurl="http://192.168.206.130:8774/v2/%(tenant_id)s",
        region="RegionOne")


def test_ensure_endpoint_present_when_absent_check():
    """ ensure_endpoint_present when the endpoint is absent, check mode"""
    # Setup
    keystone = setup()
    # We need to add a service, but not an endpoint
    service = mock.Mock(id="0ad62de6cfe044c7a77ad3a7f2851b5d",
                        type="compute",
                        description="Compute Service")
    service.name = "nova"
    keystone.services.list.return_value.append(service)


    name = "nova"
    public_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    internal_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    admin_url = "http://192.168.206.130:8774/v2/%(tenant_id)s"
    region = "RegionOne"
    check_mode = True

    # Code under test
    (changed, id) = keystone_service.ensure_endpoint_present(keystone, name,
                        public_url, internal_url, admin_url, region, check_mode)

    # Assertions
    assert changed
    assert_is_none(id)
    assert not keystone.endpoints.create.called

