from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.views import View
import re
from django import http
from django.urls import reverse
from django_redis import get_redis_connection

from apps.users.models import User
from django.db import DatabaseError

# Create your views here.
from apps.views import logger


class RegisterView(View):
    def get(self, request):

        return render(request, 'register.html')

    def post(self, request):
        data = request.POST
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        allow = data.get('allow')
        sms_code_client = data.get('sms_code')

        if not all([username, password, password2, mobile, allow,sms_code_client]):
            return http.HttpResponseBadRequest('参数不全')
        if not re.match(r'^[a-zA-Z0-9_]{5,20}$', username):
            return http.HttpResponseBadRequest('请输入5-20个字符的用户名')
        #验证用户名不能重复
        """
        需求：输入用户名之后，光标离开输入框，会发送一个ajax 请求，包含参数username ,
        然后后端校验username，计数 ，如果超过1 ，则名字重复
        """

        if password != password2:
            return http.HttpResponseBadRequest('两次输入的密码不一致')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseBadRequest('请输入正确的手机号码')

        if allow != 'on':
            return http.HttpResponseBadRequest('请勾选用户协议')

        #从redis中获取的数据都是bytes 类型
        #验证用户提交的短信验证码与redis 中的短信验证码是否一致
            # 8.1 验证 用户提交的短信验证码和redis的短信验证码是否一致
            # 8.1.1 连接reids
        redis_conn = get_redis_connection('code')
        #print(redis_conn)
        # .8.1.2 获取redis中的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        print (sms_code_server)
        # 8.1.3 判断redis中的短信验证码是否过期
        if not sms_code_server:
            return http.HttpResponseBadRequest('短信验证码已过期')
        # 8.1.4 比对
        if sms_code_server.decode() != sms_code_client:
            return http.HttpResponseBadRequest('短信验证码不一致')
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        #使用系统自带的方法 login（）里面封装了保存session，保持登陆状态
        login(request,user)
        # 响应注册结果
        return redirect(reverse('content:index'))
        #return http.HttpResponse('注册成功，重定向到首页')


#校验用户名是否重复
class RegisterUsernameCountView(View):
    def get(self,request,username):
        #当用户输入用户名之后， 失去焦点， 前端发送一个ajax请求，包含参数username
        #后台 使用get 路由 register/username/count/？username=username
        count = User.objects.filter(username=username).count()
        print (count)
        return  http.JsonResponse({'count':count})




class LoginView(View):
    def get(self,request):
        return render(request, 'login.html')

    def post(self,request):
        data = request.POST
        username = data.get('username')
        password = data.get ('password')
        remembered = request.POST.get('remembered')
        if not all([username, password]):
            return http.HttpResponseBadRequest('参数不全')
        if not re.match(r'^[a-zA-Z0-9_]{5,20}$', username):
            return http.HttpResponseBadRequest('请输入5-20个字符的用户名')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseBadRequest('密码最少8位，最长20位')

        # 认证登录用户
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request,'login.html',{'account_error_msg':'用户名或密码错误'})

        # 实现状态保持
        login(request, user)

        if remembered != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiry(None)

            # 响应登录结果
        return redirect(reverse('content:index'))

