from ..models import Event, DEFAULT_TIME, get_utc_offset, get_utc_timestamp
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status

class POSTTestSuite(APITestCase):
    """ Test suite for Events API POST requests """

    def setUp(self):
        self.client = APIClient()
        self.data = {
            "type": "uni",
            "title": "assignment",
            "date": "2024-01-01",
            "time": "23:59",
            "utc_offset": "+2",
            "interval": "10min",
            "notice_time": "10min",
            "info": "description"
        }
        self.url = "/event/"

    def test_post(self):
        data = self.data
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "assignment")

    def test_post_without_title(self):
        data = self.data
        data.pop("title")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_post_when_title_equals_blank(self):
        data = self.data
        data["title"] = ""
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class GETTestSuite(APITestCase):
    """ Test suite for Events API GET requests """

    def setUp(self):
        self.client = APIClient()
        self.url = '/event/?query='  # '/event?query=' gets redirected here
        for i in range(1, 3):  # 1 and 2
            Event.objects.create(title=f'Title-{i}', date=f'2024-01-0{i}')
        self.utc_offset = get_utc_offset('2024-01-01')
        self.id1_dict = dict([('type', 'other'), ('title', 'Title-1'), ('date', '2024-01-01'),
                              ('time', DEFAULT_TIME), ('utc_offset', self.utc_offset), ('interval', '-'),
                              ('utc_timestamp', get_utc_timestamp('2024-01-01', DEFAULT_TIME, self.utc_offset, '-')),
                              ('notice_time', '-'), ('info', None)])
        self.id2_dict = dict([('type', 'other'), ('title', 'Title-2'), ('date', '2024-01-02'),
                              ('time', DEFAULT_TIME), ('utc_offset', self.utc_offset), ('interval', '-'),
                              ('utc_timestamp', get_utc_timestamp('2024-01-02', DEFAULT_TIME, self.utc_offset, '-')),
                              ('notice_time', '-'), ('info', None)])

    def test_get_using_equal_operator(self):
        query = 'EQUAL(title,"Title-1")'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_equal_operator_lower_letters(self):
        query = 'equal(title,"Title-1")'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_and_operator_with_equal_equal(self):
        query = 'AND(EQUAL(title,"Title-1"),EQUAL(date,"2024-01-01"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_and_operator_with_equal_less_than(self):
        query = 'AND(EQUAL(title,"Title-1"),LESS_THAN(date,"2024-01-02"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_and_operator_with_equal_less_than_greater_than(self):
        query = 'AND(EQUAL(title,"Title-1"),LESS_THAN(date,"2024-01-02"),GREATER_THAN(time,"09:00"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_or_operator_with_equal_equal(self):
        query = 'OR(EQUAL(title,"Title-1"),EQUAL(title,"Title-2"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict, self.id2_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_or_operator_with_equal_greater_than(self):
        query = 'OR(EQUAL(title,"Title-1"),GREATER_THAN(date,"2023-01-01"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict, self.id2_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_not_operator(self):
        query = 'NOT(EQUAL(title,"Title-1"))'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id2_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_greater_than_operator(self):
        query = 'GREATER_THAN(date,"2024-01-01")'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id2_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_using_less_than_operator(self):
        query = 'LESS_THAN(date,"2024-01-02")'
        url = self.url + query
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_without_query(self):
        url = "/event/"
        response = self.client.get(url)
        for result in response.data:
            del result['id']
        expected_data = [self.id1_dict, self.id2_dict]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_get_post_with_invalid_query(self):
        query = 'EQUAL(title,"Title-1"'  # Missing closing bracket
        url = self.url + query
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
