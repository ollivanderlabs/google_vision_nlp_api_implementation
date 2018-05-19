from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^app/', views.BaseView.as_view(), name='home')
]