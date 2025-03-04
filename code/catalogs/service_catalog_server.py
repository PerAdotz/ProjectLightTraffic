import json
import cherrypy
import datetime
import requests

'''
its the central service for resources handling and configurations
central register

in service settings i will have only one component in the resource_catalog: []
becouse i only have one TLCatalogManger that handles zone A , but they implemented 
method (one_res_cat REST endpoint) to allow scalability ( the code is really general, as if they have more zones)
'''


class ServiceCatalogManager(object):

    def __init__(self):
        self.settings = "service_settings.json"
        self.cat = json.load(open(self.settings))

    exposed = True

    def GET(self, *uri, **parameters):
        if len(uri) == 1:
            self.settings = "service_settings.json"
            self.cat = json.load(open(self.settings))
            if uri[0] == 'res_cat': #returns the complete list of registered resouces
                return json.dumps(self.cat["resource_catalogs"])
            elif uri[0] == 'one_res_cat': #returns the last registered catalog resouce
                results = self.cat['resource_catalogs'][len(self.cat["resource_catalogs"]) - 1]
                return json.dumps(results)
            elif uri[0] == 'broker': #retuns base info of the MQTT broker
                output_website = self.cat['broker']
                output_port = self.getBrokerPort()
                output = {
                    'broker_port': output_port,
                    'broker': output_website,
                }
                print(output)
                return json.dumps(output)
            elif uri[0] == 'base_topic':
                return json.dumps(self.cat["base_topic"])
        else:
            error_string = "incorrect URI or PARAMETERS URI" + str(len(uri)) + "PAR" + str(len(parameters))
            raise cherrypy.HTTPError(400, error_string)

    def PUT(self, *uri, **params):
        '''
        allows resouces catalogs (handled by TLCatalogManager) to register and to update
        into the service Catalog, memorizing info in a json file service_settings.json 
        that is updated dynamically
        '''
        if uri[0] == 'registerResourceCatalog':
            '''
            Upon First Registration (via TLCatalogManager):
            A TLCatalogManager instance sends a PUT request to /registerResourceCatalog.
            Its details  (resource_catalog_info.json) are added to resource_catalogs of service_settings.json
            '''
            body = cherrypy.request.body.read()
            json_body = json.loads(body)
            ip = json_body["ip_address"]
            port = json_body["ip_port"]
            try:
                for item in self.cat["resource_catalogs"]:
                    #to UPDATE reseourceCatalog if found
                    if ip == item["ip_address"]:
                        if port == item["ip_port"]:
                            resourcesList = self.cat["resource_catalogs"]
                            resourcesList.remove(item)
                            resourcesList.append(json_body)
                            self.cat["resource_catalogs"] = resourcesList
                            file = open(self.settings, "w")
                            json.dump(self.cat, file)
                            return 'Registered successfully'

                #to Register resource Catalog if not found
                self.cat["resource_catalogs"].append(json_body)
                file = open(self.settings, "w")
                json.dump(self.cat, file)
                return 'Registered successfully'
            except:
                return 'An error occurred during registration of Resource Catalog'

    def getPort(self):
        return self.cat['ip_port']

    def getBrokerPort(self):
        return self.cat['broker_port']


if __name__ == "__main__":
    service_info = json.load(open('service_catalog_info.json'))
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }
    cherrypy.tree.mount(ServiceCatalogManager(), '/', conf)
    cherrypy.config.update(conf)
    cherrypy.config.update({'server.socket_host': service_info['ip_address_service']})
    cherrypy.config.update({"server.socket_port": ServiceCatalogManager().getPort()})
    cherrypy.engine.start()
    cherrypy.engine.block()
