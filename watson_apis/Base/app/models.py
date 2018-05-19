from django.db import models
from app.storage import OverwriteStorage


class BaseModel(models.Model):
    imageFile = models.FileField(storage=OverwriteStorage(), upload_to='images/', name='imageFile')
    textFile = models.FileField(storage=OverwriteStorage(), upload_to='texts/', name='textFile')

