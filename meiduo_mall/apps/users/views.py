import json
from django.contrib.auth import login, authenticate, logout

from django.shortcuts import render, redirect
from django.views import View
import re
from django import http
from django.urls import reverse
from django_redis import get_redis_connection
from utils.views import LoginRequiredJSONMixin
from apps.users.models import User, Address
from django.db import DatabaseError

from apps.users.utils import generic_verify_email_url, check_veryfy_email_token
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
        html_message = "<a href='#'>戳我,戳我,戳我有惊喜</a>"

        #将代码换成异步代码
        # send_mail(
        #     subject= subject,
        #     message = html_message,
        #     recipient_list=recipient_list,
        #     from_email = from_email
        # )
        verify_url = generic_verify_email_url(request.user.id)

        html_message = '<p>尊敬的用户您好！</p>' \
                       '<p>感谢您使用美多商城。</p>' \
                       '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                       '<p><a href="%s">%s<a></p>' % (email, verify_url, verify_url)

        from celery_tasks.email.tasks import send_verify_email

        send_verify_email.delay(
                    subject= subject,
                    message = message,
                    recipient_list=recipient_list,
                    from_email = from_email,
                    html_message =html_message)
        #返回响应
        return  http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})


class EmailVerifyView(View):

    def get(self,request):
        # 1.接收token
        token = request.GET.get('token')
        if token is None:
            return http.HttpResponseBadRequest('参数错误')
        # 2.验证token
        user_id = check_veryfy_email_token(token)
        if user_id is None:
            return http.HttpResponseBadRequest('参数错误')
        # 3.根据user_id查询用户信息
        try:
            # pk primary key 主键的意思
            # 如果我们不记得主键是哪个字段的时候,可以直接使用pk
            # 系统会自动使用主键
            # user = User.objects.get(id=user_id)
            user = User.objects.get(pk=user_id)
            # 4.改变用户信息
            if user is not None:
                user.email_active=True
                user.save()
        except User.DoesNotExist:
            return http.HttpResponseBadRequest('参数错误')
        # 5.返回相应(跳转到个人中心页面)
        return redirect(reverse('users:user_center_info'))


class AddressView(LoginRequiredMixin,View):

    def get(self,request):
        """
        1.必须是登陆用户
        2.查询登陆用户的地址信息 [Address,Address]
        3.对列表数据进行转换为字典列表
        4.传递给模板
        """
        # 2.查询登陆用户的地址信息 [Address,Address]
        addresses = Address.objects.filter(user=request.user,is_deleted=False)
        # 3.对列表数据进行转换为字典列表
        addresses_list = []
        for address in addresses:
            addresses_list.append({
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "province_id": address.province_id,
                "city": address.city.name,
                "city_id": address.city_id,
                "district": address.district.name,
                "district_id": address.district_id,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            })
        # 4.传递给模板
        context = {
            'addresses':addresses_list,
            'default_address_id':request.user.default_address_id

        }
        return render(request,'user_center_site.html',context=context)

class CreateAddressView(LoginRequiredJSONMixin,View):
    """
    需求:
        当用户填写完新增数据之后,点击新增按钮,需要让前端将 收货人等信息提交给后端

    后端:

        大体步骤:
        1.判断当前用户是否登陆
        2.接收参数
        3.验证参数
        4.数据入库
        5.返回相应

        请求方式和路由:
            POST    /addresses/create/
    """

    def post(self,request):

        #0 判断用户的地址数量是否超过20个
        count = Address.objects.filter(user=request.user,is_deleted=False).count()
        if count > 20:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'个数超过上限'})

        # 1.判断当前用户是否登陆
        # if request.user.is_authenticated

        # 2.接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseBadRequest('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseBadRequest('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseBadRequest('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseBadRequest('参数email有误')
        # 4.数据入库
        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            # 如果没有默认地址我们就设置一个默认地址
            if not request.user.default_address:
                request.user.default_address=address
                request.user.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,'errmsg':'数据库操作失败'})
        # 5.返回相应
        # 新增地址成功，将新增的地址响应给前端实现局部刷新
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','address':address_dict})


class UpdateDestoryAddressView(LoginRequiredJSONMixin,View):
    """
    需求: 当用户修改了地址信息之后,需要让前端将 这个信息全都收集过去
    后端:

        1.判断用户是否登陆
        2.根据传递过来的更新指定的地址信息
        3.更新
        4.返回相应

    请求方式和路由
        PUT addresses/id/
    """
    def put(self,request,address_id):
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 2.根据传递过来的更新指定的地址信息
        # address = Address.objects.get(pk=address_id)
        # address.recever=data.get('recever')
        # 3.更新
        try:
            # 更新成功之后,返回 1 表示更新成功
            # 返回 0 表示更新失败

            Address.objects.filter(pk=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            # 再次查询一下地址信息
            address = Address.objects.get(pk=address_id)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR})

        # 4.返回相应
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return http.JsonResponse({'address':address_dict,'code':RETCODE.OK})

    def delete(self,request,address_id):
        try:
            address = Address.objects.get(pk=address_id)

            # address.delete()
            address.is_deleted=True
            address.save()
        except Exception as e:
            pass

        return http.JsonResponse({'code':RETCODE.OK})


"""
增
    1.接收数据
    2.验证数据
    3.数据入库
    4.返回相应
删
    1.根据id进行查询
    2.删除就行
改
    1.先接收要修改哪个数据(根据id进行查询)
    2.接收修改之后的数据
    3.验证数据
    4.更新数据(保存数据)
    5.返回相应
查
    1.根据已知条件进行查询
    2.查询出来的是对象列表,我们需要将对象列表转换为字典
    3.返回数据

"""





