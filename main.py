#! /usr/bin/env python
# coding=utf-8
import json
import sys

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
max_round = 2


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


# 服务器逻辑
class Connection(object):
    # 静态集合, 保存所有连接
    clients = set()

    # 新用户连接
    def __init__(self, stream, address):
        print address[0] + '\t = [已连接]'

        # 注册连接
        Connection.clients.add(self)

        self._stream = stream
        self.address = address[0]
        self._stream.set_close_callback(self.on_close)
        self.read_message()

    # 收到消息的分配
    def read_message(self):
        self._stream.read_until('\n', self.handle_message)

    # 分配到消息的处理
    def handle_message(self, data):

        print self.address + '\t > ' + data.replace('\n', '')
        try:
            json_data = json.loads(data)
            method = json_data['method']

            # 创建房间
            if method == 'create_room':
                print self.address + '\t = [创建房间]'
                try:
                    nick = json_data['nick']
                    room = Room(state=0, round=0, curr_word="")
                    db.add(room)
                    db.commit()

                    user = User(ip=self.address, nick=nick, room=room.id, state=1)
                    db.add(user)
                    db.commit()

                    self.send_json({'method': 'create_room', 'success': True, 'room': room.id})
                except Exception as e:
                    print(e)
                    db.rollback()
                    self.send_json(
                        {'method': 'create_room', 'success': False, 'reason': u'创建房间失败, 可能是昵称过长或含有特殊字符, 请重试'})

            # 加入房间
            elif method == 'join_room':
                print self.address + '\t = [加入房间]'
                try:
                    rooms = db.query(Room).filter(Room.id == json_data['room']).all()
                    if len(rooms) < 1:
                        self.send_json({'method': 'join_room', 'success': False, 'reason': '房间不存在'})
                        self.read_message()  # 进入下次I/O循环
                        return

                    room = rooms[-1]
                    nick = json_data['nick']
                    user = User(ip=self.address, nick=nick, room=room.id, state=0)
                    db.add(user)
                    db.commit()

                    # 通知其他人有人加入房间
                    json_data = {'event': 'user_join', 'nick': nick}
                    player_list = list()

                    for remote_client in Connection.clients:
                        remote_address = remote_client.address
                        remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                        if remote_user.room == room.id:
                            remote_client.send_json(json_data)
                            player_list.append(remote_user.nick)

                    self.send_json({'method': 'join_room', 'success': True, 'players': player_list})

                except Exception as e:
                    db.rollback()
                    self.send_json({'method': 'join_room', 'success': False, 'reason': u'加入房间失败, 可能是昵称过长或含有特殊字符, 请重试'})

            # 准备游戏
            elif method == 'start_game':
                print self.address + '\t = [开始游戏]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                if user.state == 1:
                    self.new_game()
                    self.send_json({'method': 'start_game', 'success': True})

                else:
                    self.send_json({'method': 'start_game', 'success': False, 'reason': u'不是房主, 不能开始游戏'})
                    self.read_message()
                    return

            # 更新绘图
            elif method == 'update_pic':
                print self.address + '\t = [更新绘图]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                x = json_data['x']
                y = json_data['y']
                new_line = json_data['new_line']
                self.send_json({'method': 'update_pic', 'success': True})
                json_resp = {'event': 'pic_updated', 'x': x, 'y': y, 'new_line': new_line}

                for remote_client in Connection.clients:
                    remote_address = remote_client.address
                    remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                    remote_room = remote_user.room
                    if remote_room == user.room and remote_user.id != user.id:
                        remote_client.send_json(json_resp)

            # 更新提示, 此事件是由擂主所在客户端主动发起
            elif method == 'update_hint':
                print self.address + '\t = [更新提示]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                hint = json_data['hint']
                self.send_json({'method': 'update_hint', 'success': True})
                json_resp = {'event': 'hint_updated', 'hint': hint}

                for remote_client in Connection.clients:
                    remote_address = remote_client.address
                    remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                    remote_room = remote_user.room
                    if remote_room == user.room:
                        remote_client.send_json(json_resp)

            # 提交答案
            elif method == 'submit_answer':
                print self.address + '\t = [提交答案]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                room = db.query(Room).filter(Room.id == user.room).all()[-1]
                answer = json_data['answer']
                right_answer = room.curr_word
                win = answer == right_answer

                self.send_json({'method': 'submit_answer', 'success': True, 'win': win})
                if win:
                    json_resp = {'event': 'answer_submitted', 'nick': user.nick, 'win': True}
                else:
                    json_resp = {'event': 'answer_submitted', 'nick': user.nick, 'win': False, 'answer': answer}

                for remote_client in Connection.clients:
                    remote_address = remote_client.address
                    remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                    remote_room = remote_user.room
                    if remote_room == user.room:
                        remote_client.send_json(json_resp)

            # 时间到, 此事件是由擂主所在客户端发起
            elif method == 'time_up':
                print self.address + '\t = [计时结束]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                self.send_json({'method': 'time_up', 'success': True})
                json_resp = {'event': 'time_up'}

                for remote_client in Connection.clients:
                    remote_address = remote_client.address
                    remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                    remote_room = remote_user.room
                    if remote_room == user.room:
                        remote_client.send_json(json_resp)

                self.new_game()

            # 退出房间
            elif method == 'exit_room':
                print self.address + '\t = [退出房间]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                room = db.query(Room).filter(Room.id == user.room).all()[-1]
                if room.state == 1:
                    self.send_json({'method': 'exit_room', 'success': False, 'reason': '状态错误, 游戏中不允许退出房间! '})
                db.delete(user)
                db.commit()

                users = db.query(User).filter(User.room == room.id).all()
                if len(users) == 0:
                    db.delete(room)
                    db.commit()

                self.send_json({'method': 'exit_room', 'success': True})

                for remote_client in Connection.clients:
                    remote_address = remote_client.address
                    remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
                    remote_room = remote_user.room
                    if remote_room == user.room:
                        remote_client.send_json({'event': 'user_exit', 'nick': user.nick})

        except Exception as e:
            print self.address + '\t = [无法解析的命令]'
            self.send_json({'success': False, 'reason': '无法解析的命令'})
        self.read_message()

    # 新游戏
    def new_game(self):
        user = db.query(User).filter(User.ip == self.address).all()[-1]
        room = db.query(Room).filter(Room.id == user.room).all()[-1]
        users = db.query(User).filter(User.room == room.id).all()
        user_count = len(users)
        current_index = user_count - 1
        for i in range(user_count):
            if users[i].state == 2:
                current_index = i
            users[i].state = 3
        if current_index + 1 >= user_count:
            room.round += 1

        if room.round >= max_round:
            self.end_game()
            return
        next_index = (current_index + 1) % user_count
        users[next_index].state = 2

        # 发送结果
        word = self.generate_word()
        room.curr_word = word

        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
            if remote_user.room == room.id:
                if remote_user.state == 2:
                    remote_client.send_json({'event': 'generate_word', 'word': word})
                elif remote_user.state == 3:
                    remote_client.send_json({'event': 'word_generated', 'nick': users[next_index].nick})

    # 分配词语
    def generate_word(self):
        return '测试词语'

    # 游戏结束
    def end_game(self):
        print self.address + '\t = [游戏结束]'
        user = db.query(User).filter(User.ip == self.address).all()[-1]
        room = db.query(Room).filter(Room.id == user.room).all()[-1]
        users = db.query(User).filter(User.room == user.room).all()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_user = db.query(User).filter(User.ip == remote_address).all()[-1]
            if remote_user.room == room.id:
                remote_client.send_json({'event': 'game_end'})
        for remote_user in users:
            remote_user.state = 0
        if len(users) > 0:
            users[0].state = 1
        room.state = 0

    def send_json(self, json_data):
        message = json.dumps(json_data)
        print self.address + '\t < ' + message 
        self.send_message(message + '\n')

    def send_message(self, data):
        self._stream.write(data)

    def on_close(self):
        print self.address + '\t = [已断开]'
        Connection.clients.remove(self)


class GameServer(TCPServer):
    def handle_stream(self, stream, address):
        Connection(stream, address)


if __name__ == '__main__':
    print('127.0.0.1\t = [服务器启动]')
    server = GameServer()
    server.listen(8082)
    IOLoop.instance().start()
