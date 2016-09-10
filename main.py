#! /usr/bin/env python
# coding=utf-8
import json
import random
import sys
import traceback

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer

reload(sys)
sys.setdefaultencoding('utf8')

# 词库
words = '大象，敲门，西瓜，举重，手机，打嗝，牙疼，嗑瓜子，蹲下，灭火器，孙悟空，猩猩，吃面条，香蕉，拍球，拳击，睡觉，' + \
        '打麻将，雨伞，主持人，刮胡子，刷牙，企鹅，乒乓球，唇膏，武术，看书，洗头，流口水，升国旗，长颈鹿，公鸡，鸭子，' + \
        '跳舞，游泳，榴莲，遛狗，害羞，喝水，扔铅球，遥控器，高跟鞋，眼睫毛，拍马屁，剪指甲，猪，眼镜，跨栏，握手，蝴蝶，' + \
        '骑马，跳绳，广播体操，求婚，系鞋带，喷香水，兔子，跑步，篮球，电话，洗澡，拔河，扭秧歌，照镜子，奥特曼，捡钱包，' + \
        '放风筝，老鹰，金鸡独立，鸡犬不宁，垂头丧气，一刀两断，哑口无言，左顾右盼，直升飞机，东张西望，三长两短，心口如一，' + \
        '大摇大摆，龟兔赛跑，目瞪口呆，破涕为笑，眉飞色舞，满地找牙，五体投地，一无所有，睡眼朦胧，比翼双飞，大眼瞪小眼，' + \
        '一瘸一拐，闻鸡起舞，一手遮天，捧腹大笑，心急如焚，狼吞虎咽，花枝招展，七零八落，鸡飞狗跳，张牙舞爪，抓耳挠腮，' + \
        '嬉皮笑脸，连滚带爬，掩耳盗铃，手忙脚乱，手舞足蹈，张牙舞爪，婀娜多姿，挥汗如雨，纸上谈兵，含情脉脉，望梅止渴，' + \
        '一针见血，大手大脚，左右为难，虎头蛇尾，一分为二，回眸一笑，恍然大悟，上蹿下跳，狗急跳墙，画饼充饥，晕头转向，' + \
        '七上八下，白鸽，布娃娃，餐巾，仓库，瓷器，长江三峡，长颈漏斗，除草剂，大树，大头鱼，刀，冬瓜，豆沙包，耳，' + \
        '耳机，飞碟，工资，荷花，烘干机，虎，蝴蝶，护膝，花朵，环保，击剑，监狱，教师，结婚证，空格键，KTV，篮球架，' + \
        '刘翔，棉花，母亲，牛奶糖，牛肉干，牛肉面，全家桶，沙僧，圣经，升旗，实验室，狮子座，守门员，首饰，手套，水波，' + \
        '土豆，丸子，网址，鲜橙多，鲜花，小霸王，腰带，烟斗，扬州炒饭，衣橱，医生，音响，鹦鹉，油，语文书，针筒，纸杯，钻戒，' + \
        '抱头鼠窜，鸡鸣狗盗，头破血流，坐井观天，眼高手低，目瞪口呆，胸无点墨，鸡飞狗跳，鼠目寸光，盲人摸象，画蛇添足，' + \
        '画龙点睛，抱头鼠窜，狗急跳墙，虎背熊腰，守株待兔，亡羊补牢，对牛弹琴，如鱼得水，打草惊蛇，打草惊蛇，走马观花，三头六臂，' + \
        '白蚁，画廊，樱桃，胡子，猪脚，鞋架，夜晚，恶魔，洋葱，剑道，蚊帐，眼镜，宝岛，卡通，母亲，漩涡，香菇，长江，礼帽，火鸡，' + \
        '虫子，水饺，猛男，照片，地板，乌龟，床罩，犀牛，瓶子，鸵鸟，痔疮，拥抱，相框，卷纸，工资，世界，江南，漫画，眼霜，水表，' + \
        '举重，衙门，和尚，椰树，性感，伪娘，泡泡，宝石，宠物，叮当，衣领，猩猩，广告，升旗，毛豆，白宫，菜包，饼干，芹菜，国画，' + \
        '熨斗，星星，空调，熊掌，婴儿，键盘，排骨，济南，课桌，奥运，披风，金鱼，白领，包子，冬瓜，坐标，算盘，阀门，鹦鹉，公安，' + \
        '电阻，国王，邮票，床单，下载，海藻，弹簧，空气，跳伞，米饭，刀叉，书生，铁锹，名字，牧场，泡沫，书房，扇子，蜡笔，凤梨，' + \
        '轮椅，蜡烛，面包，菜刀，酒店，宾馆，山丘，眼线，背心，墨镜，织女，奥迪，干冰，数学，宿舍，叉子，沙漠，黑猫，苦瓜，音响，' + \
        '罗盘，七夕，股票，皮带，电影，公牛，秃顶，双杠，老鼠，袋鼠，春天，关羽，海豚，面板，板栗，茶叶，杯具，泰山，网络，鱼缸，' + \
        '信鸽，主机，黑板，桌球，跳绳，台球，扫帚，盖帽，杯子，美术，色眼，口红，漏水，鞭炮，榴莲，上衣，汤勺，赤壁，刺猬，大炮，' + \
        '龙虾，跳舞，树木，枫树，烟斗，轮船，丸子，海象，屏风，花架，会计，索尼，观音，薯片，李宁，天线，电车，围棋，鸽子，牙套，' + \
        '石头，神话，纽扣，食物，发带，拐杖，农村，界面，春联，茶树，唱片，手铐，毛皮，滑雪，古筝，长城，火炉，木耳，羊驼，生物，' + \
        '大蒜，名片，烟灰，拖把，栈桥，礼服，菊花，律师，绵羊，新浪，冰鞋，气球，海浪，阳台，摆饰，魂斗罗，鸭嘴帽，台湾岛，洋娃娃，' + \
        '布娃娃，显示器，显示屏，倚天剑，屠龙刀，天花板，水仙花，彼岸花，刘德华，玫瑰花，棒球帽，棒球棒，指南针，阿童木，大头鱼，' + \
        '银河系，呼啦圈，史莱克，史瑞克，绿巨人，三角架，猪鼻子，鹰钩鼻，美人痣，黑眼圈，熊猫眼，签字笔，史泰龙，煤气炉，元宵节，' + \
        '电饭锅，贺年卡，原子弹，包青天，老婆饼，老夫子，铁观音，明信片，鸭嘴兽，四不像，罗汉果，贝迷会，西红柿，钥匙扣，鼠标垫，' + \
        '游泳衣，登山包，栀子花，臭豆腐，鸡脆骨，康乃馨，游泳圈，毛毛虫，照妖镜，史努比，牛仔裤，公文包，日全食，上网本，水蜜桃，' + \
        '张三丰，椰汁，椰子汁，芭蕉扇，白头翁，手提袋，纯爷们，木乃伊，娃娃鱼，氧气瓶，折叠床，蝙蝠侠，金饭碗，贵妃椅，触摸屏，' + \
        '单人床，摄像头，曾轶可，月季花，百合花，含羞草，电影院，方便面，量角器，圆周率，丘比特，香蕉皮，旅游鞋，游戏机，加勒比，' + \
        '接力棒，乌纱帽，三文治，二人转，广告牌，录音机，嘻哈猴，青春痘，空格键，二郎神，按摩椅，沐浴露，调味品，纪念品，纪念帽，' + \
        '登山杖，登山鞋，爆米花，火腿肠，五行山，五指山，科学馆，传呼机，热气球，红绿灯，宝莲灯，招财猫，红楼梦，大熊座，圣诞树，' + \
        '计算机，乒乓球，私家车，人马座，进化论，发动机，毕业证，干衣机，打印机，纸巾盒，金丝猴，北斗星，梅花鹿，落地窗，豆沙包，' + \
        '衣帽架，调色盘，脚趾甲，音乐盒，狙击枪，穿山甲，打印纸，烤鱿鱼，蓝精灵，日月潭，热带鱼，仙人球，巡洋舰，仙女座'
word_arr = words.split('，')
arr_len = len(word_arr)


# 分配词语
def generate_word():
    index = random.randint(0, arr_len - 1)
    return word_arr[index]

# 数据库配置
DB_HOST = '139.129.4.219'
DB_USER = 'draw_and_guess'
DB_PWD = 'dng2744394782'
DB_NAME = 'draw_and_guess'
Base = declarative_base()
engine = create_engine('mysql://%s:%s@%s/%s?charset=utf8' % (DB_USER, DB_PWD, DB_HOST, DB_NAME), encoding='utf-8',
                       echo=False,
                       pool_size=100, pool_recycle=10)
db = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=True, expire_on_commit=False))
max_round = 3


# 房间ORM
class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)  # 房间号
    state = Column(Integer)  # 房间状态, 0已创建, 1游戏中
    round = Column(Integer)  # 轮数, 0未开始, 1第一轮, 2第二轮, 以此类推
    curr_word = Column(String)  # 当前词语


# 用户ORM
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # 用户号
    ip = Column(String)  # 用户ip地址
    nick = Column(String)  # 用户昵称
    room = Column(Integer)  # 用户所在房间号
    state = Column(Integer)  # 用户状态, 0非房主, 1房主, 2擂主中, 3攻擂中
    win = Column(Integer)  # 猜对状态, 0未猜对, 1已猜对


# 服务器逻辑
class Connection(object):
    # 静态列表, 保存所有连接
    clients = list()

    # 新用户连接
    def __init__(self, stream, address):

        # 挤掉重复ip的连接以防bug
        for client in Connection.clients:
            if client.address == address[0]:
                client.send_json({'event': 'ip_duplicate'})
                client.on_close()

        # 注册连接
        Connection.clients.append(self)
        print address[0] + '\t = [CONNECTED] Total clients: ' + str(len(Connection.clients))

        self._stream = stream
        self.address = str(address)
        self._stream.set_close_callback(self.on_close)
        self.read_message()

    # 收到消息的分配
    def read_message(self):
        self._stream.read_until('\n', self.handle_message)

    def has_current_user(self):
        return len(db.query(User).filter(User.ip == self.address).all()) > 0

    def get_current_user(self):
        try:
            return db.query(User).filter(User.ip == self.address).all()[-1]
        except:
            return None

    def has_current_room(self):
        return len(db.query(Room).filter(Room.id == self.get_current_user().room).all()) > 0

    def get_current_room(self):
        try:
            return db.query(Room).filter(Room.id == self.get_current_user().room).all()[-1]
        except:
            return None

    def get_user_nicks_in_current_room(self):
        result = set()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if self.get_current_user() is not None and remote_room == self.get_current_user().room:
                result.add(remote_user.nick)
        _result = list()
        for i in result:
            _result.append(i)
        return _result

    def get_user_nicks_in_room(self, room):
        result = list()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if remote_room == room:
                result.append(remote_user.nick)
        return result

    def get_users_in_current_room(self):
        result = list()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if self.get_current_user() is not None and remote_room == self.get_current_user().room:
                result.append(remote_user)
        return result

    def get_connections_in_current_room(self):
        result = list()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if self.get_current_user() is not None and remote_room == self.get_current_user().room:
                result.append(remote_client)
        return result

    def get_other_connections_in_current_room(self):
        result = list()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if self.get_current_user() is not None and remote_room == self.get_current_user().room and remote_user.id != self.get_current_user().id:
                result.append(remote_client)
        return result

    # 分配到消息的处理
    def handle_message(self, data):
        print self.address + '\t > ' + data.replace('\n', '')
        try:
            json_data = json.loads(data)
            method = json_data['method']

            # 创建房间
            if method == 'create_room':
                print self.address + '\t = [CREATE ROOM]'
                try:
                    nick = json_data['nick']
                    room = Room(state=0, round=0, curr_word="")
                    db.add(room)
                    db.commit()

                    user = User(ip=self.address, nick=nick, room=room.id, state=1, win=0)
                    db.add(user)
                    db.commit()

                    self.send_json({'method': 'create_room', 'success': True, 'room': room.id})
                except Exception as e:
                    print(e)
                    db.rollback()
                    self.send_json(
                        {'method': 'create_room', 'success': False, 'reason': u'连接数据库失败，请重试'})

            # 加入房间
            elif method == 'join_room':
                print self.address + '\t = [JOIN ROOM]'
                try:
                    rooms = db.query(Room).filter(Room.id == json_data['room']).all()
                    if len(rooms) < 1:
                        self.send_json({'method': 'join_room', 'success': False, 'reason': '房间不存在'})
                        self.read_message()  # 进入下次I/O循环
                        return

                    room = rooms[-1]
                    if room.state == 1:
                        self.send_json({'method': 'join_room', 'success': False, 'reason': '该房间已开始游戏'})
                        self.read_message()  # 进入下次I/O循环
                        return

                    nick = json_data['nick']
                    if nick in self.get_user_nicks_in_room(room.id):
                        self.send_json({'method': 'join_room', 'success': False, 'reason': '该房间已有重复昵称，请更换'})
                        self.read_message()  # 进入下次I/O循环
                        return
                    
                    user = User(ip=self.address, nick=nick, room=room.id, state=0, win=0)
                    db.add(user)
                    db.commit()

                    self.send_json(
                        {'method': 'join_room', 'success': True, 'players': self.get_user_nicks_in_current_room()})

                    # 通知其他人有人加入房间
                    for client in self.get_other_connections_in_current_room():
                        client.send_json({'event': 'user_join', 'nick': nick})

                except Exception as e:
                    db.rollback()
                    print str(e)
                    self.send_json({'method': 'join_room', 'success': False, 'reason': u'加入房间失败, 请重试'})

            # 开始游戏
            elif method == 'start_game':
                print self.address + '\t = [START GAME]'
                self.send_json({'method': 'start_game', 'success': True})
                self.new_game()

            # 更新绘图
            elif method == 'update_pic':
                print self.address + '\t = [UPDATE PIC]'

                x = json_data['x']
                y = json_data['y']
                new_line = json_data['new_line']
                eraser = json_data['eraser']
                self.send_json({'method': 'update_pic', 'success': True})
                json_resp = {'event': 'pic_updated', 'x': x, 'y': y, 'new_line': new_line, 'eraser': eraser}

                for client in self.get_other_connections_in_current_room():
                    client.send_json(json_resp)

            # 更新绘图
            elif method == 'clear_pic':
                print self.address + '\t = [CLEAR PIC]'

                self.send_json({'method': 'pic_clear', 'success': True})
                json_resp = {'event': 'pic_clear'}

                for client in self.get_other_connections_in_current_room():
                    client.send_json(json_resp)

            # 更新提示, 此事件是由擂主所在客户端主动发起
            elif method == 'update_hint':
                print self.address + '\t = [UPDATE HINT]'

                hint = json_data['hint']
                self.send_json({'method': 'update_hint', 'success': True})
                json_resp = {'event': 'hint_updated', 'hint': hint}

                for client in self.get_connections_in_current_room():
                    client.send_json(json_resp)

            # 更新提示, 此事件是由擂主所在客户端主动发起
            elif method == 'change_color':
                print self.address + '\t = [CHANGE COLOR]'

                color = json_data['color']
                self.send_json({'method': 'change_color', 'success': True})
                json_resp = {'event': 'color_changed', 'color': color}

                for client in self.get_connections_in_current_room():
                    client.send_json(json_resp)

            # 提交答案
            elif method == 'submit_answer':
                print self.address + '\t = [SUBMIT ANSWER]'

                answer = json_data['answer']
                right_answer = self.get_current_room().curr_word
                win = answer == right_answer

                self.send_json({'method': 'submit_answer', 'success': True, 'win': win})
                if win:
                    json_resp = {'event': 'answer_submitted', 'nick': self.get_current_user().nick, 'win': True}
                    cur_user = self.get_current_user()
                    cur_user.win = 1
                    db.commit()
                else:
                    json_resp = {'event': 'answer_submitted', 'nick': self.get_current_user().nick, 'win': False,
                                 'answer': answer}

                for client in self.get_other_connections_in_current_room():
                    client.send_json(json_resp)

                all_win = True
                if win:
                    for user in self.get_users_in_current_room():
                        if user.win == 0 and user.state != 2:
                            all_win = False
                    if all_win:
                        for client in self.get_connections_in_current_room():
                            client.send_json({'event': 'all_win'})
                        self.new_game()

            # 时间到, 此事件是由擂主所在客户端发起
            elif method == 'time_up':
                print self.address + '\t = [TIME UP]'

                self.send_json({'method': 'time_up', 'success': True})
                json_resp = {'event': 'time_up', 'word': self.get_current_room().curr_word}

                for client in self.get_connections_in_current_room():
                    client.send_json(json_resp)

                self.new_game()

            # 退出房间
            elif method == 'exit_room':
                self.user_exit()

        except Exception as e:
            traceback.print_exc()
            print self.address + '\t = [UNKNOWN ERROR]'
            self.send_json({'success': False, 'reason': '未知错误'})
        self.read_message()

    # 下线
    def user_exit(self):
        print self.address + '\t = [EXIT ROOM]'

        user = self.get_current_user()
        room = self.get_current_room()
        room_expired = user is not None and user.state >= 1

        for client in self.get_other_connections_in_current_room():
            if room_expired:
                client.send_json({'event': 'room_expire'})
            else:
                client.send_json({'event': 'user_exit', 'nick': user.nick})

        if user is not None:
            db.delete(user)
            db.commit()

        self.send_json({'method': 'exit_room', 'success': True})
        if room_expired and room is not None:
            db.delete(room)
            db.commit()

    # 新游戏
    def new_game(self):
        users = self.get_users_in_current_room()
        room = self.get_current_room()
        if room is not None:
            room.state = 1
        user_count = len(users)
        current_index = user_count - 1
        for i in range(user_count):
            if users[i].state == 2:
                current_index = i
            users[i].state = 3
        if current_index + 1 >= user_count:
            room.round += 1

        if room.round > max_round:
            self.end_game()
            return
        next_index = (current_index + 1) % user_count
        users[next_index].state = 2

        # 发送结果
        word = generate_word()
        room.curr_word = word
        for user in self.get_users_in_current_room():
            user.win = 0

        db.commit()

        for client in self.get_connections_in_current_room():
            remote_user = client.get_current_user()
            if remote_user.room == room.id:
                client.send_json({'event': 'game_start', 'round': room.round, 'players': self.get_user_nicks_in_current_room()})
                if remote_user.state == 2:
                    client.send_json({'event': 'generate_word', 'word': word})
                elif remote_user.state == 3:
                    client.send_json({'event': 'word_generated', 'nick': users[next_index].nick})

    # 游戏结束
    def end_game(self):
        print self.address + '\t = [GAME END]'
        for client in self.get_connections_in_current_room():
            remote_user = client.get_current_user()
            if remote_user.room == self.get_current_room().id:
                client.send_json({'event': 'game_end'})

        users = self.get_users_in_current_room()
        room = self.get_current_room()
        for remote_user in users:
            remote_user.state = 0
        if len(users) > 0:
            users[0].state = 1
        room.state = 0
        db.commit()

    def send_json(self, json_data):
        try:
            message = json.dumps(json_data, ensure_ascii=False)
            self.send_message(message + '\n')

            print self.address + '\t < ' + message
        except:
            pass

    def send_message(self, data):
        if isinstance(data.encode('utf-8'), bytes):
            self._stream.write(data.encode('utf-8'))
        else:
            print self.address + '\t = [ASSERTION ERROR]'

    def on_close(self):
        self.user_exit()

        try:
            Connection.clients.remove(self)
        except:
            pass
        print self.address + '\t = [DISCONNECTED] Total clients: ' + str(len(Connection.clients))


class GameServer(TCPServer):
    def handle_stream(self, stream, address):
        Connection(stream, address)


if __name__ == '__main__':
    print('127.0.0.1\t = [SERVER START]')
    server = GameServer()
    server.listen(8082)
    IOLoop.instance().start()
