import os
import shutil
import itertools

from math_utils import median
from rectangle import crop_using_rectangle, fill_using_rectangle, Rectangle, annotate_bboxes
from template_matching import match, multiscale_match
from utils import find_compatible_bboxes

import cv2 as cv


def read_templates(letters, directory="templates"):
    templates = []
    for letter in letters:
        templates.append(cv.imread(f"{directory}/{letter}.png", 0))
        if len(templates) > 1:
            assert templates[-1].shape[::-1] == templates[-2].shape[::-1]
    template_h, template_w = templates[0].shape
    return templates, template_w, template_h


def standardize_padding(img, padding=5, color=255, tol=50):
    # Bu fonksiyon sayesinde soruların keyfi bir şekilde kesilmesi sorun değil. Biz standartlaştıracağız zaten.
    # (Yeter ki soru metni ve bütün şıklar sığsın ve başka sorular gözükmesin.)
    # (Etrafındaki beyaz alan çok az veya çok fazla olabilir.)
    assert len(img.shape) == 2  # TODO: Aksi halde grayscale hali üzerinden color ve tol kontrolü yapılıp renkli bir şekilde kesip döndürülür.
    assert tol >= 0

    # İmgenin kenarlarındaki sırf beyaz satır ve sütunları silelim. TODO: Çok daha verimli bir şekilde yapabiliriz.
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


def find_letter_bboxes(img, templates, method, max_num_matches, threshold):

    def find_correct_scale(img, templates, method):
        # TODO: Gerekirse dönen skorları da dikkate alabiliriz. (Örneğin en düşük skorlu olanı atıp geri kalanların medyanını bulabiliriz.)
        scales = [multiscale_match(img, template, method)[2] for template in templates]
        median_scale = median(scales)
        return median_scale

    # Ne direkt match yapalım ne de bütün scalelerde match yapalım...
    scale = find_correct_scale(img, templates, METHOD)  # Bütün scalelerde match yapıp şıklar arasında ortak bir scale belirleyelim.
    # TODO: letters'ı almayıp diğer harflere kıyasla skora göre ve is_valid_layout fonksiyonuna göre otomatik olarak karar verebiliriz.

    all_letter_bboxes_as_a_list = []  # Bunda her letter için 1 ya da daha fazla bbox olacak.
    for template in templates:
        width = int(img.shape[1] * scale)  # TODO: Burada ve aşağıda round kullanalım int yerine.
        height = int(img.shape[0] * scale)
        resized_img = cv.resize(img, (width, height))  # TODO: Daha iyi bir interpolation kullanabiliriz.
        _, rectangles, _ = match(resized_img, template, method, max_num_matches=max_num_matches, threshold=threshold)
        for rectangle in rectangles:
            rectangle.scale(1.0 / scale)
        all_letter_bboxes_as_a_list.append(rectangles)
    rows = find_compatible_bboxes(all_letter_bboxes_as_a_list)  # Bunda her letter için 1 tane bbox olacak.

    return rows, scale


def find_question_bbox(img, letter_rows):
    # TODO: Şıkların sorunun altında olduğunu varsayıyoruz şimdilik. Daha sonra genelleştirelim.
    tl = (0, 0)
    br = (img.shape[1], letter_rows[0][0].tl[1] - 1)
    question_bbox = Rectangle(tl, br)
    question_bbox.shrink(img, padding=0)
    return question_bbox


def find_option_bboxes(letter_rows, img, scale, template_w):

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

    rows = [[letter_bbox.clone() for letter_bbox in letter_row] for letter_row in letter_rows]  # Klonla.

    bboxes = list(itertools.chain.from_iterable(rows))

    for bbox in bboxes:
        bbox.move_right(int(round((template_w + 1) / scale)))  # numpy float için round da float, bu yüzden int

    align_rows(rows)

    for row_idx, row in enumerate(rows):
        for col_idx, bbox in enumerate(row):
            if col_idx < len(row) - 1:
                bbox.expand_until_rectangle_next(row[col_idx + 1])
                # Ama şık kısmını kutuya almayalım, yani w piksel sola alalım
                bbox.move_left(int(round((template_w + 1) / scale)), tl=False, br=True)  # numpy float için round da float
            else:
                bbox.expand_right_forever(img)

            if row_idx < len(rows) - 1:
                bbox.expand_until_rectangle_below(rows[row_idx + 1][0])  # İlki diyoruz çünkü hepsinin aynı hizada olması beklenir.
            else:
                bbox.expand_down_forever(img)

            bbox.shrink(img, padding=0)

    for bbox in bboxes:
        bbox.vertically_expand(img, padding=5)
        bbox.shrink(img, padding=5)  # Yukarı ve aşağısı aynı kalıp yanlar expand olacak gibi.

    return rows


# Mode
FROM_SCRATCH = True   # If False -> Skip existing results
FIVE_LETTERS = False  # False -> Four letters: A, B, C, D

# Environment
QUESTIONS_PATH = "questions_with_five_options" if FIVE_LETTERS else "questions_with_four_options"
RESULTS_PATH = "results"

# Optimization
METHOD = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED'][-1]  # TODO: Diğer metotları dene.
MAX_NUM_MATCHES = 3  # Her template bu kadar aday ile eşleştirilir.
THRESHOLD = 0.15


if __name__ == "__main__":

    LETTERS = ["a", "b", "c", "d", "e"] if FIVE_LETTERS else ["a", "b", "c", "d"]

    templates, template_w, template_h = read_templates(LETTERS)

    if FROM_SCRATCH:
        shutil.rmtree(RESULTS_PATH)
        os.makedirs(RESULTS_PATH)
        for dir_name in ["letters", "options", "questions", "letters_annotated", "options_annotated", "question_annotated"]:
            os.makedirs(RESULTS_PATH + "/" + dir_name)

    question_filenames = sorted(os.listdir(QUESTIONS_PATH))
    for question_filename in question_filenames:
        filename_without_extension = os.path.splitext(question_filename)[0]

        letters_path = RESULTS_PATH + "/letters/" + filename_without_extension
        options_path = RESULTS_PATH + "/options/" + filename_without_extension
        os.makedirs(letters_path)
        os.makedirs(options_path)

        input_path = QUESTIONS_PATH + "/" + question_filename
        letters_annotation_path = RESULTS_PATH + "/letters_annotated/" + question_filename
        options_annotation_path = RESULTS_PATH + "/options_annotated/" + question_filename
        question_path = RESULTS_PATH + "/questions/" + question_filename
        question_annotation_path = RESULTS_PATH + "/question_annotated/" + question_filename

        if os.path.exists(letters_annotation_path):
            continue

        print(question_filename)
        img = cv.imread(input_path, 0)
        img = standardize_padding(img, padding=5)  # TODO: Match performansını arttırmak için contrast arttırabiliriz.

        # A) B) ... şeklindeki harflerin kendilerinini bulalım.
        letter_rows, scale = find_letter_bboxes(img, templates, METHOD, MAX_NUM_MATCHES, THRESHOLD)  # Sonra o scalede hepsini arayalım.

        # Show letter bboxes:
        letter_bboxes = list(itertools.chain.from_iterable(letter_rows))
        cv.imwrite(letters_annotation_path, annotate_bboxes(img, letter_bboxes))
        for letter, letter_bbox in zip(LETTERS, letter_bboxes):
            cv.imwrite(letters_path + f"/{letter}.png", crop_using_rectangle(img, letter_bbox))

        # Show question:
        question_bbox = find_question_bbox(img, letter_rows)
        question = crop_using_rectangle(img, question_bbox)
        cv.imwrite(question_annotation_path, annotate_bboxes(img, [question_bbox]))
        cv.imwrite(question_path, standardize_padding(question, padding=5))

        img_without_letters = img.copy()
        for letter_bbox in letter_bboxes:
            fill_using_rectangle(img_without_letters, letter_bbox, 255)

        # A) B) ... şeklindeki harflerin yanlarındaki şıkları bulalım.
        option_rows = find_option_bboxes(letter_rows, img_without_letters, scale, template_w)

        # Show option bboxes:
        option_bboxes = list(itertools.chain.from_iterable(option_rows))
        cv.imwrite(options_annotation_path, annotate_bboxes(img, option_bboxes))
        for letter, option_bbox in zip(LETTERS, option_bboxes):
            cv.imwrite(options_path + f"/{letter}.png", crop_using_rectangle(img_without_letters, option_bbox))

        print(question_filename, "done.")
