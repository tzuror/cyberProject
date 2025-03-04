import socket
import json

class Protocol:
    
    def __init__(self, command, sender, data):
        self.command = command
        self.sender = sender
        self.data = data

    def __repr__(self):
        return f"Protocol(command={self.command}, sender={self.sender}, data={self.data})"

    def to_dict(self):
        return {
            "command": self.command,
            "sender": self.sender,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            command=data_dict.get("command"),
            sender=data_dict.get("sender"),
            data=data_dict.get("data")
        )
    @classmethod
    def from_str(cls, data_str):
        data_dict = json.loads(data_str)
        return cls.from_dict(data_dict)

    def to_str(self):
        return json.dumps(self.to_dict())

# Example usage
if __name__ == "__main__":
    protocol = Protocol("CREATE_ROOM", "user123", {"room_name": "example_room"})
    print(protocol)

    protocol_dict = protocol.to_str()
    print(protocol_dict)

    new_protocol = Protocol.from_str(protocol_dict)
    print(new_protocol.data["room_name"])


    # Create a socket object
    