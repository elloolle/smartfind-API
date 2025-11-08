# import loguru
# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from .models import Recipe

# loguru.logger.add("logs/recipe.log", rotation="100 MB", retention="7 days")


# @receiver(post_save, sender=Recipe)
# def create_recipe(sender, instance, created, **kwargs):
#     if created:
#         loguru.logger.info(f"Recipe created: {instance.name}")
#     else:
#         loguru.logger.info(f"Recipe updated: {instance.name}")
