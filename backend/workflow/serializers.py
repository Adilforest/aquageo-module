from rest_framework import serializers

from .models import Application, ApprovalOrder, Signature


class SignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = ("id", "signer", "signed_at", "cert_subject", "valid", "created_at")


class ApprovalOrderSerializer(serializers.ModelSerializer):
    file = serializers.FileField(read_only=True)

    class Meta:
        model = ApprovalOrder
        fields = ("id", "number", "file", "issued_at", "created_at")


class ApplicationSerializer(serializers.ModelSerializer):
    signature = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id", "structure", "kind", "status", "submitted_by", "reviewer",
            "submitted_at", "decided_at", "comment", "created_at",
            "signature", "order",
        )
        read_only_fields = (
            "id", "status", "submitted_by", "reviewer",
            "submitted_at", "decided_at", "created_at", "signature", "order",
        )

    def get_signature(self, obj):
        signature = obj.signatures.first()
        return SignatureSerializer(signature).data if signature else None

    def get_order(self, obj):
        order = obj.orders.first()
        return ApprovalOrderSerializer(order, context=self.context).data if order else None
