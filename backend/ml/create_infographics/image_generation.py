import os
import random

import sys
from typing import Sequence, Mapping, Any, Union

import torch

# Fixed seed
# SEED = 12345678

# Random seed
SEED = random.randint(1, 2 ** 64)

SD_MODEL = "sd3.5_medium.safetensors"

CLIP1_MODEL = "clip_g.safetensors"
CLIP2_MODEL = "clip_l.safetensors"
CLIP3_MODEL = "t5xxl_fp8_e4m3fn_scaled.safetensors"
# CLIP3_MODEL = "t5xxl_fp16.safetensors"


def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Recursively call the function with the parent directory
    return find_path(name, parent_directory)


def add_comfyui_directory_to_sys_path() -> None:
    """
    Add 'ComfyUI' to the sys.path
    """
    comfyui_path = find_path("ComfyUI")
    if comfyui_path is not None and os.path.isdir(comfyui_path):
        sys.path.append(comfyui_path)
        print(f"'{comfyui_path}' added to sys.path")


def add_extra_model_paths() -> None:
    """
    Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
    """
    try:
        from main import load_extra_path_config
    except ImportError:
        print(
            "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
        )
        from utils.extra_config import load_extra_path_config

    extra_model_paths = find_path("extra_model_paths.yaml")

    if extra_model_paths is not None:
        load_extra_path_config(extra_model_paths)
    else:
        print("Could not find the extra_model_paths config file.")


add_comfyui_directory_to_sys_path()
add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    import asyncio
    import execution
    from nodes import init_extra_nodes
    import server

    # Creating a new event loop and setting it as the default loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Creating an instance of PromptServer with the loop
    server_instance = server.PromptServer(loop)
    execution.PromptQueue(server_instance)

    # Initializing custom nodes
    init_extra_nodes()


from nodes import NODE_CLASS_MAPPINGS

def run_workflow(positive_prompt: str, negative_prompt: str) -> Any:

    if positive_prompt is None:
        return None

    if negative_prompt is None:
        return None

    import_custom_nodes()
    with torch.inference_mode():
        checkpointloadersimple = NODE_CLASS_MAPPINGS["CheckpointLoaderSimple"]()
        checkpointloadersimple_4 = checkpointloadersimple.load_checkpoint(
            ckpt_name=SD_MODEL
        )

        triplecliploader = NODE_CLASS_MAPPINGS["TripleCLIPLoader"]()
        triplecliploader_11 = triplecliploader.load_clip(
            clip_name1=CLIP1_MODEL,
            clip_name2=CLIP2_MODEL,
            clip_name3=CLIP3_MODEL,
        )

        cliptextencode = NODE_CLASS_MAPPINGS["CLIPTextEncode"]()
        cliptextencode_6 = cliptextencode.encode(
            text=positive_prompt,
            clip=get_value_at_index(triplecliploader_11, 0),
        )

        cliptextencode_71 = cliptextencode.encode(
            text=negative_prompt, clip=get_value_at_index(triplecliploader_11, 0)
        )

        emptysd3latentimage = NODE_CLASS_MAPPINGS["EmptySD3LatentImage"]()
        emptysd3latentimage_135 = emptysd3latentimage.generate(
            width=1280, height=768, batch_size=1
        )

        modelsamplingsd3 = NODE_CLASS_MAPPINGS["ModelSamplingSD3"]()
        conditioningzeroout = NODE_CLASS_MAPPINGS["ConditioningZeroOut"]()
        conditioningsettimesteprange = NODE_CLASS_MAPPINGS[
            "ConditioningSetTimestepRange"
        ]()
        conditioningcombine = NODE_CLASS_MAPPINGS["ConditioningCombine"]()
        ksampler = NODE_CLASS_MAPPINGS["KSampler"]()
        vaedecode = NODE_CLASS_MAPPINGS["VAEDecode"]()
        saveimage = NODE_CLASS_MAPPINGS["SaveImage"]()

        result_array = None

        for q in range(1):
            modelsamplingsd3_13 = modelsamplingsd3.patch(
                shift=3, model=get_value_at_index(checkpointloadersimple_4, 0)
            )

            conditioningzeroout_67 = conditioningzeroout.zero_out(
                conditioning=get_value_at_index(cliptextencode_71, 0)
            )

            conditioningsettimesteprange_68 = conditioningsettimesteprange.set_range(
                start=0.2,
                end=1,
                conditioning=get_value_at_index(conditioningzeroout_67, 0),
            )

            conditioningsettimesteprange_70 = conditioningsettimesteprange.set_range(
                start=0, end=0.2, conditioning=get_value_at_index(cliptextencode_71, 0)
            )

            conditioningcombine_69 = conditioningcombine.combine(
                conditioning_1=get_value_at_index(conditioningsettimesteprange_68, 0),
                conditioning_2=get_value_at_index(conditioningsettimesteprange_70, 0),
            )

            ksampler_294 = ksampler.sample(
                seed=SEED,
                steps=40,
                cfg=5.5,
                sampler_name="dpmpp_2m",
                scheduler="sgm_uniform",
                denoise=1,
                model=get_value_at_index(modelsamplingsd3_13, 0),
                positive=get_value_at_index(cliptextencode_6, 0),
                negative=get_value_at_index(conditioningcombine_69, 0),
                latent_image=get_value_at_index(emptysd3latentimage_135, 0),
            )

            vaedecode_8 = vaedecode.decode(
                samples=get_value_at_index(ksampler_294, 0),
                vae=get_value_at_index(checkpointloadersimple_4, 2),
            )

            images = get_value_at_index(vaedecode_8, 0)

            saveimage.save_images(
                filename_prefix="product",
                images=get_value_at_index(vaedecode_8, 0),
                prompt=f"{positive_prompt} | {negative_prompt}",
            )

            if len(images) > 0:
                result_array = images[0].cpu().numpy()

        return result_array


if __name__ == "__main__":

    print(f'🖙 Введите позитивный промт:')
    positive_prompt = str(input())

    print(f'🖙 Введите негативный промт:')
    negative_prompt = str(input())

    result = run_workflow(positive_prompt = positive_prompt, negative_prompt = negative_prompt)
    print(result)
