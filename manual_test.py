import os
import cv2
import numpy as np
import tempfile
from modes.image_in_video import embed, decode
from preprocessing.video import reconstruct_video

def manual_test():
    # Create a random secret image
    rng = np.random.default_rng(42)
    secret_np = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as stmp:
        secret_path = stmp.name
    cv2.imwrite(secret_path, secret_np)
    
    # Create a dummy cover video
    frames = [rng.integers(0, 256, (200, 200, 3), dtype=np.uint8) for _ in range(20)]
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as ctmp:
        cover_path = ctmp.name
    reconstruct_video(frames, cover_path, 24.0)
    
    print(f"Embedding secret image {secret_path} into cover video {cover_path}...")
    stego_path, meta = embed(cover_path, secret_path, key="secret-password", b=2)
    print(f"Stego video created at {stego_path}")
    
    print("Decoding secret image from stego video...")
    recovered_path = decode(stego_path, key="secret-password", b=2, meta=meta)
    print(f"Recovered image saved at {recovered_path}")
    
    recovered_np = cv2.imread(recovered_path)
    
    # Compare original and recovered
    if np.array_equal(secret_np, recovered_np):
        print("SUCCESS: Recovered image matches the original!")
    else:
        difference = np.sum(np.abs(secret_np.astype(int) - recovered_np.astype(int)))
        print(f"FAILURE: Recovered image does NOT match the original. Total pixel difference: {difference}")

    # Cleanup
    for p in [secret_path, cover_path, stego_path, recovered_path]:
        if os.path.exists(p):
            os.unlink(p)

if __name__ == "__main__":
    manual_test()
