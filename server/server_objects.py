
class MEMBER:
    def __init__(self, socket, tcp_address, udp_address, name, email = None, room_code=None, id= None):
        self.socket = socket
        self.tcp_address = tcp_address
        self.udp_address = udp_address
        self.name = name
        self.room_code = room_code
        self.email = email
        self.id = id

    def get_room_code(self):
        return self.room_code

    def get_socket(self):
        return self.socket

    def get_tcp_address(self):
        return self.tcp_address
    
    def get_udp_address(self):
        return self.udp_address

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def set_room_code(self, room_code):
        self.room_code = room_code

    def send(self, data):
        self.socket.send(data)
    def get_email(self):
        return self.email
    def set_email(self, email):
        self.email = email
    def get_id(self):
        return self.id
    def set_id(self, id):
        self.id = id
    def __str__(self):
        try:
            return f"{self.name} - {self.email} - UDP : {self.get_udp_address()} -  TCP : {self.socket.getpeername()}"
        except Exception as e:
            print(e)
            return f"{self.name} "

class ROOM:
    def __init__(self, code, host: MEMBER, status: str, room_pwd: str):
        self.__ROOMCODE = code
        self.MEMBERS = set()
        self.CHAT_MEMBERS = set()
        self.__host = host
        self.__status = status
        self.__pwd = room_pwd
        self.sharing = None

    def add_member(self, member: MEMBER):
        self.MEMBERS.add(member)

    def remove_member(self, member: MEMBER):
        self.MEMBERS.remove(member)

    def get_members(self):
        return self.MEMBERS

    def get_host(self) -> MEMBER:
        return self.__host

    def set_host(self, host: MEMBER):
        self.__host = host

    def get_status(self):
        return self.__status

    def set_status(self, status):
        self.__status = status

    def get_code(self):
        return self.__ROOMCODE
    
    def get_pwd(self):
        return self.__pwd
    
    def set_pwd(self, pwd):
        self.__pwd = pwd

    def add_chat_member(self, member: MEMBER):
        self.CHAT_MEMBERS.add(member)

    def remove_chat_member(self, member: MEMBER):
        self.CHAT_MEMBERS.remove(member)
    
    def get_sharing(self):
        return self.sharing
    
    def set_sharing(self, sharing):
        self.sharing = sharing

    def get_chat_members(self):
        return self.CHAT_MEMBERS
