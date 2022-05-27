from template_matching import match, multiscale_match
import cv2 as cv


def read_templates(letters):
    templates = []
    for letter in letters:
        templates.append(cv.imread(f"templates/{letter}.png", 0))
        if len(templates) > 1:
            assert templates[-1].shape[::-1] == templates[-2].shape[::-1]
    template_w, template_h = templates[0].shape[::-1]
    return templates, template_w, template_h


def standardize_padding(img, padding=5, color=255, tol=50):
    # Bu fonksiyon sayesinde sorular keyfi bir şekilde kesilebilir. 
    # (Yeter ki soru metni ve bütün şıklar sığsın ve başka sorular gözükmesin.)
    # (Etrafındaki beyaz alan çok az veya çok fazla olabilir.)
    assert tol >= 0

    # İmgenin kenarlarındaki sırf beyaz satır ve sütunları silelim.
    # TODO: Çok daha verimli bir şekilde yapabiliriz.
    min_val = abs(color - tol)
    max_val = color + tol
    while (min_val <= img[0, :]).all() and (img[0, :] <= max_val).all():
        img = img[1:, :]
    while (min_val <= img[-1, :]).all() and (img[-1, :] <= max_val).all():
        img = img[:-1, :]
    while (min_val <= img[:, 0]).all() and (img[:, 0] <= max_val).all():
        img = img[:, 1:]
    while (min_val <= img[:, -1]).all() and (img[:, -1] <= max_val).all():
        img = img[:, :-1]

    # Resmin başına ve sonuna beyaz padding ekleyelim. Şıklar kenarlarda kalmış olabilir diye.
    img = cv.copyMakeBorder(img, padding, padding, padding, padding, cv.BORDER_CONSTANT, value=color)
    return img


def median(values):
    values = sorted(values)
    return values[len(values) // 2] if len(values) % 2 != 0 \
        else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2


def find_correct_scale(img, templates, method):
    # TODO: Gerekirse dönen skorları da dikkate alabiliriz. (Örneğin en düşük skorlu olanı atıp geri kalanların medyanını bulabiliriz.)
    scales = [multiscale_match(img, template, method)[2] for template in templates]
    median_scale = median(scales)
    return median_scale


def find_letter_bboxes(img, templates, letters, scale, method):
    letter_bboxes = {}
    for template, letter in zip(templates, letters):
        width = int(img.shape[1] * scale)  # TODO: Burada ve aşağıda round kullanalım int yerine.
        height = int(img.shape[0] * scale)
        _, rect, score = match(cv.resize(img, (width, height)), template, method)  # TODO: Daha iyi bir interpolation kullanabiliriz.
        rect.scale(1.0 / scale)
        letter_bboxes[letter] = rect
    return letter_bboxes


def align_rows(rows):
    for row in rows:
        y_vals = []
        for bbox in row:
            y_vals.append(bbox.tl[1])
        y_val = round(median(y_vals))
        print(y_vals, y_val)
        for bbox in row:
            bbox.move_down(y_val - bbox.tl[1])
            bbox.expand_down(bbox.height() - row[0].height())  # Yükseklikleri eşit olsun.
