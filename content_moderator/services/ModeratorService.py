import json
import os

import requests
from dotenv import load_dotenv

from simple_django_project.celery import app

from django.conf import settings
from content_moderator.models import Image

load_dotenv()

imageParams = {
        "models": settings.IMAGE_MODERATE_CATEGORY,
        "api_user": os.getenv("SIGHT_ENGINE_API_USER"),
        "api_secret": os.getenv("SIGHT_ENGINE_API_SECRET"),
    }

@app.task
def moderateImage(imageId):
    image = Image.objects.get(id=imageId)
    image_path = image.image_file.path
    file = {"media": open(image_path, "rb")}
    r = requests.post(
        "https://api.sightengine.com/1.0/check.json", files=file, data=imageParams
    )
    output = json.loads(r.text)
    image.percentage_of_illegality = output[IMAGE_MODERATE_CATEGORY]['prob']
    if image.percentage_of_illegality <= settings.CRITICAL_IMAGE_PROB:
        image.status = 'approved'
    else:
        image.status = 'rejected'
    image.save()
def moderateText(text):
    pass


def moderateVideo(video):
    pass

# s = r"C:\Users\Leo\Desktop\Прога\content_moderator\media\images\image.png"
# moderateImage(s)



def moderateVideo(video):
    pass


# s = r"C:\Users\Leo\Desktop\Прога\content_moderator\media\images\image.png"
# moderateImage(s)
