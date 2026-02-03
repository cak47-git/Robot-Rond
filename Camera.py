import cv2
import numpy as np

def detect_red_ball_on_frame(frame, min_radius=10, max_radius=400, param1=50, param2=30, min_dist=20):
    """
    Detects only red circular or circle-like objects in a video frame.
    Args:
        frame (numpy.ndarray): The video frame (BGR image).
        min_radius (int): Minimum radius of detected circles.
        max_radius (int): Maximum radius of detected circles.
        param1 (int): Upper threshold for the internal Canny edge detector.
        param2 (int): Threshold for center detection.
        min_dist (int): Minimum distance between detected circle centers.
    Returns:
        tuple: (circles_list, hsv, mask, gray, gray_blurred)
    """
    if frame is None or frame.size == 0:
        print("Error: Empty frame.")
        return None, None, None, None, None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define the lower and upper bounds for red color in HSV
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    # Create masks for the two ranges of red
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Apply morphological operations to reduce noise
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # Apply the mask to the grayscale image
    gray = cv2.bitwise_and(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), mask=mask)
    gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

    circles = cv2.HoughCircles(
        gray_blurred,
        cv2.HOUGH_GRADIENT,
        1,
        min_dist,
        param1=param1,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius,
    )

    if circles is not None:
        circles = np.uint16(np.around(circles[0, :]))
        return circles.tolist(), hsv, mask, gray, gray_blurred
    else:
        return None, hsv, mask, gray, gray_blurred

def draw_circles_on_frame(frame, circles):
    """Draws circles on the frame.
    Args:
        frame (numpy.ndarray): The video frame (BGR image).
        circles (list): List of circles (x, y, radius).
    """
    if frame is None or frame.size == 0:
        print("Error: Empty frame.")
        return

    if circles is not None:
        for x, y, r in circles:
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)  # Draw center
    cv2.imshow("Detected Red Ball", frame)

# Se connecter à la caméra
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

while True:
    # Prendre une image de la caméra
    ret, frame = cap.read()

    # Trouver une balle rouge sur l'image
    circles, hsv, mask, gray, gray_blurred = detect_red_ball_on_frame(frame)

    # Mettre un cercle vert autour de la ball trouvée pour debug
    draw_circles_on_frame(frame.copy(), circles)

    # Montrer d'autres les étapes de la detection de la balle rouge pour debug
    if hsv is not None:
        cv2.imshow("HSV", hsv)
    if gray is not None:
        cv2.imshow("Gray", gray)
#    if gray_blurred is not None:
#        cv2.imshow("Gray Blurred", gray_blurred)
#    if mask is not None:
#        cv2.imshow("Mask", mask)

    # Si le script est lancé en ligne de commande, on peut quitter avec 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()