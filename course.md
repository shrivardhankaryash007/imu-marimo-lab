# IMUs from chip to controller

This course uses a local right-handed east–north–up (ENU) world, with body x
forward, y left, z up. All data and component parameters in the experiments are
synthetic. Angles are displayed in degrees and converted to radians for dynamics. For a
full estimator and control walkthrough, open the [3D attitude lab](attitude_lab.py)
and its [equations](attitude-theory.md).

## Sensors

### What comes out of the chip?

A **3-axis accelerometer** measures specific force in its own axes. In a local
world, $f_s = R_{ws}^{\mathsf T}(a_w-g_w)$. Here $R_{ws}$ maps sensor vectors
into world axes, and $g_w=(0,0,-g)$. Level on a bench, $a_w=0$ and the sensor
reads +1 g on z. In ideal free fall $a_w=g_w$ so it reads zero. A tilted or
translating sensor can give the same component reading in different motions.

A capacitive MEMS accelerometer has a suspended silicon proof mass. The sensor
housing accelerates with the board. Relative displacement of the mass changes
opposed capacitances. A damped spring-and-mass model is
$m\ddot x+c\dot x+kx=-m f_x$. At steady specific force $x=-m f_x/k$.
For a simple opposed parallel-gap model,
$C_\pm=\epsilon A/(d\mp x)$. Near center $\Delta C\approx 2\epsilon Ax/d^2$.
Actual comb geometry and closed-loop force-rebalance electronics vary. The
figure shows qualitative displacement, scaled up for visibility. The toy
spring response ignores resonances, damping and stops.

A **3-axis gyro** measures angular velocity $\omega$, usually reported in °/s or
rad/s. A MEMS rate gyro drives a mass at resonance. Rotation creates a sense-axis
Coriolis term $a_C=2v_{drive}\times\omega$ in the rotating sensor frame.
The lab uses one instant with drive velocity on +x and rate on +z. The actual
sense signal oscillates with the drive and electronics demodulate it. Angular
acceleration $\alpha=d\omega/dt$ is derived from rate samples. Differentiation
amplifies noise, so filtering and timestamp accuracy matter.

### How the chips are made

A capacitive silicon process can start with a silicon-on-insulator wafer. A
lithography mask defines anchors, flexures, masses and electrodes. Deep etching
forms the structural shapes. Removing a sacrificial layer under moving regions
releases the mass while the anchors stay attached. The process then seals the
device with a cap, sets the cavity pressure for its required damping, connects
it to signal-conditioning electronics and trims/calibrates the packaged part.
A digital module adds conversion, compensation, filtering, FIFO and bus logic.
Several sensor dies and an ASIC can share one package. The sequence, materials
and bonding method vary by product. Explore the stage selector on the cutaway.

### Which kind should I choose?

| Term | What it usually means |
|---|---|
| 3-axis sensor | One transducer family measured on x, y and z |
| 6-axis IMU | Three specific-force and three angular-rate channels |
| 9-axis module | 6-axis measurements plus three magnetic-field channels |
| AHRS | Estimates attitude and heading from sensors and references |
| INS | Propagates attitude, velocity and position. Aiding can bound drift |
| MEMS, optical, mechanical | MEMS uses microstructures. Fiber-optic and ring-laser gyros infer rotation from the Sagnac effect. Mechanical gyros use angular momentum. Other accelerometers may be force-balanced, resonant or piezoelectric |

The channel count is not the number of mechanical degrees of freedom. A free
rigid body has three translations and three rotations.

For a real board compare range and saturation, noise density, bandwidth and
sample rate separately, bias repeatability and in-run stability, scale and
cross-axis errors, temperature, vibration sensitivity, shock, time stamps,
latency, supply current and calibration support. A ±2 g setting has less
headroom than ±8 g. Check whether filter bandwidth and noise change with the
setting. Application-grade labels vary and need a datasheet comparison.
For white noise with density $n$, RMS noise is approximately $n\sqrt{B_{ENBW}}$,
where $B_{ENBW}$ is the filter's equivalent noise bandwidth. Bias stability is a
different error source. A long stationary log and Allan deviation can help
separate short-term noise from slower bias effects. Stiffen the mount or
characterize its resonance before trying to fix vibration entirely in software.

[ADI capacitive acceleration and gyros](https://www.analog.com/en/resources/technical-articles/accelerometer-and-gyroscopes-sensors-operation-sensing-and-applications.html) · [ETH fabrication lab](https://vvz.ethz.ch/Vorlesungsverzeichnis/sucheLehrangebot.view?abschnittId=120302&ansicht=2&lang=en&seite=0&semkez=2026S) · [Bosch BMI270 datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi270-ds000.pdf)

## Magnetometer

A magnetometer measures a magnetic-field vector in µT. A Hall element produces
a voltage transverse to current and perpendicular field. AMR changes resistance
with the angle to the material magnetization. TMR uses the tunnelling resistance
of layers with relative magnetic orientation. Chip designs use different
transducers, structures and signal conditioning to obtain three axes.

An approximate model is $m_{raw}=A R_{ws}^{\mathsf T} m_w + b$. **Hard iron**
adds an offset $b$, often from nearby permanent magnetic fields. **Soft iron**
changes scale and direction, represented by $A$. Rotate a level device through
360° and view the horizontal projection. An ideal circle shifts under a bias
and deforms under distortion. Real 3D calibration needs diverse orientations,
a stable field and a fit for both bias and distortion. A successful fit in one
location cannot remove a nearby motor field that varies with current.

For heading, rotate the measured field into a level frame or project it onto
the plane perpendicular to gravity. Use `atan2` and the stated axis convention.
This experiment keeps the sensor level. Magnetic north differs from true north.
With east-positive declination $D$, true compass heading is magnetic heading
plus $D$, wrapped to 0–360°. Declination and inclination vary by location.
At low horizontal field strength, a magnetic heading is poorly conditioned.

[TI Hall effect](https://www.ti.com/document-viewer/lit/html/sszt164) · [TDK TMR](https://www.micronas.tdk.com/en/technologies/tmr-angle-sensors) · [VectorNav calibration and heading](https://www.vectornav.com/resources/inertial-navigation-primer)

## Attitude

**Attitude** is the rotation from one set of axes to another at an instant.
Attitude changing means the body basis vectors turn relative to the reference.
Position is a translation and is independent of attitude. A gyroscope measures
that turning rate in body/sensor coordinates. Arbitrary 3D roll, pitch and yaw
rates cannot generally be integrated as three independent angles.

The displayed Euler rotation is $R_{wb}=R_z(\psi)R_y(\theta)R_x(\phi)$.
The columns show the body axes in the world. A rotated sensor mount is another
rotation $R_{bs}$ from sensor to body. Then $R_{ws}=R_{wb}R_{bs}$ and
$R_{wb}=R_{ws}R_{bs}^{\mathsf T}$. In this experiment the mounting offset is a
rotation about body z. A point offset from the reference origin is a different
quantity and belongs in the motion experiment. Positive mathematical yaw is
counterclockwise from East. Compass heading is clockwise from North.

At rest gravity constrains tilt. Gravity cannot resolve yaw about its own axis.
A calibrated magnetic field, a known fixture alignment, vision or a suitable
GNSS heading source can establish a heading reference. A single GNSS course
from motion is a velocity direction and may differ from body heading. For a
known object, define its axes, measure the rigid mount rotation against a
fixture or estimate it from multiple known orientations, and validate it on a
held-out rotation. For real alignment also verify timestamps and axis signs.

A strapdown estimator commonly propagates a normalized unit quaternion or a
rotation matrix using the body rate, then corrects it with observations. At
Euler pitch ±90°, multiple roll/yaw pairs describe the same attitude. Quaternions
avoid that coordinate singularity. A reference and a consistent initial
orientation are still needed.

[VectorNav reference frames and attitude](https://www.vectornav.com/resources/inertial-navigation-primer) · [SciPy Rotation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html)

## Motion & position

### What if I put the IMU somewhere else on the object?

Choose a reference point $O$ and measure the fixed body-frame vector $r_b$ from
$O$ to the sensor $S$. In world axes, $r_w=R_{wb}r_b$. For a rigid body:

$$p_S=p_O+r_w,\qquad v_S=v_O+\omega_w\times r_w$$

$$a_S=a_O+\alpha_w\times r_w+\omega_w\times(\omega_w\times r_w)$$

Subtract the last two terms to recover the reference-point acceleration from
sensor-point acceleration. Different points share angular velocity but sweep
different paths. A sensor that moves relative to the object needs additional
relative-motion terms. A flexible structure needs a model beyond this rigid one.

### How does inertial navigation infer position?

At each update, estimate attitude from angular rate and applicable aiding.
Correct bias and map sensor force to the world. Then $a_w=R_{ws}f_s+g_w$.
Correct the lever arm for the desired reference point and integrate acceleration
for velocity and velocity for position. Start from known or estimated $R_0$,
$v_0$ and $p_0$. The accelerometer cannot distinguish constant velocity from
rest. Absolute position does not come from IMU samples alone.

The lab is planar with known yaw and correct clocks. Gravity has no horizontal
component here. The horizontal trajectory combines translation, rotation and
angular acceleration. The aided curve represents a deliberately ideal reset to
both known position and velocity. Real navigation fuses noisy measurements
with uncertainty rather than resetting to truth. In full 3D an attitude error
leaks gravity into horizontal acceleration. A constant acceleration error
$b$ creates about $bt$ velocity error and $\tfrac12bt^2$ position error on a
fixed axis. Earth rotation, a changing local navigation frame and coning or
sculling may matter for higher accuracy or longer distances.

[MIT 3D rigid body kinematics](https://ocw.mit.edu/courses/16-07-dynamics-fall-2009/419be4d742e628d70acfbc5496eab967_MIT16_07F09_Lec25.pdf) · [PX4 EKF2 and IMU offsets](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf)

## 3D pose reconstruction

This snapshot puts the sensor at a freely chosen x/y/z offset while the body
rotates about a non-axis-aligned direction. The body has 20° roll and −30°
pitch before its selected yaw. The mount also has fixed 10° roll and 15°
pitch plus the selected mount yaw. The arrows show the recovered body attitude
and the rigid offset in East/North/Up coordinates.

Inputs to this reconstruction are a known or estimated sensor position,
velocity and attitude, specific force, angular rate, angular acceleration,
and an independently measured mounting transform. Taking the transpose of
$R_{bs}$ undoes the mount rotation. Subtracting the world offset, its rotational
velocity and its rotational acceleration maps the sensor state to the reference.
Changing the sensor location changes its trajectory and acceleration while the
recovered reference state stays the same in the ideal model.

An inertial chip alone provides neither the known initial position/velocity
nor absolute heading. This walkthrough starts with sensor pose/velocity from
simulation truth to isolate geometry. For a real setup, get the starting state
or periodic corrections from a fixture, encoders, zero-velocity observations,
GNSS, cameras or another appropriate reference. Measure and validate the lever
arm, mounting angles and clock offset separately. Differentiating gyro data
for angular acceleration calls for attention to noise and bandwidth.

[MIT 3D rigid body kinematics](https://ocw.mit.edu/courses/16-07-dynamics-fall-2009/419be4d742e628d70acfbc5496eab967_MIT16_07F09_Lec25.pdf) · [Kalibr spatial and temporal calibration](https://github.com/ethz-asl/kalibr/wiki/camera-imu-calibration)

## Fusion

Gyro integration reacts quickly and drifts under bias. Static gravity gives an
absolute tilt direction, but a translating sensor sees additional specific
force. A complementary filter predicts from rate and nudges toward a gravity
observation when it trusts that observation:

$$\hat\theta^-_k=\hat\theta_{k-1}+(\omega_k-b_g)\Delta t,\quad
\hat\theta_k=\hat\theta^-_k+\beta(\theta_{acc,k}-\hat\theta^-_k)$$

The lab is one axis with fixed gain, no explicit bias estimate and synthetic
motion. The sample gain $\beta$ depends on sample rate. Raising it reacts faster
to the accelerometer, including when the accelerometer appears to tilt under
translation. The optional gate checks the measured norm near 1 g. A plausible
norm can still hide translational interference, so use it as one heuristic.

A real AHRS can blend gravity and magnetic references only where credible. A
navigation EKF estimates states and covariance, predicts with inertial inputs,
checks measurement innovations and fuses GNSS, wheel odometry, barometry,
vision or zero-velocity events as appropriate. It cannot manufacture an
unobservable position or heading. Compare against reference truth using RMSE,
peak error and drift during deliberate sensor outages.

[x-io Fusion AHRS](https://github.com/xioTechnologies/Fusion) · [OpenVINS propagation and calibration](https://docs.openvins.com/) · [ETH EuRoC camera + IMU data](https://projects.asl.ethz.ch/datasets/euroc-mav/)

## Control & applications

A sensor measures motion, an estimator infers state, and a controller changes
motion through an actuator. For a one-axis body with inertia $J$, damping $c$
and disturbance $d$, $J\ddot\theta=u+d-c\dot\theta$. A PD controller can use
$u=K_p(\theta_{ref}-\hat\theta)-K_d\hat\omega$ within actuator limits. Here the
controller receives exact simulated angle and rate to isolate feedback. Real
systems need estimator error, filtering delay, saturation, rate limits and
sampling bandwidth accounted for. This one-axis lab is not a tuning guide for
hardware.

| Application | Why inertial data is useful | Practical question |
|---|---|---|
| Phone, game controller, wearable | Tilt, gestures, steps | Is power, latency or robustness the limiting factor? |
| Camera gimbal and flight control | Fast attitude and rate feedback | Can vibration, phase lag or saturation destabilize the loop? |
| Mobile robot and vehicle | Short-term motion between odometry/GNSS/vision updates | Where are the sensor and reference point, and will wheels slip? |
| Survey, marine and aviation | Attitude, heading and aided navigation | What drift and availability can the error budget tolerate? |
| Machine condition monitoring | Frequency content of vibration | Is bandwidth and the mount stiff enough to see the feature? |

### Build an algorithm in small checks

1. Define output, target accuracy, rates, frames, origin and operating motion.
2. Log raw time-stamped axes. Verify a static six-face acceleration test and
   gyro zero, direction, scales, saturation and temperature sensitivity.
3. Calibrate alignment and offsets. Measure latency and synchronise sources.
   Use filtering before decimation and pick bandwidth for the application.
4. Validate attitude on a known fixture. Then add lever-arm correction,
   short-duration dead reckoning and aiding as needed.
5. Compare against independent truth at rest, under rotation, translation and
   aiding outage. Inspect residuals. Add actuator feedback only after validation.

[PX4 estimator guide](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf) · [PX4 controller diagrams](https://docs.px4.io/main/en/flight_stack/controller_diagrams) · [ACEINNA simulation](https://github.com/Aceinna/gnss-ins-sim)
