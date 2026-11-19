# IMU teaching: hardware and reusable sources

Research snapshot: 2026-11-19. Scope: public primary sources for explaining sensor physics, practical fabrication/grade distinctions, and reusable learning assets. Manufacturer pages and university course material are preferred; source dates/spec revisions should be checked again before procurement.

## Teaching spine and sensor physics

- **Accelerometer / MEMS proof mass.** Analog Devices explains that MEMS accelerometers measure displacement of a suspended mass, commonly through capacitance; its diagrams make the spring-mass and differential-capacitance model easy to translate into a classroom animation. [ADI, “Accelerometer and Gyroscopes Sensors: Operation, Sensing, and Applications”](https://www.analog.com/en/resources/technical-articles/accelerometer-and-gyroscopes-sensors-operation-sensing-and-applications.html) and [accelerometer glossary](https://www.analog.com/en/resources/glossary/accelerometer.html).
- **Gyro / Coriolis.** The ADI article shows a driven resonant mass and an orthogonal sense mode: rotation creates Coriolis acceleration and a measurable cross-axis displacement. This supports a staged explanation (drive motion → rotate frame → Coriolis force → sense capacitance → angular-rate output), while explicitly distinguishing a gyro from an accelerometer.
- **Magnetometer modalities.** A Hall element converts perpendicular magnetic field and current into transverse Hall voltage; TI’s article/training resources cover element, signal conditioning, and applications ([TI Hall effect](https://www.ti.com/document-viewer/lit/html/sszt164), [Precision Labs magnetic sensors](https://training-dev.ti.com/en-us/design-development/educational-resources/video/series/precision-labs/ti-precision-labs-magnetic-sensors)). AMR is resistance change with field orientation; ADI notes its 180° ambiguity for a single dipole ([ADI AN-1314](https://www.analog.com/en/resources/app-notes/an-1314.html)). TMR is a magnetoresistive effect using quantum tunneling; TDK gives a manufacturer explanation and angle-sensor guide ([TDK TMR overview](https://www.micronas.tdk.com/en/technologies/tmr-angle-sensors), [TDK guide](https://product.tdk.com/en/products/selectionguide/tmr-angle.html)). NIST provides authoritative background on real AMR/TMR sensor characteristics and noise, useful for a more advanced module ([NIST MR sensor noise](https://www.nist.gov/publications/low-frequency-noise-measurements-commercial-magnetoresistive-magnetic-field-sensors)).

## Fabrication and course precedents

- ETH Zurich’s **Embedded MEMS Lab** has students fabricate an accelerometer and covers photolithography, dry/wet and sacrificial etching, critical-point drying, packaging, electrical connection, testing, and characterization. This is a strong real-world process-flow reference; cleanroom access makes it unsuitable as a default remote activity. [ETH course catalogue](https://vvz.ethz.ch/Vorlesungsverzeichnis/sucheLehrangebot.view?abschnittId=120302&ansicht=2&lang=en&seite=0&semkez=2026S).
- Singapore University of Technology and Design’s MEMS course combines fundamentals, process flow, packaging, and cleanroom work ([SUTD course](https://www.sutd.edu.sg/course/30-113-design-and-fabrication-of-microelectromechanical-systems-mems)). Washington University’s course overview names deposition, lithography, wet/dry etching, packaging, and device design/fabrication as student outcomes ([WashU IMSE](https://imse.washu.edu/facilities/micronanofab/education.html)). These are good sources for separating what can be taught with an explainer from what requires a fab.
- Useful fabrication story for the explainer: silicon/device layer + patterned anchors/springs/proof mass + sacrificial layer removal/release + drying/package + electrical readout. The precise stack and etch sequence are process-specific; do not depict one university flow as universal commercial manufacturing.

## Actual parts and performance context

Use datasheets as primary examples for range, bandwidth, noise, interfaces, package, calibration, and limitations—not as substitutes for exposing the microscopic sensing mechanism.

| Part / source | What it teaches |
|---|---|
| [Bosch BMI270 datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi270-ds000.pdf) | Consumer 6-axis accel+gyro; selectable ranges, sample rates, filters, FIFO and power modes. Good example of a calibrated digital product rather than a bare sensor structure. |
| [ST LSM6DSOX datasheet](https://www.st.com/resource/en/datasheet/lsm6dsox.pdf) | 6-axis system-in-package; interfaces, operating modes, digital filtering and embedded functions. |
| [ADI ADXL354/355 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/adxl354_adxl355.pdf) | Dedicated low-noise accelerometer; contrast consumer IMUs with higher-stability measurement-grade components. |
| [ST LIS2MDL datasheet](https://www.st.com/resource/en/datasheet/lis2mdl.pdf) | 3-axis digital magnetometer; range, noise, power, interfaces and application constraints. |
| [TDK TAS2141-AAAB product data](https://product.tdk.com/en/search/sensor/angle/tmr-angle/info?part_no=TAS2141-AAAB) | TMR angle sensor; illustrates that magnetic sensor technologies also appear as analog position sensors, not only 3-axis compass ICs. |

**Grade framing:** show consumer/mobile, industrial/robotics, and tactical/navigation as application/performance classes, not a single sensor taxonomy. Datasheets expose the measurable axes (bias stability, noise density, range, bandwidth, temperature sensitivity, vibration/shock, calibration); “grade” is not a standardized label across vendors. Avoid claiming a particular chip is tactical-grade unless its vendor explicitly specifies it.

## Interactive and open-source assets

- [Accelerometer simulation (RitvikModani)](https://github.com/RitvikModani/accelerometer-simulation): single-file HTML interactive with gravity projection, telemetry and oscilloscope. Useful as a reference for an approachable browser interaction; validate its equations/licence before reuse.
- [RWTH IMU-Simulator](https://github.com/rwth-irt/IMU-Simulator): C++/ROS 2 measurement simulator with gravity/Earth rotation, bias, scale/misalignment, stochastic noise, saturation and quantization. Strong advanced exercise/reusable model, but not a proof-mass visualizer.
- [INSTINCT IMU Simulator Node](https://unistuttgart-ins.github.io/INSTINCT/imu_simulator_node.html): interactive configuration for trajectory and physical effects, including Coriolis acceleration; useful for systems-level exploration.
- [Open-source MEMS inertial co-optimization paper/code context](https://pmc.ncbi.nlm.nih.gov/articles/PMC8777840/): Python system-level electromechanical simulation of a capacitive accelerometer and Coriolis vibratory gyro. More engineering depth than introductory teaching.
- TI’s [Precision Labs magnetic sensors](https://training-dev.ti.com/en-us/design-development/educational-resources/video/series/precision-labs/ti-precision-labs-magnetic-sensors) supplies reusable short lessons for Hall-based sensing and specifications; use as source/reference rather than assuming an existing interactive AMR/TMR model.

## Implications for an IMU learning experience

1. Make the core interaction a causal model: let learners set linear acceleration/tilt, gyro drive amplitude/rotation, and magnetic field direction; show proof-mass displacement or field transduction, then expose digitized readings and failure modes.
2. Treat accelerometer, gyro and magnetometer as physically distinct transducers. The magnetometer comparison should contrast Hall voltage with AMR/TMR resistance response; avoid labeling every magnetometer as Hall or implying the magnetic sensor is part of every IMU.
3. Pair conceptual visualizations with actual datasheet plots/specs so learners see where ideal models end (bias, noise, range clipping, bandwidth, temperature, magnetic interference, calibration).
4. Use fabrication as a process-flow narrative and optional advanced course/lab pathway. Releasing a working MEMS device is specialized cleanroom work; for broad access, simulate the process and use a breakout board for measurable sensor data.
5. Existing simulators mostly model board-level sensor outputs, navigation effects, or inertial measurement errors. The sources above did not reveal a single open interactive teaching tool that unifies MEMS proof-mass mechanics, Coriolis drive/sense dynamics, Hall/AMR/TMR transduction, fabrication and grade-specific datasheets. That integration is a reasonable differentiator (inference from the surveyed sources).
