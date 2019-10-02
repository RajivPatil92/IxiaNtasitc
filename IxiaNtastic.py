################################################################################
# Import Libraries
################################################################################
import IxNetwork
import time
import json
import yaml
from prettytable import PrettyTable
import logging


# DEFINE THE TRAFFIC ITEMS THAT YOU WANT THEM TO BE IN THE TABLE FOR STATISTICS
TRAFFIC_STATS = ['Tx Port', 'Rx Port', 'Traffic Item', 'Source/Dest Value Pair', 'Tx Frames', 'Rx Frames', 'Frames Delta', 'Loss %']
'''
<<<<<<<<<<<<<<<              POSSIBLE DEFINITIONS FOR TRAFFIC_STATS items            >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
['Tx Port', 'Rx Port', 'Traffic Item', 'Source/Dest Value Pair', 'Tx Frames', 'Rx Frames', 'Frames Delta', 'Loss %', 
 'Tx Frame Rate', 'Rx Frame Rate', 'Tx L1 Rate (bps)', 'Rx L1 Rate (bps)', 'Rx Bytes', 'Tx Rate (Bps)', 'Rx Rate (Bps)', 
 'Tx Rate (bps)', 'Rx Rate (bps)', 'Tx Rate (Kbps)', 'Rx Rate (Kbps)', 'Tx Rate (Mbps)', 'Rx Rate (Mbps)', 
 'Store-Forward Avg Latency (ns)', 'Store-Forward Min Latency (ns)', 'Store-Forward Max Latency (ns)', 'First TimeStamp', 
 'Last TimeStamp']
'''

# CHECK the TreeBreakdown Code to make Changes to the below List
SPECIAL_ATTR_LIST = ['-name','-connectedTo','-count','-multiplier','-numberOfAddressesAsy']

#Yaml file definition
YAML_FILE = "ixaDetails.yaml"

################################################################################################
#                                   YAML EXTRACTOR                                             #
#   THIS FUNCTION IS USED TO EXTRACT YAML-CONTENTS FROM  YAML_FILE WHICH IS LATER USED TO      #
#   TO PARSE TO CREATE TOPOLOGY AND CREATED TRAFFIC FLOWS                                      #
################################################################################################
def IxiaYamlExtractor():
    CaptureThat.info("````````````````````````````````` YAML PARSER ''''''''''''''''''''''''''''''''''''")
    with open(YAML_FILE) as f:
        yamlParser = yaml.load_all(f)
        print(yamlParser)
        for data in yamlParser:
            CaptureThat.info(data)
            return(data)

################################################################################################
#                                                                                              #
#*_*_*_*_*_*_*_*_*_*_*_*_*_*_*   CLASS IxiaConnector    *_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*#
#                                                                                              #
#   Init Variables                                                                             #
#       -> vmip: IP of System running IxNetwork                                                #
#       -> apiPort: TCP port of the Ixia API Server expecting connection (default: 8009)       #
#       -> chassis: DNS name of the Ixia-Chassis                                               #
#       -> ixVersion: Version of IxNetwork running on the Chassis                              #
#                                                                                              #
#   Public Functions:                                                                          #
#       -> ConnectPhysicalPorts():  Create Virtual Ports and attach the physical ports to it   #
#       -> treeBreakdown():         Main function to break YAML tree elements, parse and       #
#                                   create topology, scenarios and traffic elements.           #
#       -> setScenarios():          Function to create scenarios                               #
#       -> startProtocols():        Function to Start Protocols                                #
#       -> stopProtocols():         Function to stop Protocols                                 #
#       ----------------------------------------------------------------------------------     #
#       -> createTraffic():         Function to Create Traffic                                 #
#       -> StartTraffic():          Function to Start Traffic                                  #
#       -> StopTraffic():           Function to Stop Traffic                                   #
#       -> getTrafficStatistics():  Function to Obtain Statistics after running traffic        #
#                                                                                              #
################################################################################################
class IxiaConnector:
    def __init__(self, vmip, apiPort, chassis, ixVersion):
        self.vPortList = []
        self.InterfaceList = []
        self.ipList = []
        self.Topology = []
        self.IXIA_VM_IP = vmip
        self.IXIA_ServerPort = apiPort
        self.CHASSIS_DNS = chassis  # IP Fails to work. Always have the DNS entry of the IXIA
        self.CHASSIS_IXIA_VERSION = ixVersion
        self.ToplgyperPort = {}

        # Establishing Connection to the API Server
        self.ixNet = IxNetwork.IxNet()

        CaptureThat.debug("connecting to IxNetwork client")
        self.ixNet.connect(self.IXIA_VM_IP, '-port', self.IXIA_ServerPort, '-version', self.CHASSIS_IXIA_VERSION, '-setAttribute', 'strict')
        self.root = self.ixNet.getRoot()
        CaptureThat.info("Connected to IxNetwork client {} - {}".format(self.CHASSIS_DNS,self.IXIA_VM_IP))
        CaptureThat.info("Ixia Version {} running on the script".format(self.CHASSIS_IXIA_VERSION))
        print("Unable to Connect to IXIA-Network-VM. Ensure the API Server software is running and Try again")
        try:
            # Cleaning up IxNetwork
            CaptureThat.debug("Cleaning up IxNetwork...")
            self.ixNet.execute('newConfig')
        except:
            print("Unable to create a New Configuration. Please make sure there is no Active Configuration running on the VM")
            CaptureThat.fatal("Unable to create a New Configuration. Please make sure there is no Active Configuration running on the VM")

    def ConnectPhysicalPorts(self, listofPorts):
        # Assign real ports
        for every in listofPorts:
            self.__assignPort__(every)
        time.sleep(5)

    def __assignPort__(self, data):
        # Extracting the Independent Components from the Tuple
        # print(realPort)
        chassis1 = data[0]
        card1 = data[1]
        port1 = data[2]
        name = data[3]
        topologyInfo = data[4]

        # ------------------    Creating VirtualPort Object ------------------------
        vport = self.ixNet.add(self.root, 'vport')
        self.ixNet.commit()
        vport = self.ixNet.remapIds(vport)[0]
        self.ToplgyperPort[vport] = topologyInfo  # ------> Key Element of the Code. Topology Tree attached to virtual ports

        # Adding Topologies
        topo = self.ixNet.add(self.root, 'topology')
        self.ixNet.commit()
        self.ixNet.setAttribute(topo, '-vports', vport)

        # --------------------- Creating a Chassis Object   -----------------------------
        chassisObj1 = self.ixNet.add(self.root + '/availableHardware', 'chassis')
        self.ixNet.setAttribute(chassisObj1, '-hostname', chassis1)
        self.ixNet.commit()
        chassisObj1 = self.ixNet.remapIds(chassisObj1)[0]
        print(chassisObj1)

        # ---------------   Linking the Physical Port to the VirtualPort Object -------------------------
        cardPortRef1 = chassisObj1 + '/card:%s/port:%s' % (card1, port1)
        self.ixNet.setMultiAttribute(vport, '-connectedTo', cardPortRef1, '-rxMode', 'captureAndMeasure', '-name', name)
        self.ixNet.commit()

    def getVPorts(self):
        return self.ixNet.getList(self.root, 'vport')

    # Set Scenarios for the Ports added in the Scenario
    def setScenarios(self):
        self.deviceGroup = []

        topoList = self.ixNet.getList(self.root, 'topology')
        for key,value in self.ToplgyperPort.items():
            for i in topoList:
                if self.ixNet.getAttribute(i,'-vports')[0] == key:
                    CaptureThat.debug("VPORT_MATCH: Topology for specific vPort Found!!")
                    CaptureThat.debug("Preparing to Configure Device Groups")
                    topoInfo = self.ToplgyperPort[key]['deviceGroup']
                    topoPointer = i
                    break

            self.ixNet.add(topoPointer, 'deviceGroup')                  # Add Device-Groups to Topology
            self.ixNet.commit()                                         # Commit the Changes
            dg1 = self.ixNet.getList(topoPointer, 'deviceGroup')[0]     # Select the First device-Group (NOTE: Currently ONLY ONE DEVICE-GROUP
            print(topoInfo)                                             # is supported by the program. Will upgrade the code
            self.treeBreakdown('deviceGroup/1',dg1,topoInfo[0])
        CaptureThat.info("CONFIG_COMPLETE: Completed Configuring Scenarios")

    '''
    ########################################################################
    #                       HEART OF THE PROGRAM                           #
    ########################################################################
    #   IF NOT SURE, DO NOT EDIT THIS FUNCTION, THE PARSING MECHANISM      #
    #   MAY NOT WORK. THIS IS A RECURSIVE FUNCTION- BREAKS AND PARSES      #
    #   YAML CONTENT.                                                      #
    #   IF THE PARSING FAILS, MAKE SURE THE YAML IS PROPERLY CREATED       #
    # ---------------------------------------------------------------------#
    #   NOTE:                                                              # 
    #   *   FOR EVERY ITERABLE OBJECT IN IXIA-API, INCLUDE "/1" AFTER THE  #
    #   VARIABLE DEFINTION. FOR EXAMPLE, FOR MULTIPLE DEVICE-GROUP DEFIN-  #
    #   -ITIONS, USE "deviceGroup/1", instead of "deviceGroup. This will   #
    #   will be rectified in future updates. Contributions are welcome :)  #
    #                                                                      #
    #   *  IN ADDITION, CERTAIN VARIABLES ARE NOT HANDLED DUE TO RECURSIVE #
    #   CALL, ADD THEM TO "SPECIAL_ATTR_LIST" LIST PRESENT IN THE START    #
    #   OF THE CODE.                                                       #
    #                                                                      #
    ########################################################################
    '''
    def treeBreakdown(self,Parent,Pointer,data):
        newPtr = Pointer
        CaptureThat.debug("")
        CaptureThat.debug("#"*125)
        CaptureThat.debug("\tBeginning to scan the YAML objects for PARENT:{}".format(Parent))
        CaptureThat.debug("#" * 125)
        # Scan the Entire Tree including sub-tree structures
        for key,value in data.items():

            #Catch the Iterable Objects from the YAML file
            if "/1" in key:
                CaptureThat.debug("---------------------------CHILD-OBJECT-CONFIG------------------------------------")
                CaptureThat.debug("\tParent ---> {}".format(Parent))
                CaptureThat.debug("\tKey ---> {}".format(key))
                CaptureThat.debug("\tPointer ---> {}".format(newPtr))

                actualKey = key.replace("/1", "")
                d_ptr = self.ixNet.add(newPtr, actualKey)           # Add the Child-Object to Ixia-Device-Group tree Structure
                self.ixNet.commit()                                 # Commit the Changes
                newPtr = self.ixNet.getList(Pointer, actualKey)[0]  # Extract the Pointer for newly created child-object
                self.treeBreakdown(newPtr,newPtr,value)             # Perform a Recursive Call by Passing Child Objects and the sub-tree structure
                self.ixNet.commit()                                 # Once Completed, Perform the final Commit

            #Catch the Attribute type Variables
            elif '-' in key:
                CaptureThat.debug("-------------------------------ATTRIBUTE-CONFIG---------------------------------")
                CaptureThat.debug("\tParent ---> {}".format(Parent))
                CaptureThat.debug("\tKey  ---> {}".format(key))
                CaptureThat.debug("\tPointer ---> {}".format(Pointer))

                if key in SPECIAL_ATTR_LIST:                        # CAN BE MODIFIED FOR FUTURE USE, WITH RESPECT TO CONNECTOR LINK OPTIMIZATION
                    self.setMultiAttr(Pointer, key, value)
                else:                                               # The normal case will fall into this category
                    treepath = self.ixNet.getAttribute(Parent, key)
                    CaptureThat.debug("\tTreePath ---> {}".format(treepath))
                    self.setMultiAttr(treepath,key,value)
                self.ixNet.commit()
            newPtr = Pointer                                        # After every lookup, we re-define the Pointer


    def setMultiAttr(self,treePath, key, dataPtr, deviceGroup=None):
        CaptureThat.debug("\tATTR_CONFIG: Attribute ---> {}".format(key))
        CaptureThat.debug("\tATTR_CONFIG: Path ---> {}".format(treePath))
        CaptureThat.debug("\tATTR_CONFIG: Argument Received ---> {}".format(dataPtr))
        CaptureThat.debug("")

        try:
            if '/singleValue' in dataPtr.keys():
                singleVal = dataPtr['/singleValue']['-value']
                self.ixNet.setMultiAttribute(treePath + '/singleValue', '-value', singleVal)
            elif '/counter' in dataPtr.keys():
                startVal = dataPtr['/counter']['-start']
                stepVal = dataPtr['/counter']['-step']
                self.ixNet.setMultiAttribute(treePath + '/counter', '-start', startVal, '-step', stepVal)
            # ixNet.setMultiAttribute(ixNet.getAttribute(ipv4_1, '-address') + '/counter', '-start', '22.1.1.1', '-step', '0.0.1.0')
            CaptureThat.debug("\t<<<<<<<< Successfully Configured the Attribute {} >>>>>>>>>>>>".format(key))
            CaptureThat.debug("")
        except:
            CaptureThat.warning("")
            CaptureThat.warning("\tATTR_CONFIG_BYPASS: Attribute doesnot seem to be a multivalue object")
            CaptureThat.warning("\tATTR_CONFIG_BYPASS: Trying to configure as a constant")
            CaptureThat.warning("")
            try:
                if str(dataPtr).isdigit():
                    self.ixNet.setMultiAttribute(treePath, key, dataPtr)
                else:
                    self.ixNet.setMultiAttribute(treePath, key, dataPtr)
                CaptureThat.info("\t<<<<<<<<< Successfully Configured the Attribute {}  >>>>>>>>>>>".format(key))
            except:
                CaptureThat.fatal("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                CaptureThat.fatal("!!   ATTR_CONFIG_FAIL: Failed to Configure the Attribute {}".format(key))
                CaptureThat.fatal("!!   ATTR_CONFIG_FAIL: Path Recieved-> {}".format(treePath))
                CaptureThat.fatal("!!   ATTR_CONFIG_FAIL: Received Arguments-> {}".format(dataPtr))
                CaptureThat.fatal("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!    Exception Caught. Check the logs    !!!!!!!!!!!!!!")
        #    print("Caught key exception. Known Issue...")

    ################################################################################
    #                              Start All Protocols
    ################################################################################
    def startProtocols(self):
        print("Starting all Protocols")
        CaptureThat.info("-------------------------- STARTING PROTOCOLS -----------------------------------")
        self.ixNet.execute('startAllProtocols')
        CaptureThat.info("Starting All Protocols")
        print("Sleeping 30 seconds for Protocols to start")
        CaptureThat.debug("Sleep 30sec for protocols to start")
        time.sleep(30)

    ################################################################################
    #                               Stop all protocols
    ################################################################################
    def stopProtocols(self):
        CaptureThat.info("vvvvvvvvvvvvvvvvvvvvvvvvvv STOP PROTOCOL vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        print("Stopping all Protocols")
        self.ixNet.execute('stopAllProtocols')
        CaptureThat.info('Stopped protocols')

    ################################################################################
    #                           Configure L2-L3 traffic
    ################################################################################
    def createTraffic(self,Name,source,destination,PktSize = 1500,PercentLineRate = 10,PktCount = 1000000):
        CaptureThat.debug("Configuring L2-L3 Traffic Item")
        print("Configuring L2-L3 Traffic Item")
        ti1 = self.ixNet.add(self.ixNet.getRoot() + '/traffic', 'trafficItem')

        self.ixNet.setMultiAttribute(ti1,
                                     '-name', 'Traffic IPv4',
                                     '-trafficType', 'ipv4',
                                     '-allowSelfDestined', False,
                                     '-trafficItemType', 'l2L3',
                                     '-mergeDestinations', True,
                                     '-egressEnabled', False,
                                     '-srcDestMesh', 'manyToMany',
                                     '-enabled', True,
                                     '-routeMesh', 'fullMesh',
                                     '-transmitMode', 'interleaved',
                                     '-biDirectional', True,
                                     '-hostsPerNetwork', 1)
        self.ixNet.commit()
        self.ixNet.setAttribute(ti1, '-trafficType', 'ipv4')
        self.ixNet.commit()
        self.ixNet.add(ti1, 'endpointSet',
                  '-name', Name,                                                # Function Argument-1
                  '-sources', source,                                           # Function Argument-2
                  '-destinations', destination,                                 # Function Argument-3
                  '-sourceFilter', '',
                  '-destinationFilter', '')
        self.ixNet.commit()
        self.ixNet.setMultiAttribute(ti1 + "/configElement:1/frameSize",
                                '-type', 'fixed',
                                '-fixedSize', PktSize)                          # Function Argument-4
        self.ixNet.setMultiAttribute(ti1 + "/configElement:1/frameRate",
                                '-type', 'percentLineRate',
                                '-rate', PercentLineRate)                       # Function Argument-5
        self.ixNet.setMultiAttribute(ti1 + "/configElement:1/transmissionControl",
                                '-duration', 1,
                                '-iterationCount', 1,
                                '-startDelayUnits', 'bytes',
                                '-minGapBytes', 12,
                                '-frameCount', PktCount,                        # Function Argument-6
                                '-type', 'fixedFrameCount',
                                '-interBurstGapUnits', 'nanoseconds',
                                '-interBurstGap', 0,
                                '-enableInterBurstGap', False,
                                '-interStreamGap', 0,
                                '-repeatBurst', 1,
                                '-enableInterStreamGap', False,
                                '-startDelay', 0,
                                '-burstPacketCount', 1, )
        self.ixNet.setMultiAttribute(ti1 + "/tracking", '-trackBy', ['sourceDestValuePair0'])
        self.ixNet.commit()
        return ti1

    ################################################################################
    #                                   start traffic
    ################################################################################
    def StartTraffic(self,TrafficItem):
        CaptureThat.debug("Starting L2/L3 Traffic")
        r = self.ixNet.getRoot()
        self.ixNet.execute('generate', TrafficItem)
        self.ixNet.execute('apply', r + '/traffic')
        self.ixNet.execute('start', r + '/traffic')
        time.sleep(15)

    ################################################################################
    #                               Stop L2/L3 traffic
    ################################################################################
    def StopTraffic(self):
        CaptureThat.debug('Stopping L2/L3 traffic')
        self.ixNet.execute('stop', self.ixNet.getRoot() + '/traffic')
        time.sleep(5)

    ###############################################################################
    #               Retrieve L2/L3 traffic item statistics
    ###############################################################################
    def getTrafficStatistics(self):
        Stat_Table = PrettyTable()
        CaptureThat.debug('Verifying all the L2-L3 traffic stats')
        viewPage = '::ixNet::OBJ-/statistics/view:"Flow Statistics"/page'
        statcap = self.ixNet.getAttribute(viewPage, '-columnCaptions')
        #Custom Table for Items. Edit the TRAFFIC_STATS list to modify the output
        Stat_Table.field_names = TRAFFIC_STATS
        CaptureThat.debug("Extracting Statistics from the executed Traffic Item")
        for statValList in self.ixNet.getAttribute(viewPage, '-rowValues'):
            rowData = []
            for statVal in statValList:
                index = 0
                for satIndv in statVal:
                    #CherryPicking Process
                    if statcap[index] in TRAFFIC_STATS:
                        rowData.append(satIndv)
                    index = index + 1
            # Add the Row Details
            Stat_Table.add_row(rowData)
        #Print the results
        print(Stat_Table)
        CaptureThat.debug("Completed Traffic Statistics")
        CaptureThat.debug("")
        CaptureThat.debug("")
        CaptureThat.info("\n"+str(Stat_Table))



if __name__ == '__main__':
    #---------------------- LOGGING BLOCK   -----------------------------------
    # Create and configure logger
    logging.basicConfig(filename="IxiaNtastic.log",format='%(asctime)s %(message)s',filemode='w')
    # Creating an Logger object
    CaptureThat = logging.getLogger()
    # Setting the threshold of logger to DEBUG
    CaptureThat.setLevel(logging.DEBUG)

    # ------------------- Extract Basic IXIA Details for establishing Connection ---------------------------
    ChassisName = []
    PortTupleList = []
    IxiaJson = IxiaYamlExtractor()
    print(IxiaJson)
    VM_IP = IxiaJson['ixiaVM']
    API_port = IxiaJson['ixiaAPIServerPort']
    ixVersion = IxiaJson['ixVersion']

    # --------------------------------- Get Details of All Chassis ------------------------------------
    for every in IxiaJson['ixiaChassis']:
        for eachPort in every["ports"]:
            tup = (every["name"], eachPort["slot"], eachPort["port"],eachPort["topology"]["name"],eachPort["topology"])
            PortTupleList.append(tup)
        ChassisName.append(every)

    #---------------------------------- Ixia Connection-Handler ------------------------------------
    ixHandler = IxiaConnector(VM_IP, API_port, ChassisName[0], ixVersion)
    # Let's start assigning Physical Ports
    ixHandler.ConnectPhysicalPorts(PortTupleList)

    ixHandler.setScenarios()
    ixHandler.startProtocols()
    TrafficItem = ixHandler.createTraffic('Simple_IPv4', ["::ixNet::OBJ-/topology:1/deviceGroup:1/ethernet:1/ipv4:1"],
                                     ["::ixNet::OBJ-/topology:2/deviceGroup:1/ethernet:1/ipv4:1"])

    #-------------- Executing Traffic Item  -----------------------
    ixHandler.StartTraffic(TrafficItem)
    ixHandler.StopTraffic()
    ixHandler.getTrafficStatistics()
    CaptureThat.info("")
    CaptureThat.info("")
    CaptureThat.info("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@   <<<<    END OF SCRIPT  >>>>>   @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

    #   ------------------  END OF CODE -----------------

