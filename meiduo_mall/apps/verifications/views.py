from django.shortcuts import render

# Create your views here.
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
1.验证图形验证码通过
2.生成短信验证码
3.





"""