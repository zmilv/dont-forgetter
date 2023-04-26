from django.test import TestCase
from ..models import Event
from ..views import EventsAPIView as View


class ViewTestSuite(TestCase):
    """
    Test suite for functions within views.py
    """

    def setUp(self):
        for i in range(1, 3):  # 1 and 2
            Event.objects.create(title=f'Title-{i}', date=f'2024-01-0{i}')
        self.view_class = View()

    def test_equal_kwargs(self):
        result = View._equal_kwargs('date', '2024-01-01')
        expected_result = {'date': '2024-01-01'}
        self.assertEqual(result, expected_result)

    def test_greater_than_kwargs(self):
        result = View._greater_than_kwargs('date', '2024-01-01')
        expected_result = {'date__gt': '2024-01-01'}
        self.assertEqual(result, expected_result)

    def test_less_than_kwargs(self):
        result = View._less_than_kwargs('date', '2024-01-01')
        expected_result = {'date__lt': '2024-01-01'}
        self.assertEqual(result, expected_result)

    def test_and_kwargs(self):
        result = View._and_kwargs(self.view_class, 'EQUAL(title,"Title-1")', 'EQUAL(date,"2024-01-01")')
        expected_result = {'title': 'Title-1', 'date': '2024-01-01'}
        self.assertEqual(result, expected_result)

    def test_or_operator(self):
        result = View.or_operator(self.view_class, 'EQUAL(title,"Title-1")', 'EQUAL(title,"Title-2")')
        expected_result = Event.objects.filter(pk__in=(1, 2))
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_not_operator(self):
        result = View.not_operator(self.view_class, 'EQUAL(title,"Title-1")')
        expected_result = Event.objects.filter(pk=2)
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_parse_query_using_equal_operator(self):
        result = View.parse_query(self.view_class, 'EQUAL(title,"Title-1")')
        expected_result = 'equal', ('title', 'Title-1')
        self.assertEqual(result, expected_result)

    def test_parse_query_using_and_operator_with_equal_less_than(self):
        result = View.parse_query(self.view_class, 'AND(EQUAL(title,"Title-1"),LESS_THAN(date,"2024-01-01"))')
        expected_result = 'and', ('EQUAL(title,Title-1)', 'LESS_THAN(date,2024-01-01)')
        self.assertEqual(result, expected_result)

    def test_get_filter_kwargs_using_equal_operator(self):
        result = View.get_filter_kwargs(self.view_class, 'equal', ('title', "Title-1"))
        expected_result = {'title': 'Title-1'}
        self.assertEqual(result, expected_result)

    def test_get_filter_kwargs_using_and_operator_with_equal_less_than(self):
        result = View.get_filter_kwargs(self.view_class, 'and', ('EQUAL(title,"Title-1")',
                                                                 'LESS_THAN(date,"2024-01-01")'))
        expected_result = {'title': 'Title-1', 'date__lt': '2024-01-01'}
        self.assertEqual(result, expected_result)

    def test_get_queryset_using_equal_operator(self):
        result = View.get_queryset(self.view_class, 'equal', ('title', 'Title-1'))
        expected_result = Event.objects.filter(pk=1)
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_and_operator_with_equal_less_than(self):
        result = View.get_queryset(self.view_class, 'and', ('EQUAL(title,"Title-1")', 'LESS_THAN(date,"2024-01-02")'))
        expected_result = Event.objects.filter(pk=1)
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_not_operator(self):
        result = View.get_queryset(self.view_class, 'not', ('EQUAL(title,"Title-2")',))
        expected_result = Event.objects.filter(pk=1)
        self.assertQuerysetEqual(result, expected_result, ordered=False)

    def test_get_queryset_using_or_operator(self):
        result = View.get_queryset(self.view_class, 'or', ('EQUAL(title,"Title-1")', 'EQUAL(title,"Title-2")'))
        expected_result = Event.objects.filter(pk__in=(1, 2))
        self.assertQuerysetEqual(result, expected_result, ordered=False)
