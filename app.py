import gradio as gr
import json
import os
import openai

dump_controls = False
log_to_console = False


def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.Textbox(value="", interactive=False)


def add_file(history, file):
    with open(file.name, mode="rb") as f:
        content = f.read()

        if isinstance(content, bytes):
            content = content.decode('utf-8', 'replace')
        else:
            content = str(content)

    fn = os.path.basename(file.name)
    history = history + [(f'```{fn}\n{content}\n```', None)]

    gr.Info(f"File added as {fn}")

    return history

def submit_text(txt_value):
    return add_text([chatbot, txt_value], [chatbot, txt_value])

def undo(history):
    history.pop()
    return history

def dump(history):
    return str(history)

def load_settings():  
    # Dummy Python function, actual loading is done in JS  
    pass  

def save_settings(acc, sec, prompt, temp, tokens, model):  
    # Dummy Python function, actual saving is done in JS  
    pass  

def process_values_js():
    return """
    () => {
        return ["oai_key", "system_prompt", "seed"];
    }
    """

def bot(message, history, oai_key, system_prompt, seed, temperature, max_tokens, model):
    try:
        openai.api_key = oai_key

        seed_i = None
        if seed:
            seed_i = int(seed)

        history_openai_format = []
        if system_prompt:
                history_openai_format.append({"role": "system", "content": system_prompt})
        for human, assi in history:
            if human is not None:
                history_openai_format.append({"role": "user", "content": human})
            if assi is not None:
                history_openai_format.append({"role": "assistant", "content": assi})
        if message:
            history_openai_format.append({"role": "user", "content": message})

        if log_to_console:
            print(f"br_prompt: {str(history_openai_format)}")

        response = openai.ChatCompletion.create(
            model=model,
            messages= history_openai_format,
            temperature=temperature,
            seed=seed_i,
            max_tokens=max_tokens
        )

        if log_to_console:
            print(f"br_response: {str(response)}")

        history[-1][1] = response.choices[0].message.content
        if log_to_console:
            print(f"br_result: {str(history)}")

    except Exception as e:
        raise gr.Error(f"Error: {str(e)}")

    return "", history

with gr.Blocks() as demo:
    gr.Markdown("# OAI Chat (Nils' Version™️)")

    with gr.Accordion("Settings"):
        oai_key = gr.Textbox(label="OpenAI API Key", elem_id="oai_key")
        model = gr.Dropdown(label="Model", value="gpt-4-1106-preview", allow_custom_value=True, elem_id="model",
                            choices=["gpt-4-1106-preview", "gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-1106"])
        system_prompt = gr.TextArea("You are a helpful AI.", label="System Prompt", lines=3, max_lines=250, elem_id="system_prompt")  
        seed = gr.Textbox(label="Seed", elem_id="seed")
        temp = gr.Slider(0, 1, label="Temperature", elem_id="temp", value=1)
        max_tokens = gr.Slider(1, 4000, label="Max. Tokens", elem_id="max_tokens", value=4000)
        save_button = gr.Button("Save Settings")  
        load_button = gr.Button("Load Settings")  

        load_button.click(load_settings, js="""  
            () => {  
                let elems = ['#oai_key textarea', '#system_prompt textarea', '#seed textarea', '#temp input', '#max_tokens input', '#model'];
                elems.forEach(elem => {
                    let item = document.querySelector(elem);
                    let event = new InputEvent('input', { bubbles: true });
                    item.value = localStorage.getItem(elem.split(" ")[0].slice(1)) || '';
                    item.dispatchEvent(event);
                });
            }  
        """)

        save_button.click(save_settings, [oai_key, system_prompt, seed, temp, max_tokens, model], js="""  
            (oai, sys, seed, temp, ntok, model) => {  
                localStorage.setItem('oai_key', oai);  
                localStorage.setItem('system_prompt', sys);  
                localStorage.setItem('seed', seed);  
                localStorage.setItem('temp', document.querySelector('#temp input').value);  
                localStorage.setItem('max_tokens', document.querySelector('#max_tokens input').value);  
                localStorage.setItem('model', model);  
            }  
        """) 

    chatbot = gr.Chatbot(
        [],
        elem_id="chatbot",
        show_copy_button=True,
        height=350
    )

    with gr.Row():
        txt = gr.TextArea(
            scale=4,
            show_label=False,
            placeholder="Enter text and press enter, or upload a file",
            container=False,
            lines=3,            
        )
        submit_btn = gr.Button("🚀 Send", scale=0)
        submit_click = submit_btn.click(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, [txt, chatbot, oai_key, system_prompt, seed, temp, max_tokens, model], [txt, chatbot],
        )
        submit_click.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)

    with gr.Row():
        btn = gr.UploadButton("📁 Upload", size="sm")
        undo_btn = gr.Button("↩️ Undo")
        undo_btn.click(undo, inputs=[chatbot], outputs=[chatbot])

        clear = gr.ClearButton(chatbot, value="🗑️ Clear")

    if dump_controls:
        with gr.Row():
            dmp_btn = gr.Button("Dump")
            txt_dmp = gr.Textbox("Dump")
            dmp_btn.click(dump, inputs=[chatbot], outputs=[txt_dmp])

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
        bot, [txt, chatbot, oai_key, system_prompt, seed, temp, max_tokens, model], [txt, chatbot],
    )
    txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)
    file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False, postprocess=False)

demo.queue().launch()