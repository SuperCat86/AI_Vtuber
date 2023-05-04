from bilibili_api import live, sync
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai
import queue
import datetime
import threading
import subprocess

# 设置API密钥
openai.api_key = ""

# 设置模型ID
model_engine = "text-davinci-003"

# 设置代理ip和端口号
proxies = {'http': "http://127.0.0.1:21882", 'https': "http://127.0.0.1:21882"}
openai.proxy = proxies

QuestionList = queue.Queue(10)  # 定义问题队列
QuestionName = queue.Queue(10)  # 定义用户名队列
AnswerList = queue.Queue()  # 定义AI回复队列
MpvList = queue.Queue()  # 定义播放队列
LogsList = queue.Queue()  # 定义日志队列
is_ai_ready = True  # 定义是否接受到ChatGPT response标志
is_tts_ready = True  # 定义语音是否生成完成标志
is_mpv_ready = True  # 定义是否播放完成标志
AudioCount = 0

room_id = int(input("请输入直播间编号: "))  # 输入直播间编号
room = live.LiveDanmaku(room_id)  # 连接弹幕服务器

sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")


def chatgpt(audience_prompt: str):
    """
    :param audience_prompt: 观众提示
    :return: AI完成
    """
    # 向OpenAI API发送请求，获取ChatGPT的回复
    response = openai.Completion.create(
        engine=model_engine,  # engine：指定要使用的模型引擎，即ChatGPT或其他OpenAI提供的预训练模型
        prompt=f"{audience_prompt}",  # prompt：要求模型基于该字符串生成回复
        max_tokens=500,  # max_tokens：生成回复的最大标记数(max:2048)
        n=1,  # n：要生成的回复数量
        stop=None,  # stop：如果生成的回复中出现了该字符串，则表示已完成生成
        temperature=0.5,  # temperature：用于控制生成回复的随机性和多样性的值
    )
    # 获取回复中的文本
    message = response.choices[0].text.strip()
    return message


@room.on('DANMU_MSG')  # 弹幕消息事件回调函数
async def on_danmaku(event):
    """
     获取并处理弹幕消息
    """
    global QuestionList
    global QuestionName
    global LogsList
    content = event["data"]["info"][1]  # 获取弹幕内容
    user_name = event["data"]["info"][2][1]  # 获取用户昵称
    print(f"\033[33m[{user_name}]\033[0m:{content}")  # 打印弹幕信息，名字为黄色
    if not QuestionList.full():
        QuestionName.put(user_name)  # 将用户名放入队列
        QuestionList.put(content)  # 将弹幕消息放入队列
        time1 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        LogsList.put(f"[{time1}] [{user_name}]：{content}")
        print('\033[32mSystem>>\033[0m已将该条弹幕添加入问题队列')
    else:
        print('\033[32mSystem>>\033[0m队列已满，该条弹幕被丢弃')


def ai_response():
    """
    从问题队列中提取一条，生成回复并存入回复队列中
    """
    global is_ai_ready
    global QuestionList
    global AnswerList
    global QuestionName
    global LogsList
    prompt = QuestionList.get()
    user_name = QuestionName.get()
    ques = LogsList.get()
    response = chatgpt(prompt)
    answer = f'回复{user_name}：{response}'
    AnswerList.put(answer)
    current_question_count = QuestionList.qsize()
    print(f'\033[32mSystem>>\033[0m[{user_name}]的回复已存入队列，当前剩余问题数:{current_question_count}')
    time2 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("./logs.txt", "a", encoding="utf-8") as f:  # 将问答写入logs
        f.write(f"{ques}\n[{time2}] {answer}\n========================================================\n")
    is_ai_ready = True  # 指示AI已经准备好回复下一个问题


def check_answer():
    """
    如果AI没有在生成回复且队列中还有问题 则创建一个生成的线程
    """
    global is_ai_ready
    global QuestionList
    global AnswerList
    if not QuestionList.empty() and is_ai_ready:
        is_ai_ready = False
        answers_thread = threading.Thread(target=ai_response())
        answers_thread.start()


def tts_generate():
    """
    从回复队列中提取一条，通过edge-tts生成AudioCount编号对应的语音
    """
    global is_tts_ready
    global AnswerList
    global MpvList
    global AudioCount
    response = AnswerList.get()
    print(f"\033[31m[ChatGPT]\033[0m{response}")  # 打印AI回复信息
    with open("./output/output.txt", "w", encoding="utf-8") as f:
        f.write(f"{response}")  # 将要读的回复写入临时文件
    subprocess.run(
        f'edge-tts.exe --voice zh-CN-XiaoyiNeural --f .\output\output.txt --write-media .\output\output{AudioCount}.mp3 2>nul',
        shell=True)  # 执行命令行指令
    begin_name = response.find('回复')
    end_name = response.find("：")
    name = response[begin_name + 2:end_name]
    print(f'\033[32mSystem>>\033[0m对[{name}]的回复已成功转换为语音并缓存为output{AudioCount}.mp3')
    MpvList.put(AudioCount)
    AudioCount += 1
    is_tts_ready = True  # 指示TTS已经准备好回复下一个问题


def check_tts():
    """
    如果语音已经放完且队列中还有回复 则创建一个生成并播放TTS的线程
    :return:
    """
    global is_tts_ready
    if not AnswerList.empty() and is_tts_ready:
        is_tts_ready = False
        tts_thread = threading.Thread(target=tts_generate())
        tts_thread.start()


def mpv_read():
    """
    按照MpvList内的名单播放音频直到播放完毕
    :return:
    """
    global MpvList
    global is_mpv_ready
    while not MpvList.empty():
        temp1 = MpvList.get()
        current_mpvlist_count = MpvList.qsize()
        print(f'\033[32mSystem>>\033[0m开始播放output{temp1}.mp3，当前待播语音数：{current_mpvlist_count}')
        subprocess.run(f'mpv.exe -vo null .\output\output{temp1}.mp3 1>nul', shell=True)  # 执行命令行指令
        subprocess.run(f'del /f .\output\output{temp1}.mp3 1>nul', shell=True)
    is_mpv_ready = True


def check_mpv():
    """
    若mpv已经播放完毕且播放列表中有数据 则创建一个播放音频的线程
    :return:
    """
    global is_mpv_ready
    global MpvList
    if not MpvList.empty() and is_mpv_ready:
        is_mpv_ready = False
        tts_thread = threading.Thread(target=mpv_read())
        tts_thread.start()


def main():
    sched1.add_job(check_answer, 'interval', seconds=1, id=f'answer', max_instances=4)
    sched1.add_job(check_tts, 'interval', seconds=1, id=f'tts', max_instances=4)
    sched1.add_job(check_mpv, 'interval', seconds=1, id=f'mpv', max_instances=4)
    sched1.start()
    sync(room.connect())  # 开始监听弹幕流


if __name__ == '__main__':
    main()
