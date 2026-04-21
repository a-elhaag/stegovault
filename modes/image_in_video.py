import cv2


def resize_overlay(overlay, max_width=150):
    h, w = overlay.shape[:2]
    scale = max_width / w
    return cv2.resize(overlay, (int(w * scale), int(h * scale)))


def overlay_image(frame, overlay, x, y, alpha=0.7):
    h, w = overlay.shape[:2]


    if y + h > frame.shape[0] or x + w > frame.shape[1]:
        return frame

    roi = frame[y:y+h, x:x+w]

    
    blended = cv2.addWeighted(roi, 1 - alpha, overlay, alpha, 0)

    frame[y:y+h, x:x+w] = blended
    return frame


def image_in_video(video_path, image_path, output_path):
    cap = cv2.VideoCapture(video_path)

    overlay = cv2.imread(image_path)
    overlay = resize_overlay(overlay)

    width = int(cap.get(3))
    height = int(cap.get(4))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

    
        x = width - overlay.shape[1] - 10
        y = 10

        frame = overlay_image(frame, overlay, x, y)

        out.write(frame)

    cap.release()
    out.release()

    print("Video created successfully!")
    return output_path
