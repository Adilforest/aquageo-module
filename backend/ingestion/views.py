from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsEngineer
from catalog.models import ObjectType

from .extract import run_parse
from .models import ParseJob
from .serializers import ParseJobSerializer


def _source_kind_for(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return ParseJob.SourceKind.EXCEL
    if name.endswith(".pdf"):
        return ParseJob.SourceKind.PDF
    return ParseJob.SourceKind.MANUAL


@extend_schema(tags=["ingestion"])
class ParseJobViewSet(ModelViewSet):
    """Upload a document (+ object_type), parse it, return the draft + confidence."""

    queryset = ParseJob.objects.select_related("result_structure").all()
    serializer_class = ParseJobSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsEngineer()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        type_code = request.data.get("object_type") or request.data.get("type")
        if not upload:
            return Response({"detail": "file is required"}, status=400)
        if not type_code:
            return Response({"detail": "object_type is required"}, status=400)
        object_type = ObjectType.objects.filter(pk=type_code).first()
        if object_type is None:
            return Response({"detail": f"unknown object_type '{type_code}'"}, status=400)

        job = ParseJob.objects.create(
            source_kind=_source_kind_for(upload.name),
            file=upload,
            created_by=request.user if request.user.is_authenticated else None,
        )
        run_parse(job, object_type)
        return Response(self.get_serializer(job).data, status=201)
