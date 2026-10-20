"""Run on the Windows Docker HOST, never in the client browser/container."""

import argparse
import hashlib
import hmac
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "data/biometrics"
guard = threading.RLock()
capture = None
owner = ""
timer = None
app = FastAPI(title="Caméra USB du PC hôte", docs_url=None, redoc_url=None, openapi_url=None)


def authorized(authorization: str = Header(default="")):
    expected = (ROOT / ".secrets/camera_key").read_text().strip()
    if not hmac.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(401, "Unauthorized")


class Command(BaseModel):
    username: str = Field(default="", max_length=64)
    session: str = Field(default="", max_length=128)


def model_path(username):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    return DIRECTORY / (hashlib.sha256(username.encode()).hexdigest() + ".yml")


def close_camera():
    global capture, owner, timer
    with guard:
        if capture is not None:
            capture.release()
        capture, owner = None, ""
        if timer:
            timer.cancel()
            timer = None


def open_camera(session):
    global capture, owner, timer
    if capture is not None:
        raise HTTPException(409, "Caméra occupée")
    if "USB_CAMERA_INDEX" not in os.environ:
        raise HTTPException(503, "Configurez USB_CAMERA_INDEX pour la caméra USB externe")
    capture = cv2.VideoCapture(int(os.environ["USB_CAMERA_INDEX"]), cv2.CAP_DSHOW)
    if not capture.isOpened():
        close_camera()
        raise HTTPException(503, "Caméra USB inaccessible")
    owner = session
    timer = threading.Timer(130, close_camera)
    timer.daemon = True
    timer.start()


def face_sample(detector):
    ok, image = capture.read()
    if not ok:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(90, 90))
    if len(faces) != 1:
        return None
    x, y, w, h = faces[0]
    return cv2.equalizeHist(cv2.resize(gray[y : y + h, x : x + w], (160, 160)))


def detector():
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def train(username):
    with guard:
        open_camera("enrollment")
        try:
            samples, end = [], time.monotonic() + 18
            cascade = detector()
            while time.monotonic() < end and len(samples) < 24:
                face = face_sample(cascade)
                if face is not None:
                    samples.append(face)
                time.sleep(0.15)
            if len(samples) < 20:
                raise HTTPException(422, "Visage unique insuffisamment visible : recommencez")
            model = cv2.face.LBPHFaceRecognizer_create()
            model.train(samples, np.ones(len(samples), dtype=np.int32))
            destination = model_path(username)
            temporary = destination.with_suffix(".tmp.yml")
            model.write(str(temporary))
            temporary.replace(destination)
            return {"enrolled": True}
        finally:
            close_camera()


@app.post("/verify", dependencies=[Depends(authorized)])
def verify(command: Command):
    with guard:
        open_camera(command.session)
        try:
            path = model_path(command.username)
            model = cv2.face.LBPHFaceRecognizer_create(
                threshold=float(os.getenv("FACE_DISTANCE_THRESHOLD", "55"))
            )
            if path.exists():
                model.read(str(path))
                model.setThreshold(float(os.getenv("FACE_DISTANCE_THRESHOLD", "55")))
            cascade, consecutive, end = detector(), 0, time.monotonic() + 8
            while time.monotonic() < end:
                face = face_sample(cascade)
                label = model.predict(face)[0] if face is not None and path.exists() else -1
                consecutive = consecutive + 1 if label == 1 else 0
                if consecutive >= 5:
                    return {"matched": True}
                time.sleep(0.1)
            return {"matched": False}
        except Exception:
            close_camera()
            raise


@app.post("/close", dependencies=[Depends(authorized)])
def close(command: Command):
    with guard:
        if command.session == owner:
            close_camera()
    return {"closed": True}


@app.post("/enroll", dependencies=[Depends(authorized)])
def enroll(command: Command):
    return train(command.username)


@app.post("/delete", dependencies=[Depends(authorized)])
def delete(command: Command):
    with guard:
        model_path(command.username).unlink(missing_ok=True)
    return {"deleted": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    if args.bootstrap:
        username = os.getenv("DEMO_USERNAME", "operator")
        if model_path(username).exists():
            raise SystemExit("Already enrolled. Use back-office management to replace the model.")
        print("Présentez le visage de l'administrateur devant la caméra USB du PC hôte.")
        train(username)
        print("Enrôlement initial terminé, aucune image brute conservée.")
    else:
        import uvicorn

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8765,
            access_log=False,
            ssl_certfile=str(ROOT / ".secrets/camera_cert"),
            ssl_keyfile=str(ROOT / ".secrets/camera_tls_key"),
        )
