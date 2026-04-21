"""Tests for modes.image_in_video: embed, decode."""

import os
from modes.image_in_video import embed, decode


def test_embed_creates_output():
    video_path = "test_input.mp4"
    image_path = "test_image.png"
    output_path = "test_output.mp4"

    
    result = embed(video_path, image_path, output_path)

 
    assert result == output_path

   
    assert os.path.exists(output_path)


def test_decode_runs():
    video_path = "test_output.mp4"

    result = decode(video_path)

    
    assert result is None or isinstance(result, str)

def test_output_not_empty():
    output_path = "test_output.mp4"
    assert os.path.getsize(output_path) > 0
