import honeybee
from honeybee.room import Room

def create_room(width, length, height):
    room = Room.from_box('room',width,length,height)

    return room