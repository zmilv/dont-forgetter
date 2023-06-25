import re
from abc import ABCMeta, abstractmethod

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Event, Note
from core.serializers import EventSerializer, NoteSerializer
from core.validators import regex_dict

QUERY_LIMIT = 5


class APIQueryFuncs:
    """Functions that help dissect API queries"""

    @staticmethod
    def _equal_kwargs(prop, value):
        return {prop: value}

    @staticmethod
    def _greater_than_kwargs(prop, value):
        return {f"{prop}__gt": value}

    @staticmethod
    def _less_than_kwargs(prop, value):
        return {f"{prop}__lt": value}

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
        regex = "^[a-zA-Z_]+\(.+\)$"
        if not re.fullmatch(regex, query):
            raise ValueError(f"Invalid query. Accepted regular expression: {regex}")

    @staticmethod
    def parse_query_operator(query_split):
        valid_operators = ("equal", "and", "or", "not", "greater_than", "less_than")
        operator = query_split[0].lower()
        if operator not in valid_operators:
            raise ValueError(
                "Invalid operator. Available operators: EQUAL, AND, OR, NOT, GREATER_THAN, LESS_THAN"
            )
        return operator

    @staticmethod
    def parse_query_arguments(query_split):
        args = query_split[1][:-1]
        if args.count("(") > 0:
            # For nested queries
            args = args.split("),")
            args[:-1] = [arg + ")" for arg in args[:-1]]
        else:
            # For basic queries
            args = args.split(",")
        if not args:
            raise ValueError("No arguments provided")
        args = [arg.strip('"').strip("'") for arg in args]
        return tuple(args)

    @classmethod
    def parse_query(cls, query):
        cls.query_regex_check(query)
        query_split = query.split("(", 1)
        operator = cls.parse_query_operator(query_split)
        args = cls.parse_query_arguments(query_split)
        return operator, args

    @classmethod
    def get_filter_kwargs(cls, operator, args):
        # Converts parsed query into kwargs for filter method
        operator_kwargs_func = getattr(cls, f"_{operator}_kwargs")
        return operator_kwargs_func(*args)

    @classmethod
    def get_queryset(cls, operator, args, queryset=Event.objects):
        # Executes the required data filtering/selection operations based on operator
        if operator in ("equal", "and", "less_than", "greater_than"):
            return queryset.filter(**cls.get_filter_kwargs(operator, args))
        elif operator in ("not", "or"):
            operator_func = getattr(cls, f"{operator}_operator")
            return operator_func(*args)


ownership_error_message = "You are not the owner of this object"


def apply_swagger_schema(swagger_kwargs):
    """Decorator for overriding the automatically generated swagger schema for children of the APIView abstract class
    in order to include extra details"""

    def decorator(cls):
        class DecoratedClass(cls):
            @swagger_auto_schema(**swagger_kwargs)
            def post(self, request):
                return super().post(request)

        return DecoratedClass

    return decorator


class APIView(GenericAPIView, metaclass=ABCMeta):
    """An abstract class for building API views for different models"""

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

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            try:
                # Update entry if one already exists
                event_object = get_object_or_404(self.model, id=request.data.get("id"))
                if event_object.user != request.user:
                    return Response(
                        {"result": "error", "message": ownership_error_message},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                serializer = self.serializer_class(
                    event_object,
                    data=request.data,
                    context={"request": request},
                    partial=True,
                )
            except Http404:
                # Otherwise create new entry
                serializer = self.serializer_class(
                    data=request.data, context={"request": request}
                )
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"result": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    query_description = (
        "Defines the filter to be applied to the data set. Available operators: equal, and, or, not,"
        " greater_than, less_than. Some operators can be combined. See readme at "
        "https://github.com/zmilv/dont-forgetter for usage examples."
    )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "query",
                openapi.IN_QUERY,
                description=query_description,
                type=openapi.TYPE_STRING,
            )
        ]
    )
    def get(self, request):
        try:
            user = request.user
            query = self.request.query_params.get("query", "")
            if not query:
                # Get all entries if no query provided
                self.queryset = (
                    self.model.objects.all()
                    .filter(user=user)
                    .order_by(self.order_by)[:QUERY_LIMIT]
                )
            else:
                self.queryset = APIQueryFuncs.get_queryset(
                    *APIQueryFuncs.parse_query(query),
                    queryset=self.model.objects.all().filter(user=user),
                ).order_by(self.order_by)[:QUERY_LIMIT]
            serializer = self.serializer_class(self.queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"result": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class APIDetailView(GenericAPIView, metaclass=ABCMeta):
    """An abstract class for building detail API views for different models"""

    @property
    @abstractmethod
    def model(self):
        pass

    @property
    @abstractmethod
    def serializer_class(self):
        pass

    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        try:
            event = self.model.objects.get(pk=id)
            if event.user == request.user:
                serializer = self.serializer_class(event)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                {"result": "error", "message": ownership_error_message},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"result": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, id):
        try:
            event = self.model.objects.get(pk=id)
            if event.user == request.user:
                event.delete()
                return Response(
                    {"result": "success", "message": f"ID{id} deleted"},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"result": "error", "message": ownership_error_message},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"result": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@apply_swagger_schema(
    {
        "request_body": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "date"],
            properties={
                "category": openapi.Schema(type=openapi.TYPE_STRING, default="other"),
                "notification_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="<set in user settings>",
                    enum=["email", "sms"],
                ),
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "date": openapi.Schema(
                    type=openapi.TYPE_STRING, pattern=regex_dict["date"]
                ),
                "time": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="<set in user settings>",
                    pattern=regex_dict["time"],
                ),
                "notice_time": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="-",
                    pattern=regex_dict["interval_and_notice"] + ' OR "-"',
                ),
                "interval": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="-",
                    pattern=regex_dict["interval_and_notice"] + ' OR "-"',
                ),
                "info": openapi.Schema(type=openapi.TYPE_STRING),
                "utc_offset": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="<set in user settings>",
                    pattern=regex_dict["utc_offset"],
                ),
            },
        )
    }
)
class EventAPIView(APIView):
    """An APIView for storing and getting events"""

    model = Event
    serializer_class = EventSerializer
    order_by = "utc_timestamp"


class EventAPIDetailView(APIDetailView):
    """An APIView for getting and deleting specific events"""

    model = Event
    serializer_class = EventSerializer


@apply_swagger_schema(
    {
        "request_body": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["info"],
            properties={
                "category": openapi.Schema(type=openapi.TYPE_STRING, default="other"),
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "info": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    }
)
class NoteAPIView(APIView):
    """An APIView for storing and getting notes"""

    model = Note
    serializer_class = NoteSerializer
    order_by = "-updated_at"


class NoteAPIDetailView(APIDetailView):
    """An APIView for getting and deleting specific notes"""

    model = Note
    serializer_class = NoteSerializer


class APIWelcomeView(GenericAPIView):
    """A class for the welcome endpoint"""

    def get(self, request):
        try:
            import json

            welcome_message = (
                "Welcome to dont-forgetter API! To get started, use the /user/register endpoint to "
                "create an account. If using the API via browser, you can log in using the button at "
                "top right. Otherwise, please use the /user/login endpoint to obtain a JWT token. "
                "Provide this token in the headers of your requests in order to access data requiring "
                "authentication. To create events and notes, visit /event and /note endpoints "
                "respectively. Documentation: https://dont-forgetter.rest/docs/ and "
                "https://github.com/zmilv/dont-forgetter"
            )
            return Response(
                {"welcome_message": welcome_message}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"result": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
