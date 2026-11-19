## Sensor fusion

The gyro predicts how the sensor turns. The accelerometer and magnetometer
supply directions the prediction can be checked against. In this convention
$R_{ws}$ maps the sensor frame into the world. When translation is small, the
accelerometer gives an upward reference. The magnetometer supplies heading
information when the field is trustworthy.

$$
\hat R_{ws}^- = \hat R_{ws}\operatorname{Exp}((y_g-\hat b)\Delta t),\qquad
h= (\hat R_{ws}^-)^T d_w,\qquad \hat R_{wb}=\hat R_{ws} R_{bs}^{T}
$$

Here $y_g$ is measured gyro rate, $\hat b$ is estimated gyro bias, $d_w$ is a
known world direction, and $h$ is that direction predicted in sensor axes.
$R_{bs}$ is the measured mounting rotation. Gravity constrains tilt. Heading
about gravity needs another reference.

## Complementary filter

Use a fixed correction gain. The cross product points in the direction that
reduces the mismatch between the measured direction $z$ and the prediction $h$.

$$
e=z\times h,\qquad
\hat R^+ = \hat R^-\operatorname{Exp}(k_p\Delta t\,e),\qquad
\hat b^+ = \hat b^- - k_i\Delta t\,e
$$

For one angle, with a 10° prediction and an 8° measurement, a 10% correction
moves the estimate to $10^\circ + 0.1(8^\circ-10^\circ)=9.8^\circ$.

## Kalman filter

Track uncertainty as well as the rotation. In the error-state filter, $P$ is the
covariance of small attitude and gyro-bias errors, $Q$ models process noise,
$R_m$ models observation noise, and $H$ describes how a state error moves the
predicted reference vector. The residual is $r=z-h$.

$$
P^- = \Phi P \Phi^T + Q,\qquad S=HP^-H^T+R_m
$$

$$
K=P^-H^TS^{-1},\qquad \delta x=Kr,\qquad \mathrm{NIS}=r^TS^{-1}r
$$

With a scalar prior variance of 4 deg² and measurement variance of 1 deg²,
$K=4/(4+1)=0.8$. The same −2° residual moves 10° to 8.4°. Increasing the
measurement variance to 16 deg² drops the gain to 0.2. The notebook shows the
actual update, rejection decision and rotation for any selected sample.

## Recursive least squares

RLS estimates model parameters from streaming data. In this experiment the
model is a gyro calibration, $y=s\,\omega_{ref}+b$, where $s$ is scale and $b$
is bias. Give the filter a measured reference rate from a known fixture or
encoder. One constant speed gives only one equation for the two unknowns.

$$
\phi=\begin{bmatrix}\omega_{ref}\\1\end{bmatrix},\quad
\theta=\begin{bmatrix}s\\b\end{bmatrix},\quad
K=\frac{P\phi}{\lambda+\phi^TP\phi},\quad
\theta^+=\theta+K(y-\phi^T\theta)
$$

$$
P^+=\frac{P-K\phi^TP}{\lambda},\qquad 0<\lambda\le 1
$$

With $\lambda=1$, old data keep their weight. With $\lambda<1$, a bias change
can be learned faster, with greater sensitivity to noise. RLS calibrates the
measurement model here. Use the fitted parameters to correct a gyro reading
with $\omega_{corr}=(y-\hat b)/\hat s$ before integrating it. The complementary
filter and EKF then estimate attitude. [Recursive estimation reference](https://www.mathworks.com/help/ident/ref/recursivels-system-object.html)

## Control theory

The estimator measures how far the body is from its desired rotation $R_d$.
The controller generates torque. The plant inertia $J$ determines the motion
produced by torque and disturbance $\tau_d$.

$$
e_b=\operatorname{Log}(\hat R_{wb}^{T}R_d),\qquad
\tau=\operatorname{clip}(K_p e_b-K_d\hat\omega_b)
$$

$$
J\dot\omega_b=\tau+\tau_d-\omega_b\times(J\omega_b)
$$

For a small unsaturated rotation about a principal axis, the natural frequency
is $\omega_n=\sqrt{K_p/J_i}$ and damping is
$\zeta=K_d/(2\sqrt{J_iK_p})$. Change gain, damping and torque limit in the
control experiment to see where that small-angle model stops being predictive.
