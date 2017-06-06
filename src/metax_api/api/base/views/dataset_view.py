from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import detail_route
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from metax_api.models import Dataset
from .common_view import CommonViewSet
from ..serializers import DatasetReadSerializer

import logging
_logger = logging.getLogger(__name__)
d = logging.getLogger(__name__).debug

class DatasetViewSet(CommonViewSet):

    authentication_classes = ()
    permission_classes = ()

    # note: override get_queryset() to get more control
    queryset = Dataset.objects.all()
    serializer_class = DatasetReadSerializer
    object = Dataset

    lookup_field = 'pk'

    # allow search by external identifier (urn, or whatever string in practice) as well
    lookup_field_other = 'identifier'

    def __init__(self, *args, **kwargs):
        self.set_json_schema(__file__)
        super(DatasetViewSet, self).__init__(*args, **kwargs)

    def get_object(self):
        """
        Overrided from rest_framework generics.py method to also allow searching by the field
        lookup_field_other.

        future todo:
        - query params:
            - dataset (string)
            - owner_email (string)
            - fields (list of strings)
            - offset (integer) (paging)
            - limit (integer) (limit for paging)
        """

        if self.is_primary_key(self.kwargs.get(self.lookup_field, False)) or not hasattr(self, 'lookup_field_other'):
            # lookup by originak lookup_field. standard django procedure
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        else:
            # lookup by alternative field lookup_field_other
            lookup_url_kwarg = self.lookup_field_other

            # replace original field name with field name in lookup_field_other
            self.kwargs[lookup_url_kwarg] = self.kwargs.pop(self.lookup_field)

        queryset = self.filter_queryset(self.get_queryset())

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = { lookup_url_kwarg: self.kwargs[lookup_url_kwarg] }

        try:
            obj = get_object_or_404(queryset, **filter_kwargs)
        except Exception as e:
            _logger.debug('get_object(): could not find an object with field and value: %s: %s' % (lookup_url_kwarg, filter_kwargs[lookup_url_kwarg]))
            raise Http404

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj
