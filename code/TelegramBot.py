#First you should run: pip install pyTelegramBotAPI

import os
import telepot
from telepot.loop import MessageLoop
import json
import requests
import time
import threading

class TelegramBot:
    exposed = True
    
    def __init__(self, telegram_Bot_info, service_catalog_info):
        # Retrieve broker info from service catalog
            self.service_catalog_info = json.load(open(service_catalog_info))
            request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/broker'
            r = requests.get(request_string)
            rjson = json.loads(r.text)
            self.broker = rjson["broker"]
            self.port = rjson["broker_port"]

            # Retrieve resource catalog info from service catalog
            request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/one_res_cat'
            r = requests.get(request_string)
            self.rc = json.loads(r.text)

            # Details about telegram_bot
            self.info = telegram_Bot_info
            info = json.load(open(self.info))
            self.token = info["Token"]
            self.zones = info['zone'] #list of zones covered by telegram bot
            self.bot = telepot.Bot(self.token)
            MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

    def register(self):
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg["text"]  # zone requested by client
        print(message)
        if message in self.zones:
            request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/ZoneDatabase' + '/' + message
            r = requests.get(request_string)
            zoneDatabase = json.loads(r.text)
            self.bot.sendMessage(chat_ID, text="Updated Database of Zone\n"+ message +":\n" + json.dumps(zoneDatabase, indent=4))
        else:
            self.bot.sendMessage(chat_ID, text="Zone NOT found!")

    def background(self):
        while True:
            self.register()
            time.sleep(10)


if __name__ == '__main__':
    TB = TelegramBot('TelegramBot_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=TB.background)

    b.start()
