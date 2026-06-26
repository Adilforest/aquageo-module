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
    # Read-only conveniences for the gov-flow UI (#30): show the draft object's
    # name and who submitted/reviewed without an extra round-trip per row.
    structure_name = serializers.CharField(source="structure.name_ru", read_only=True)
    submitted_by_username = serializers.SerializerMethodField()
    reviewer_username = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id", "structure", "structure_name", "kind", "status",
            "submitted_by", "submitted_by_username", "reviewer", "reviewer_username",
            "submitted_at", "decided_at", "comment", "created_at",
            "signature", "order",
        )
        read_only_fields = (
            "id", "status", "submitted_by", "reviewer",
            "submitted_at", "decided_at", "created_at", "signature", "order",
            "structure_name", "submitted_by_username", "reviewer_username",
        )

    def get_submitted_by_username(self, obj):
        return obj.submitted_by.username if obj.submitted_by_id else None

    def get_reviewer_username(self, obj):
        return obj.reviewer.username if obj.reviewer_id else None

    def get_signature(self, obj):
        signature = obj.signatures.first()
        return SignatureSerializer(signature).data if signature else None

    def get_order(self, obj):
        order = obj.orders.first()
        return ApprovalOrderSerializer(order, context=self.context).data if order else None
