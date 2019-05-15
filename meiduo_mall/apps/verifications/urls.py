from django.conf.urls import url,include
from .import views
urlpatterns = [
    #url(r'^admin/', admin.site.urls),   url(r'^$', views.ImageCodeView.as_view(), name='ImageCode'),
url(r'^image_codes/(?P<uuid>[\w-]+)/$', views.ImageCodeView.as_view()),
]
