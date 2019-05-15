from django.shortcuts import render

# Create your views here.
from libs.yuntongxun.sms import CCP

"""
图片验证码的需求

前端需要生成一个uuid,这个uuid是可以确保在浏览器端唯一的,前端需要将uuid传递给后端

后端:
    路由和请求方式
    GET     提取URL的特定部分，如/weather/beijing/2018，可以在服务器端的路由中用正则表达式截取；
            image_codes/(?P<uuid>[\w-]+)/
            查询字符串（query string)，形如key1=value1&key2=value2
            verifications/?uuid=xxxx
    步骤
    1.接收这个uuid
    2.生成图片验证码,和保存图片验证码的内容
    3.把图片返回给浏览器
"""
from django import http
from django.shortcuts import render

# Create your views here.
from django.views import View

#from libs.yuntongxun.sms import CCP

from django.http import JsonResponse
from django_redis import get_redis_connection
from libs.captcha.captcha import captcha

class ImageCodeView(View):

    def get(self,request,uuid):
        # 1.接收这个uuid 已经获取了
        # uuid=request.GET.get('')
        # 2.生成图片验证码,和保存图片验证码的内容
            # 2.1 生成图片验证码,

        # generate_captcha 它返回2个值,第一个值是 图片验证码的内容
        # 第二个值是图片验证码的二进制图片
        text,code,image = captcha.generate_captcha()
        #print("code:",code)
        #print("text:",text)

            # 2.2 保存图片验证码的内容 redis
        #2.2.1 连接redis

        redis_conn = get_redis_connection('code')
        #2.2.2 保存数据
        # redis_conn.setex(键,过期时间,值)
        # redis_conn.setex(key,expire,value)
        redis_conn.setex('img_%s'%uuid,120,text)
        # 3.把图片返回给浏览器
        # application/json

        # content_type 其实就是MIME类型
        # 语法: 大类/小类
        # image 图片
        # image/jepg image/png image/gif
        # text/html     text/javascript     text/css

        # Content-Type:text/html 默认是 text/html
        # return http.HttpResponse(image)
        return http.HttpResponse(image,content_type='image/jpeg')

"""
短信验证码需求分析：
1.点击发送短信验证码的时候，前端搜集 校验手机号， 图形验证码， uuid 这些东西发送给后端
2.后端接收这些数据，验证数据，生成短信验证码，然后保存短信验证码， 发送验证码，返回响应




"""

class SMSCodeView():
    #1.后端要接收的数据
    def get(self,request,mobile):
        uuid = request.GET.get('image_code_id') #图片验证码的UUID
        text_client = request.GET.get('image_code') #用户输入的图片验证码
     #2.验证数据 ： 2.1对比用户提交的图片验证码和redis存储的是否一致
                #2.2 redis 中的图片验证码有可能过期，判断是否过期
        from django_redis import  get_redis_connection
        redis_conn = get_redis_connection('code')
        text_server = redis_conn.get('img_%s'% uuid)
        if text_server is None:
            return  http.HttpResponseBadRequest("验证码已过期")
        if text_client != text_server:
            return http.HttpResponseBadRequest("图片验证码不一致")
        #开始生成短信验证码

        from random import randint
        sms_code = randint(1000,9999)
        #保存短信验证码
        redis_conn.setex('sms_%s'%mobile ,300,sms_code)
        #发送短信验证码

        CCP().send_template_sms(mobile, [sms_code, 5], 1)

        # 返回响应
        return http.JsonResponse({'code':200})


