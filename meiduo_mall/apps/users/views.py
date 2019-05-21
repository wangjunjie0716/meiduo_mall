import json

from django.contrib.auth import login, authenticate, logout

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
from utils.response_code import RETCODE

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

        next = request.GET.get('next')
        if next:
            response =redirect(next)
        else:
            response = redirect(reverse('content:index'))

            # 8.返回相应 设置cookie
        #response = redirect(reverse('content:index'))
            # 设置cookie信息
            # response.set_cookie(key,value,max_age=)
        if remembered != 'on':
                # 说明不需要记住
            response.set_cookie('username', user.username, max_age=None)
        else:
                # 需要记住
            response.set_cookie('username', user.username, max_age=14 * 24 * 3600)



            # 响应登录结果
        return response


class LogoutView(View):
    def get(self,request):
        """实现退出登录逻辑"""
        # 清理session
        logout(request)
        # 退出登录，重定向到登录页
        response = redirect(reverse('content:index'))
        # 退出登录时清除cookie中的username
        response.delete_cookie('username')
        return response


# class UserCenterInfo(View):
#
#     def get(self,request):
#         context = {
#             'username': request.user.username,
#             'mobile': request.user.mobile,
#             'email': request.user.email,
#             'email_active': request.user.email_active
#         }
#         if request.user.is_authenticated():
#             return render(request, 'user_center_info.html',context=context)
#         else:
#             return redirect(reverse('users:login'))


from django.contrib.auth.mixins import LoginRequiredMixin

class UserCenterInfo(LoginRequiredMixin,View):
    # 必须是登陆用户才可以访问
    # 如果用户没有登陆，默认会调转到系统的　登陆路由
    #系统的默认登陆路由是：/accounts/login/
    #
    def get(self,request):

        #1.获取指定的数据组织上下文
        context = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active
        }

        return render(request,'user_center_info.html',context=context)

from django.contrib.auth.mixins import  LoginRequiredMixin
class Save_EmailView(View):
    #需求：当用户在邮件输入框中，输入一个邮件地址后，点击保存按钮，前端讲邮箱信息发送给后端
    #后端：需要确定请求方式和路由
    #大体步骤：１．必须是登录用户才可以更新邮箱信息，　２．接收用户提交的邮箱信息　３．验证邮箱信息是否符合邮箱规则，４．保存数据５．返回相应
    def put(self,request):
        #email =  request.GET.get('email')
        body = request.body
        body_str = body.decode()
        data = json.loads(body_str)
        email = data.get("email")
        if not all([email]):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数错误'})
        if not re.match(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$',email):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数错误'})
        if not request.user.is_authenticated():
            return http.JsonResponse({'code':RETCODE.SESSIONERR,'errmsg':'未登录'})
        #更新数据
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponse({'code':RETCODE.DBERR,'ermsg':'更新错误'})
        #发送激活邮件
        from django.core.mail import send_mail
        subject = '主题'
        message = 'message'
        recipient_list = [email]
        from_email = 'junjie90716@163.com'
        html_message = "<a href='#'>这是美多商场激活链接</a>"
        send_mail(
            subject= subject,
            message = html_message,
            recipient_list=recipient_list,
            from_email = from_email
        )

        #返回响应
        return  http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})












