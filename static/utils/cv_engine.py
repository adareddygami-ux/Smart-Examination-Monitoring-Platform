import cv2
import os
import numpy as np
from flask import current_app

def get_face_detector():
    """Loads and returns the Haar Cascade classifier."""
    cascade_path = get_cascade_path('haarcascade_frontalface_default.xml')
    return cv2.CascadeClassifier(cascade_path)

def get_cascade_path(filename):
    """Resolve cascade files across OpenCV wheel layouts."""
    candidates = [
        os.path.join(cv2.data.haarcascades, filename),
        os.path.join(os.path.dirname(cv2.__file__), 'data', filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

def extract_face(image):
    """Detects and returns the cropped face from an image. Returns None if 0 or >1 faces detected."""
    detector = get_face_detector()
    if detector.empty():
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    if len(faces) == 1:
        x, y, w, h = faces[0]
        return gray[y:y+h, x:x+w]
    return None

def verify_face(registered_photo_filename, live_frame):
    """
    Compares the live frame against the registered photo using LBPH.
    Returns True if similarity exceeds threshold, False otherwise.
    """
    if not registered_photo_filename:
        return False
        
    upload_folder = current_app.config['UPLOAD_FOLDER']
    registered_path = os.path.join(upload_folder, registered_photo_filename)
    
    if not os.path.exists(registered_path):
        return False
        
    reg_img = cv2.imread(registered_path)
    if reg_img is None:
        return False
        
    reg_face = extract_face(reg_img)
    live_face = extract_face(live_frame)
    
    if reg_face is None or live_face is None:
        return False
        
    # Resize both to the same size for better LBPH performance
    reg_face = cv2.resize(reg_face, (200, 200))
    live_face = cv2.resize(live_face, (200, 200))
    
    # Identity verification must use a face matcher, not a generic image
    # similarity check that could accept a different person.
    if not hasattr(cv2, 'face'):
        raise RuntimeError('OpenCV face recognizer is unavailable')

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([reg_face], np.array([1]))
    _, confidence = recognizer.predict(live_face)

    # LBPH confidence is a distance: lower means a closer face match.
    return confidence < 70.0

def analyze_frame(live_frame):
    """
    Analyzes the frame during live monitoring.
    Returns a dict with the status of the face.
    """
    detector = get_face_detector()
    profile_cascade = cv2.CascadeClassifier(get_cascade_path('haarcascade_profileface.xml'))
    eye_cascade = cv2.CascadeClassifier(get_cascade_path('haarcascade_eye.xml'))

    if detector.empty():
        return {'status': 'No Face'}
    
    gray = cv2.cvtColor(live_frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    if len(faces) == 0:
        # Check for profile face (looking away)
        profiles = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)) if not profile_cascade.empty() else ()
        if len(profiles) > 0:
            return {'status': 'Looking Away'}
            
        # Try flipping the image for the other profile
        flipped_gray = cv2.flip(gray, 1)
        profiles_flipped = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)) if not profile_cascade.empty() else ()
        if len(profiles_flipped) > 0:
            return {'status': 'Looking Away'}
            
        return {'status': 'No Face'}
        
    elif len(faces) > 1:
        return {'status': 'Multiple Faces'}
    
    # Face is present, now check for eyes
    x, y, w, h = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=5, minSize=(15, 15)) if not eye_cascade.empty() else ()
    
    if len(eyes) == 0:
        return {'status': 'Eyes Not Detected'}
        
    return {'status': 'Face Present'}
