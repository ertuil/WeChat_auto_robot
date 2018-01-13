
__author__ = 'ertuil'
__version__ = '0.0.1'

########################################################################
########## import ######################################################
########################################################################

import itchat
import time
import re
import requests
import threading
import shutil  
import os

########################################################################
########## Config ######################################################
########################################################################

'''
配置模块，用于设置常用变量
'''

robot_on = True    # 开启智能机器人
group_on = True    # 机器人群聊开关
retrieve_on = True # 撤回消息记录          
api_url = 'http://www.tuling123.com/openapi/api'
apikey = '7047e78c39ed424ead5948a0b1dd78cd'
robot_name = '英梨梨'     # 机器人名称
self_name = '那天去'      # 自己的名字
call_name = '呐'         # 对客称呼
max_list = 3            # 新闻、菜谱的条目数

event_time = 3600        # 循环发送介绍信息！   



self_local = '芜湖'       # 查询天气的地点
ask_list = ['你好你好','三人行必有我聊天'] # 发送每日关心的群列表
ask_time = 6 # 推送每日天气和新闻等时间
 
known_names = []
is_on = True

########################################################################
########## utils #######################################################
########################################################################

def self_command(cmds):
    '''
    这里是用于通过微信给自己发送指令，控制机器人的开关等。
    '''
    flag = True
    global is_on
    global robot_on
    global group_on
    global retrieve_on
    if cmds == '退出':
        is_on = False
        quit_app()
        logs('控制 退出')
    elif cmds == '启动':
        robot_on = True
        logs('控制 robot：\t'+str(robot_on))
    elif cmds == '关闭':
        robot_on = False
        logs('控制 robot：\t'+str(robot_on))
    elif cmds == '群聊启动':
        group_on = True
        logs('控制 group：\t'+str(group_on))
    elif cmds == '群聊关闭':
        group_on = False
        logs('控制 group：\t'+str(group_on))
    elif cmds == '记录启动':
        retrieve_on = True
        logs('控制 retrieve：\t'+str(retrieve_on))
    elif cmds == '记录关闭':
        retrieve_on = False
        logs('控制 retrieve：\t'+str(retrieve_on))
    elif cmds == '清理缓存':
        clear_cache()
        logs('控制 清理缓存')
    elif cmds == '问候':
        sent_hello()
    else :
        flag = False
    return flag
    

def logs(obg):
    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+'\t'+obg)

def clear_cache():
    '''
    清楚本地缓存的照片、等。
    '''
    shutil.rmtree('./tmp')  
    os.mkdir('./tmp')  


def clear_list():
    logs('Clearing list')
    known_names.clear()



########################################################################
########## events ######################################################
########################################################################

'''
事件轮讯机制
'''

def events():
    '''
    基于事件间隔的事件循环机制，定时清楚访问列表，每天定时推送天气等
    '''
    global timer
    global is_on
    clear_list()
    if int(time.strftime("%H", time.localtime())) == ask_time:
        sent_hello()
    if is_on:
        timer = threading.Timer(event_time, events)
        timer.start()

def quit_app():
    '''
    接收到退出信号，关闭定时器，注销微信
    '''
    global timer
    timer.cancel()
    itchat.logout()

########################################################################
########## robot  ######################################################
########################################################################

'''
图灵服务器等接口
'''

def get_response(msg, user_id,loc = ''):
    '''
    调用图灵机器人、并解析结果的返回的json。
    参数:     msg:传入的文本
             user_id: 用户id
             loc：可选、位置信息
             返回：一个带有对话内容的list数组
    '''

    data = {'key': apikey,
            'info': msg,
            'userid': user_id
            }
    if not loc == '':
        data['loc'] = loc
    logs(str(data))
    try:
        req = requests.post(api_url, data=data).json()
    except:
        return ''

    code = req.get('code')
    logs(str(req))

    text = re.sub('^亲',call_name,req.get('text'))

    if code == 100000 :
        return (robot_name+"(小助手):"+text,)
    elif code == 200000:
        return robot_name+"(小助手):"+text , req.get('url')
    elif code == 302000:
        ans = [robot_name+"(小助手):"+text,]
        news = req.get('list')
        idx = 0
        while idx < len(news) and idx < max_list:
            ans.append(news[idx]['article']+":"+news[idx]['detailurl'])
            idx += 1
        return ans
    elif code == 308000:
        ans = [robot_name+"(小助手):"+text,]
        news = req.get('list')
        idx = 0
        while idx < len(news) and idx < max_list:
            ans.append(news[idx]['name']+"\t:"+news[idx]['info']+"\t详见\t:"+news[idx]['detailurl'])
            idx += 1
        return ans
    elif code == 40004:
        return robot_name+"(小助手):今天我累了，休息休息～～"
    else :
        return robot_name+"(小助手):发生了不可明状的错误"


def init_info(user_name,is_group = False):
    '''
    如果是第一次启动机器人，返回一个小介绍
    '''

    if user_name not in known_names:
        if is_group == False and itchat.search_friends(userName=user_name)['NickName'] == self_name:
            itchat.send(robot_name+"(小助手):我是 "+self_name+" 的专属智能小助手 "+robot_name+" 。主人现在不在线，就由我来为您提供服务！",'filehelper')
        else:
            itchat.send(robot_name+"(小助手):我是 "+self_name+" 的专属智能小助手 "+robot_name+" 。主人现在不在线，就由我来为您提供服务!",user_name)
            if is_group:
                itchat.send('各位可以@我，来和我对话哦！！我可以查询天气、新闻……',user_name)
        known_names.append(user_name)

########################################################################
########## retrieve ####################################################
########################################################################

'''
用于监控撤销消息
'''

records = {}

def save_msg(user_name,msg):
    '''
    保存所有的文本资料
    '''
    if user_name not in records:
        records[user_name] = [msg,]
    else:
        records[user_name].append(msg)

def retr_msg(user_name):
    '''
    查找撤回的内容
    '''
    try:
        req = records[user_name].pop()
        return itchat.search_friends(userName=user_name)['NickName'] + '撤回了消息:\t'+req['Content']
    except:
        pass

########################################################################
########## news ########################################################
########################################################################

def new_day():
    ans = []
    data = {'key': apikey,
        'info': self_local+'天气',
        'userid': 'root'
    }

    req = requests.post(api_url, data=data).json()
    text = re.sub('^亲',call_name,req.get('text'))
    ans.append(robot_name+"(小助手):今天的天气:"+text)

    data = {'key': apikey,
        'info': '新闻',
        'userid': 'root'
    }
    req = requests.post(api_url, data=data).json()
    news = req.get('list')
    idx = 0
    while idx < len(news) and idx < max_list:
        ans.append(news[idx]['article']+":"+news[idx]['detailurl'])
        idx += 1
    return ans

def sent_hello():
    infos = new_day()
    for chatroom in ask_list:
        for info in infos:
            itchat.send(info,itchat.search_chatrooms(name=chatroom)[0]['UserName'])


########################################################################
########## wechat register #############################################
########################################################################

'''
注册微信消息，给出应答
'''

@itchat.msg_register(['Note'])
def auto_retreive(msg):
    if re.search("\[.*撤回了一条消息\]", msg['Content']) and retrieve_on:
        reqs = retr_msg(msg['FromUserName'])
        itchat.send(reqs,'filehelper')

@itchat.msg_register(['Text', 'Map', 'Card', 'Sharing'])
def Tuling_robot(msg):
    if itchat.search_friends(userName=msg['FromUserName'])['NickName'] == self_name:
        if self_command(msg['Content']) :
            return 

    if retrieve_on:
        save_msg(msg['FromUserName'],msg)

    if robot_on:
        init_info(msg['FromUserName'])
        loc = ''
        if msg['Type'] == 'Map':
            try:
                loc = re.search('poiname=\"(.*)\"',msg['OriContent']).group(1)
                msg['Content'] = '在这里'
            except:
                loc = ''
        respones = get_response(msg['Content'], msg['FromUserName'],loc)
        
        if itchat.search_friends(userName=msg['FromUserName'])['NickName'] == self_name:
            for info in respones:
                itchat.send(info, toUserName='filehelper')
        else:
            for info in respones:
                itchat.send(info, msg['FromUserName'])

@itchat.msg_register(['Picture', 'Recording', 'Attachment', 'Video'])
def download_files(msg):
    filename = './tmp/'+msg['FileName']
    msg["Text"](filename)
    itchat.send(itchat.search_friends(userName=msg['FromUserName'])['NickName']+" 发送了一个"+ msg['Type'],'filehelper')
    if msg['Type'] == 'Picture':
        itchat.send("@img@"+filename,'filehelper')
    elif msg['Type'] == 'Video':
        itchat.send("@vid@"+filename,'filehelper')
    else:
        itchat.send("@fil@"+filename,'filehelper')
        
    if robot_on:
        init_info(msg['FromUserName'])
        if itchat.search_friends(userName=msg['FromUserName'])['NickName'] == self_name:
            itchat.send(robot_name+"(小助手):主人已经收到了这个文件！", 'filehelper')
        else:
            itchat.send(robot_name+"(小助手):主人已经收到了这个文件！", msg['FromUserName'])

@itchat.msg_register(['Text', 'Map', 'Card', 'Sharing'], isGroupChat=True)
def group_reply(msg):
    if msg['isAt'] and group_on and robot_on:
        init_info(msg['FromUserName'],is_group = True)
        loc = ''
        if msg['Type'] == 'Map':
            try:
                loc = re.search('poiname=\"(.*)\"',msg['OriContent']).group(1)
                msg['Content'] = '查看这里'
            except:
                loc = ''
        respones = get_response(msg['Content'], msg['FromUserName'],loc)

        itchat.send("@%s"%msg['ActualNickName'],msg['FromUserName'])

        for info in respones:
            itchat.send(info, msg['FromUserName'])

@itchat.msg_register(['Text', 'Map', 'Card', 'Sharing'],isMpChat =True)
def mp_robot(msg):
    if robot_on and group_on:
        init_info(msg['FromUserName'],True)
        loc = ''
        if msg['Type'] == 'Map':
            try:
                loc = re.search('poiname=\"(.*)\"',msg['OriContent']).group(1)
                msg['Content'] = '在这里'
            except:
                loc = ''
        respones = get_response(msg['Content'], msg['FromUserName'],loc)
        for info in respones:
            itchat.send(info, msg['FromUserName'])


########################################################################
########## itchat run ##################################################
########################################################################

if __name__ == '__main__':
    timer = threading.Timer( 1 , events)
    timer.start()
    itchat.auto_login(hotReload=True,enableCmdQR=2)
    itchat.run()