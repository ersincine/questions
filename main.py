import os
import shutil
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


def median(values):
    values = sorted(values)
    return values[len(values) // 2] if len(values) % 2 != 0 \
        else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2


def find_correct_scale(img, templates, method):
    scales = [multiscale_match(img, template, method)[2] for template, letter in zip(templates, letters)]
    median_scale = median(scales)
    return median_scale


def find_letter_bboxes(img, templates, letters, scale, method):
    letter_bboxes = {}
    for template, letter in zip(templates, letters):
        width = int(img.shape[1] * scale)
        height = int(img.shape[0] * scale)
        _, rect, score = match(cv.resize(img, (width, height)), template, method)
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


FIVE_LETTERS = False

SKIP_IF_EXISTS = True
DELETE_ALL_EXISTING_RESULTS = False

METHOD = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED'][-1]

QUESTIONS_PATH = "questions_with_five_options" if FIVE_LETTERS else "questions_with_four_options"
RESULTS_PATH = "results"

letters = ["a", "b", "c", "d", "e"]
if not FIVE_LETTERS:
    letters = letters[:-1]

templates, template_w, template_h = read_templates(letters)

if DELETE_ALL_EXISTING_RESULTS:
    shutil.rmtree(RESULTS_PATH)
    os.makedirs(RESULTS_PATH)

question_filenames = sorted(os.listdir(QUESTIONS_PATH))
for question_filename in question_filenames:

    if SKIP_IF_EXISTS and os.path.exists(RESULTS_PATH + "/" + question_filename):
        continue

    print(question_filename)

    question_path = QUESTIONS_PATH + "/" + question_filename
    img = cv.imread(question_path, 0)

    # Resmin başına ve sonuna beyaz padding ekleyelim. Şıklar kenarlarda kalmış olabilir diye.
    img = cv.copyMakeBorder(img, 5, 5, 5, 5, cv.BORDER_CONSTANT, value=255)

    img_w, img_h = img.shape[::-1]

    options_annotated = img.copy()
    option_contents_annotated = img.copy()

    # Ne direkt match yapalım ne de bütün scalelerde match yapalım.
    # Onun yerine bütün scalelerde match yapıp şıklar arasında ortak bir scale belirleyelim.
    # Sonra o scalede hepsini arayalım.
    scale = find_correct_scale(img, templates, METHOD)
    bboxes = find_letter_bboxes(img, templates, letters, scale, METHOD)

    for letter in letters:
        cv.rectangle(options_annotated, bboxes[letter].tl, bboxes[letter].br, 0, 2)
    cv.imwrite(RESULTS_PATH + "/_" + question_filename, options_annotated)
    # Yukarıda bboxes içinde harfler var. Aşağıda artık içerik olacak.

    for letter in letters:
        bboxes[letter].move_right(round((template_w + 1) / scale))

    tl_rows = [bboxes[letter].tl[1] for letter in letters]
    tl_cols = [bboxes[letter].tl[0] for letter in letters]

    path = []
    for idx in range(len(letters) - 1):
        row_diff = tl_rows[idx + 1] - tl_rows[idx]
        col_diff = tl_cols[idx + 1] - tl_cols[idx]
        if row_diff > col_diff * 10:
            path.append("down")
        elif col_diff > row_diff * 10:
            path.append("right")
        else:
            assert False, (tl_cols[idx + 1], tl_cols[idx], tl_rows[idx + 1], tl_rows[idx])
    print(path)

    if "down" not in path:
        print("Hepsi yan yana:")
        if FIVE_LETTERS:
            print("A) B) C) D) E)")
        else:
            print("A) B) C) D)")

        rows = [[bbox for bbox in bboxes.values()]]  # Only 1 row

    elif path.count("down") == len(path):
        print("Hepsi alt alta:")
        if FIVE_LETTERS:
            print("A) B) C) D) E)", sep="\n")
        else:
            print("A) B) C) D)", sep="\n")

        rows = [[bbox] for bbox in bboxes.values()]  # len(letters) rows

    elif path.count("down") == 1:
        print("2 satırda toplanmışlar:")
        if FIVE_LETTERS:
            # Not: Şıklar yukarıdan aşağıya değil soldan sağa doldurulmuş olmalıdır.
            if path[1] == "down":
                print("A) B)")
                print("C) D) E)")
                rows = [[bboxes["a"], bboxes["b"]],
                        [bboxes["c"], bboxes["d"], bboxes["e"]]]

            elif path[2] == "down":
                print("A) B) C)")
                print("D) E)")
                rows = [[bboxes["a"], bboxes["b"], bboxes["c"]],
                        [bboxes["d"], bboxes["e"]]]

            else:
                assert False  # Geri kalan düzenler pek makul değil gibi. Ama istisna görülürse kodlanır.

        else:
            assert path[1] == "down"
            print("A) B)")
            print("C) D)")
            rows = [[bboxes["a"], bboxes["b"]],
                    [bboxes["c"], bboxes["d"]]]

    else:
        assert False
        # Burada kalanların en makul olanı 5 şık için 3 satır olması:
        # A) B)
        # C) D)
        # E)
        # Bunu kodlayabiliriz.

    align_rows(rows)

    for row_idx, row in enumerate(rows):
        for col_idx, bbox in enumerate(row):
            if col_idx < len(row) - 1:
                bbox.expand_until_rectangle_next(row[col_idx + 1])
                # Ama şık kısmını kutuya almayalım, yani w piksel sola alalım
                bbox.move_left(round((template_w + 1) / scale), tl=False, br=True)
            else:
                bbox.expand_right_forever(img)

            if row_idx < len(rows) - 1:
                bbox.expand_until_rectangle_below(rows[row_idx + 1][0])  # İlki diyoruz çünkü hepsinin aynı hizada olması beklenir.
            else:
                bbox.expand_down_forever(img)

            bbox.shrink(img, padding=0)

    for letter in letters:
        bboxes[letter].vertically_expand(img, padding=5)
        bboxes[letter].shrink(img, padding=5)  # Yukarı ve aşağısı aynı kalıp yanlar expand olacak gibi.

    for letter in letters:
        cv.rectangle(option_contents_annotated, bboxes[letter].tl, bboxes[letter].br, 0, 2)

    cv.imwrite(RESULTS_PATH + "/" + question_filename, option_contents_annotated)
    print(question_filename, "done.")
