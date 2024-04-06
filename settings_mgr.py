def generate_download_settings_js(dl_fn, control_ids):
    js_code = """
    async (""" + ", ".join([f'{ctrl[0]}' for ctrl in control_ids]) + """) => {  
        const password = prompt("Please enter a password for encryption", " ");
        if (!password) {
            alert("No password provided. Cancelling download.");
            return;
        }
        
        let settings = {""" + ", ".join([f'"{ctrl[0]}": {ctrl[0]}' for ctrl in control_ids]) + """};
        const settingsStr = JSON.stringify(settings);
        const textEncoder = new TextEncoder();
        const encodedSettings = textEncoder.encode(settingsStr);
        const salt = crypto.getRandomValues(new Uint8Array(16));
        const passwordBuffer = textEncoder.encode(password);
        const keyMaterial = await crypto.subtle.importKey('raw', passwordBuffer, {name: 'PBKDF2'}, false, ['deriveKey']);
        const key = await crypto.subtle.deriveKey(
            {name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256'}, 
            keyMaterial, 
            {name: 'AES-GCM', length: 256}, 
            false, 
            ['encrypt']
        );
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const encryptedSettings = await crypto.subtle.encrypt({name: 'AES-GCM', iv: iv}, key, encodedSettings);
        const blob = new Blob([salt, iv, new Uint8Array(encryptedSettings)], {type: 'application/octet-stream'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '""" + dl_fn + """';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }"""
    return js_code

def generate_upload_settings_js(control_ids):
    js_code = """
    async () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.onchange = async e => {
            const file = e.target.files[0];
            if (!file) {
                alert("No file selected.");
                return;
            }
            
            const password = prompt("Please enter the password for decryption", " ");
            if (!password) {
                alert("No password provided. Cancelling upload.");
                return;
            }
            
            const arrayBuffer = await file.arrayBuffer();
            const salt = arrayBuffer.slice(0, 16);
            const iv = arrayBuffer.slice(16, 28);
            const encryptedData = arrayBuffer.slice(28);
            const textEncoder = new TextEncoder();
            const passwordBuffer = textEncoder.encode(password);
            const keyMaterial = await crypto.subtle.importKey('raw', passwordBuffer, {name: 'PBKDF2'}, false, ['deriveKey']);
            const key = await crypto.subtle.deriveKey(
                {name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256'}, 
                keyMaterial, 
                {name: 'AES-GCM', length: 256}, 
                false, 
                ['decrypt']
            );
            
            try {
                const decryptedData = await crypto.subtle.decrypt({name: 'AES-GCM', iv: iv}, key, encryptedData);
                const textDecoder = new TextDecoder();
                const settingsStr = textDecoder.decode(decryptedData);
                const settings = JSON.parse(settingsStr);
                """ + "\n".join([f'document.querySelector("{ctrl[1]}").value = settings["{ctrl[0]}"];' for ctrl in control_ids]) + """
                """ + "\n".join([f'document.querySelector("{ctrl[1]}").dispatchEvent(new InputEvent("input", {{ bubbles: true }}));' for ctrl in control_ids]) + """
            } catch (err) {
                alert("Failed to decrypt. Check your password and try again.");
                console.error("Decryption failed:", err);
            }
        };
        input.click();
    }"""
    return js_code