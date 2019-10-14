# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import unittest
import pytest
import asyncio

from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ServiceResponseError,
    ClientAuthenticationError
)
from azure.core.pipeline.transport import (
    AioHttpTransport
)

from azure.core.pipeline.transport import AioHttpTransport
from multidict import CIMultiDict, CIMultiDictProxy

from azure.storage.blob.aio import (
    BlobServiceClient,
    ContainerClient,
    BlobClient,
    LocationMode,
    LinearRetry,
    ExponentialRetry,
    NoRetry
)

from testcase import (
    ResponseCallback,
    RetryCounter,
)
from devtools_testutils import ResourceGroupPreparer, StorageAccountPreparer
from asyncblobtestcase import (
    AsyncBlobTestCase,
)


class AiohttpTestTransport(AioHttpTransport):
    """Workaround to vcrpy bug: https://github.com/kevin1024/vcrpy/pull/461
    """
    async def send(self, request, **config):
        response = await super(AiohttpTestTransport, self).send(request, **config)
        if not isinstance(response.headers, CIMultiDictProxy):
            response.headers = CIMultiDictProxy(CIMultiDict(response.internal_response.headers))
            response.content_type = response.headers.get("content-type")
        return response


# --Test Class -----------------------------------------------------------------
class StorageRetryTestAsync(AsyncBlobTestCase):
    # --Test Cases --------------------------------------------
    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_on_server_error_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        service = self._create_storage_service(BlobServiceClient, storage_account, storage_account_key, transport=AiohttpTestTransport())

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=500).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                await service.create_container(container_name, raw_response_hook=callback)
        finally:
            await service.delete_container(container_name)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_on_timeout_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                await service.create_container(container_name, raw_response_hook=callback)
        finally:
            await service.delete_container(container_name)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_callback_and_retry_context_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        def assert_exception_is_present_on_retry_context(**kwargs):
            self.assertIsNotNone(kwargs.get('response'))
            self.assertEqual(kwargs['response'].status_code, 408)


        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                await service.create_container(
                    container_name, raw_response_hook=callback,
                    retry_hook=assert_exception_is_present_on_retry_context)
        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_on_socket_timeout_async(self, resource_group, location, storage_account, storage_account_key):
        if not self.is_live:
            return
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)

        # make the connect timeout reasonable, but packet timeout truly small, to make sure the request always times out
        socket_timeout = 0.000000000001
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, connection_timeout=socket_timeout, transport=AiohttpTestTransport())

        assert service._client._client._pipeline._transport.connection_config.timeout == socket_timeout

        # Act
        try:
            with self.assertRaises(ServiceResponseError) as error:
                await service.create_container(container_name)
            # Assert
            # This call should succeed on the server side, but fail on the client side due to socket timeout
            self.assertTrue('read timeout' in str(error.exception), 'Expected socket timeout but got different exception.')

        finally:
            # we must make the timeout normal again to let the delete operation succeed
            try:
                await service.delete_container(container_name, connection_timeout=11)
            except:
                pass

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_no_retry_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=NoRetry(), transport=AiohttpTestTransport())


        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            with self.assertRaises(HttpResponseError) as error:
                await service.create_container(container_name, raw_response_hook=callback)
            self.assertEqual(error.exception.response.status_code, 408)
            self.assertEqual(error.exception.reason, 'Created')

        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_linear_retry_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                await service.create_container(container_name, raw_response_hook=callback)
        finally:
            await service.delete_container(container_name)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_exponential_retry_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=3, retry_total=3)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        try:
            container = await service.create_container(container_name)

            # Force the create call to 'timeout' with a 408
            callback = ResponseCallback(status=200, new_status=408)

            # Act
            with self.assertRaises(HttpResponseError):
                await container.get_container_properties(raw_response_hook=callback.override_status)

            # Assert the response was called the right number of times (1 initial request + 3 retries)
            self.assertEqual(callback.count, 1+3)
        finally:
            # Clean up
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_exponential_retry_interval_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        retry_policy = ExponentialRetry(initial_backoff=1, increment_base=3, random_jitter_range=3)
        context_stub = {}

        for i in range(10):
            # Act
            context_stub['count'] = 0
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 1
            self.assertTrue(0 <= backoff <= 4)

            # Act
            context_stub['count'] = 1
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 4(1+3^1)
            self.assertTrue(1 <= backoff <= 7)

            # Act
            context_stub['count'] = 2
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 10(1+3^2)
            self.assertTrue(7 <= backoff <= 13)

            # Act
            context_stub['count'] = 3
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 28(1+3^3)
            self.assertTrue(25 <= backoff <= 31)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_linear_retry_interval_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        context_stub = {}

        for i in range(10):
            # Act
            retry_policy = LinearRetry(backoff=1, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 1
            self.assertTrue(0 <= backoff <= 4)

            # Act
            retry_policy = LinearRetry(backoff=5, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 5
            self.assertTrue(2 <= backoff <= 8)

            # Act
            retry_policy = LinearRetry(backoff=15, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 15
            self.assertTrue(12 <= backoff <= 18)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_invalid_retry_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Force the create call to fail by pretending it's a teapot
        callback = ResponseCallback(status=201, new_status=418).override_status

        # Act
        try:
            with self.assertRaises(HttpResponseError) as error:
                await service.create_container(container_name, raw_response_hook=callback)
            self.assertEqual(error.exception.response.status_code, 418)
            self.assertEqual(error.exception.reason, 'Created')
        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_with_deserialization_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('retry')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        try:
            created = await service.create_container(container_name)

            # Act
            callback = ResponseCallback(status=200, new_status=408).override_first_status
            containers = service.list_containers(name_starts_with='retry', raw_response_hook=callback)

            # Assert
            listed = []
            async for c in containers:
                listed.append(c)
            self.assertTrue(len(listed) >= 1)
        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_secondary_location_mode_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Act
        try:
            container = await service.create_container(container_name)
            container.location_mode = LocationMode.SECONDARY

            # Override the response from secondary if it's 404 as that simply means
            # the container hasn't replicated. We're just testing we try secondary,
            # so that's fine.
            response_callback = ResponseCallback(status=404, new_status=200).override_first_status

            # Assert
            def request_callback(request):
                self.assertNotEqual(-1, request.http_request.url.find('-secondary'))

            request_callback = request_callback
            await container.get_container_properties(
                raw_request_hook=request_callback, raw_response_hook=response_callback)
        finally:
            # Delete will go to primary, so disable the request validation
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_to_secondary_with_put_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(retry_to_secondary=True, initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Act
        try:
            # Fail the first create attempt
            response_callback = ResponseCallback(status=201, new_status=408).override_first_status

            # Assert
            # Confirm that the create request does *not* get retried to secondary
            # This should actually throw InvalidPermissions if sent to secondary,
            # but validate the location_mode anyways.
            def retry_callback(location_mode=None, **kwargs):
                self.assertEqual(LocationMode.PRIMARY, location_mode)

            with self.assertRaises(ResourceExistsError):
                await service.create_container(
                    container_name, raw_response_hook=response_callback, retry_hook=retry_callback)

        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_retry_to_secondary_with_get_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(retry_to_secondary=True, initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())

        # Act
        try:
            container = await service.create_container(container_name)
            response_callback = ResponseCallback(status=200, new_status=408).override_first_status

            # Assert
            # Confirm that the get request gets retried to secondary
            def retry_callback(retry_count=None, location_mode=None, **kwargs):
                # Only check this every other time, sometimes the secondary location fails due to delay
                if retry_count % 2 == 0:
                    self.assertEqual(LocationMode.SECONDARY, location_mode)

            await container.get_container_properties(
                raw_response_hook=response_callback, retry_hook=retry_callback)
        finally:
            await service.delete_container(container_name)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage', sku='Standard_GRS')
    @AsyncBlobTestCase.await_prepared_test
    async def test_location_lock_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        # Fail the first request and set the retry policy to retry to secondary
        # The given test account must be GRS
        class MockTransport(AioHttpTransport):
            CALL_NUMBER = 1
            ENABLE = False
            async def send(self, request, **kwargs):
                if MockTransport.ENABLE:
                    if MockTransport.CALL_NUMBER == 2:
                        assert request.url.find('-secondary')
                        # Here's our hack
                        # Replace with primary so the test works even
                        # if secondary is not ready
                        request.url = request.url.replace('-secondary', '')

                response = await super(MockTransport, self).send(request, **kwargs)

                if MockTransport.ENABLE:
                    assert response.status_code == 200
                    if MockTransport.CALL_NUMBER == 1:
                        response.status_code = 408
                    elif MockTransport.CALL_NUMBER == 2:
                        pass
                    else:
                        pytest.fail("This test is not supposed to do more calls")
                    MockTransport.CALL_NUMBER += 1
                return response

        retry = ExponentialRetry(retry_to_secondary=True, initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry,
            transport=MockTransport())
        container = service.get_container_client('containername')
        created = await container.create_container()

        # Act
        MockTransport.ENABLE = True

        # Assert
        def retry_callback(retry_count=None, location_mode=None, **kwargs):
            # This call should be called once, with the decision to try secondary
            retry_callback.called = True
            if MockTransport.CALL_NUMBER == 1:
                self.assertEqual(LocationMode.SECONDARY, location_mode)
            elif MockTransport.CALL_NUMBER == 2:
                self.assertEqual(LocationMode.SECONDARY, location_mode)
            else:
                pytest.fail("This test is not supposed to retry more than once")
        retry_callback.called = False

        containers = service.list_containers(
            results_per_page=1, retry_hook=retry_callback)
        await containers.__anext__()
        assert retry_callback.called

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    @AsyncBlobTestCase.await_prepared_test
    async def test_invalid_account_key_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=3, retry_total=3)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, transport=AiohttpTestTransport())
        service.credential.account_name = "dummy_account_name"
        service.credential.account_key = "dummy_account_key"

        # Shorten retries and add counter
        retry_counter = RetryCounter()
        retry_callback = retry_counter.simple_count

        # Act
        with self.assertRaises(ClientAuthenticationError):
            await service.create_container(container_name, retry_callback=retry_callback)

        # Assert
        # No retry should be performed since the signing error is fatal
        self.assertEqual(retry_counter.count, 0)

# ------------------------------------------------------------------------------
