# Interactive engineering study tools

## Recommendation

Build the reusable lesson library around **local marimo notebooks**. Keep each lesson as readable Python plus Markdown, make the equation, graph and controls share one calculation, and use a local model for optional Q&A. Link out to existing simulators when they already teach the physical interaction well. This adds a coherent, remixable study path without rebuilding a circuit simulator, motion tracker or phone-sensor app.


## What existing tools do well

| Tool | Best fit | Limits for a personal engineering library |
|---|---|---|
| [PhET simulations](https://phet.colorado.edu/en/simulations) | Polished, guided physics interactions; e.g. circuit construction and basic mechanics. PhET provides desktop and individual simulation downloads for offline use ([offline access](https://phet.colorado.edu/en/offline-access)). | A collection of topic-specific simulations, not a place to author and version lessons that join equations, plots, measured data and Q&A. Use as a referenced activity or offline companion. |
| [Falstad CircuitJS](https://falstad.com/circuit/) | Fast circuit exploration with animated current/voltage, editable components and many examples. It offers standalone offline builds and links its source; the simulator is GPL-2.0-or-later ([directions](https://falstad.com/circuit/about.html)). | Focused on circuits. It is an excellent companion for circuit intuition, but does not replace a cross-topic notebook collection. |
| [Tracker](https://opensourcephysics.github.io/tracker-website/) | Video-based motion analysis and modeling; supports common video formats and offers a browser version ([Tracker Online](https://opensourcephysics.github.io/tracker-online/)). | A specialist motion-analysis workflow, not a general authoring/Q&A framework. Treat measurements as inputs to a lesson; prefer its desktop app for selected local video. |
| [phyphox](https://phyphox.org/) | Real phone sensors, ready-made experiments and export of recorded data for analysis in another tool. | Sensor use depends on a phone and its available sensors. It complements rather than replaces desktop simulations and authored explanations. |

Free or browser-accessible does not always mean open source or private. These are separate questions: check each tool's source/license and data path before using it with non-public material. PhET's offline installers and PhET-iO are documented separately from ordinary web use ([offline](https://phet.colorado.edu/en/offline-access), [PhET-iO note](https://phet.colorado.edu/en/help-center/getting-started)).

## marimo versus Jupyter

| | marimo | Jupyter + ipywidgets |
|---|---|---|
| Interaction model | Reactive dependency graph: controls update dependent outputs automatically. Notebooks are Python source files, easy to diff and keep alongside lessons ([reactivity](https://docs.marimo.io/guides/reactivity/), [key concepts](https://docs.marimo.io/getting_started/key_concepts/)). | Mature, broad Python ecosystem. Widgets expose trait values and `observe`/button callbacks; outputs are managed inside notebook output areas ([widget basics](https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Basics.html), [events](https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Events.html), [Output](https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html)). |
| Fit here | Best default for small, self-contained lessons whose slider, equation and plot should stay in sync. PEP 723 gives a single-file dependency declaration; the current project already runs this way ([package management](https://docs.marimo.io/guides/package_management/)). | Best when a lesson needs a library or existing workflow that is already Jupyter-first. Its flexibility also means callbacks and output clearing need more explicit state management. |
| Authoring tradeoff | Reactive rules discourage hidden/out-of-order state and make a lesson easier to rerun. | Highest adoption and extensions; execution order and mutable state can diverge from the visible cell order. |

Use marimo as the library format, and export or provide Jupyter notebooks only when compatibility is useful. Use PhET/Falstad/Tracker/phyphox as linked or imported-data activities, not competing lesson runtimes.

## marimo chat callback and live simulation context

`mo.ui.chat(model, ...)` takes a callable `model(messages, config)`. `messages` is a list of `mo.ai.ChatMessage` objects; inspect `message.role` (`user`, `assistant`, or `system`) and `message.content` (basic text messages contain strings). The model returns a string or another displayable object. The chat element's `.value` is the conversation history, also a list of messages. The optional `on_message` callback receives the message list. See the [chat API](https://docs.marimo.io/api/inputs/chat/) and its [history](https://docs.marimo.io/api/inputs/chat/#accessing-chat-history) and [custom context](https://docs.marimo.io/api/inputs/chat/#custom-model-with-additional-context) examples.

Keep the chat widget in its own stable cell. Do not make its cell depend on slider `.value`s or rebuild it from the plotting cell: marimo re-evaluates cells affected by widget changes, and reconstructing the chat element risks replacing its frontend history. For fresh context without recreating the UI, keep a session-state getter in the model closure and read it only when a user submits:

```python
get_sim, set_sim = mo.state({"R_kohm": 10.0, "C_uf": 100.0, "t_s": 1.0})


def set_parameter(name):
    def update(value):
        set_sim({**get_sim(), name: value})

    return update


def tutor(messages, config):
    state = get_sim()  # read at submission time, not while defining the chat cell
    history = [
        {"role": message.role, "content": message.content}
        for message in messages
        if isinstance(message.content, str)
    ]
    return local_answer(
        history,
        system_context=f"Current simulation settings: {state}",
        config=config,
    )


chat = mo.ui.chat(tutor)
chat
```

Connect each control with an `on_change=set_parameter("R_kohm")` callback and keep the chat creation independent of the live state value. The getters/setters from [`mo.state`](https://docs.marimo.io/api/state/) are intended for state that must be read or updated imperatively. This preserves a chat transcript across ordinary slider moves while each submitted answer sees the latest settings. The state is session state; persist it explicitly only if a lesson needs a saved run. Filter/format message content deliberately if enabling attachments or rich message parts.

## Optional Q&A

marimo supports built-in local providers. Its Ollama guide uses the OpenAI-compatible local endpoint `http://127.0.0.1:11434/v1`; LM Studio is also documented as a local provider ([provider guide](https://docs.marimo.io/guides/configuration/llm_providers/)). The sidebar AI assistant is a separate feature: it receives notebook code as context and lets the user choose read-only, suggest-edits or full access. For study Q&A, `mo.ui.chat` is the better-shaped interface because the lesson controls its context and the model callback; avoid granting editor full access to a teaching assistant unless code execution/editing is intentional ([AI assistant](https://docs.marimo.io/guides/editor_features/ai_completion/)).


This repository uses an opt-in chat-completions endpoint. See the [README](README.md#optional-tutor) for provider and local-server configuration.

## Sources checked

- marimo [chat API](https://docs.marimo.io/api/inputs/chat/), [state API](https://docs.marimo.io/api/state/), [reactivity](https://docs.marimo.io/guides/reactivity/), [LLM providers](https://docs.marimo.io/guides/configuration/llm_providers/).
- Jupyter Widgets [basics](https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Basics.html), [events](https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Events.html), [Output](https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html).
- PhET [offline access](https://phet.colorado.edu/en/offline-access); Falstad [simulator/about/license](https://falstad.com/circuit/about.html); Tracker [site](https://opensourcephysics.github.io/tracker-website/) and [browser app](https://opensourcephysics.github.io/tracker-online/); phyphox [features](https://phyphox.org/).
