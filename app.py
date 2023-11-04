import gradio as gr
import json
import os
import boto3

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

def save_settings(acc, sec, prompt, temp):  
    # Dummy Python function, actual saving is done in JS  
    pass  

def process_values_js():
    return """
    () => {
        return ["access_key", "secret_key", "token"];
    }
    """

def bot(message, history, aws_access, aws_secret, aws_token, temperature, max_tokens):
    try:
        prompt = "\n\n"
        for human, assi in history:
            if prompt is not None:
                prompt += f"Human: {human}\n\n"
            if assi is not None:
                prompt += f"Assistant: {assi}\n\n"
        if message:
            prompt += f"Human: {message}\n\n"
        prompt += f"Assistant:"

        if log_to_console:
            print(f"br_prompt: {str(prompt)}")

        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
        })

        sess = boto3.Session(
            aws_access_key_id=aws_access,
            aws_secret_access_key=aws_secret,
            aws_session_token=aws_token,
            region_name='eu-central-1')
        br = sess.client(service_name="bedrock-runtime")

        response = br.invoke_model(body=body, modelId="anthropic.claude-v2",
                                accept="application/json", contentType="application/json")
        response_body = json.loads(response.get('body').read())
        br_result = response_body.get('completion')

        history[-1][1] = br_result
        if log_to_console:
            print(f"br_result: {str(history)}")

    except Exception as e:
        raise gr.Error(f"Error: {str(e)}")

    return "", history

with gr.Blocks() as demo:
    gr.Markdown("# Amazon™️ Bedrock™️ Chat™️ (Nils' Version™️) feat. Anthropic™️ Claude-2™️")

    with gr.Accordion("Settings"):
        aws_access = gr.Textbox(label="AWS Access Key", elem_id="aws_access")
        aws_secret = gr.Textbox(label="AWS Secret Key", elem_id="aws_secret")
        aws_token = gr.Textbox(label="AWS Session Token", elem_id="aws_token")
        temp = gr.Slider(0, 1, label="Temperature", elem_id="temp", value=1)
        max_tokens = gr.Slider(1, 4000, label="Max. Tokens", elem_id="max_tokens", value=4000)
        save_button = gr.Button("Save Settings")  
        load_button = gr.Button("Load Settings")  

        load_button.click(load_settings, js="""  
            () => {  
                let elems = ['#aws_access textarea', '#aws_secret textarea', '#aws_token textarea', '#temp input', '#max_tokens input'];
                elems.forEach(elem => {
                    let item = document.querySelector(elem);
                    let event = new InputEvent('input', { bubbles: true });
                    item.value = localStorage.getItem(elem.split(" ")[0].slice(1)) || '';
                    item.dispatchEvent(event);
                });
            }  
        """)

        save_button.click(save_settings, [aws_access, aws_secret, aws_token, temp, max_tokens], js="""  
            (acc, sec, tok, prompt, temp, ntok) => {  
                localStorage.setItem('aws_access', acc);  
                localStorage.setItem('aws_secret', sec);  
                localStorage.setItem('aws_token', tok);  
                localStorage.setItem('temp', document.querySelector('#temp input').value);  
                localStorage.setItem('max_tokens', document.querySelector('#max_tokens input').value);  
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
            bot, [txt, chatbot, aws_access, aws_secret, aws_token, temp, max_tokens], [txt, chatbot],
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
        bot, [txt, chatbot, aws_access, aws_secret, aws_token, temp, max_tokens], [txt, chatbot],
    )
    txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)
    file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False, postprocess=False)

demo.queue().launch()