import cherrypy
import json
from datetime import datetime
import requests
import threading
import time

EXPIRATION_TIMEOUT = 60  # threshold in seconds above which device subscriptions must be considered as Expired (doubts on functioning )

#every 10 seconds periodically registers in the service_catalog_server
class TLCatalogManager(object):
    exposed = True #cherrypy exposes class methods as endpoints REST

    '''
    handles HTTP requests to register resources, getting info of the broker
    and retrieve data related to devices
    catalog.json is the key because tracks devices and handles their info 
    and also updates the system thanks to the methods of TLCatalogManager
    '''

    def __init__(self, resource_catalog_info, service_catalog_info):
        self.name = 'catalog.json' #local archive for the info of the registerd devices and the broker
        self.cat = json.load(open(self.name))
        self.resource_cat_info_file = resource_catalog_info
        self.resource_cat_info = json.load(open(self.resource_cat_info_file))
        #info to configure and comunicate of the resource_catalog
        self.service_catalog_info = json.load(open(service_catalog_info))
        #service catalog info gives the indo to connect to the service_catalog_server


    def GET(self, *uri, **params):
        '''
        when a client does a GET the server reads the data in resoucesList (in catalog.json) to answer the request
        '''
        if len(uri[0]) > 0:
            if (uri[0] != 'broker') and (uri[0] != 'allResources') and (uri[0] != 'resourceID') and (
                    uri[0] != 'allUsers') and (uri[0] != 'userID') and (uri[0] != 'ZoneDatabase'):
                error_string = "incorrect URI:\n" + str(uri)
                raise cherrypy.HTTPError(400, error_string)
            else:
                if uri[0] == 'broker':
                    # Retrieve information about broker
                    brokerInfo = self.cat['broker']
                    return json.dumps(brokerInfo)

                if uri[0] == 'allResources':
                    # Retrieve all registered devices
                    output = json.dumps(self.cat['devicesList'])
                    return output

                if uri[0] == 'resourceID':
                    # Retrieve the information of a device given its ID
                    id = int(params['ID'])
                    for item in self.cat['resourcesList']:
                        if id == int(item['ID']):
                            output = json.dumps(item)
                            return output
                    return 'Resource/Device ID not found'

                if uri[0] == 'ZoneDatabase':
                    # Retrieve the information Zone Database (all failures among devices)
                    zone = uri[1]
                    listZone = []
                    for item in self.cat['resourcesList']:
                        if item['zone'] == zone:
                            # Check if resource's status is ok
                            if item['status'] != 'OK':
                                listZone.append(item)
                            # Check if resource's registration has expired
                            elif (time.time() - item['lastUpdate']) > EXPIRATION_TIMEOUT:
                                item['status'] = 'EXPIRED'
                                listZone.append(item)
                    ZoneDatabase = {"zone": listZone}
                    output = json.dumps(ZoneDatabase)
                    return output

    #PUT used to register resouces in the service, receives a json message with the resource info
    def PUT(self, *uri, **params):
        if uri[0] == 'registerResource': #endpoint to register od update the resource
            body = cherrypy.request.body.read()
            json_body = json.loads(body)
            # Update "lastUpdate" of the resource
            json_body["lastUpdate"] = time.time() #also update last update time
            id = json_body['ID'] #iD of the resource
            try:
                for item in self.cat['resourcesList']:  #for all registered resources in the catalog.json
                    if id == item['ID']: #look for the one with the same ID, if there is (so the resources its already registered)
                        #then just UPDATE its info
                        devicesList = self.cat['resourcesList']
                        devicesList.remove(item) #remove the old version
                        devicesList.append(json_body) #append the new version
                        self.cat['resourcesList'] = devicesList
                        # Update "lastUpdate" of resource catalog catalog.json
                        self.cat['lastUpdate'] = time.time()
                        file = open(self.name, "w")
                        json.dump(self.cat, file) #dump the updated catalog
                        return 'Registered successfully'

                #if the resources has not been found in the catalog then add it, REGISTRATION
                self.cat['resourcesList'].append(json_body)
                # Update "lastUpdate" of resource catalog
                self.cat['lastUpdate'] = time.time()
                file = open(self.name, "w")
                json.dump(self.cat, file)
                return 'Registered successfully'
            except:
                return 'An error occurred during registration of Resource'


    #register every 10 seconds (background) sends a request to the service_catalog
    #to register the catalog of resources (itself) toknow if the server is running
    def register(self):
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' \
                         + self.service_catalog_info["ip_port_service"] + '/registerResourceCatalog'
        data = self.resource_cat_info
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def background(self): 
        #periodically register itself to the ServiceCatalogManager
        #to make sure that the resource catalog (itself) remains reachable to other components
        while True:
            self.register()
            time.sleep(10)


if __name__ == '__main__':
    res_cat_server = TLCatalogManager('resource_catalog_info.json', 'service_catalog_info.json')

    #thread used to periodically register without blocking CherryPY server answering REST requests
    b = threading.Thread(name='background', target=res_cat_server.background)

    b.start()

    resource_info = json.load(open('resource_catalog_info.json'))
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(res_cat_server, '/', conf)
    cherrypy.config.update(conf)
    cherrypy.config.update({'server.socket_host': resource_info['ip_address']})
    cherrypy.config.update({"server.socket_port": int(resource_info['ip_port'])})
    cherrypy.engine.start()
    cherrypy.engine.block()
