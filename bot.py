#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import telepot
import time
from telepot.loop import MessageLoop
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

def save_status(obj):
    with open('chats.json', 'w') as f:
        f.write(json.dumps(obj))

def save_allowed(s):
    with open('allowed.json', 'w') as f:
        f.write(json.dumps(list(s)))

if not os.path.isfile('chats.json'):
    save_status({})

if not os.path.isfile('allowed.json'):
    save_allowed(set())

chats = {}
allowed = []
TOKEN = ""
PASSWORD = "changeme"

with open('chats.json', 'r') as f:
    chats = json.load(f)

with open('allowed.json', 'r') as f:
    allowed = set(json.load(f))

if os.path.isfile('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
        if config['token'] == "":
            sys.exit("No token defined. Define it in a file called token.txt.")
        if config['password'] == "":
            print("WARNING: Empty Password for registering to use the bot." +
                  " It could be dangerous, because anybody could use this bot" +
                  " and forward messages to the channels associated to it")
        TOKEN = config['token']
        PASSWORD = config['password']
else:
    sys.exit("No config file found. Remember changing the name of config-sample.json to config.json")

def is_allowed(msg):
    if msg['chat']['type'] == 'channel':
        return True  # all channel admins are allowed to use the bot (channels don't have sender info)
    return 'from' in msg and msg['from']['id'] in allowed

def handle(msg):
    print("Message: " + str(msg))
    content_type, chat_type, chat_id = telepot.glance(msg)
    txt = msg.get('text', msg.get('caption', ''))

    if msg['chat']['type'] != 'channel':
        if txt.startswith("/addme"):
            if msg['chat']['type'] != 'private':
                bot.sendMessage(chat_id, "This command is meant to be used only on personal chats.")
            else:
                used_password = " ".join(txt.strip().split(" ")[1:])
                if used_password == PASSWORD:
                    allowed.add(msg['from']['id'])
                    save_allowed(allowed)
                    bot.sendMessage(chat_id, f"{msg['from']['first_name']}, you have been registered as an authorized user of this bot.")
                else:
                    bot.sendMessage(chat_id, "Wrong password.")
        elif txt.startswith("/rmme"):
            allowed.remove(msg['from']['id'])
            save_allowed(allowed)
            bot.sendMessage(chat_id, "Your permission for using the bot was removed successfully.")
    
    if is_allowed(msg):
        if txt.startswith("/add "):
            txt_split = txt.strip().split(" ")
            if len(txt_split) == 2 and txt_split[1][0] == "#":
                tag = txt_split[1].lower()
                name = msg['chat'].get('title', f"Personal chat with {msg['chat'].get('first_name', '')}")
                chats[tag] = {'id': chat_id, 'name': name}
                bot.sendMessage(chat_id, f"{name} added with tag {tag}")
                save_status(chats)
            else:
                bot.sendMessage(chat_id, "Incorrect format. It should be _/add #{tag}_", parse_mode="Markdown")
        elif txt.startswith("/rm "):
            txt_split = txt.strip().split(" ")
            if len(txt_split) == 2 and txt_split[1][0] == "#":
                tag = txt_split[1].lower()
                if tag in chats and chats[tag]['id'] == chat_id:
                    del chats[tag]
                    bot.sendMessage(chat_id, f"Tag {tag} deleted from taglist.")
                    save_status(chats)
                else:
                    bot.sendMessage(chat_id, "Tag doesn't exist on TagList or you can't delete it from a different chat.")
        elif txt.startswith("/taglist"):
            response = "<b>TagList</b>"
            for tag, chat in sorted(chats.items()):
                response += f"\n<b>{tag}</b>: <i>{chat['name']}</i>"
            bot.sendMessage(chat_id, response, parse_mode="HTML")
        elif txt.startswith("#"):
            tags = [t.lower() for t in txt.strip().split() if t.startswith("#")]
            if tags:
                for tag in tags:
                    if tag in chats:
                        bot.forwardMessage(chats[tag]['id'], chat_id, msg['message_id'])
                        if 'reply_to_message' in msg:
                            bot.forwardMessage(chats[tag]['id'], chat_id, msg['reply_to_message']['message_id'])
                    else:
                        bot.sendMessage(chat_id, f"Failed to send messages to tag {tag}", parse_mode="HTML")

bot = telepot.Bot(TOKEN)

MessageLoop(bot, handle).run_as_thread()
print('Listening ...')

# Define a simple HTTP server to keep the bot running and listen on port 8080
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_http_server():
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, SimpleHandler)
    print("Starting HTTP server on port 8080...")
    httpd.serve_forever()

# Run HTTP server in a separate thread
http_thread = threading.Thread(target=run_http_server)
http_thread.daemon = True
http_thread.start()

# Keep the bot running
while True:
    time.sleep(10)
