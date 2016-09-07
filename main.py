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
    # 静态列表, 保存所有连接
    clients = list()

    # 新用户连接
    def __init__(self, stream, address):
        # 注册连接
        Connection.clients.append(self)
        print address[0] + '\t = [CONNECTED] Total clients: ' + str(len(Connection.clients))

        self._stream = stream
        self.address = address[0]
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
        result = list()
        for remote_client in Connection.clients:
            remote_address = remote_client.address
            remote_users = db.query(User).filter(User.ip == remote_address).all()
            if len(remote_users) <= 0:
                continue
            remote_user = remote_users[-1]
            remote_room = remote_user.room
            if self.get_current_user() is not None and remote_room == self.get_current_user().room:
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

                    user = User(ip=self.address, nick=nick, room=room.id, state=1)
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
                    nick = json_data['nick']
                    user = User(ip=self.address, nick=nick, room=room.id, state=0)
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

            # 准备游戏
            elif method == 'start_game':
                print self.address + '\t = [START GAME]'

                if self.get_current_user().state == 1:
                    self.send_json({'method': 'start_game', 'success': True})
                    self.new_game()

                else:
                    self.send_json({'method': 'start_game', 'success': False, 'reason': u'不是房主, 不能开始游戏'})

            # 更新绘图
            elif method == 'update_pic':
                print self.address + '\t = [UPDATE PIC]'

                x = json_data['x']
                y = json_data['y']
                new_line = json_data['new_line']
                self.send_json({'method': 'update_pic', 'success': True})
                json_resp = {'event': 'pic_updated', 'x': x, 'y': y, 'new_line': new_line}

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

            # 提交答案
            elif method == 'submit_answer':
                print self.address + '\t = [SUBMIT ANSWER]'

                answer = json_data['answer']
                right_answer = self.get_current_room().curr_word
                win = answer == right_answer

                self.send_json({'method': 'submit_answer', 'success': True, 'win': win})
                if win:
                    json_resp = {'event': 'answer_submitted', 'nick': self.get_current_user().nick, 'win': True}
                else:
                    json_resp = {'event': 'answer_submitted', 'nick': self.get_current_user().nick, 'win': False,
                                 'answer': answer}

                for client in self.get_other_connections_in_current_room():
                    client.send_json(json_resp)

            # 时间到, 此事件是由擂主所在客户端发起
            elif method == 'time_up':
                print self.address + '\t = [TIME UP]'

                user = db.query(User).filter(User.ip == self.address).all()[-1]
                self.send_json({'method': 'time_up', 'success': True})
                json_resp = {'event': 'time_up'}

                for client in self.get_connections_in_current_room():
                    client.send_json(json_resp)

                self.new_game()

            # 退出房间
            elif method == 'exit_room':
                self.user_exit()

        except Exception as e:
            print str(e)
            print self.address + '\t = [UNKNOWN ERROR]'
            self.send_json({'success': False, 'reason': '未知错误'})
        self.read_message()

    # 下线
    def user_exit(self):
        print self.address + '\t = [EXIT ROOM]'

        if self.get_current_room() is not None and self.get_current_room().state == 1:
            self.send_json({'method': 'exit_room', 'success': False, 'reason': '状态错误, 游戏中不允许退出房间! '})
            return
        user = self.get_current_user()
        room_expired = user is not None and user.state == 1
        if user is not None:
            db.delete(user)
            db.commit()

        self.send_json({'method': 'exit_room', 'success': True})

        for client in self.get_other_connections_in_current_room():
            if room_expired:
                client.send_json({'event': 'room_expire'})
            else:
                client.send_json({'event': 'user_exit', 'nick': user.nick})

        room = self.get_current_room()
        if room_expired and room is not None:
            db.delete(room)
            db.commit()

    # 新游戏
    def new_game(self):
        users = self.get_users_in_current_room()
        room = self.get_current_room()
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
        word = self.generate_word()
        room.curr_word = word

        db.commit()

        for client in self.get_connections_in_current_room():
            remote_user = client.get_current_user()
            if remote_user.room == room.id:
                client.send_json({'event': 'game_start', 'players': self.get_user_nicks_in_current_room()})
                if remote_user.state == 2:
                    client.send_json({'event': 'generate_word', 'word': word})
                elif remote_user.state == 3:
                    client.send_json({'event': 'word_generated', 'nick': users[next_index].nick})

    # 分配词语
    def generate_word(self):
        return '测试词语'

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

        Connection.clients.remove(self)
        print self.address + '\t = [DISCONNECTED] Total clients: ' + str(len(Connection.clients))

class GameServer(TCPServer):
    def handle_stream(self, stream, address):
        Connection(stream, address)


if __name__ == '__main__':
    print('127.0.0.1\t = [SERVER START]')
    server = GameServer()
    server.listen(8082)
    IOLoop.instance().start()
