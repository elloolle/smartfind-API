import os

import boto3
from dotenv import load_dotenv

from simple_django_project.celery import app

from django.conf import settings
load_dotenv()

AwsConnection = None


def createAwsConnection(func):
    def wrapper(*args, **kwargs):
        global AwsConnection
        if AwsConnection is None:
            session = boto3.session.Session()
            AwsConnection = session.client(
                service_name=settings.AWS_SERVICE_NAME,
                endpoint_url=settings.AWS_ENDPOINT_URL,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
        return func(*args, **kwargs)

    return wrapper


@app.task
@createAwsConnection
def uploadFile(file_path, file_name=None):
    if file_name is None:
        file_name = file_path
    AwsConnection.upload_file(file_path, os.getenv("AWS_BUCKET_NAME"), file_name)


@createAwsConnection
def generatePresignedURL(file_name, expiration=settings.PRESIGNED_URL_EXPIRATION):
    return AwsConnection.generate_presigned_url(
        "get_object",
        Params={"Bucket": os.getenv("AWS_BUCKET_NAME"), "Key": file_name},
        ExpiresIn=expiration,
    )


def f():
    print("hello")
    print(AwsConnection is None)
