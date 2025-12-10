import tensorflow as tf
import coremltools as ct
import os
import numpy as np

# Since this script is in the root of stable_diffusion, we need to adjust the path
# to import from stable_diffusion_tf_models
import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, '../stable_diffusion_tf_models'))

from interface import get_models

def convert_text_encoder():
    """
    Converts the Text Encoder part of the model to Core ML format.
    """
    print("Fetching Keras Text Encoder model architecture...")
    # Get the Keras models. We only need the text_encoder for this step.
    # is_sd2=False corresponds to the SD 1.x models.
    text_encoder, _, _, _, _, _, _, _ = get_models(is_sd2=False)

    print("Model architecture loaded.")

    # Define the input shapes for the Core ML model.
    # The input names should ideally match the Keras model's input names
    # for clarity, but it's the shape and type that are critical.
    mlmodel_inputs = [
        ct.TensorType(name="input_word_ids", shape=(1, 77), dtype=np.int32),
        ct.TensorType(name="input_pos_ids", shape=(1, 77), dtype=np.int32)
    ]

    print("Starting Core ML conversion...")
    # Convert the model
    model = ct.convert(
        [text_encoder], # The model or list of models to convert
        inputs=mlmodel_inputs,
        source="tensorflow", # Explicitly tell coremltools the source framework
        # No outputs need to be specified, coremltools will infer them.
    )

    print("Conversion successful.")

    # Create a directory to save the models
    output_dir = "coreml_models"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, "TextEncoder.mlpackage")
    print(f"Saving converted model to {output_path}...")

    model.save(output_path)
    print("Model saved successfully.")


if __name__ == "__main__":
    convert_text_encoder()
