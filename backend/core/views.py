from .serializers import EventsSerializer
from rest_framework import views, status
from rest_framework.response import Response
from core.models import Event
from django.shortcuts import get_object_or_404
from django.http import Http404
import re


class EventsAPIView(views.APIView):
    """
    An APIView for storing and getting events.
    """
    serializer_class = EventsSerializer

    """ POST request """

    def post(self, request):
        try:
            try:
                # Update entry if one already exists
                event_object = get_object_or_404(Event, id=request.data.get('id'))
                serializer = EventsSerializer(event_object, data=request.data)
            except Http404:
                # Otherwise create new entry
                serializer = EventsSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    """ GET request """

    @staticmethod
    def _equal_kwargs(prop, value):
        return {prop: value}

    @staticmethod
    def _greater_than_kwargs(prop, value):
        return {f'{prop}__gt': value}

    @staticmethod
    def _less_than_kwargs(prop, value):
        return {f'{prop}__lt': value}

    def _and_kwargs(self, *queries):
        # Accepts unlimited number of arguments
        kwargs = dict()
        for query in queries:
            kwargs.update(self.get_filter_kwargs(*self.parse_query(query)))
        return kwargs

    def or_operator(self, a, b, queryset=Event.objects):
        kwargs_a = self.get_filter_kwargs(*self.parse_query(a))
        kwargs_b = self.get_filter_kwargs(*self.parse_query(b))
        return queryset.filter(**kwargs_a) | queryset.filter(**kwargs_b)

    def not_operator(self, query, queryset=Event.objects):
        kwargs = self.get_filter_kwargs(*self.parse_query(query))
        return queryset.exclude(**kwargs)

    @staticmethod
    def query_regex_check(query):
        pattern = '[a-zA-Z]+\(.+\)'
        if not re.search(pattern, query):
            raise ValueError(f'Invalid query. Accepted regular expression: {pattern}')

    @staticmethod
    def parse_query_operator(query_split):
        valid_operators = ('equal', 'and', 'or', 'not', 'greater_than', 'less_than')
        operator = query_split[0].lower()
        if operator not in valid_operators:
            raise ValueError('Invalid operator. Available operators: EQUAL, AND, OR, NOT, GREATER_THAN, LESS_THAN')
        return operator

    @staticmethod
    def parse_query_arguments(query_split):
        args = query_split[1][:-1].replace('"', '')
        if args.count('(') > 0:
            # For nested queries
            args = args.split('),')
            args[:-1] = [arg + ")" for arg in args[:-1]]
        else:
            # For basic queries
            args = args.split(',')
        if not args:
            raise ValueError('No arguments provided')
        return tuple(args)

    def parse_query(self, query):
        self.query_regex_check(query)
        query_split = query.split('(', 1)
        operator = self.parse_query_operator(query_split)
        args = self.parse_query_arguments(query_split)
        return operator, args

    def get_filter_kwargs(self, operator, args):
        # Converts parsed query into kwargs for filter method
        operator_kwargs_func = getattr(self, f'_{operator}_kwargs')
        return operator_kwargs_func(*args)

    def get_queryset(self, operator, args, queryset=Event.objects):
        # Executes the required data filtering/selection operations based on operator
        if operator in ('equal', 'and', 'less_than', 'greater_than'):
            return queryset.filter(**self.get_filter_kwargs(operator, args))
        elif operator in ('not', 'or'):
            operator_func = getattr(self, f'{operator}_operator')
            return operator_func(*args)

    def get(self, request):
        try:
            query = self.request.query_params.get('query', '')
            if not query:
                # Get all entries if no query provided
                queryset = Event.objects
            else:
                queryset = self.get_queryset(*self.parse_query(query))
            serializer = EventsSerializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
