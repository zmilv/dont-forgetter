from .serializers import EventSerializer, NoteSerializer
from rest_framework import views, status
from rest_framework.response import Response
from core.models import Event, Note
from django.shortcuts import get_object_or_404
from django.http import Http404
import re
from abc import ABCMeta, abstractmethod

QUERY_LIMIT = 5


class APIQueryFuncs:
    """ Functions that help dissect API queries """

    @staticmethod
    def _equal_kwargs(prop, value):
        return {prop: value}

    @staticmethod
    def _greater_than_kwargs(prop, value):
        return {f'{prop}__gt': value}

    @staticmethod
    def _less_than_kwargs(prop, value):
        return {f'{prop}__lt': value}

    @classmethod
    def _and_kwargs(cls, *queries):
        # Accepts unlimited number of arguments
        kwargs = dict()
        for query in queries:
            kwargs.update(cls.get_filter_kwargs(*cls.parse_query(query)))
        return kwargs

    @classmethod
    def or_operator(cls, a, b, queryset=Event.objects):
        kwargs_a = cls.get_filter_kwargs(*cls.parse_query(a))
        kwargs_b = cls.get_filter_kwargs(*cls.parse_query(b))
        return queryset.filter(**kwargs_a) | queryset.filter(**kwargs_b)

    @classmethod
    def not_operator(cls, query, queryset=Event.objects):
        kwargs = cls.get_filter_kwargs(*cls.parse_query(query))
        return queryset.exclude(**kwargs)

    @staticmethod
    def query_regex_check(query):
        regex = '^[a-zA-Z_]+\(.+\)$'
        if not re.fullmatch(regex, query):
            raise ValueError(f'Invalid query. Accepted regular expression: {regex}')

    @staticmethod
    def parse_query_operator(query_split):
        valid_operators = ('equal', 'and', 'or', 'not', 'greater_than', 'less_than')
        operator = query_split[0].lower()
        if operator not in valid_operators:
            raise ValueError('Invalid operator. Available operators: EQUAL, AND, OR, NOT, GREATER_THAN, LESS_THAN')
        return operator

    @staticmethod
    def parse_query_arguments(query_split):
        args = query_split[1][:-1]
        if args.count('(') > 0:
            # For nested queries
            args = args.split('),')
            args[:-1] = [arg + ")" for arg in args[:-1]]
        else:
            # For basic queries
            args = args.split(',')
        if not args:
            raise ValueError('No arguments provided')
        args = [arg.strip('"').strip("'") for arg in args]
        return tuple(args)

    @classmethod
    def parse_query(cls, query):
        cls.query_regex_check(query)
        query_split = query.split('(', 1)
        operator = cls.parse_query_operator(query_split)
        args = cls.parse_query_arguments(query_split)
        return operator, args

    @classmethod
    def get_filter_kwargs(cls, operator, args):
        # Converts parsed query into kwargs for filter method
        operator_kwargs_func = getattr(cls, f'_{operator}_kwargs')
        return operator_kwargs_func(*args)

    @classmethod
    def get_queryset(cls, operator, args, queryset=Event.objects):
        # Executes the required data filtering/selection operations based on operator
        if operator in ('equal', 'and', 'less_than', 'greater_than'):
            return queryset.filter(**cls.get_filter_kwargs(operator, args))
        elif operator in ('not', 'or'):
            operator_func = getattr(cls, f'{operator}_operator')
            return operator_func(*args)


class APIView(views.APIView, metaclass=ABCMeta):
    """ An abstract class for building API views for different models """

    @property
    @abstractmethod
    def model(self):
        pass

    @property
    @abstractmethod
    def serializer_class(self):
        pass

    @property
    @abstractmethod
    def order_by(self):
        pass

    def post(self, request):
        try:
            try:
                # Update entry if one already exists
                event_object = get_object_or_404(self.model, id=request.data.get('id'))
                serializer = self.serializer_class(event_object, data=request.data)
            except Http404:
                # Otherwise create new entry
                serializer = self.serializer_class(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            query = self.request.query_params.get('query', '')
            if not query:
                # Get all entries if no query provided
                queryset = self.model.objects.all().order_by(self.order_by)[:QUERY_LIMIT]
            else:
                queryset = APIQueryFuncs.get_queryset(*APIQueryFuncs.parse_query(query), queryset=self.model.
                                                      objects.all()).order_by(self.order_by)[:QUERY_LIMIT]
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APIDetailView(views.APIView, metaclass=ABCMeta):
    """ An abstract class for building detail API views for different models """

    @property
    @abstractmethod
    def model(self):
        pass

    @property
    @abstractmethod
    def serializer_class(self):
        pass

    def get(self, request, id):
        try:
            event = self.model.objects.get(pk=id)
            serializer = self.serializer_class(event)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, id):
        try:
            if id:
                event = self.model.objects.get(pk=id)
                event.delete()
                return Response({"result": "success", "message": f"ID{id} deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"result": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventAPIView(APIView):
    """ An APIView for storing and getting events """
    model = Event
    serializer_class = EventSerializer
    order_by = 'utc_timestamp'


class EventAPIDetailView(APIDetailView):
    """ An APIView for getting and deleting specific events """
    model = Event
    serializer_class = EventSerializer
    order_by = 'utc_timestamp'


class NoteAPIView(APIView):
    """ An APIView for storing and getting notes """
    model = Note
    serializer_class = NoteSerializer
    order_by = '-updated_at'


class NoteAPIDetailView(APIDetailView):
    """ An APIView for getting and deleting specific notes """
    model = Note
    serializer_class = NoteSerializer
    order_by = '-updated_at'
