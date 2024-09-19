import gradio as gr
import base64
import os
import requests
import json
import fitz
from PIL import Image
import io
from settings_mgr import generate_download_settings_js, generate_upload_settings_js

from doc2json import process_docx

dump_controls = False
log_to_console = False

temp_files = []

def encode_image(image_data):
    """Generates a prefix for image base64 data in the required format for the
    four known image formats: png, jpeg, gif, and webp.

    Args:
    image_data: The image data, encoded in base64.

    Returns:
    A string containing the prefix.
    """

    # Get the first few bytes of the image data.
    magic_number = image_data[:4]
  
    # Check the magic number to determine the image type.
    if magic_number.startswith(b'\x89PNG'):
        image_type = 'png'
    elif magic_number.startswith(b'\xFF\xD8'):
        image_type = 'jpeg'
    elif magic_number.startswith(b'GIF89a'):
        image_type = 'gif'
    elif magic_number.startswith(b'RIFF'):
        if image_data[8:12] == b'WEBP':
            image_type = 'webp'
        else:
            # Unknown image type.
            raise Exception("Unknown image type")
    else:
        # Unknown image type.
        raise Exception("Unknown image type")

    return f"data:image/{image_type};base64,{base64.b64encode(image_data).decode('utf-8')}"

def process_pdf_img(pdf_fn: str):
    pdf = fitz.open(pdf_fn)
    message_parts = []

    for page in pdf.pages():
        # Create a transformation matrix for rendering at the calculated scale
        mat = fitz.Matrix(0.6, 0.6)
        
        # Render the page to a pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Encode image to base64
        base64_encoded = base64.b64encode(img_byte_arr).decode('utf-8')
        
        # Construct the data URL
        image_url = f"data:image/png;base64,{base64_encoded}"
        
        # Append the message part
        message_parts.append({
            "type": "text",
            "text": f"Page {page.number} of file '{pdf_fn}'"
        })
        message_parts.append({
            "type": "image_url",
            "image_url": {
                "url": image_url,
                "detail": "high"
            }
        })

    pdf.close()

    return message_parts

def encode_file(fn: str) -> list:
    user_msg_parts = {}
    text_content = ""

    # if fn.endswith(".docx"):
    #     user_msg_parts.append({"type": "text", "text": process_docx(fn)})
    # elif fn.endswith(".pdf"):
    #     user_msg_parts.extend(process_pdf_img(fn))
    if False:
        pass
    else:
        with open(fn, mode="rb") as f:
            content = f.read()

        isImage = False
        if isinstance(content, bytes):
            try:
                # try to add as image
                content = encode_image(content)
                isImage = True
            except:
                # not an image, try text
                text_content = text_content + content.decode('utf-8', 'replace')
        else:
            text_content = text_content + str(content)

        if isImage:
            pass
            # user_msg_parts.append({"type": "image_url",
            #                     "image_url":{"url": content}})
        else:
            user_msg_parts["text"] = text_content

    return user_msg_parts

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
        if model == "whisper":
            result = ""
            whisper_prompt = system_prompt
            for human, assi in history:
                if human is not None:
                    if type(human) is tuple:
                        pass
                    else:
                        whisper_prompt += f"\n{human}"
                if assi is not None:
                        whisper_prompt += f"\n{assi}"

            if message.text:
                whisper_prompt += message.text
            if message.files:
                for file in message.files:
                    audio_fn = os.path.basename(file.path)
                    with open(file.path, "rb") as f:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1", 
                            prompt=whisper_prompt,
                            file=f,
                            response_format="text"
                            )
                    whisper_prompt += f"\n{transcription}"
                    result += f"\n``` transcript {audio_fn}\n {transcription}\n```"
            
            yield result

        elif model == "dall-e-3":
            response = client.images.generate(
                model=model,
                prompt=message.text,
                size="1792x1024",
                quality="hd",
                n=1,
            )
            yield gr.Image(response.data[0].url)
        else:
            seed_i = None
            if seed:
                seed_i = int(seed)

            if log_to_console:
                print(f"bot history: {str(history)}")

            history_openai_format = []
            user_msg_parts = ""
            if system_prompt:
                    history_openai_format.append({"role": "system", "content": system_prompt})
            for human, assi in history:
                if human is not None:
                    if type(human) is tuple:
                        fc = encode_file(human[0])
                        if fc["text"]:
                            user_msg_parts = user_msg_parts + fc["text"]
                    else:
                        user_msg_parts = user_msg_parts + human

                if assi is not None:
                    if user_msg_parts:
                        history_openai_format.append({"role": "user", "content": user_msg_parts})
                        user_msg_parts = ""

                    history_openai_format.append({"role": "assistant", "content": assi})

            if message['text']:
                user_msg_parts = user_msg_parts + message['text']
            if message['files']:
                for file in message['files']:
                    fc = encode_file(file['path'])
                    if fc["text"]:
                        user_msg_parts = user_msg_parts + fc["text"]
            history_openai_format.append({"role": "user", "content": user_msg_parts})
            user_msg_parts = []

            if log_to_console:
                print(f"br_prompt: {str(history_openai_format)}")

            url = "http://localhost:8000/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": history_openai_format,
                "max_tokens": max_tokens,
                "stream": True
            }

            response = requests.post(url, headers=headers, json=data, stream=True)

            if response.status_code != 200:
                gr.Error(f"Error: Received status code {response.status_code} {response.text}")
                return

            full_content = ""

            try:
                for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                event_data = line[6:]  # Remove 'data: ' prefix
                                if event_data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(event_data)
                                    content = chunk_data['choices'][0]['delta']['content']
                                    full_content += content
                                    yield full_content
                                except json.JSONDecodeError:
                                    gr.Error(f"Failed to decode JSON: {event_data}")
                                except KeyError:
                                    gr.Error(f"Unexpected data structure: {chunk_data}")

            except requests.exceptions.RequestException as e:
                gr.Error(f"An error occurred: {e}")

        if log_to_console:
            print(f"br_result: {str(full_content)}")

    except Exception as e:
        raise gr.Error(f"Error: {str(e)}")

def import_history(history, file):
    with open(file.name, mode="rb") as f:
        content = f.read()

        if isinstance(content, bytes):
            content = content.decode('utf-8', 'replace')
        else:
            content = str(content)
    os.remove(file.name)

    # Deserialize the JSON content
    import_data = json.loads(content)

    # Check if 'history' key exists for backward compatibility
    if 'history' in import_data:
        history = import_data['history']
        system_prompt.value = import_data.get('system_prompt', '')  # Set default if not present
    else:
        # Assume it's an old format with only history data
        history = import_data

    return history, system_prompt.value  # Return system prompt value to be set in the UI

with gr.Blocks(delete_cache=(86400, 86400)) as demo:
    gr.Markdown("# OAI Chat (Nils' Version™️)")
    with gr.Accordion("Startup"):
        gr.Markdown("""Use of this interface permitted under the terms and conditions of the 
                    [MIT license](https://github.com/ndurner/oai_chat/blob/main/LICENSE).
                    Third party terms and conditions apply, particularly
                    those of the LLM vendor (OpenAI) and hosting provider (Hugging Face). This app and the AI models may make mistakes, so verify any outputs.""")

        oai_key = gr.Textbox(label="OpenAI API Key", elem_id="oai_key")
        model = gr.Dropdown(label="Model", value="gpt-4-turbo", allow_custom_value=True, elem_id="model",
                            choices=["gpt-4-turbo", "gpt-4o-2024-08-06", "chatgpt-4o-latest", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo-preview", "gpt-4-1106-preview", "gpt-4", "gpt-4-vision-preview", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-1106", "whisper", "dall-e-3"])
        system_prompt = gr.TextArea("You are a helpful yet diligent AI assistant. Answer faithfully and factually correct. Respond with 'I do not know' if uncertain.", label="System Prompt", lines=3, max_lines=250, elem_id="system_prompt")  
        seed = gr.Textbox(label="Seed", elem_id="seed")
        temp = gr.Slider(0, 2, label="Temperature", elem_id="temp", value=1)
        max_tokens = gr.Slider(1, 16384, label="Max. Tokens", elem_id="max_tokens", value=800)
        save_button = gr.Button("Save Settings")  
        load_button = gr.Button("Load Settings")  
        dl_settings_button = gr.Button("Download Settings")
        ul_settings_button = gr.Button("Upload Settings")

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

        control_ids = [('oai_key', '#oai_key textarea'),
                       ('system_prompt', '#system_prompt textarea'),
                       ('seed', '#seed textarea'),
                       ('temp', '#temp input'),
                       ('max_tokens', '#max_tokens input'),
                       ('model', '#model')]
        controls = [oai_key, system_prompt, seed, temp, max_tokens, model]

        dl_settings_button.click(None, controls, js=generate_download_settings_js("oai_chat_settings.bin", control_ids))
        ul_settings_button.click(None, None, None, js=generate_upload_settings_js(control_ids))

    chat = gr.ChatInterface(fn=bot, multimodal=True, additional_inputs=controls, retry_btn = None, autofocus = False)
    chat.textbox.file_count = "multiple"
    chatbot = chat.chatbot
    chatbot.show_copy_button = True
    chatbot.height = 350

    if dump_controls:
        with gr.Row():
            dmp_btn = gr.Button("Dump")
            txt_dmp = gr.Textbox("Dump")
            dmp_btn.click(dump, inputs=[chatbot], outputs=[txt_dmp])

    with gr.Accordion("Import/Export", open = False):
        import_button = gr.UploadButton("History Import")
        export_button = gr.Button("History Export")
        export_button.click(lambda: None, [chatbot, system_prompt], js="""
            (chat_history, system_prompt) => {
                const export_data = {
                    history: chat_history,
                    system_prompt: system_prompt
                };
                const history_json = JSON.stringify(export_data);
                const blob = new Blob([history_json], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'chat_history.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
            """)
        dl_button = gr.Button("File download")
        dl_button.click(lambda: None, [chatbot], js="""
            (chat_history) => {
                // Attempt to extract content enclosed in backticks with an optional filename
                const contentRegex = /```(\\S*\\.(\\S+))?\\n?([\\s\\S]*?)```/;
                const match = contentRegex.exec(chat_history[chat_history.length - 1][1]);
                if (match && match[3]) {
                    // Extract the content and the file extension
                    const content = match[3];
                    const fileExtension = match[2] || 'txt'; // Default to .txt if extension is not found
                    const filename = match[1] || `download.${fileExtension}`;
                    // Create a Blob from the content
                    const blob = new Blob([content], {type: `text/${fileExtension}`});
                    // Create a download link for the Blob
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    // If the filename from the chat history doesn't have an extension, append the default
                    a.download = filename.includes('.') ? filename : `${filename}.${fileExtension}`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } else {
                    // Inform the user if the content is malformed or missing
                    alert('Sorry, the file content could not be found or is in an unrecognized format.');
                }
            }
        """)
        import_button.upload(import_history, inputs=[chatbot, import_button], outputs=[chatbot, system_prompt])

demo.unload(lambda: [os.remove(file) for file in temp_files])
demo.queue().launch()