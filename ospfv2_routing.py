import json
with open('intent.json', 'r') as file:
    routing_data = json.load(file)

import configparser



def Ospf_Routing(AS_number, routing_data=routing_data):
    '''
    :param AS_number:
    :param routing_data: les informations contenues dans le fichier json
    '''
    if routing_data["AS"][AS_number]["igp"] == "OSPF":
        for router in routing_data["AS"][AS_number]["routers"]:
            Write_Ospf(router,AS_number)


def Write_Ospf(router,AS_number):
        '''
        :param router: Le routeur avec ses informations (dans le fichier intent.json)
        :param AS_number:
        '''
        process_id = router[1:]
        area_id = AS_number[1:]

        path = "config/R"+process_id+"_i"+process_id+"_startup-config.cfg"

        waitinglist = []
        for interface in routing_data["AS"][AS_number]["routers"][router]["interfaces"]:
            waitinglist.append(interface) #mettre les interfaces en attente de config dans la liste
            
        
        with open(path, "r") as f:
                config = f.readlines()

        j = 0
        NewNewConfig=[]
        while j < len(config) :
            NewNewConfig.append(config[j])
            if config[j].startswith("no ip http secure-server"):
                NewNewConfig.append("!\n")

                NewNewConfig.append(f"router ospf {process_id}\n")
                NewNewConfig.append(f" network 192.168.0.0 0.0.255.255 area {area_id}\n")
                NewNewConfig.append(f" passive-interface default\n")
                for interfaces in waitinglist:
                    NewNewConfig.append(f" no passive-interface {interfaces}\n")
                NewNewConfig.append(f" redistribute bgp {AS_number} route-map FROM-PROVIDER-IN\n") #---------------------------------DEMANDER AU PROF
                NewNewConfig.append(f" redistribute bgp {AS_number} route-map FROM-CUSTOMER-IN\n")
            j+=1

        #on ecrit la nouvelle config
        with open(path,"w") as f:
            for line in NewNewConfig:
                f.write(line)

if __name__ == "__main__":
    Ospf_Routing("102")