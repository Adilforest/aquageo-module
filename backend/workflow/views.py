from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsEngineer, IsManager

from .models import Application
from .serializers import ApplicationSerializer
from .services import TransitionError, decide, submit


@extend_schema(tags=["workflow"])
class ApplicationViewSet(ModelViewSet):
    """Applications: engineers submit, managers decide. Gov-flow for new objects."""

    queryset = Application.objects.select_related(
        "structure", "submitted_by", "reviewer"
    ).all()
    serializer_class = ApplicationSerializer
    filterset_fields = ["status", "kind", "structure"]

    def get_permissions(self):
        if self.action in ("create", "submit", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsEngineer()]
        if self.action == "decide":
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user, status=Application.Status.DRAFT)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = self.get_object()
        try:
            submit(application, request.user)
        except TransitionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(application).data)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        application = self.get_object()
        decision = str(request.data.get("decision", "")).lower()
        if decision not in ("approve", "reject"):
            return Response({"detail": "decision must be 'approve' or 'reject'"}, status=400)
        try:
            decide(
                application, request.user,
                approve=(decision == "approve"),
                comment=request.data.get("comment", ""),
            )
        except TransitionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(application).data)
