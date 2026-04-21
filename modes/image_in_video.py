import cv2
import struct
import numpy as np


def to_bits(data: bytes):
    return ''.join(f"{byte:08b}" for byte in data)


def from_bits(bits: str):
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))


# ================= EMBED =================
def embed(video_path, image_path, output_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("Cannot open video")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Cannot read image")

    h, w, c = img.shape
    data = img.tobytes()

    # header: height, width, channels, data length
    header = struct.pack("IIII", h, w, c, len(data))
    payload = header + data

    bits = to_bits(payload)
    bit_idx = 0

    width = int(cap.get(3))
    height = int(cap.get(4))
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0

    # lossless codec
    fourcc = cv2.VideoWriter_fourcc(*'FFV1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    capacity = width * height * 3 * int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if len(bits) > capacity:
        raise ValueError("Data too large for video capacity")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        flat = frame.flatten()

        for i in range(len(flat)):
            if bit_idx < len(bits):
                
                flat[i] = (int(flat[i]) & 254) | int(bits[bit_idx])
                bit_idx += 1

        frame = flat.reshape(frame.shape)
        out.write(frame)

    cap.release()
    out.release()

    return output_path


# ================= DECODE =================
def decode(video_path, output_image_path="decoded.png"):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("Cannot open video")

    bits = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        flat = frame.flatten()

        for value in flat:
            bits += str(value & 1)

    cap.release()


    header_bytes = from_bits(bits[:128])
    h, w, c, length = struct.unpack("IIII", header_bytes)

    data_bits = bits[128:128 + (length * 8)]
    data_bytes = from_bits(data_bits)

    img_array = np.frombuffer(data_bytes, dtype=np.uint8)
    img = img_array.reshape((h, w, c))

    cv2.imwrite(output_image_path, img)

    return output_image_path
