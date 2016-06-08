from unittest import TestCase

from mock import MagicMock

from elasticluster import OpenStackCloudProvider


class TestOpenStackCloudProvider(TestCase):
    @staticmethod
    def _create_provider():
        return OpenStackCloudProvider('irrelevant', 'irrelevant', 'irrelevant', 'https://example.com')

    def test_that_is_instance_running_returns_true_if_instance_in_active_state_and_cloud_init_finished(self):
        provider = self._create_provider()
        instance = MagicMock()
        instance.status = 'ACTIVE'
        provider._load_instance = MagicMock(return_value=instance)
        provider.is_cloud_init_finished = MagicMock(return_value=True)

        assert provider.is_instance_running('some_id')

    def test_that_is_instance_running_returns_false_if_instance_not_in_active_state_ignoring_cloud_init(self):
        # Given an OpenStack provider with a fake instance claiming not being active
        provider = self._create_provider()
        instance = MagicMock()
        instance.status = 'something other than ACTIVE'
        provider._load_instance = MagicMock(return_value=instance)
        # Then
        assert not provider.is_instance_running('some_id')

    def test_is_cloud_init_finished_when_entry_found_then_return_true(self):
        # Given the console output has a matching line
        provider = self._create_provider()
        provider.get_console_output = MagicMock(
            return_value="[   14.632794] cloud-init[2077]: Cloud-init v. 0.7.5 finished at Tue, 07 Jun 2016 15:10:35 +0000. Datasource DataSourceOpenStack [net,ver=2].  Up 14.62 seconds")
        # Then
        assert provider.is_cloud_init_finished('irrelevant')

    def test_is_cloud_init_finished_when_entry_not_found_then_return_false(self):
        # Given the console output has no matching lines
        provider = self._create_provider()
        provider.get_console_output = MagicMock(return_value="not what is expected\nalso not was is expected")
        # Then
        assert not provider.is_cloud_init_finished('irrelevant')
