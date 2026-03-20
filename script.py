import json
from pathlib import Path
from ospf_routing import Ospf_Routing
from rip_routing import rip_routing
from drag_and_drop import drag_and_drop
from bgp_routing_communities import writeBGPconfig


def load_intent(file_path):  # on charge le fichier intent
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def dump_intent(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def set_prefix(data, source):
    autonomous_systems = data.get('AS', {})

    for autonomous_system, as_data in autonomous_systems.items():
        network = as_data.setdefault('network', {})

        network['prefix'] = f"10.{autonomous_system}.0.0"
        network['subnet'] = "/16"

    dump_intent(source, data)


def set_address(data, source):

    autonomous_systems = data.get('AS', {})
    router_to_as = {}

    #  Mapping router → AS
    for num_as, info_as in data["AS"].items():
        for r in info_as["routers"]:
            router_to_as[r[1:]] = num_as

    #  Compteur de liens intra-AS
    link_counter = {}

    for as_id, as_data in autonomous_systems.items():

        link_counter.setdefault(as_id, 0)

        prefix = as_data['network']['prefix']  # ex: 10.101.0.0
        base_prefix = ".".join(prefix.split('.')[:2])  # → 10.101

        for router, router_data in as_data.get('routers', {}).items():

            r_id = int(router[1:])

            for interface, interface_data in router_data.get('interfaces', {}).items():

                #  LOOPBACK
                if interface == "Loopback0":
                    interface_data['ipv4'] = f"{r_id}.{r_id}.{r_id}.{r_id}"
                    interface_data['mask'] = "/32"
                    continue

                neighbor = interface_data.get('ngbr')
                if not neighbor:
                    continue

                n_id = int(neighbor[1:])
                neighbor_as = router_to_as[str(n_id)]

                #  INTER-AS
                if neighbor_as != as_id:

                    if r_id < n_id:
                        ip = f"172.{as_id}.{neighbor_as}.1"
                    else:
                        ip = f"172.{as_id}.{neighbor_as}.2"

                    interface_data['ipv4'] = ip
                    interface_data['mask'] = "/30"

                #  INTRA-AS
                else:

                    subnet_id = link_counter[as_id]
                    link_counter[as_id] += 1

                    if r_id < n_id:
                        ip = f"{base_prefix}.{subnet_id}.1"
                    else:
                        ip = f"{base_prefix}.{subnet_id}.2"

                    interface_data['ipv4'] = ip
                    interface_data['mask'] = "/30"

    dump_intent(source, data)


def create_config_files(data):
    # Créer le dossier config s'il n'existe pas pour éviter le crash
    Path("config").mkdir(exist_ok=True)
    autonomous_systems = data.get('AS', {})
    for as_id, as_data in autonomous_systems.items():
        # On crée les fichiers de config de chaque routeur
        for router in as_data.get('routers', {}).keys():
            r_id = router[1:]
            open(f"config/{router}_i{r_id}_private-config.cfg", "w").close()
            open(f"config/{router}_i{r_id}_startup-config.cfg", "w").close()


def config_interfaces(data):  # on écrit dans les fichiers de config des routeurs
    autonomous_systems = data.get('AS', {})
    for as_id, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            r_id = router[1:]
            with open(f"config/{router}_i{r_id}_startup-config.cfg", "w", encoding='utf-8') as file:
                # Header Standard
                file.write(
                    f"!\nhostname R{r_id}\n!\nboot-start-marker\nboot-end-marker\n!\n")
                file.write(
                    "no aaa new-model\nip cef\nipv6 unicast-routing\nipv6 cef\n!\n")

                # Configuration des interfaces
                for interface, interface_data in router_data.get('interfaces', {}).items():
                    file.write(f"interface {interface}\n")
                    file.write(" no ip address\n")

                    # On utilise le masque spécifique (/128 ou /64) défini dans set_address
                    mask = interface_data.get('mask') or "/64"
                    ipv6 = interface_data.get('ipv6', '')

                    if ipv6:
                        if interface != "Loopback0":
                            file.write(" ipv6 enable\n")
                            file.write(" negotiation auto\n")
                            file.write(" no shutdown\n")
                        file.write(f" ipv6 address {ipv6}{mask}\n")
                    file.write("!\n")

                # on respecte la syntaxe des fichiers de config
                file.write("!\nip forward-protocol nd\n!\nno ip http server\nno ip http secure-server\n!\n!\n!\n!\ncontrol-plane\n!\nline con 0\n exec-timeout 0 0\n privilege level 15\n logging synchronous\nline vty 0 4\n login\n!\nend\n")

        rip_routing(as_id, data)  # on ajoute la config RIP si besoin
        Ospf_Routing(as_id, data)  # on ajoute la config OSPF si besoin
        writeBGPconfig(data)  # on ajoute la config BGP


# Exécution
source = 'intent.json'
data = load_intent(source)
set_prefix(data, source)
set_address(data, source)
dynamips = Path("Venezuela/project-files/dynamips")
create_config_files(data)
config_interfaces(data)
drag_and_drop(dynamips)
print("Configurations générées avec succès dans le dossier /config")
