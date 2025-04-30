# SDN-based Space Systems Framework for Simulations (S3FS)

This project developed a simulation framework for SDN-based space systems for the Earth Observation use case. The framework implements dynamic Inter-Satellite Links (ISL) and a dynamic topology based on the orbital dynamics of the Walker Constellation. The framework is designed to simulate a constellation of satellites in low Earth orbit (LEO) that communicate with ground stations via satellite terminals connected through an SDN network. The framework allows for experimentation with different routing protocols through the POX controller.

For a detailed discussion of the S3FS framework refer to the following reference publication:

- Uhongora, U., Thinyane, M., & Law, YW. (2024) __"Development of an SDN-based Space Systems Simulation Framework for Intrusion Detection."__ IEEE International Conference on Cyber Security and Resilience (IEEE CSR), *__Forthcoming__*.

## Simulation framework features and details:

- **Simulated Walker Constellation:** The simulation comprises a Walker-Delta constellation of 20 satellites arranged in a typical orbit pattern around Earth. This is simulated using the Satellite Communications Toolbox of MATLAB with the following parameters: radius = 7200km, inclination = 70 degrees, number of orbital planes = 4, phasing = 1, and argument of latitute = 15 degrees. The orbital motion is simulated for 24 hours at per second resolution. 
- **SDN Network Simulation:** The simulation is based on a Software Defined Networking (SDN) architecture, where the network control plane is separated from the data forwarding elements. This allows for flexible configuration and management of the satellite network through programmable switches called OpenFlow switches. The framework utilizes the Mininet network simulation tool. 
- **Dynamic Inter-Satellite Links (ISL):** The framework dynamically creates ISLs based on the relative positions of satellites in orbit, ensuring that communication links are established only when necessary for data exchange between satellites and ground stations.
- **POX Controller:** The framework uses the POX controller to experiment with different routing protocols, allowing users to test and evaluate the performance of various networking strategies within the simulated environment. However, the framework can be run with an other suitable controller as well.
