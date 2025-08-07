import sys, getopt, time, threading, re, random
from enum import IntEnum
import numpy as np
import pandas as pd
import networkx as nx
from mininet.net import Mininet
from mininet.clean import Cleanup
from mininet.node import RemoteController, Switch, OVSSwitch

ISLDATA_FILE = 'data/walker_delta_20.npy' # Path to the ISL data file
# ISL data file should be a numpy array with shape (NUM_NODES, NUM_NODES, NUM_INTERVALS)
# where NUM_NODES is the number of nodes in the network and NUM_INTERVALS is the number of time intervals

NUM_NODES = 21 # Number of nodes in the network
# This should match the number of nodes in the ISL data file

CONTROLLER_IP = '127.0.0.1' # IP address of the controller
# This should be the IP address of the controller running POX, ONOS, ODL, or any other SDN controller
# If you are running the controller on a different machine, change this to the appropriate IP address
# If you are running the controller on the same machine, you can leave it as is

BROADCAST_IP = '10.0.0.255' # Broadcast IP address for the network
OPENFLOW_VERSION = 'OpenFlow14' # OpenFlow version to use
SIMULATION_INTERVAL = 60 # Simulation interval in seconds
# This is the sleep time between simulation intervals, it can be changed to a lower value for faster simulations
# or a higher value for slower simulations, depending on the use case

TMP_STORAGE_INTERVAL = 100 # Interval for temporary storage of metrics
PING_TIMEOUT = 5 # Timeout for ping commands in seconds
TESTING = False # If set to True, the simulation will run in the test mode with a shorter interval

DO_DEBUG = True # If set to True, the simulation will print debug messages

STOP_SIMULATION = False 

# For normal traffic simulation
TRANSMISSION_PORT = 5789
TRANSMISSION_INTERVAL = 60
NO_BUNDLES_TO_SEND = 1441
BUNDLE_SIZE = '20M'

# For attack simulation
ATTACK_HOST = "h25"
VICTIM_HOST = "h0"
ATTACK_PACKETS_NUM = 100
ATTACK_PORT = 8000

class TheAttack(IntEnum):
    NONE = 0
    SYN_FLOOD = 1
    SYN_FLOW_FLOOD = 2
    PORT_SCAN = 3
    SMURF = 4
    
def main(argv):
    global SIMULATION_INTERVAL, TMP_STORAGE_INTERVAL, TESTING, ATTACK_HOST, VICTIM_HOST
    isldata = loadISLdata()

    try:
        opts, args = getopt.getopt(argv, "tra:i:", ["test", "interval=", "run", "attack="])
    except:
        print('simulationscript.py -t -r -a <attack> -i <interval>')
        sys.exit(1)
        
    if len(opts) == 0:
        print('Info: No options provided, running the simulation in the test mode')
        
        SIMULATION_INTERVAL = 10
        TMP_STORAGE_INTERVAL = 3
        TESTING = True
        
        runSimulation(isldata, 3)
        
    for opt, arg in opts:
        if opt in ("-t", "--test"):
            if DO_DEBUG: print('Info: Testing the simulation')
            
            SIMULATION_INTERVAL = 10
            TMP_STORAGE_INTERVAL = 3
            TESTING = True
            
            runSimulation(isldata, 3)
        elif opt in ("-i", "--interval"):
            interval = int(arg)
            if DO_DEBUG: print(f'Info: Simulation interval set to: {interval}')
            runSimulation(isldata, interval)
        elif opt in ("-r", "--run"):
            runSimulation(isldata)
        elif opt in ("-a", "--attack"):
            attackNum = int(arg)
            
            SIMULATION_INTERVAL = 10
            TMP_STORAGE_INTERVAL = 3
            TESTING = True
            
            if attackNum not in list(map(int, TheAttack)):
                print(f'Error: Incorrect attack number specified')
            else:
                if DO_DEBUG: print(f'Info: {TheAttack(attackNum).name} Attack simulation from ({ATTACK_HOST}) to ({VICTIM_HOST})')
                runSimulation(isldata, interval = 5, attacking = TheAttack(attackNum))
                
    print('Info: S3FS simulation script finished running')
    sys.exit(0)
    
def runSimulation(data, interval = 1440, attacking = TheAttack.NONE):  
    simulation_start = time.time()
    G = nx.Graph()
    nodeids = range(data.shape[0])
    G.add_nodes_from(nodeids)
    
    if DO_DEBUG: print('Info: Cleaning up Mininet')
    Cleanup.cleanup()
    
    if DO_DEBUG: print('Info: Connecting to the controller')
    c3 = RemoteController('c3', ip=CONTROLLER_IP, port=6633, protocols=OPENFLOW_VERSION)
    SatNet = initializeNetwork(G) if attacking is TheAttack.NONE else initializeAttackNetwork(G)
    SatNet.addController(c3)
    
    SatNet.start()
    
    configureNodes(SatNet)
        
    if DO_DEBUG: print(f'Instruction: ######### START YOUR TCPDUMP ON SPECIFIC INTERFACES ###########')
    time.sleep(15)
    
    def simulationThread():
        metrics = []
        pingmetrics = {}
        for i in range(data.shape[2]):
            if i > interval or STOP_SIMULATION:
                break
            
            start = time.time()
            cpustart = time.process_time()
            
            G.clear_edges()
            
            edges = list(zip(*np.where(data[:,:,i] == 1)))
            G.add_edges_from(edges)
            
            added, removed = updateNetwork(SatNet, G)
            
            end = time.time()
            cpuend = time.process_time()
            
            pingstats = pingGroundStation(SatNet, "h0")
            pingmetrics[i] = pingstats
            
            pingduration = time.time() - end
            elapsed = end - start
            processing = cpuend - cpustart
            
            metrics.append([i, added, removed, elapsed, processing, pingduration])
            
            print(f'\n######## Interval: {i} ############### Added: {added} | Removed: {removed} | Time : {elapsed:.2f} ({processing:.2f}) | Pings: {pingduration:.2f} seconds')
            
            if i % TMP_STORAGE_INTERVAL == 0:
                tmpmetrics = pd.DataFrame(metrics)
                tmpmetrics.to_csv('tmpmetrics.csv', index = False)        
            
            time.sleep(SIMULATION_INTERVAL)
            
        
        print(f'\n----------------- Done with the animation | Total duration = {(time.time() - simulation_start):.2f} seconds ---------------------\n')
                
        themetrics = pd.DataFrame(metrics)
        themetrics.columns = ['interval', 'added', 'removed', 'elapsed', 'processing', 'pings']
        themetrics.to_csv('metrics.csv', index = False)
        
        thepingmetrics = pd.DataFrame(pingmetrics)
        # print(thepingmetrics)
        thepingmetrics.to_csv('pingmetrics.csv', index=False)
        
        print('\n------------------ Info: Cleaning up after myself --------------------')
        Cleanup.cleanup()

    def attackThread():
        if DO_DEBUG: print(f'Info: Starting the attack thread - setting up the victim')
        attackHost = SatNet.get(ATTACK_HOST)
        victimHost = SatNet.get(VICTIM_HOST)
        target_ip = victimHost.IP()
        target_port = ATTACK_PORT
        
        victimHost.pexec(f'python -m http.server {target_port} &')
 
        if DO_DEBUG: print(f'Info: Initializing the attacker host for {attacking.name}')
        
        match attacking:
            case TheAttack.NONE:
                print(f'Info: Just chilling not attacking anyone')
            case TheAttack.SYN_FLOOD:
                attackHost.pexec(f'wget http://{target_ip}:{target_port}')
                attackHost.pexec(f'hping3 -c {ATTACK_PACKETS_NUM} -U -d 120 -S -w 64 -p {target_port} --flood {target_ip}')
            case TheAttack.SYN_FLOW_FLOOD:
                attackHost.pexec(f'wget http://{target_ip}:{target_port}')
                attackHost.pexec(f'hping3 -c {ATTACK_PACKETS_NUM} -U -d 120 -S -w 64 -p {target_port} --flood --rand-source {target_ip}')
            case TheAttack.SMURF:
                attackHost.pexec(f'hping3 -1 --flood --spoof {target_ip} {BROADCAST_IP}')
            case TheAttack.PORT_SCAN:
                attackHost.pexec(f'nmap -p0- -A -T4 {target_ip}')
            case _:
                if DO_DEBUG: print(f'Error: Unknown attack type {attacking}')
 
    simThread = threading.Thread(target=simulationThread)
    simThread.start()
    
    attThread = threading.Thread(target=attackThread)
    if attacking is not TheAttack.NONE: attThread.start()
    
    return 
    
def loadISLdata():
    data = None
    try:
        data = np.load(ISLDATA_FILE)
    except:
        print('Error: Could not load the ISL interval data')
        sys.exit(1)
        
    return data

def initializeAttackNetwork(graph):
    net = initializeNetwork(graph)
    
    h25 = net.addHost("h25")
    s0 = net.get("s0")
    
    net.addLink(h25,s0)
    if DO_DEBUG: print(f'Just added and linked (h25) to (s0)')
    
    return net

def initializeNetwork(graph):
    net = Mininet(controller=None, topo = None, build = False)
    
    # Construct mininet
    for n in graph.nodes:
        tmp_name = f's{n}'
        tmp_sat_node = f'h{n}'
        addedSwitch = net.addSwitch(tmp_name, protocols="OpenFlow14")
        # Add single host on designated switches
        addedHost = net.addHost(tmp_sat_node)

        # directly add the link between hosts and their gateways and attach - to activate interfaces
        net.addLink(tmp_name, tmp_sat_node)
        
    # Connect your switches to each other as defined in networkx graph
    for (n1, n2) in graph.edges:
        net.addLink(f's{n1}',f's{n2}')
        
    attachSwitches(net.switches)
    
    return net

def attachSwitches(switches):
    for switch in switches:
        if DO_DEBUG: print(f'Activating switch({switch})')
        [switch.attach(f'{x}') for x in switch.ports]  

def attachPorts(interfaces):
    for interface in interfaces:
        if isinstance(interface.node, Switch):
            if DO_DEBUG: print(f'Activating interface({interface})')
            interface.node.attach(interface)
        else:
            if DO_DEBUG: print(f'Info: Interface({interface}) node is not a switch')
        
def detachPorts(interfaces):
    for interface in interfaces:
        if isinstance(interface.node, Switch):
            if DO_DEBUG: print(f'Deactivating interface({interface})')
            interface.node.detach(interface)
        else:
            if DO_DEBUG: print(f'Info: Interface({interface}) node is not a switch')

def configureNodes(net, attacking = TheAttack.NONE):
    #TODO configure the ground station to store the sent info from the satellites
    
    if DO_DEBUG: print ("Info: Disabling ipv6 and setting up transmission")
    GS_IP = net.get('h0').IP()
    
    for h in net.hosts:        
        h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        
        if attacking is TheAttack.NONE: #TODO for the attack simulations, do not generate normal traffic - think carefully about this 
            if(str(h) == 'h0'):
                h.sendCmd(f'nc -lk -p {TRANSMISSION_PORT} &> /dev/null')
            else:
                h.sendCmd(f'for i in {{1..{NO_BUNDLES_TO_SEND}}}; do dd if=/dev/urandom count=1 bs={BUNDLE_SIZE} | nc -w 5 {GS_IP} {TRANSMISSION_PORT} ; sleep {TRANSMISSION_INTERVAL}; done')

    for sw in net.switches:
        sw.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        sw.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        sw.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

def linkExists(net, node1, node2):
    x = str(node1)
    y = str(node2)   
    
    result = False
    for link in net.links:
        if not (link.intf1 and link.intf2):
            continue
        
        a = (link.intf1.node.name.replace("s", ""), link.intf2.node.name.replace("s", ""))            
        result = result or ((x, y) == a or (y, x) == a)
        
        if result:
            break

    return result        

def updateNetwork(net, graph):
    #remove those in mininet not in graph
    addedPorts = []
    removedPorts = []
    
    for link in net.links:
        if not (link.intf1 and link.intf2):
            continue
            
        if (str(link.intf1.node).startswith("h") or str(link.intf2.node).startswith("h")):
            continue
    
        mlink1 = (int(link.intf1.node.name.replace("s", "")), int(link.intf2.node.name.replace("s", "")))
        mlink2 = (int(link.intf2.node.name.replace("s", "")), int(link.intf1.node.name.replace("s", "")))
        
        if(mlink1 not in graph.edges) or (mlink2 not in graph.edges):
            removedPorts.extend([link.intf1, link.intf2])
            if DO_DEBUG: print(f'--- Deleting {mlink1} / {mlink2}')
            link.delete() #linkdown
    
    # add those in graph not in mininet
    for (n1, n2) in graph.edges:
        connected = linkExists(net, n1, n2) 
        
        if not connected:
            switch1 = f's{n1}'
            switch2 = f's{n2}'
            lnk = net.addLink(switch1, switch2) 
            addedPorts.extend([lnk.intf1, lnk.intf2])
            if DO_DEBUG: print(f'+++ Added {switch1} to {switch2}')
            
    attachPorts(addedPorts)
    detachPorts(removedPorts)
    
    return len(addedPorts), len(removedPorts)

def parsePingResults( pingOutput ):
    errorTuple = (1, 0, 0, 0, 0, 0)
    # Check for downed link
    r = r'[uU]nreachable'
    m = re.search( r, pingOutput )
    if m is not None:
        return errorTuple
    r = r'(\d+) packets transmitted, (\d+)( packets)? received'
    m = re.search( r, pingOutput )
    if m is None:
        return errorTuple
    sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
    r = r'rtt min/avg/max/mdev = '
    r += r'(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms'
    m = re.search( r, pingOutput )
    if m is None:
        return errorTuple
    
    rttmin = float( m.group( 1 ) )
    rttavg = float( m.group( 2 ) )
    rttmax = float( m.group( 3 ) )
    rttdev = float( m.group( 4 ) )
    return sent, received, rttmin, rttavg, rttmax, rttdev

def pingGroundStation(net, gs="h0"):
    GS = net.get(gs)
    results = []
    
    for host in net.hosts:
        
        if(str(host) != str(GS)):
            if host.intfs:
                result = host.pexec( f'ping -c 2 -W {PING_TIMEOUT} {GS.IP()}' )
                
                sent, received, rttmin, rttavg, rttmax, rttdev = parsePingResults( " ".join(str(val) for val in result) )
                results.append(f'({host},{sent},{received},{rttmin},{rttavg},{rttmax},{rttdev})')
    
    print (f'\n***** Reachability Test to Ground Station ({GS}) ----- (host, sent, received, RTT min, RTT avg, RTT max, RTT dev) ***** \n {" , ".join(results)}') 
            
    return results

def random_mac():
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))
 
def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

if __name__ == "__main__":
    main(sys.argv[1:])