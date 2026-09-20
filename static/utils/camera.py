import cv2
import os
from datetime import datetime

def capture_photo(upload_folder: str, candidate_name: str) -> str:
    """
    Opens the webcam, displays a live preview, and captures an image when SPACE is pressed.
    Press ESC to cancel.
    Returns the filename of the captured image, or None if canceled.
    """
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return None

    print("Press SPACE to capture the photo. Press ESC to cancel.")
    
    filename = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Display the resulting frame
        cv2.imshow('Registration Photo Capture (SPACE to capture, ESC to cancel)', frame)
        
        # Wait for key press
        key = cv2.waitKey(1)
        
        if key % 256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            break
        elif key % 256 == 32:
            # SPACE pressed
            safe_name = "".join([c for c in candidate_name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(' ', '_').lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{timestamp}.jpg"
            filepath = os.path.join(upload_folder, filename)
            
            # Save the frame
            cv2.imwrite(filepath, frame)
            print(f"{filename} written!")
            break

    cap.release()
    cv2.destroyAllWindows()
    
    return filename
