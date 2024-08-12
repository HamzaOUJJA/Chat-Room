import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import random
import string

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

def generate_unique_code(length=4):
    while True:
        code = ''.join(random.choices(string.ascii_lowercase, k=length))
        if code not in rooms:
            return code

@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = "join" in request.form
        create = "create" in request.form

        if not name:
            return render_template("index.html", error="Please enter a name.", code=code, name=name)

        if join and not code:
            return render_template("index.html", error="Please enter a room code.", code=code, name=name)

        if create:
            code = generate_unique_code()
            rooms[code] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("index.html", error="Room does not exist.", code=code, name=name)

        session["room"] = code
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("index.html")

@app.route("/room")
def room():
    room_code = session.get("room")
    name = session.get("name")

    if not room_code or not name or room_code not in rooms:
        return redirect(url_for("home"))

    room_data = rooms[room_code]
    return render_template("room.html", code=room_code, messages=room_data["messages"], session_name=name)

@socketio.on("message")
def handle_message(data):
    room_code = session.get("room")

    if room_code and room_code in rooms:
        content = {"name": session.get("name"), "message": data["data"]}
        rooms[room_code]["messages"].append(content)
        send(content, to=room_code)
        print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def handle_connect(auth):
    room_code = session.get("room")
    name = session.get("name")

    if room_code and name and room_code in rooms:
        join_room(room_code)
        rooms[room_code]["members"] += 1
        send({"name": name, "message": " entered the room"}, to=room_code)
        print(f"{name} joined room {room_code}")

@socketio.on("disconnect")
def handle_disconnect():
    room_code = session.get("room")
    name = session.get("name")

    if room_code in rooms:
        rooms[room_code]["members"] -= 1
        if rooms[room_code]["members"] == 0:
            del rooms[room_code]

    leave_room(room_code)
    send({"name": name, "message": "has left the room"}, to=room_code)
    print(f"{name} has left the room {room_code}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
