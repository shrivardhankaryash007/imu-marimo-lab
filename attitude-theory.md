# IMU attitude estimation and geometric control

These notes set the conventions and equations used by the attitude lab. The lab is a small, deterministic teaching model: it replays sampled IMU data, implements matrix filters on SO(3), applies magnetometer and norm gates, and compares controllers on separate plants. It is useful for seeing signs, drift, convergence, and saturation. It is not a flight-ready estimator or a substitute for sensor calibration, timestamp integrity, vibration handling, or safety analysis.

## Frames, measurements, and motion

Use a right-handed ENU world frame: $x$ east, $y$ north, $z$ up. This is distinct from body axes, commonly $x$ forward, $y$ left, $z$ up; a fixed sensor-to-body rotation maps one to the other. Let $R_{wb}\in SO(3)$ actively rotate body coordinates into world coordinates: $v_w=R_{wb}v_b$. Let $R_{bs}$ rotate sensor coordinates into body coordinates. The lab estimates sensor orientation $R_{ws}$ and reports body orientation as $R_{wb}=R_{ws}R_{bs}^T$. If mounting orientation is unknown, sensor attitude alone cannot identify body attitude; calibrate $R_{bs}$ or define the sensor as the controlled body reference. Then

$$
R_{ws}=R_{wb}R_{bs},\qquad R_{bw}=R_{wb}^T.
$$

A sensor vector already uses sensor axes; a predicted world reference in sensor axes is $R_{ws}^T d_w$. The inverse rotation reverses the mapping; for Euler angles it also reverses composition order, so do not infer inverse angles by simply negating each component.

The lab models the gyro in sensor axes: $y_g=R_{bs}^T\omega_b+b_s+n_g$, where $b_s$ is sensor-frame bias. Correct bias before integrating; $\omega_s=y_g-b_s$ propagates $R_{ws}$ by right multiplication. The accelerometer reports specific force, not world acceleration: $f_s=R_{sw}(a_w-g_w)+b_a+n_a$. With ENU gravity $g_w=[0,0,-g]^T$, a stationary, level sensor reads approximately $+g$ along its upward axis. During translation, $f_s$ also contains linear acceleration, so treating it as gravity is wrong.

For a sensor displaced from a rigid body's reference point by body vector $r$,
$$
a_{s,w}=a_{o,w}+R_{wb}\big[\alpha_b\times r+\omega_b\times(\omega_b\times r)\big],
$$
where $a_{o,w}$ is the reference-point acceleration in world axes and $\alpha$ is angular acceleration. The cross-product terms are body-frame accelerations; rotate them into sensor axes before applying sensor-frame measurement equations. The lab may subtract these terms only as a truth-only synthetic baseline, where simulated angular acceleration and lever arm are known. It must not imply real sensor compensation: practical use requires a known mounting transform and lever arm, calibrated axes, filtered angular-rate and angular-acceleration estimates, and careful delay/noise treatment. If the sensor mount relative to the body is unknown, the body point and lever arm are not recoverable from IMU samples alone. Calibrate scale, nonorthogonality and biases. Two nonparallel known directions constrain a 3D rotation; one direction leaves rotation about itself unresolved.

Gravity provides roll and pitch information but not yaw: rotating about gravity does not change its predicted measurement. Under negligible translation, the normalized body specific force follows

$$
\frac{f_b}{g}=[-\sin\theta,\;\cos\theta\sin\phi,\;\cos\theta\cos\phi]^T.
$$

Read tilt with $\phi=\operatorname{atan2}(f_y,f_z)$ and
$\theta=\operatorname{atan2}(-f_x,\sqrt{f_y^2+f_z^2})$ after applying the mount
rotation. For heading, remove the magnetic component parallel to up:
$m_\perp=m-(m^Tu)u$. Given two nonparallel references, make orthonormal bases
$W=[u_w,\hat m_{\perp,w},u_w\times\hat m_{\perp,w}]$ and
$S=[u_s,\hat m_{\perp,s},u_s\times\hat m_{\perp,s}]$. Their alignment gives
$R_{ws}=WS^T$ as a possible static initialization. The ENU yaw convention starts
at east and increases counterclockwise. Compass heading starts at north and
increases clockwise, so use $\mathrm{wrap}_{360}(90^\circ-\psi)$ when referenced
to true north. A magnetometer or another heading reference can observe yaw only when its field/reference is known and disturbances are controlled. Magnetometers need hard/soft-iron and alignment calibration and should be gated during field anomalies.

## Attitude representations

A rotation matrix has nine entries but only three degrees of freedom; preserve orthogonality and determinant +1. Euler ZYX angles encode $R=R_z(\psi)R_y(\theta)R_x(\phi)$: yaw, pitch, roll. Away from singularity,
$$
\theta=\asin(-R_{31}),\quad \phi=\atan2(R_{32},R_{33}),\quad \psi=\atan2(R_{21},R_{11}).
$$
At pitch $\pm90^\circ$, roll and yaw are not separately determined (gimbal singularity); clamp the asin input for roundoff and do not use Euler angles as the filter state.

For a unit quaternion $q_{ws}$, sensor-rate integration is a right multiplication: $q^+=q\otimes\operatorname{Exp}_q(\omega_s\Delta t)$, then normalize. For a rotation vector $\delta$, let $a=\|\delta\|$ and use $\operatorname{Exp}_q(\delta)=[\cos(a/2),\;(\delta/a)\sin(a/2)]$ with the zero-angle limit. In matrix form this is $R^+=R\operatorname{Exp}([\omega_s]_\times\Delta t)$, often written $R^+=R\operatorname{Exp}(\omega_s\Delta t)$. The exponential is on SO(3), not componentwise Euler addition. Small increments use the first-order approximation, but the exact exponential is inexpensive and avoids avoidable integration error.

## Complementary filters

A scalar complementary filter estimates roll and pitch by blending gyro prediction with accelerometer tilt. For a chosen angle component, predict $\theta^- = \theta + (y_g-b_s)\Delta t$, compute an accelerometer angle $\theta_a$, then correct $\theta\leftarrow\theta^-+\alpha\,\mathrm{wrap}(\theta_a-\theta^-)$, where $\alpha=1-e^{-\Delta t/\tau}$. This is intuitive but coordinates become awkward near large tilts and it does not represent coupled 3D rotations.

A 3D complementary correction uses direction vectors in sensor axes. Let $z=f_s/\|f_s\|$ be measured upward direction when acceleration is near gravity; let $h=R_{ws}^T d$ be the predicted direction for world reference $d$. Define $e=z\times h$. With this order, for $R^+=R\operatorname{Exp}(\delta)$, the sign $+ke$ corrects small attitude error under the stated residual convention. Check the sign with a known positive rotation before relying on it. A proportional correction may be added to gyro rate; a fixed-gain integral term can estimate gyro bias, e.g. $\dot b=-k_i e$, with sign and units verified against the chosen error definition. Bound the integral and disable or reduce it when the vector is unreliable. Normalize and gate accelerometer/magnetometer vectors; do not force a correction from a vector with poor norm or disturbed direction.

## Error-state Kalman filter

Represent the nominal attitude by $\hat R$, and a small right-multiplicative attitude error by $R=\hat R\operatorname{Exp}(\delta\theta)$. The error state is $x=[\delta\theta,\delta b_g]$. Under gyro input corrected by nominal bias, a common first-order continuous model is
$$
\dot x=F x+w,\qquad F=\begin{bmatrix}-[\hat\omega_s]_\times&-I\\0&0\end{bmatrix}.
$$
The nominal rate $\hat\omega_s$ is in sensor axes; the negative signs follow this right-error convention. Discretize with $\Phi\simeq I+F\Delta t$ for small steps (or a matrix exponential), then
$$
P^- = \Phi P\Phi^T+Q_d.
$$
For the simulated teaching model use $Q_d=\operatorname{diag}(\sigma_g^2\Delta t I_3,\sigma_b^2\Delta t I_3)$. This diagonal approximation omits attitude-bias cross terms; production discretization should derive process covariance from the continuous noise model and units.

For a normalized known world direction $d$, predict its sensor measurement as $h=\hat R_{ws}^T d$. The Jacobian for the right attitude error is $H=[h]_\times$ because $\operatorname{Exp}(-\delta\theta)h\simeq h+[h]_\times\delta\theta$. For residual $r=z-h$, use
$$
S=HP^-H^T+R_m,\quad K=P^-H^TS^{-1},\quad \delta\hat x=Kr.
$$
Compute normalized innovation squared $\mathrm{NIS}=r^TS^{-1}r$. An approximate 99% chi-square gate is $9.21$ for a 2D tangent-plane residual; choose the threshold for the actual residual dimension and desired false-rejection rate. A vector direction has only two independent degrees of freedom; normalization creates correlated components, so a tangent-plane residual/covariance is more principled than blindly assigning three independent noise values.

Update covariance with Joseph form $P^+=(I-KH)P^-(I-KH)^T+KR_mK^T$ for numerical symmetry/positive-semidefinite robustness. Inject the correction: $\hat R\leftarrow\hat R\operatorname{Exp}(\delta\hat\theta)$, $\hat b_g\leftarrow\hat b_g+\delta\hat b_g$. Reset the error mean to zero and transform covariance through the reset Jacobian (first-order attitude block approximately $I-\tfrac12[\delta\hat\theta]_\times$, with convention-dependent sign). Symmetrize only to remove roundoff, not to conceal a bad model.

Tune with recorded static and dynamic data. Start from sensor noise/bias characterization, then inspect attitude error, bias estimates, innovation and NIS. Too much process noise follows gyro but jitters; too little measurement noise over-trusts disturbed vectors; overly tight gates reject valid maneuvers. Keep accelerometer updates weak or disabled under high linear acceleration. Use magnetometer gating and heading checks independently from gravity updates.

## Worked gain example

Suppose the estimated roll is $10^\circ$, while a trusted static accelerometer reports $8^\circ$. The wrapped residual is $-2^\circ=-0.0349$ rad. With a scalar correction fraction $\alpha=0.1$, the estimate becomes $10^\circ+0.1(-2^\circ)=9.8^\circ$. If the sample interval is 10 ms, that blend corresponds to $\tau=-\Delta t/\ln(1-\alpha)\approx95$ ms. For comparison, a one-dimensional Kalman prediction with variance $P^-=4\,\mathrm{deg}^2$ and observation variance $R_m=1\,\mathrm{deg}^2$ gives $K=4/(4+1)=0.8$. The same innovation moves the estimate to $8.4^\circ$ and leaves posterior variance $0.8\,\mathrm{deg}^2$. With noisier $R_m=16\,\mathrm{deg}^2$, the gain drops to $0.2$ and the estimate becomes $9.6^\circ$. The lab's 3D EKF uses the corresponding matrix equations.

The scalar complementary example illustrates a discrete blend: faster correction reduces drift but passes more vibration and translational acceleration into tilt.

## Timing and validation

Use starter replay gates of $|\|f_s\|-g|\le0.14g$ for accelerometer norm and relative magnetometer magnitude deviation $\le0.23$ from its calibrated nominal value. These are tunable lab values, not universal limits. An optional approximate NIS cutoff is $9.21$ for a two-dimensional tangent residual (99% chi-square); use the proper dimension and covariance for other residuals.

Use sensor timestamps and measured $\Delta t$, not a nominal loop delay. Reject or explicitly handle duplicate, out-of-order, and implausibly large intervals; document any interpolation. Ensure every sample is consumed once and record units, frame, calibration, filter state, innovations, gates, and saturation. Validate with static poses, known positive/negative single-axis rotations, a full turn and return, changing yaw with gravity only, magnetic disturbance, acceleration, dropped samples, and replay determinism. Compare against an independent reference when available. Check orthogonality $R^TR$, determinant, quaternion norm, bounded covariance, and angle wrapping. Unit tests can verify algebra, but replay and physical checks reveal convention and timing mistakes.

## Geometric attitude control

For desired body-to-world attitude $R_d$ and estimate $\hat R_{wb}$, define body-frame attitude error $e=\operatorname{Log}(\hat R_{wb}^TR_d)$, the rotation vector taking current orientation toward desired. A simple torque law is
$$
\tau=\operatorname{clip}(K_p e-K_d\omega_b),\qquad
J\dot\omega=\tau+\tau_d-\omega\times J\omega.
$$
Here $J$ is inertia and $\tau_d$ disturbance torque. Clip is component/actuator limit and needs an explicit policy; torque saturation means the commanded dynamics cannot be achieved. At small angles around a principal axis with inertia $J_i$, the unsaturated ideal closed loop is $J_i\ddot e+K_{d,i}\dot e+K_{p,i}e=0$, so $\omega_n=\sqrt{K_p/J_i}$ and $\zeta=K_d/(2\sqrt{J_iK_p})$. This gives an initial scale, not a guarantee under delay, coupling, noise, or saturation. Respect actuator torque/rate limits and avoid integral windup if integral action is added. Keep estimation and actuation separate in experiments: replay one fixed measurement stream through candidate estimators, then feed each estimate to its own identical controlled plant. Otherwise plant divergence changes sensor inputs and confounds the comparison.

## Sources and scope

These conventions and standard constructions are grounded in Joan Solà, “Quaternion kinematics for the error-state Kalman filter,” arXiv:1711.02508; the OpenVINS documentation on propagation, IMU state and update models; x-io Technologies’ Fusion AHRS implementation and algorithm notes; and PX4’s EKF2 and controller documentation. The equations above state the convention explicitly because signs and left/right perturbations vary between references. The lab’s SO(3) filters, ideal compensation, simplified covariance discretization, and controlled plants are educational baselines; production systems need validated sensor models, calibration, robust timing, fault handling, platform-specific limits, and independent verification.

- Solà: https://arxiv.org/abs/1711.02508
- OpenVINS IMU propagation and measurement models: https://docs.openvins.com/propagation.html and https://docs.openvins.com/update-feat.html
- x-io Fusion: https://github.com/xioTechnologies/Fusion
- PX4 EKF2: https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf.html
- PX4 controller diagrams: https://docs.px4.io/main/en/flight_stack/controller_diagrams.html
