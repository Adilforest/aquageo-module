"""Report export endpoints (issue #31).

``/api/v1/reports/condition-summary/?format=pdf|xlsx`` builds a summary of the
infrastructure condition (distribution by condition / type / territory + risk
summary) and streams it as a PDF or an Excel workbook. The same map/dashboard
filters (type/condition/basin/district/search) are honored, and the numbers are
taken from the shared stats service, never recomputed.
"""
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from . import services


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """Don't let DRF interpret ``?format=`` — here it selects the export format
    (pdf/xlsx), not a DRF renderer. Default negotiation would 404 on ``format=pdf``.
    """

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)

XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
PDF_CONTENT_TYPE = "application/pdf"

FILTER_PARAMS = [
    OpenApiParameter("type", str, many=True),
    OpenApiParameter("condition", str, many=True),
    OpenApiParameter("basin", str),
    OpenApiParameter("district", str),
    OpenApiParameter("search", str),
    OpenApiParameter(
        "format", str, enum=["pdf", "xlsx"],
        description="Export format (default pdf).",
    ),
]


class ConditionSummaryReportView(APIView):
    """Condition-summary report as PDF (default) or Excel."""

    permission_classes = [AllowAny]
    content_negotiation_class = IgnoreClientContentNegotiation

    @extend_schema(
        tags=["reports"],
        parameters=FILTER_PARAMS,
        responses={(200, PDF_CONTENT_TYPE): OpenApiTypes.BINARY},
    )
    def get(self, request):
        fmt = (request.GET.get("format") or "pdf").lower()
        report = services.build_condition_summary(request)
        if fmt == "xlsx":
            payload = services.render_xlsx(report)
            response = HttpResponse(payload, content_type=XLSX_CONTENT_TYPE)
            response["Content-Disposition"] = (
                'attachment; filename="condition-summary.xlsx"'
            )
            return response
        payload = services.render_pdf(report)
        response = HttpResponse(payload, content_type=PDF_CONTENT_TYPE)
        response["Content-Disposition"] = (
            'attachment; filename="condition-summary.pdf"'
        )
        return response
