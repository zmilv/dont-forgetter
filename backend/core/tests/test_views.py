from django.test import TestCase
from core.models import Event
from core.views import APIQueryFuncs
from users.models import CustomUser
from django.contrib.auth.hashers import make_password


class TestAPIQueryFuncs(TestCase):
    """
    Test suite for API query helper functions within views.py
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        for i in range(1, 3):  # 1 and 2
            Event.objects.create(
                title=f"Title-{i}", date=f"2024-01-0{i}", user=self.user
            )
        self.query_funcs_instance = APIQueryFuncs()

    def test_equal_kwargs(self):
        result = APIQueryFuncs._equal_kwargs("date", "2024-01-01")
        expected_result = {"date": "2024-01-01"}
        self.assertEqual(result, expected_result)

    def test_greater_than_kwargs(self):
        result = APIQueryFuncs._greater_than_kwargs("date", "2024-01-01")
        expected_result = {"date__gt": "2024-01-01"}
        self.assertEqual(result, expected_result)

    def test_less_than_kwargs(self):
        result = APIQueryFuncs._less_than_kwargs("date", "2024-01-01")
        expected_result = {"date__lt": "2024-01-01"}
        self.assertEqual(result, expected_result)

    def test_and_kwargs(self):
        result = APIQueryFuncs._and_kwargs(
            'EQUAL(title,"Title-1")', 'EQUAL(date,"2024-01-01")'
        )
        expected_result = {"title": "Title-1", "date": "2024-01-01"}
        self.assertEqual(result, expected_result)

    def test_or_operator(self):
        result = APIQueryFuncs.or_operator(
            'EQUAL(title,"Title-1")', 'EQUAL(title,"Title-2")'
        )
        expected_result = Event.objects.filter(title__in=("Title-1", "Title-2"))
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_not_operator(self):
        result = APIQueryFuncs.not_operator('EQUAL(title,"Title-1")')
        expected_result = Event.objects.filter(title="Title-2")
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_parse_query_using_equal_operator(self):
        result = APIQueryFuncs.parse_query('EQUAL(title,"Title-1")')
        expected_result = "equal", ("title", "Title-1")
        self.assertEqual(result, expected_result)

    def test_parse_query_using_and_operator_with_equal_less_than(self):
        result = APIQueryFuncs.parse_query(
            'AND(EQUAL(title,"Title-1"),LESS_THAN(date,"2024-01-01"))'
        )
        expected_result = "and", (
            'EQUAL(title,"Title-1")',
            'LESS_THAN(date,"2024-01-01")',
        )
        self.assertEqual(result, expected_result)

    def test_get_filter_kwargs_using_equal_operator(self):
        result = APIQueryFuncs.get_filter_kwargs("equal", ("title", "Title-1"))
        expected_result = {"title": "Title-1"}
        self.assertEqual(result, expected_result)

    def test_get_filter_kwargs_using_and_operator_with_equal_less_than(self):
        result = APIQueryFuncs.get_filter_kwargs(
            "and", ('EQUAL(title,"Title-1")', 'LESS_THAN(date,"2024-01-01")')
        )
        expected_result = {"title": "Title-1", "date__lt": "2024-01-01"}
        self.assertEqual(result, expected_result)

    def test_get_queryset_using_equal_operator(self):
        result = APIQueryFuncs.get_queryset("equal", ("title", "Title-1"))
        expected_result = Event.objects.filter(title="Title-1")
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_and_operator_with_equal_less_than(self):
        result = APIQueryFuncs.get_queryset(
            "and", ('EQUAL(title,"Title-1")', 'LESS_THAN(date,"2024-01-02")')
        )
        expected_result = Event.objects.filter(title="Title-1")
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_not_operator(self):
        result = APIQueryFuncs.get_queryset("not", ('EQUAL(title,"Title-2")',))
        expected_result = Event.objects.filter(title="Title-1")
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_or_operator(self):
        result = APIQueryFuncs.get_queryset(
            "or", ('EQUAL(title,"Title-1")', 'EQUAL(title,"Title-2")')
        )
        expected_result = Event.objects.filter(title__in=("Title-1", "Title-2"))
        self.assertQuerysetEqual(result, expected_result, ordered=False)
