import math
import zmq
import cv2
import numpy as np
import socket
import json
import websockets
import asyncio
from time import time
import mediapipe as mp
import matplotlib.pyplot as plt


def detectPose(image, pose, display=True):

    # Create a copy of the input image.
    output_image = image.copy()

    # Convert the image from BGR into RGB format.
    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Perform the Pose Detection.
    results = pose.process(imageRGB)

    # Retrieve the height and width of the input image.
    height, width, _ = image.shape

    # Initialize a list to store the detected landmarks.
    landmarks = []

    # Check if any landmarks are detected.
    if results.pose_landmarks:

        # Draw Pose landmarks on the output image.
        mp_drawing.draw_landmarks(image=output_image, landmark_list=results.pose_landmarks,
                                  connections=mp_pose.POSE_CONNECTIONS)

        # Iterate over the detected landmarks.
        for landmark in results.pose_landmarks.landmark:

            # Append the landmark into the list.
            landmarks.append((int(landmark.x * width), int(landmark.y * height),
                                  (landmark.z * width)))

    # Check if the original input image and the resultant image are specified to be displayed.
    if display:

        # Display the original input image and the resultant image.
        plt.figure(figsize=[22,22])
        plt.subplot(121);plt.imshow(image[:,:,::-1]);plt.title("Original Image");plt.axis('off');
        plt.subplot(122);plt.imshow(output_image[:,:,::-1]);plt.title("Output Image");plt.axis('off');

        # Also Plot the Pose landmarks in 3D.
        mp_drawing.plot_landmarks(results.pose_world_landmarks, mp_pose.POSE_CONNECTIONS)

    # Otherwise
    else:

        # Return the output image and the found landmarks.
        return output_image, landmarks

def vid_detection():
    pose_video = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, model_complexity=1)

    # Initialize the VideoCapture object to read from the webcam.
    video = cv2.VideoCapture(0)

    # Create named window for resizing purposes
    cv2.namedWindow('Pose Detection', cv2.WINDOW_NORMAL)

    # Initialize the VideoCapture object to read from a video stored in the disk.
    # video = cv2.VideoCapture('media/running.mp4')

    # Set video camera size
    video.set(3, 1280)
    video.set(4, 960)

    # Initialize a variable to store the time of the previous frame.
    time1 = 0

    # Iterate until the video is accessed successfully.
    while video.isOpened():

        # Read a frame.
        ok, frame = video.read()

        # Check if frame is not read properly.
        if not ok:
            # Break the loop.
            break

        # Flip the frame horizontally for natural (selfie-view) visualization.
        frame = cv2.flip(frame, 1)

        # Get the width and height of the frame
        frame_height, frame_width, _ = frame.shape

        # Resize the frame while keeping the aspect ratio.
        frame = cv2.resize(frame, (int(frame_width * (640 / frame_height)), 640))

        # Perform Pose landmark detection.
        frame, _ = detectPose(frame, pose_video, display=False)

        # Set the time for this frame to the current time.
        time2 = time()

        # Check if the difference between the previous and this frame time > 0 to avoid division by zero.
        if (time2 - time1) > 0:
            # Calculate the number of frames per second.
            frames_per_second = 1.0 / (time2 - time1)

            # Write the calculated number of frames per second on the frame.
            cv2.putText(frame, 'FPS: {}'.format(int(frames_per_second)), (10, 30), cv2.FONT_HERSHEY_PLAIN, 2,
                        (0, 255, 0), 3)

        # Update the previous frame time to this frame time.
        # As this frame will become previous frame in next iteration.
        time1 = time2

        # Display the frame.
        cv2.imshow('Pose Detection', frame)

        # Wait until a key is pressed.
        # Retreive the ASCII code of the key pressed
        k = cv2.waitKey(1) & 0xFF

        # Check if 'ESC' is pressed.
        if (k == 27):
            # Break the loop.
            break

    # Release the VideoCapture object.
    video.release()

    # Close the windows.
    cv2.destroyAllWindows()


def calculateAngle(landmark1, landmark2, landmark3):
    '''
    This function calculates angle between three different landmarks.
    Args:
        landmark1: The first landmark containing the x,y and z coordinates.
        landmark2: The second landmark containing the x,y and z coordinates.
        landmark3: The third landmark containing the x,y and z coordinates.
    Returns:
        angle: The calculated angle between the three landmarks.

    '''

    # Get the required landmarks coordinates.
    x1, y1, _ = landmark1
    x2, y2, _ = landmark2
    x3, y3, _ = landmark3

    # Calculate the angle between the three points
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))

    # Check if the angle is less than zero.
    if angle < 0:
        # Add 360 to the found angle.
        angle += 360

    # Return the calculated angle.
    return angle


def classifyPose(landmarks, output_image, display=False):

    # Initialize the label of the pose. It is not known at this stage.
    #Unknown pose
    label = 'Unknown Pose'

    # Specify the color (Red) with which the label will be written on the image.
    color = (0, 0, 255)

    # Calculate the required angles.
    # ----------------------------------------------------------------------------------------------------------------

    # Get the angle between the left shoulder, elbow and wrist points.
    left_elbow_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value],
                                      landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value])

    # Get the angle between the right shoulder, elbow and wrist points.
    right_elbow_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value],
                                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value],
                                       landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value])

    # Get the angle between the left elbow, shoulder and hip points.
    left_shoulder_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value],
                                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                                         landmarks[mp_pose.PoseLandmark.LEFT_HIP.value])

    # Get the angle between the right hip, shoulder and elbow points.
    right_shoulder_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value],
                                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value],
                                          landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value])

    # Get the angle between the left hip, knee and ankle points.
    left_knee_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.LEFT_HIP.value],
                                     landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value],
                                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value])

    # Get the angle between the right hip, knee and ankle points
    right_knee_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value],
                                      landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value],
                                      landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value])

    # Get the angle between the left hip, knee and ankle points.
    left_hip_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                                     landmarks[mp_pose.PoseLandmark.LEFT_HIP.value],
                                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value])

    # Get the angle between the right hip, knee and ankle points
    right_hip_angle = calculateAngle(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value],
                                      landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value],
                                      landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value])

    if left_shoulder_angle > 70 and left_shoulder_angle < 120 and right_shoulder_angle > 70 and right_shoulder_angle < 120:

        if left_elbow_angle > 155 and left_elbow_angle < 205 and right_elbow_angle > 155 and right_elbow_angle < 205:

            if left_knee_angle > 160 and left_knee_angle < 205 and right_knee_angle > 160 and right_knee_angle < 205 and left_hip_angle > 170 and left_hip_angle < 190 and right_hip_angle > 170 and right_hip_angle < 190:
                # Specify the label of the pose that is tree pose.
                #tree pose
                label = "T Pose"
                #label = 1

            if 240 < left_knee_angle < 300 and 130 < left_hip_angle < 220:
                #'T + Knee Pose'
                label = 'T + Knee Pose'


        if left_elbow_angle > 50 and left_elbow_angle < 120 and right_elbow_angle > 230 and right_elbow_angle < 310:

            if left_knee_angle > 150 and left_knee_angle < 205 and right_knee_angle > 150 and right_knee_angle < 205 and left_hip_angle > 170 and left_hip_angle < 190 and right_hip_angle > 170 and right_hip_angle < 190:
                # Specify the label of the pose that is tree pose.
                # 'Flexin Pose'
                label = 'Flexin Pose'




    if label != 'Unknown Pose':
        # Update the color (to green) with which the label will be written on the image.
        color = (0, 255, 0)

    # ----------------------------------------------------------------------------------------------------------------

    # Check if it is the warrior II pose or the T pose.
    # As for both of them, both arms should be straight and shoulders should be at the specific angle.
    # ----------------------------------------------------------------------------------------------------------------

    # # Check if the both arms are straight.
    # if left_elbow_angle > 155 and left_elbow_angle < 205 and right_elbow_angle > 155 and right_elbow_angle < 205:
    #
    #     # Check if shoulders are at the required angle.
    #     if left_shoulder_angle > 70 and left_shoulder_angle < 120 and right_shoulder_angle > 70 and right_shoulder_angle < 120:
    #
    #         # Check if it is the warrior II pose.
    #         # ----------------------------------------------------------------------------------------------------------------
    #
    #         # Check if one leg is straight.
    #         if left_knee_angle > 165 and left_knee_angle < 195 or right_knee_angle > 165 and right_knee_angle < 195:
    #
    #             # Check if the other leg is bended at the required angle.
    #             if left_knee_angle > 90 and left_knee_angle < 120 or right_knee_angle > 90 and right_knee_angle < 120:
    #                 # Specify the label of the pose that is Warrior II pose.
    #                 label = 'Warrior II Pose'
    #
    #                 # ----------------------------------------------------------------------------------------------------------------
    #
    #         # Check if it is the T pose.
    #         # ----------------------------------------------------------------------------------------------------------------
    #
    #         # Check if both legs are straight
    #         if left_knee_angle > 150 and left_knee_angle < 205 and right_knee_angle > 150 and right_knee_angle < 205 and left_hip_angle > 170 and left_hip_angle < 190 and right_hip_angle > 170 and right_hip_angle < 190:
    #             # Specify the label of the pose that is tree pose.
    #             label = 'T Pose'
    #
    # # ----------------------------------------------------------------------------------------------------------------
    #
    # # Check if it is the tree pose.
    # # ----------------------------------------------------------------------------------------------------------------
    #
    # # Check if one leg is straight
    # if left_knee_angle > 165 and left_knee_angle < 195 or right_knee_angle > 165 and right_knee_angle < 195:
    #
    #     # Check if the other leg is bended at the required angle.
    #     if left_knee_angle > 315 and left_knee_angle < 335 or right_knee_angle > 25 and right_knee_angle < 45:
    #         # Specify the label of the pose that is tree pose.
    #         label = 'Tree Pose'

    # ----------------------------------------------------------------------------------------------------------------

    # Check if the pose is classified successfully
    if label != 'Unknown Pose':
        # Update the color (to green) with which the label will be written on the image.
        color = (0, 255, 0)

        # Write the label on the output image.
#    cv2.putText(output_image, label, (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    # Check if the resultant image is specified to be displayed.
    if display:

        # Display the resultant image.
        plt.figure(figsize=[10, 10])
        plt.imshow(output_image[:, :, ::-1]);
        plt.title("Output Image");
        plt.axis('off');

    else:

        # Return the output image and the classified label.
        return output_image, label


async def vid_detection_classification(websocket):


    # Setup Pose function for video.
    pose_video = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, model_complexity=1)

    # Initialize the VideoCapture object to read from the webcam.
    camera_video = cv2.VideoCapture(0)
    camera_video.set(3, 1280)
    camera_video.set(4, 960)

    # Initialize a resizable window.
    cv2.namedWindow('Pose Classification', cv2.WINDOW_NORMAL)

    # Iterate until the webcam is accessed successfully.
    while camera_video.isOpened():

        # Read a frame.
        ok, frame = camera_video.read()

        # Check if frame is not read properly.
        if not ok:
            # Continue to the next iteration to read the next frame and ignore the empty camera frame.
            continue

        # Flip the frame horizontally for natural (selfie-view) visualization.
        frame = cv2.flip(frame, 1)

        # Get the width and height of the frame
        frame_height, frame_width, _ = frame.shape

        # Resize the frame while keeping the aspect ratio.
        frame = cv2.resize(frame, (int(frame_width * (640 / frame_height)), 640))

        # Perform Pose landmark detection.
        frame, landmarks = detectPose(frame, pose_video, display=False)

        # Check if the landmarks are detected.
        if landmarks:
            # Perform the Pose Classification.
            frame, label = classifyPose(landmarks, frame, display=False)
            bytes_to_send = str.encode(label)
            if label != 'Unknown Pose':
                try:
                    jsonData = {
                        "label": label
                    }
                    #client_socket.send(bytes_to_send)
                    await websocket.send(json.dumps(jsonData))
                    print(bytes_to_send)
                except ValueError:
                    print("error")


        # Display the frame.
        cv2.imshow('Pose Classification', frame)

        # Wait until a key is pressed.
        # Retreive the ASCII code of the key pressed
        k = cv2.waitKey(1) & 0xFF

        # Check if 'ESC' is pressed.
        if (k == 27):
            # Break the loop.
            break

    # Release the VideoCapture object and close the windows.
    camera_video.release()
    cv2.destroyAllWindows()



async def serve():

   async with websockets.serve(vid_detection_classification, "localhost", 5555):
        await  asyncio.Future()






if __name__ == '__main__':

    # context = zmq.Context()
    # socket = context.socket(zmq.REP)
    # socket.bind("tcp://*:5555")

    # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.bind(('127.0.0.1', 5555))
    # server.listen(5)

    print(f"Server listening on port {5555}...")

    mp_pose = mp.solutions.pose

    # Setting up the Pose function.
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.3, model_complexity=2)

    # Initializing mediapipe drawing class, useful for annotation.
    mp_drawing = mp.solutions.drawing_utils


    asyncio.run(serve())

   # asyncio.get_event_loop().run_until_complete(serve())

    #
    # while True:
    #     client_socket, addr = server.accept()
    #     vid_detection_classification(client_socket)


# See PyCharm help at https://www.jetbrains.com/help/pycharm/