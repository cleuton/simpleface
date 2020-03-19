import sys
import cv2
import numpy as np
FACE_CASCADE_FILE = "./data/haarcascades/haarcascade_frontalface_alt.xml"
EYE_CASCADE_FILE = "./data/haarcascades/haarcascade_eye_tree_eyeglasses.xml"

def prepareImage(img):
    # Converts the image in the format you want
    preparedImage = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return preparedImage

def angle_between_2_points(p1, p2):
    # Get the angle of the horizontal line between 2 points (tuples)
    x1, y1 = p1
    x2, y2 = p2
    tan = (y2 - y1) / (x2 - x1)
    return np.degrees(np.arctan(tan))

def get_rotation_matrix(p1, p2):
    # Get a rotation matrix to straighten two points horizontally (the eyes)
    angle = angle_between_2_points(p1, p2)
    x1, y1 = p1
    x2, y2 = p2
    xc = (x1 + x2) // 2
    yc = (y1 + y2) // 2
    M = cv2.getRotationMatrix2D((xc, yc), angle, 1)
    return M   

def crop_image(image, det):
    # Crop the image to the size of the detected face
    left, top, right, bottom = det
    return image[top:bottom, left:right]   

def resizeAndPad(img, size, padColor=0):
    # Resizes and, if necessary, pads the face chip
    h, w = img.shape[:2]
    sh, sw = size
    error = 0

    # interpolation method
    if h > sh or w > sw: # shrinking image
        interp = cv2.INTER_AREA
    else: # stretching image
        interp = cv2.INTER_CUBIC

    # aspect ratio of image
    aspect = w/h  # if on Python 2, you might need to cast as a float: float(w)/h

    # compute scaling and pad sizing
    if aspect > 1: # horizontal image
        new_w = sw
        new_h = np.round(new_w/aspect).astype(int)
        pad_vert = (sh-new_h)/2
        pad_top, pad_bot = np.floor(pad_vert).astype(int), np.ceil(pad_vert).astype(int)
        pad_left, pad_right = 0, 0
    elif aspect < 1: # vertical image
        new_h = sh
        new_w = np.round(new_h*aspect).astype(int)
        pad_horz = (sw-new_w)/2
        pad_left, pad_right = np.floor(pad_horz).astype(int), np.ceil(pad_horz).astype(int)
        pad_top, pad_bot = 0, 0
    else: # square image
        new_h, new_w = sh, sw
        pad_left, pad_right, pad_top, pad_bot = 0, 0, 0, 0

    # set pad color
    if len(img.shape) is 3 and not isinstance(padColor, (list, tuple, np.ndarray)): # color image but only one color provided
        padColor = [padColor]*3

    # scale and pad
    try: 
        scaled_img = cv2.resize(img, (new_w, new_h), interpolation=interp)
        scaled_img = cv2.copyMakeBorder(scaled_img, pad_top, pad_bot, pad_left, pad_right, borderType=cv2.BORDER_CONSTANT, value=padColor)
    except:
        scaled_img = None
        error = 1

    return error,scaled_img      

def detectFaces(img, img_h=64,img_w=64,face_cascade_file=FACE_CASCADE_FILE,eye_cascade_file=EYE_CASCADE_FILE):
    # Detects any faces in the image and return a list with the original image and any other faces
    finalfaces=[]
    finalImage = prepareImage(img)
    face_cascade = cv2.CascadeClassifier()
    face_cascade.load(face_cascade_file)
    eyes_cascade = cv2.CascadeClassifier()
    eyes_cascade.load(eye_cascade_file)
    faces_collection = face_cascade.detectMultiScale(finalImage)
    faces_chips = []
    s_height, s_width = img.shape[:2]
    for (x,y,w,h) in faces_collection:
        center = (x + w//2, y + h//2)
        img = cv2.ellipse(img, center, (w//2, h//2), 0, 0, 360, (255, 0, 255), 4)
        faceROI = finalImage[y:y+h,x:x+w]
        eyes = eyes_cascade.detectMultiScale(faceROI)
        detected_eyes=[]
        eye_sum=0.0
        i=0
        for (x2,y2,w2,h2) in eyes:
            i=i+1
            eye_center = (x + x2 + w2//2, y + y2 + h2//2)
            eye_size = w2 * h2
            eye_sum = eye_sum + eye_size
            print("size:",eye_size)
            detected_eyes.append((eye_center,eye_size,(x2,y2,w2,h2)))

        # Now we have to be sure that we are processing just eyes
        eye_average = eye_sum / i
        eye_centers=[]
        print("Average:",eye_average)
        half_average=eye_average / 2
        for eye in detected_eyes:
            print("one eye:",eye[1])
            if eye[1] >= half_average:
                eye_centers.append(eye[0])
                print("eye ok:",eye_centers)
                x2,y2,w2,h2 = eye[2]
                radius = int(round((w2 + h2)*0.25))
                img = cv2.circle(img, eye[0], radius, (255, 0, 0 ), 4)  
        rotation_matrix = get_rotation_matrix(eye_centers[0], eye_centers[1])
        rotated = cv2.warpAffine(finalImage, rotation_matrix, (s_height, s_width), flags=cv2.INTER_CUBIC)
        cropped = crop_image(rotated, (x,y,w+x,h+y))      
        squared = resizeAndPad(cropped, (img_h,img_w), 127) 
        faces_chips.append(squared[1])       
    finalfaces.append(img)
    finalfaces.extend(faces_chips)
    return finalfaces

def imageFromFile(file, img_h=64,img_w=64):
    # Loads an image from a file
    img = cv2.imread(file)
    return recFaces(img, img_h,img_w)

def recFaces(img, img_h=64,img_w=64):
    # Main function to detect faces
    finalImage = detectFaces(img, img_h,img_w)
    return finalImage

if __name__=="__main__":
    # Writes any face chip on the same folder as input image
    # Arguments: <filename.jpg> <face_cascade_model> <eye_cascade_model>
    image_file = None
    if len(sys.argv)>1:
        image_file=sys.argv[1]
        if len(sys.argv)>2:
            face_cascade_file=sys.argv[2]
            if len(sys.argv>3):
                eye_cascade_file=sys.argv[3]
    else:
        print("Use: python pythonfaces.py <image file> <face cascade> <eye cascade>")
        sys.exit(1)
    images = imageFromFile(image_file,img_h=128,img_w=128)
    title = "Main image"
    for image in images:
        cv2.imshow(title,image)
        title = "Extrated face"
    cv2.waitKey(0)
    


