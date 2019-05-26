from django.conf.urls import url,include
from django.contrib import admin
from .import views

urlpatterns = [
    #url(r'^admin/', admin.site.urls),
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_]{5,20})/$', views.RegisterUsernameCountView.as_view(),
        name='usernamecount'),
    url(r'^login/$',views.LoginView.as_view(), name='login'),
    url(r'^logout/$',views.LogoutView.as_view(), name='logout'),
    url(r'^user_center_info/$',views.UserCenterInfo.as_view(), name='user_center_info'),
    url(r'^emails/$',views.Save_EmailView.as_view(), name='email'),
    url(r'^emails/verification/$',views.EmailVerifyView.as_view(), name='email'),
    url(r'^Address/$',views.AddressView.as_view(), name='address'),
    url(r'^addresses/create/$',views.CreateAddressView.as_view(), name='address_create'),
    url(r'^addresses/(?P<address_id>\d+)/$',views.UpdateDestoryAddressView.as_view(),name='updateaddress'),
]