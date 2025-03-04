from MyMQTT import *
import time
import json
import requests
import threading


class LedManager:
    def __init__(self, ledmanager_info, service_catalog_info):
        # Retrieve broker info (port and broker name) from service catalog info,calling a GET from service_catalog_server
        self.service_catalog_info = json.load(open(service_catalog_info))
        #retrievs IP address and Port od the service_catalog_server from service_catalog_info.json to use it to do a GET
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["broker"]
        self.port = rjson["broker_port"]
        # Retrieve last registered resource catalog info from service catalog, calling a GET from service_catalog_server
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/one_res_cat'
        #one_res_cat gives me the info of resource catalog (resource_catalog_info.json) because its the only resource catalog we have 
        r = requests.get(request_string)
        self.rc = json.loads(r.text)
        # Details about sensor
        self.info = ledmanager_info 
        info = json.load(open(self.info))
        for s in info["serviceDetails"]:
            if s["serviceType"]=='MQTT':
                self.topicS = s["topicS"] #topic to which it is subscribed to receive messages from sensors
                self.topicP = s["topicP"] #topic on which it publishes messages for the acrivations of leds
        self.clientID = info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self) #configure MQTT

    def register(self):
        '''
        periodicallty registers itself to the resource catalog to confirm it is active
        '''
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    # Method to START and SUBSCRIBE
    def start(self):
        self.client.start()
        time.sleep(3)  # Timer of 3 second (to deal with asynchronous)
        #useful to avoid the risk of subscribung to a topic before the connection with the broker starts
        self.client.mySubscribe(self.topicS)  #subscribe to subscribeTopic (to receive all messages from sensor in A zone)

    # Method to UNSUBSCRIBE and STOP
    def stop(self):
        self.client.unsubscribe()
        time.sleep(3) #to allow the client to unsubscribe from topics
        self.client.stop()

    def notify(self, topic, payload):
        '''
        when it receives a message from a sensors, the message is processed

        '''
        messageReceived = json.loads(payload)
        bn = messageReceived["bn"] #identifies the sensor that sended the message
        id = bn.split('_')
        sensorType = id[1] #sensor type (p for the button (pedestrian) , c for the movement sensor (car))
        trafficLightID = id[2] #id of the Led associated to the sensor
        obj = 0
        if messageReceived["e"]["n"] == "button": #if the message its from a button (pedestrian)
            obj = "pedestrian"
        elif messageReceived["e"]["n"] == "motion": #if the message its from a movement sensor (car)
            obj = "car"
        if messageReceived["e"]["v"]: #if the value of the event its true (not 0)
            if sensorType == "p": #if its a button, creates a specific topic for that Led for the pedetrian
                specific_topic = self.topicP + '/' + trafficLightID
                self.publish(specific_topic, obj) #publishes a messages to that led with the object detected, a pedestrian
            elif sensorType == "c":
                self.publish(self.topicP, obj)#publishes a messages to ALL led in zone A with the object detected, a car

    def publish(self, topicP, obj):
        '''
        if the sensor detects a pedestrian or a car , the manager publishes under topicPublish
        '''
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "led",
                "u": "detection",
                "t": time.time(),
                "v": obj
            }
        }
        self.client.myPublish(topicP, msg)
        print("published\n" + json.dumps(msg) + '\nOn topic: ' + f'{topicP}')

    def background(self):  
        #periodically register itself every 10 seconds to the TLCatalogManager
        #focus on its resources status and device data
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    ledMan = LedManager('ledmanagerA_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=ledMan.background)
    f = threading.Thread(name='foreground', target=ledMan.foreground)

    b.start() #attivate the backgorund periodically register
    f.start() #attivate the subsxirpiton to MQTT topics

    while True:
        time.sleep(3)

    # ledMan.stop()
