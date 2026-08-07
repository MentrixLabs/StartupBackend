## Image Generation

Image generator based on ComfyUI workflow. It requires ComfyUI repository with downloaded models.

#### Clone https://github.com/comfyanonymous/ComfyUI

    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    pip install -r requirements
    python main.py

#### Download clips and models into models folders

For download, you need to authorize your account with Hugginface

Download into `models/checkpoints`
```
https://huggingface.co/stabilityai/stable-diffusion-3.5-medium/resolve/main/sd3.5_medium.safetensors7
```

Download into `models/clip`
```
https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/blob/main/text_encoders/clip_l.safetensors
https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/blob/main/text_encoders/clip_g.safetensors

https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/blob/main/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors
OR
https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/blob/main/text_encoders/t5xxl_fp16.safetensors
```
(if using t5xxl_fp16.safetensors, update script)

Put `image_generation.py` script into ComfyUI folder

Run `run_workflow(positive_prompt, negative_prompt)` method from another Python script, which returns numpy array for an
image.
It also saves generated image into `ComfyUI/output` folder.

Run `python image_generation.py` from command line to test.

#### To export ComfyUI workflow into new python script use an extension https://github.com/pydn/ComfyUI-to-Python-Extension

Cd into ComfyUI custom_nodes and clone extension in there

    cd ComfyUI/custom_nodes
    git clone https://github.com/pydn/ComfyUI-to-Python-Extension.git

Restart ComfyUI