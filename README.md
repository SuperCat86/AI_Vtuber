#### AI Vtuber

AI Vtuber是一个AI虚拟主播项目，可以接入Bilibili的直播中，她会根据弹幕与观众进行互动。她的工作原理是读取Bilibili直播间的弹幕，将其发送给AI模型，再将获取到的文本转换成语音，最后通过声卡在直播间中进行播放。

##### 运行环境

* AI模型：OpenAI旗下的text-davinci-003模型
* 语音模型：edge-tts
* 操作系统：Windows10+
* 编程语言：Python3.6+
* 音频播放器：mpv
* 虚拟声卡：VB-Audio

##### 使用方法

1.安装依赖：

```shell
pip install bilibili-api-python edge-tts
```

2.配置环境变量：

下载安装mpv，并将其添加到环境变量中

3.设置API密匙：

登录OpenAI官网，如果先前没有账号需要注册一个。获取API密匙：https://platform.openai.com/account/api-keys

将密匙填入openai.api_key = ""

4.设置代理ip和端口号

如果你使用了魔法，需要将代理ip和端口号替换成自己的

```python
proxies = {'http': "http://127.0.0.1:21882", 'https': "http://127.0.0.1:21882"}
openai.proxy = proxies
```

5.安装声卡

为了能够让B站直播间的观众听得到主播的声音，需要安装虚拟声卡，推荐使用[VB-Audio Virtual Apps](https://vb-audio.com/Cable/)

6.启动程序

* 打开命令行，输入以下代码

  ```shell
  python main2.1.py
  ```

* 输入你的B站直播间编号

* 启动成功

注：

程序运行日志将保存在logs.txt
生成的音频文件将由mpv.exe
