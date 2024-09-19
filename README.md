# MLX Chat

Chat interface for [MLX](https://github.com/ml-explore/mlx) for on-device Language Model use on Apple Silicon.
Built on [FastMLX](https://github.com/Blaizzy/fastmlx).

## Features:
 * Plaintext file upload
 * chat history download
 * file download
   * example: download an ICS calendar file the model has created for you
* streaming chat

## Using
1. (Install fastmlx: `pip3 install mlx-lm fastmlx`)
1. (Install model(s): run infra.py to view supported/installed models, modify & run infra-add.py to download & install new model)
1. `pip3 install -r requirements.txt`
1. `python3 ./app.py``
1. Check output, open "local URL" in browser
1. Enter/select locally available model to chat with