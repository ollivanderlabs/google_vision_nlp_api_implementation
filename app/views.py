import base64
import json
import os
import random
import string
from pathlib import Path
from django.shortcuts import render
from django.views.generic import CreateView
from django.http import HttpResponse
from googleapiclient import discovery

from Base import settings
from . import forms

# AWS Boto Imports
import boto3

from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_file('svc_cred.json')
# credentials = GoogleCredentials.get_application_default()


def dict_to_item(raw):
    if type(raw) is dict:
        resp = {}
        for k, v in raw.items():
            if type(v) is str:
                resp[k] = {
                    'S': v
                }
            elif type(v) is int:
                resp[k] = {
                    'I': str(v)
                }
            elif type(v) is dict:
                resp[k] = {
                    'M': dict_to_item(v)
                }
            elif type(v) is list:
                resp[k] = []
                for i in v:
                    resp[k].append(dict_to_item(i))

        return resp
    elif type(raw) is str:
        return {
            'S': raw
        }
    elif type(raw) is int:
        return {
            'I': str(raw)
        }


def generate_pid():
    digits = "".join([random.choice(string.digits) for i in range(4)])
    pid = digits
    return pid


def vision_image_manager(image_file):
    # Instantiates a client
    service = discovery.build('vision', 'v1', credentials=credentials)
    # text.png is the image file.
    file_name = str(image_file)
    with open(file_name, 'rb') as image:
        image_content = base64.b64encode(image.read())
        service_request = service.images().annotate(body={
            'requests': [{
                'image': {
                    'content': image_content.decode('UTF-8')
                },
                'features': [{
                    'type': 'LABEL_DETECTION',
                }]
            }]
        })
    response = service_request.execute()
    print(response['responses'])
    res_dict = dict(response)
    return res_dict


def nlp_text_manager(text_path):
    text = text_path
    txt = Path(text_path).read_text(encoding='cp1252')
    service = discovery.build('language', 'v1beta1', credentials=credentials)
    service_request = service.documents().analyzeSentiment(
        body={
            'document': {
                'type': 'PLAIN_TEXT',
                'content': txt
            }
        }
    )
    response = service_request.execute()
    print(response)
    dict_response = dict(response)
    return dict_response


def post_to_dynamo_db(image, text):
    session = boto3.Session(
        aws_access_key_id=settings.AWS_SERVER_PUBLIC_KEY,
        aws_secret_access_key=settings.AWS_SERVER_SECRET_KEY
    )
    client = session.resource('dynamodb')
    table = client.Table('basetbl')
    table.put_item(
        Item={
            'id': int(generate_pid()),
            'imageResponse': dict_to_item(image),
            'textResponse': dict_to_item(text)
        }
    )


class BaseView(CreateView):
    def get(self, request, *args, **kwargs):
        return render(request, 'form.html', {})

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            post_data = request.POST.copy()
            form = forms.BaseForm(post_data, request.FILES)
            print('get post req')
            if form.is_valid():
                obj = form
                obj.imageFile = form.cleaned_data['imageFile']
                obj.textFile = form.cleaned_data['textFile']
                obj.save()
                # Process the image using Google's vision API
                image_path = os.path.join(settings.MEDIA_ROOT, 'images/', obj.imageFile.name)
                # print(image_path)
                image = vision_image_manager(image_path)
                text_path = os.path.join(settings.MEDIA_ROOT, 'texts/', obj.textFile.name)
                text = nlp_text_manager(text_path)
                results = {
                    'imageResponse': image,
                    'textResult': text
                }
                post_to_dynamo_db(image, text)
                return HttpResponse('Get post request along with files', status=200, )
