from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsManager
from .serializers import UserSerializer


class MeView(RetrieveAPIView):
    """Return the authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ManagerAreaView(APIView):
    """Stub endpoint gated by the manager role — used to exercise RBAC.

    Real manager-only resources (application review, signing) arrive in M5.
    """

    permission_classes = [IsManager]

    @extend_schema(responses={200: OpenApiResponse(description="Доступ разрешён")})
    def get(self, request):
        return Response({"ok": True, "role": request.user.role})
