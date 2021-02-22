# bot.py

import asyncio
import contextlib
import html
import json
import re
import socket
import struct
import threading
import time
import urllib.parse
import urllib.request
import uuid
import yaml

from aiocqhttp import CQHttp, Event


def getDefaultConfig():
    __doc__ = """
    # Provides the default configuration for the plugin.
motd:
    servers:
        本地服务器(localhost):
            [127.0.0.1, 19132]
        lifeboat:
            [play.lbsg.net, 19132]
    aliases:
        - 查服
        - "!motdbe"
        - Hey bot, Tell me the Message of the Day for a Minecraft Bedrock server which is located at
    hintformat:
        "用法：\\n{alias} [--help|-?]\\n{alias} <服务器地址>:[端口]\\n{alias} <服务器别名>\\n{alias} --list"
        # "Usage：\\n{alias} [--help|-?]\\n{alias} <ServerIP>:[ServerPort]\\n{alias} <ServerAlias>\\n{alias} --list"
    returnformat:
        "{motd}({subMotd})\\n版本：{version}({protocolVersion})\\n在线玩家：{playerCount}/{maximumPlayerCount}"
        # "{motd}({subMotd})\\nVersion：{version}({protocolVersion})\\nPlayers：{playerCount}/{maximumPlayerCount}"
    errorsformat:
        addressInvalid: "错误：服务器地址无效。"   # "Error: invalid server address"
        timeout: "错误：服务器超时。"   # "Error: timeout"
        generic: "错误：{error}"   # "Error: {error}"
    
xhsock:
    servers_groups_map:
        #375546131: # GroupID
        #    HOST: "a.remote.host"
        #    PORT: 8989
        #    nHOST: "0.0.0.0"
        #    nPORT: 8969
        #    name: "QQ聊天" # "QQChat"
    errorsformat:    
        messageIsTooLong: "消息过长，请分开发送" # "The message is too long, please split it apart and send it again."
    
    """
    configDefault = yaml.load(__doc__,Loader=yaml.SafeLoader)
    assert(isinstance(configDefault,dict))
    return configDefault

def createConfigYaml(fileHandle):
    config = getDefaultConfig()
    fileHandle.write(yaml.dump(config,allow_unicode=True))
    fileHandle.close()
    return config

def loadConfigFromYaml(fileHandle):
    return yaml.load(fileHandle.read(),Loader=yaml.SafeLoader)




async def motdPE(HOST,PORT=19132):
    #HOST,PORT=input("Server:").split(":")
    #PORT=int(PORT)
    logger=print
    
    OFFLINE_MESSAGE_DATA_ID = struct.pack("16s",bytes([0x00, 0xFF, 0xFF, 0x00, 0xFE, 0xFE, 0xFE, 0xFE, 0xFD, 0xFD, 0xFD, 0xFD, 0x12, 0x34, 0x56, 0x78]))
    command=b"\x01"+struct.pack('Q', int(time.time())) + OFFLINE_MESSAGE_DATA_ID + struct.pack("Q",2)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        sock.sendto(command, (HOST, PORT))    
        received = sock.recvfrom(1024)
    logger("Received: {}".format(received))
    logger(received[0][0:1]==b"\x1C")
    logger(received[0][17:33]==OFFLINE_MESSAGE_DATA_ID)
    #CQP.addLog(CQP.AC, CQP.CQLOG_INFOSEND, 'MC Motdpe',f"{received[0][35:].decode('utf-8',errors='replace')},{received[1]}")
    try:
        recSeries=received[0][35:].decode("UTF-8").split(";")
    except:
        recSeries=received[0][35:].decode("GBK").split(";")
    logger(recSeries)
    
    recjson=json.dumps({
    	#"serverIp":received[1][0],
    	"edition":recSeries[0] if len(recSeries)>0 else "",
    	"motd":recSeries[1] if len(recSeries)>1 else "",
    	"protocolVersion":int(recSeries[2]) if len(recSeries)>2 else 0,
    	"version":recSeries[3]if len(recSeries)>3 else "",
    	"playerCount":int(recSeries[4]) if len(recSeries)>4 else 0,
    	"maximumPlayerCount":int(recSeries[5]) if len(recSeries)>5 else 0,
    	"serverId":int(recSeries[6]) if len(recSeries)>6 else 0,
    	"subMotd":recSeries[7] if len(recSeries)>7 else "",
    	"gameType":recSeries[8] if len(recSeries)>8 else "",
    	"nintendoLimited":bool(recSeries[9]) if len(recSeries)>9 else False,
    	"ipv4Port":int(recSeries[10]) if len(recSeries)>10 else None,
    	"ipv6Port":int(recSeries[11]) if len(recSeries)>11 else None
    },
    indent=4, sort_keys=False, ensure_ascii=False)
    return recjson

def motdF(mj):
    md=json.loads(mj)
    motda=config["motd"]["returnformat"].format(**md)

    return motda



class chatDT:
    def __init__(self,HOST,PORT,nHOST,nPORT,name,coding="gbk"):
        self.HOST,self.PORT=HOST,PORT
        self.nHOST,self.nPORT=nHOST,nPORT
        self.coding=coding
        self.uid=uuid.uuid4()
        self.name=name
        self.remIP=(HOST, PORT)
        self.locIP=(nHOST,nPORT)
        
    async def __aenter__(self):
        #loop = asyncio.get_running_loop()
        #self.transport,self.protocol = loop.create_datagram_endpoint(protocol_factory)
        self.sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.locIP)
        #self.sock.setblocking(0)	
        self.reg()
        return self
    async def __aexit__(self,*args):
        self.unreg()
        self.sock.close()
        
    def logger(self,s):
        print(s)
    def timeStamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    def packConstructor(self,method,msg=None):
        if msg and method=="msg":
            return bytes(f"CMD=msg,KEY={self.uid},MSG=[{self.timeStamp()} Chat] {msg}", self.coding)
        elif method=="listall":
            return bytes(f"CMD=msg,KEY={self.uid},MSG=[{self.timeStamp()} Chat] 玩家 ListBot 说:Listall执行\nlistd", self.coding)
        else:
            return bytes(f"CMD={method},PORT={self.nPORT},KEY={self.uid},NAME={self.name}" , self.coding)
    
    def reg(self):
        self.sock.sendto(self.packConstructor("reg"), self.remIP)
    def unreg(self):
        self.sock.sendto(self.packConstructor("unreg"), self.remIP)
    def sendMsg(self,msg):
        self.sock.sendto(self.packConstructor("msg",msg),self.remIP)
    def listAll(self):
        pass#self.sock.sendto(self.packConstructor("listall"),self.remIP)



bot = CQHttp()


@bot.on_message('private')
@bot.on_message('group')
async def _(event: Event):
    #await bot.send(event, '你发了：')
    #return {'reply': event.message}
    msg = event.message
    serverList=config["motd"]["servers"]
    syntaxHint=config["motd"]["hintformat"]
    errors = config["motd"]["errorsformat"]
    if msg == "查服" or msg=="查服 --help" or msg=="查服 -?" or msg=="查服 ":
        await bot.send(event, f"{syntaxHint}")
    elif msg[:3] =="查服 ":
        showAddr=False
        try:
            try:H,P=msg[3:].split(":")
            except:H,P=msg[3:],None
            if msg[3:] in serverList.keys():
                H,P=serverList[msg[3:]]
                showAddr=True
            if msg[3:] == "--list":
                await bot.send(event, f"{' '.join(serverList.keys())}")
                return None
            motdres= await motdPE(H,PORT=int(P) if P else 19132)
            if not showAddr:
                await bot.send(event, f"{motdF(motdres)}")
            else:
                await bot.send(event, f"地址：{H}:{P}\n{motdF(motdres)}")
            
        except socket.timeout:
            await bot.send(event, errors["timeout"])
        except socket.gaierror:
            await bot.send(event, errors["addressInvalid"])

        except Exception as e:
            await bot.send(event, errors["generic"].format(error = repr(e)))
        return None

@bot.on_message('group')
async def _chat(event: Event):
        async def Q2nick(r):
            try:
                info = await bot.get_group_member_info(group_id=event.group_id,user_id=event.user_id)
                fromOne = info['card']
            #if str(r) in Q2Nick.keys():
            #    fromOne=Q2Nick[str(r)]
            #else:fromOne=str(r)
            except Exception as e:
                print(repr(e))
                fromOne = str(r)
            return fromOne
    
        def faceRepl(result):
            try:
                r=int(re.search(r'id=(\d+)',result.group()).group(1))#CQP.addLog(CQP.AC, CQP.CQLOG_INFOSEND, 'MC聊天发送机器人',r)
                d={0:'惊讶',1:'撇嘴',2:'色',3:'发呆',4:'得意',5:'流泪',6:'害羞',7:'闭嘴',8:'睡',9:'大哭',10:'尴尬',11:'发怒',12:'调皮',13:'呲牙',14:'微笑',15:'难过',16:'酷',18:'抓狂',19:'吐',20:'偷笑',21:'可爱',22:'白眼',23:'傲慢',24:'饥饿',25:'困',26:'惊恐',27:'流汗',28:'憨笑',29:'大兵',30:'奋斗',31:'咒骂',32:'疑问',34:'晕',35:'折磨',36:'衰',37:'骷髅',38:'敲打',39:'再见',41:'发抖',42:'爱情',43:'跳跳',46:'猪头',49:'拥抱',53:'蛋糕',54:'闪电',55:'炸弹',56:'刀',57:'足球',59:'便便',60:'咖啡',61:'饭',63:'玫瑰',64:'凋谢',66:'爱心',67:'心碎',69:'礼物',74:'太阳',75:'月亮',76:'强',77:'弱',78:'握手',79:'胜利',85:'飞吻',86:'怄火',89:'西瓜',96:'冷汗',97:'擦汗',98:'抠鼻',99:'鼓掌',100:'糗大了',101:'坏笑',102:'左哼哼',103:'右哼哼',104:'哈欠',105:'鄙视',106:'委屈',107:'快哭了',108:'阴险',109:'亲亲',110:'吓',111:'可怜',112:'菜刀',113:'啤酒',114:'篮球',115:'乒乓',116:'示爱',117:'瓢虫',118:'抱拳',119:'勾引',120:'拳头',121:'差劲',122:'爱你',123:'不',124:'好',125:'转圈',126:'磕头',127:'回头',128:'跳绳',129:'挥手',130:'激动',131:'街舞',132:'献吻',133:'左太极',134:'右太极',136:'双喜',137:'鞭炮',138:'灯笼',139:'发财',140:'K歌',141:'购物',142:'邮件',143:'帅',144:'喝彩',145:'祈祷',146:'爆筋',147:'棒棒糖',148:'喝奶',149:'下面',150:'香蕉',151:'飞机',152:'开车',153:'高铁左车头',154:'车厢',155:'高铁右车头',156:'多云',157:'下雨',158:'钞票',159:'熊猫',160:'灯泡',161:'风车',162:'闹钟',163:'打伞',164:'彩球',165:'钻戒',166:'沙发',167:'纸巾',168:'药',169:'手枪',170:'青蛙',171:'茶',172:'眨眼睛',173:'泪奔',174:'无奈',175:'卖萌',176:'小纠结',177:'喷血',178:'斜眼笑',179:'doge',180:'惊喜',181:'骚扰',182:'笑哭',183:'我最美',184:'河蟹',185:'羊驼',186:'栗子',187:'幽灵',188:'蛋',189:'马赛克',190:'菊花',191:'肥皂',192:'红包',193:'大笑',194:'不开心',195:'啊',196:'惶恐',197:'冷漠',198:'呃',199:'好棒',200:'拜托',201:'点赞',202:'无 聊',203:'托脸',204:'吃',205:'送花',206:'害怕',207:'花痴',208:'小样儿',209:'脸红',210:'飙泪',211:'我不看',212:'托腮',213:'哇哦',214:'啵啵',215:'糊脸',216:'拍头',217:'扯一扯',218:'舔一舔',219:'蹭一蹭',220:'拽炸天',221:'顶呱呱',222:'抱抱',223:'暴击',224:'开枪',225:'撩一撩',226:'拍桌',227:'拍手',228:'恭喜',229:'干杯',230:'嘲讽',231:'哼',232:'佛系',233:'掐 一掐',234:'惊呆',235:'颤抖',236:'啃头',237:'偷看',238:'扇脸',239:'原谅',240:'喷脸',241:'生日快乐'}
                if r in d.keys():
                    faceStr=d[r]
                else: faceStr = str(f"#{r}")
                return f"[/{faceStr}]"
            except:#CQP.addLog(CQP.AC, CQP.CQLOG_INFOSEND, 'MC聊天发送机器人',result.group())
                return result.group()
        def atRepl(result):
            try:
                r=int(re.search(r'qq=(\d+)',result.group()).group(1))#CQP.addLog(CQP.AC, CQP.CQLOG_INFOSEND, 'MC聊天发送机器人',r)
                ID=r#Q2nick(r)
                #print(ID)
                return f"@{ID}"
            except:
                #print('MC聊天发送机器人',result.group())
                return result.group()
        global qunids
        if event.group_id in qunids:
            msg = event.message
            qunindex=qunids.index(event.group_id)
            msgd=re.sub("\[CQ:.*\]","[]",msg)
            if len(msgd)>=200:
                await bot.send(event, config["xhsock"]["errorsformat"]["messageIsTooLong"],at_sender=True)
                await bot.deleteMsg(message_id=event.message_id)
                return None
                
            for msgs in msg.split("\r\n"):
                #CQP.addLog(CQP.AC, CQP.CQLOG_INFOSEND,'MC聊天发送机器人',str(CQP.getGroupMemberList(CQP.AC,DTGroup) ))
                msgs=re.sub(r'(\[CQ:image,file=.*?\])',"[图片]",msgs)
                msgs=re.sub(r'(\[CQ:face,id=[0-9]*?\])',faceRepl,msgs)
                msgs=re.sub(r'(\[CQ:at,qq=[0-9]*?\])',atRepl,msgs)
                msgs=re.sub("\[CQ:.*\]","[未支持消息]",msgs)
            
                print('MC聊天发送机器人',f"收到群消息")
                fromOne=await Q2nick(event.user_id)
                print(fromOne)
                css[qunindex].sendMsg(f"玩家 {fromOne} 说:{msgs}")
                print('MC聊天发送机器人',f"发送“{msgs}”到远端")    
        return None

@bot.on_request('group')
async def beInvitedToGroup(event: Event):
    return {"approve":True}

@bot.on_meta_event('lifecycle.connect')
async def botInit(event: Event):
    global css,qunids
    print("机器人初始化。")
    servermap = config["xhsock"]["servers_groups_map"]
    qunids=servermap.keys()
    argsd=servermap.values()
    
    def recvSend(loop,cs,qunid):
        while 1:
            #try:
                chattext = cs.sock.recvfrom(1024)[0].decode(cs.coding,errors="replace")
                print('MC聊天发送机器人',"收到事件")
                headerret=re.search("MSG=(.*)",chattext)
                if headerret:
                    event.group_id = qunid
                    loop.create_task(bot.send(event, headerret.group(1)))
            #except Exception as e:
            #    print('MC聊天发送机器人',f"错误：{repr(e)}")
    async with contextlib.AsyncExitStack() as aes:
        css = [await aes.enter_async_context(chatDT(*argsd[i].values())) for i in range(len(argsd))]
        loop = asyncio.get_running_loop()
        for i in range(len(css)):
            #await loop.create_task(recvSend(css[i],qunids[i]))
            recvWork=threading.Thread(target=recvSend,args=(loop,css[i],qunids[i]))
            recvWork.start()
        while 1:
            await asyncio.sleep(60)


        



if __name__ == "__main__":
    try:
        configFile = open("config.yml","r")
        if not len(configFile.read()): raise IOError
    except IOError:
        configFile = createConfigYaml(open("config.yml","w"))
    else:
        config = loadConfigFromYaml(configFile)
    bot.run(host='127.0.0.1', port=5700)
