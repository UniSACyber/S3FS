# SDN-based Space Systems Framework for Simulations (S3FS)

This project developed a simulation framework for SDN-based space systems for the Earth Observation use case. The framework implements dynamic Inter-Satellite Links (ISL) and a dynamic topology based on the orbital dynamics of the Walker Constellation. The framework is designed to simulate a constellation of satellites in low Earth orbit (LEO) that communicate with ground stations via satellite terminals connected through an SDN network. The framework allows for experimentation with different routing protocols through the POX controller.

For a detailed discussion of the S3FS framework refer to the following reference publication:

- Uhongora, U., Thinyane, M., & Law, YW. (2024) __"Development of an SDN-based Space Systems Simulation Framework for Intrusion Detection."__ IEEE International Conference on Cyber Security and Resilience (IEEE CSR), *__Forthcoming__*.

## Simulation framework features:

- **Simulated Walker Constellation:** The simulation comprises a Walker-Delta constellation of 20 satellites arranged in a typical orbit pattern around Earth. This is simulated using the Satellite Communications Toolbox of MATLAB with the following parameters: radius = 7200km, inclination = 70 degrees, number of orbital planes = 4, phasing = 1, and argument of latitute = 15 degrees. The orbital motion is simulated for 24 hours at per second resolution. 
- **SDN Network Simulation:** The simulation is based on a Software Defined Networking (SDN) architecture, where the network control plane is separated from the data forwarding elements. This allows for flexible configuration and management of the satellite network through programmable switches called OpenFlow switches. The framework utilizes the Mininet network simulation tool. 
- **Dynamic Inter-Satellite Links (ISL):** The framework dynamically creates ISLs based on the relative positions of satellites in orbit, ensuring that communication links are established only when necessary for data exchange between satellites and ground stations. The connectivity between the network nodes (i.e., the satellites and the ground station), represented as adjacency metrices between the networks nodes, across all the simulation intervals is available as a 3D numpy array in the repository (`isldata.npy`).  

   - This ISL connectivity data has a reduced per-minute resolution and therefore has a (21 x 21 x 1441) shape and contains binary values indicating whether an ISL exists between two nodes at a given interval. The graphic below shows an example ISL connectivity matrix for a single simulation interval.
   <p align="center">
    <img src="graphics/isldata.png" alt="ISL Connectivity Matrix for interval 7" width="400">
   </p>
- **POX Controller:** The framework uses the POX controller to experiment with different routing protocols, allowing users to test and evaluate the performance of various networking strategies within the simulated environment. However, the framework can be run with an other suitable controller as well.
- **Traffic Generation:** The simulation framework includes a traffic generation functionality that allows for the creation of normal network traffic and attack network traffic patterns between satellites and ground stations. The normal traffic is generated for the Earth Observation use case where data from the satellites are transmitted to ground station, while the attack traffic represents various types of cyber-attacks such as denial-of-service (DoS) attacks or reconnaisance attacks targeting the variuos elements of the satellite network.
- **Simulation Metrics:** The simulation framework provides two sets of metrics that can be used to evaluate the performance of the simulated network. 
   - The first set of metrics (stored in the file `metrics.csv`) track the number of network interfances added and removed, the elapsed CPU and wall time for the network reconfiguration, and to the duration for the traceability test between the satellites and the ground station. 
   - The second set of metrics (stored in the file `pingmetrics.csv`) tracks the traceability of the ground station from each satellite by pinging the ground station from each satellite. These metrics track the number of pings sent and received, as well at the minimum, maximum, average, and standard deviation round-trip time for each traceability test.
