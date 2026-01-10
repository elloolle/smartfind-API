from django.db import migrations


def seed_products(apps, schema_editor):
    from django.conf import settings

    Product = apps.get_model("core", "Product")

    products = getattr(settings, "DEFAULT_PRODUCTS", [])

    for p in products:
        Product.objects.update_or_create(
            name=p["name"],
            defaults={
                "plan": p.get("plan"),
                "month_price": p.get("month_price"),
                "delay": p.get("delay"),
            },
        )


def unseed_products(apps, schema_editor):
    from django.conf import settings

    Product = apps.get_model("core", "Product")

    products = getattr(settings, "DEFAULT_PRODUCTS", [])
    names = [p.get("name") for p in products if p.get("name")]

    if names:
        Product.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_products, reverse_code=unseed_products),
    ]
