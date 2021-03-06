import cv2
import numpy as np
import sys

def dist(t1, t2):
    (x1, y1) = t1
    (x2, y2) = t2
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

class Box:
    def modify(self, box1, box2):
        x = min([box1.x, box2.x])
        y = min([box1.y, box2.y])
        x2 = max([box2.x, box1.x])
        y2 = max([box1.y, box2.y])
        self.x, self.y, self.w, self.h = x,y,x2-x, y2-y
        self.N = self.w*self.h
        self.num_pixels = box1.num_pixels + box2.num_pixels
        self.mean_x = (box1.num_pixels*box1.mean_x + box2.num_pixels*box2.mean_x)/(box1.num_pixels + box2.num_pixels)

    def __init__(self, image, x, y, w, h):
        self.image_shape = image.shape
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.N = w*h
        mean_x = 0
        mean_y = 0
        num_pixels = 0
        for j in range(x,x+w):
            for i in range(y,y+h):
                if image[i,j]==0:
                    mean_x += j
                    mean_y += i
                    num_pixels += 1
        self.num_pixels = num_pixels
        if(num_pixels == 0):
            self.w = 0
            self.h = 0
            self.mean_x = 1000
            self.mean_y = 1000
            
        else:
            self.mean_x = mean_x/num_pixels
            self.mean_y = mean_y/num_pixels
            mean_1_1 = 0;
            mean_2_0 = 0;
            mean_0_2 = 0;
            for j in range(x,x+w):
                for i in range(y, y+h):
                    if image[i,j] == 0:
                        mean_1_1 += (i - self.mean_x)*(j - self.mean_y)
                        mean_2_0 += (j - self.mean_x)**2
                        mean_0_2 += (i - self.mean_y)**2
            if(mean_2_0 == mean_0_2):
                self.theta = 0
            else:
                self.theta = 0.5*np.arctan(2*mean_1_1/(mean_2_0 - mean_0_2))
    def distance(self, box2):
        # Taken from stackoverflow
        (x1, y1, x1b, y1b) = (self.x, self.y, self.x + self.w, self.y + self.h)
        (x2, y2, x2b, y2b) = (box2.x, box2.y, box2.x + box2.w, box2.y + box2.h)
        left = x2b < x1
        right = x1b < x2
        bottom = y2b < y1
        top = y1b < y2
        if top and left:
            return dist((x1, y1b), (x2b, y2))
        elif left and bottom:
            return dist((x1, y1), (x2b, y2b))
        elif bottom and right:
            return dist((x1b, y1), (x2, y2b))
        elif right and top:
            return dist((x1b, y1b), (x2, y2))
        elif left:
            return x1 - x2b
        elif right:
            return x2 - x1b
        elif bottom:
            return y1 - y2b
        elif top:
            return y2 - y1b
        else:             # rectangles intersect
            return 0

def high_boost(image, i, j, w):
    return_value = 0
    for x in range(i-1,i+1):
        for y in range(j-1,j+1):
            return_value -= image[x,y]
    return_value += (w+1)*image[i,j]
    return (return_value/9.0)


def preprocess(img):
    img = cv2.medianBlur(img,3)
    sobel = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize = 5)
    m,n = img.shape
    intermediate_image = np.ones((m,n), dtype = np.uint8)*255
    f = 11
    threshold = 70
    for i in range(1,m-1):
        for j in range(1,n-1):
            s = sobel[i,j]/255.0
            g = img[i,j]/255.0
            z = 0.4
            if s <= 0.5:
                z = 0.8
            w = (z*(1-s) + (1-z)*(1-g))*(f-8) + 8
            boost = high_boost(img, i, j, w)
            # intermediate_image[i,j] = boost
            if boost <= threshold:
                intermediate_image[i,j] = 0
    # intermediate_image = cv2.medianBlur(img, 3)
    intermediate_image = cv2.medianBlur(intermediate_image,3)
    # cv2.imwrite('test.jpg',intermediate_image)
    return intermediate_image

def separation(image, originalImage):
    img = image.copy()
    image = cv2.bitwise_not(image)
    _, contours, _ = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    # print(len(contours))
    boxes = [] # list of the tuples 

    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        if(w*h < 25):
            continue
        boxes.append(Box(image, x, y, w, h))
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 1)
        cv2.rectangle(originalImage, (x, y), (x + w, y + h), (0, 255, 0), 1)
    

    cv2.imwrite('intermediate_boxed.png', img)
    cv2.imwrite('original_boxes.png', originalImage)
    return boxes

# def merge(boxes, n_max):
#     for n in range(1, N_max+1):
#         r = 8 - 6 *(n - 1)/(n_max - 1)
#         for box in boxes:
#             if box.num_pixels == n:

def merge_boxes(img, boxes):
    num_boxes = len(boxes)
    for i in range(num_boxes):
        for j in range(i+1, num_boxes):
            if boxes[i].distance(boxes[j])  == 0:
                new_box = Box(img, 0,0,0,0)
                new_box.modify(boxes[i],boxes[j])
                modded = [new_box]
                for k in range(0, num_boxes):
                    if not(k == i) and not(k == j):
                        modded.append(boxes[k])
                return merge_boxes(img, modded)
    return boxes



def find_eyes(boxes):
    boxes.sort(key = lambda x: x.y)
    possible_eyes = []
    for box in boxes:
        # Check if the box height is between 7% - 15%
        if not(box.h >= 0.07*box.image_shape[0] and box.h <= 0.15*box.image_shape[1]):
            continue
        if not(box.w >= 0.2*box.image_shape[1]):
            continue
        if box.w < box.h:
            continue
        possible_eyes.append(box)
    num_boxes = len(possible_eyes)
    while len(possible_eyes) > 2:
        distance_to_nearest_box = []
        for i in range(len(possible_eyes)):
            minimum = 10000
            for j in range(len(possible_eyes)):
                if not(i == j):
                    if minimum > np.abs(possible_eyes[i].mean_y - possible_eyes[j].mean_y):
                        minimum = np.abs(possible_eyes[i].mean_y - possible_eyes[j].mean_z)
            distance_to_nearest_box.append(minimum)
        _, idx = min((val, idx) for (idx, val) in enumerate(distance_to_nearest_box))
        possible_eyes.pop(idx)
    # for eye in possible_eyes:
    #     print(str(eye.mean_x) + " "+ str(eye.mean_y))
    possible_eyes.sort(key = lambda box : box.mean_x)
    return possible_eyes

def find_mouth(boxes, possible_eyes):
    # print(possible_eyes)
    distance_between_eyes = np.abs(possible_eyes[1].mean_x - possible_eyes[0].mean_x)
    boxes = [box for box in boxes if (box.mean_y > possible_eyes[0].mean_y + distance_between_eyes/2)]
    # Now ignore all the boxes of width < 50% of the distance between eyes
    boxes = [box for box in boxes if ((box.w > distance_between_eyes/3) and box.w > box.h)]
    boxes.sort(key = lambda box : box.y)
    return boxes[0]

def find_nostrils(boxes, eyes, mouth):
    boxes = [box for box in boxes if box.mean_y > eyes[0].mean_y and box.mean_y < mouth.mean_y]
    left_nostril_candidates = [box for box in boxes if box.mean_x < mouth.mean_x]
    right_nostril_candidates = [box for box in boxes if box.mean_x > mouth.mean_x]
    left_nostril_candidates.sort(key = lambda box : box.mean_x)
    right_nostril_candidates.sort(key = lambda box : box.mean_x)
    return [left_nostril_candidates[-1],right_nostril_candidates[0]]

def getFeatures(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # print(image.shape)
    image = image.astype(np.float32)
    prep_image = preprocess(image)
    boxes = separation(prep_image, image)
    # boxes = merge_boxes(prep_image, boxes)
    peyes = find_eyes(boxes)
    # print(len(peyes))
    mouth = find_mouth(boxes, peyes)
    # nostrils = find_nostrils(boxes, peyes, mouth)
    # for e in peyes:
    #     print(e.mean_x, e.mean_y)
    return peyes+[mouth]#+nostrils



# path = 'images/ted_face.jpg'

# getFeatures(path)

# image = cv2.imread('images/portrait2.jpg',cv2.IMREAD_GRAYSCALE)
# print(image.shape)
# image = image.astype(np.float32)
# prep_image = preprocess(image)
# boxes = separation(prep_image)
# find_eyes(boxes)