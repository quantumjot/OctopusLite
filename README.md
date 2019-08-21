# OctopusLite

**WORK IN PROGRESS**
*Please note, this is not the full repository (yet)*


OctopusLite is a simple script based timelapse acquisition system. It uses other open-source hardware control software for image acquisition and some hardware synchronisation. Mostly takes care of stage control for long timelapse experiments. Integrates with other real-time image processing software (such as *Sequitr* and *BayesianTracker*) via RPC, to enable remote (automated) control over image acquisition.

### TODO
+ [x] Read/Set stage parameters from stage controller object
+ [x] Automatic placement of FOVs on microplates
+ [ ] Better hardware triggering of light sources
+ [ ] Finalise RPC control protocol
