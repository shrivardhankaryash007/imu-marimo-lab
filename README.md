# IMU marimo lab

Two interactive Python notebooks for learning how inertial sensors work and how
sensor fusion and feedback control turn their measurements into motion. Both use
synthetic data with known truth and run locally without an account or API key.

| Notebook | What you can explore |
| --- | --- |
| [IMUs from chip to controller](imu.py) | MEMS cutaway, magnetometer calibration, attitude and frames, drift and aiding, arbitrary 3D offsets, complementary fusion, and feedback. [Course notes](course.md) |
| [IMU math, sensor fusion, and control](attitude_lab.py) | Open the live equation explorer to see substitutions from the selected sample. Compare complementary and Kalman filters, fit gyro scale and bias with RLS, and change feedback gains and torque limits. [Equation guide](equations.md) · [Full derivations](attitude-theory.md) |

## Open on a Mac

In Finder, double-click **Open IMU Math.command** for equations, filtering and
control, or **Open IMU Course.command** for the sensor and mechanics course.
The launcher opens the notebook in your browser and installs uv for your user
if needed. The first launch may take longer while dependencies are downloaded.
Keep the launchers and notebooks together in the same folder. Leave the Terminal
window open while you use the notebook.

## Run from a terminal

On other platforms, install [uv](https://docs.astral.sh/uv/getting-started/installation/),
clone the repo, and run a notebook. The first launch provisions its isolated
Python 3.11 environment.

```sh
git clone https://github.com/shrivardhankaryash007/imu-marimo-lab.git
cd imu-marimo-lab
uvx --python 3.11 marimo@0.25.2 run --sandbox=uv --host 127.0.0.1 --token imu.py
```

To open the 3D lab, use `attitude_lab.py` in the last command. To modify a
notebook interactively, change `run` to `edit`. Keep the Python modules and
Markdown notes alongside the notebooks. Export a chosen takeaway as Markdown,
or export the sampled time series as CSV from the 3D lab.

## Optional tutor

The tutor starts off. To enable it, copy `.env.example` to `.env`, fill in your
provider's chat API base URL, model ID, and API key if required, and start the
notebook with that file. The Mac launchers load `.env` automatically. The
repository ignores `.env`.

```sh
uvx --python 3.11 --env-file .env marimo@0.25.2 run --sandbox=uv --host 127.0.0.1 --token imu.py
```

Use an API that supports OpenAI-compatible `POST /chat/completions`. You can
connect a hosted provider, a local server, or a compatible gateway in front of
other models. Use the model ID assigned by your provider. For example:

| Provider or server | Example `IMU_TUTOR_BASE_URL` |
| --- | --- |
| [OpenAI](https://platform.openai.com/docs/api-reference/chat/create) | `https://api.openai.com/v1` |
| [Gemini compatibility API](https://ai.google.dev/gemini-api/docs/openai) | `https://generativelanguage.googleapis.com/v1beta/openai` |
| [Local Ollama compatibility API](https://docs.ollama.com/api/openai-compatibility) | `http://127.0.0.1:11434/v1` |
| [Local LM Studio](https://lmstudio.ai/docs/developer/openai-compat) | `http://127.0.0.1:1234/v1` |

Only an explicitly submitted tutor message contacts your configured endpoint.
The request includes your question, recent conversation, and the selected
experiment and lesson context. Hosted endpoints use HTTPS and may charge for
requests. Local servers can leave the key blank if they allow it. The labs and
exports work regardless of tutor configuration.

## Work on it

`imu_sensor.py` and `imu_navigation.py` contain the core models. `attitude_filters.py`
and `attitude_sim.py` hold the 3D estimators and controlled plants. Plot and tutor
modules are separate so you can change the math or provider independently.

For a new quantitative example, bind the displayed equation to the experiment's
actual computed values with marimo controls. Define the symbols and their units
next to the substitutions. Use the shared attitude chart layout and check
title, axes, and legend spacing in the browser at wide and narrow widths.

```sh
uv run --no-project --python 3.11 --with 'numpy==2.4.6' --with 'plotly==6.5.2' --with 'pytest>=8,<10' pytest -q
```

Reference material is organized into [hardware](hardware-sources.md),
[navigation](navigation-sources.md), and [learning tools](learning-tools.md).
