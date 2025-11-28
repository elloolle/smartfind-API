from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/",
        include(
            [
                path("users/", include("users.urls")),
                path("embeddings/", include("embeddings.urls")),
                path("payments/", include("subscription_payments.urls")),
            ]
        ),
    ),
]
