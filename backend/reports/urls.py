from django.urls import path

from .views import ConditionSummaryReportView

urlpatterns = [
    path(
        "reports/condition-summary/",
        ConditionSummaryReportView.as_view(),
        name="report-condition-summary",
    ),
]
