import cv2 as cv
import numpy as np

from rectangle import Rectangle


def match(img, template, method, max_num_matches=1, threshold=0.0):
    assert threshold >= 0.0
    # max_num_matches = 1 --> threshold will be ignored.

    # img = img.copy()
    w, h = template.shape[::-1]

    method = eval(method)
    minimization = method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]  # Otherwise maximization

    result = cv.matchTemplate(img, template, method)
    modified_result = result.copy()

    rectangles = []
    scores = []
    while True:

        if len(rectangles) == max_num_matches:
            break

        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(modified_result)

        if minimization:
            top_left = min_loc
            score = -min_val
            fill_value = np.inf
        else:
            top_left = max_loc
            score = max_val
            fill_value = -np.inf

        if len(scores) > 0:
            if abs(scores[0] - score) / max(scores[0], score) > threshold:
                break

        bottom_right = (top_left[0] + w, top_left[1] + h)
        rectangle = Rectangle(top_left, bottom_right)

        rectangles.append(rectangle)
        scores.append(score)

        row_start = top_left[1] - h // 2
        row_end = top_left[1] + h // 2
        col_start = top_left[0] - w // 2
        col_end = top_left[0] + w // 2

        """
        # Bana mantıklı gelen şu:
        row_start = top_left[1]
        row_end = top_left[1] + h
        col_start = top_left[0]
        col_end = top_left[0] + w
        """

        # TODO: Eğer kenarlarda bulunduğu zaman bu kod çalışmazsa max(..., 0) falan yapılır.
        # TODO: 1 piksellik bir hata olabilir.
        modified_result[row_start: row_end, col_start: col_end] = fill_value

        """
        if max_num_matches > 1:
            print("Ersin")
            print(row_start, row_end, col_start, col_end)
            import matplotlib.pyplot as plt
            import os
            num = 1
            while os.path.exists(f"x{num}.png"):
                num += 1
            plt.imsave(f"x{num}.png", modified_result)

        """
    return result, rectangles, scores


def multiscale_match(img, template, method, min_scale=0.2, max_scale=5.0, num_scales=50):
    best_score = None
    best_rectangle = None
    best_scale = None

    for scale in np.geomspace(min_scale, max_scale, num_scales)[::-1]:  # np.linspace
        width = int(img.shape[1] * scale)
        height = int(img.shape[0] * scale)
        dim = (width, height)

        if width < template.shape[1] or height < template.shape[0]:
            break

        resized_img = cv.resize(img, dim)
        _, rectangles, scores = match(resized_img, template, method, max_num_matches=1)
        assert len(rectangles) == 1 and len(scores) == 1
        rectangle = rectangles[0]
        score = scores[0]

        if best_score is None or score > best_score:
            best_score = score
            best_rectangle = rectangle
            best_scale = scale

    #print(best_scale)
    best_rectangle.scale(1 / best_scale)
    return best_rectangle, best_score, best_scale
