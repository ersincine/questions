import itertools
from typing import List

from rectangle import is_there_any_intersection, Rectangle


def _is_valid_layout(bboxes: List[Rectangle]):
    five_letters = len(bboxes) == 5

    if is_there_any_intersection(bboxes):
        return False, None

    tl_rows = [bbox.tl[1] for bbox in bboxes]
    tl_cols = [bbox.tl[0] for bbox in bboxes]

    path = []
    for idx in range(len(bboxes) - 1):
        row_diff = tl_rows[idx + 1] - tl_rows[idx]
        col_diff = tl_cols[idx + 1] - tl_cols[idx]

        print("diff", row_diff, col_diff)

        if row_diff < 0 and col_diff < 0:
            print("False New")
            return False, None  # Sol üste gitmiş

        cannot_be_down = False
        cannot_be_right = False

        # For 10-31-2021_15:47:52_1855805448.png

        if col_diff < 0:
            col_diff = 0
            cannot_be_right = True

        if row_diff < 0:
            row_diff = abs(row_diff)
            cannot_be_down = True

        if row_diff > col_diff * 10:
            if cannot_be_down:
                print("False cannot_be_down")
                return False, None
            path.append("down")
        elif col_diff > row_diff * 10:
            if cannot_be_right:
                print("False cannot_be_right")
                return False, None
            path.append("right")
        else:
            print("False A")
            print(tl_cols[idx + 1], tl_cols[idx], tl_rows[idx + 1], tl_rows[idx])
            return False, None
    print(path)

    if "down" not in path:
        print("Hepsi yan yana:")
        if five_letters:
            print("A) B) C) D) E)")
        else:
            print("A) B) C) D)")

        rows = [[bbox for bbox in bboxes]]  # Only 1 row

    elif path.count("down") == len(path):
        print("Hepsi alt alta:")
        if five_letters:
            print("A) B) C) D) E)", sep="\n")
        else:
            print("A) B) C) D)", sep="\n")

        rows = [[bbox] for bbox in bboxes]  # len(letters) rows

    elif path.count("down") == 1:
        print("2 satırda toplanmışlar:")
        if five_letters:
            # Not: Şıklar yukarıdan aşağıya değil soldan sağa doldurulmuş olmalıdır.
            if path[1] == "down":
                print("A) B)")
                print("C) D) E)")
                rows = [bboxes[:2], bboxes[2:]]

            elif path[2] == "down":
                print("A) B) C)")
                print("D) E)")
                rows = [bboxes[:3], bboxes[3:]]

            else:
                print("False B")
                return False, None  # Geri kalan düzenler pek makul değil gibi. Ama istisna görülürse kodlanır.

        else:
            if path[1] != "down":
                print("False C")
                return False, None
            print("A) B)")
            print("C) D)")
            rows = [bboxes[:2], bboxes[2:]]

    else:
        print("False D")
        return False, None
        # Burada kalanların en makul olanı 5 şık için 3 satır olması:
        # A) B)
        # C) D)
        # E)
        # Bunu kodlayabiliriz.

    return True, rows


def find_compatible_bboxes(all_letter_bboxes_as_a_list):
    # Bunun i. elemanı i. harf için bütün dikdörtgenleri içeriyor.
    letter_bboxes_as_a_list = []
    for bboxes in all_letter_bboxes_as_a_list:
        if len(bboxes) == 1:
            letter_bboxes_as_a_list.append(bboxes[0])
        else:
            letter_bboxes_as_a_list.append(None)

    if all([bbox is not None for bbox in letter_bboxes_as_a_list]):
        is_valid, rows = _is_valid_layout(letter_bboxes_as_a_list)
        assert is_valid
        return rows

    valid_combinations = []
    product = list(itertools.product(*all_letter_bboxes_as_a_list))
    print("len(product) =", len(product))
    for combination in product:
        is_valid, rows = _is_valid_layout(combination)
        if is_valid:
            valid_combinations.append(rows)

    assert len(valid_combinations) != 0

    if len(valid_combinations) == 1:
        return valid_combinations[0]
    else:

        print("len(valid_combinations) =", len(valid_combinations))

        # En yüksek olasılıklı olanı falan seçmek lazım. Ama şuna göre bir çözüm yapalım şimdilik:
        # For 10-31-2021_15:47:52_1855805448.png
        # Ortalama y ne kadar yüksekse o kadar iyidir. (Çünkü soruda A) B) falan geçiyorsa muhtemelen şıklar aşağıdadır.)

        best_combination = None
        best_combination_total_y = None
        for valid_combination in valid_combinations:
            print(valid_combination)
            total_y = sum([bbox.tl[0] for row in valid_combination for bbox in row])
            if best_combination_total_y is None or total_y > best_combination_total_y:
                best_combination = valid_combination
                best_combination_total_y = total_y

        return best_combination

        #assert False  # TODO: Şimdilik böyle dursun. Sonra scoreları çarpımı en büyük olanı falan seçeriz.
    # TODO: Çalışmazsa şunu yapabiliriz: Tek seçenekli eşleşmelere uyduracak şekilde seçeriz onlardan önceki ve sonrakileri.
