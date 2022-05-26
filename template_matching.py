import cv2 as cv
import numpy as np


def add_pairs(pair0, pair1):
    return pair0[0] + pair1[0], pair0[1] + pair1[1]


def last_column_contains_non_white(crop, tol=50, white=255):
    return any(crop[:, -1] < white - tol)


def last_row_contains_non_white(crop, tol=50, white=255):
    return any(crop[-1, :] < white - tol)


def first_column_contains_non_white(crop, tol=50, white=255):
    return any(crop[:, 0] < white - tol)


def first_row_contains_non_white(crop, tol=50, white=255):
    return any(crop[0, :] < white - tol)


#def last_columns_contains_black(crop, num_cols, tol=50, black=0):
#    return (crop[:, -num_cols:] < black + tol).any()


def last_rows_contains_black(crop, num_rows, tol=50, black=0):
    return (crop[-num_rows:, :] < black + tol).any()


#def first_columns_contains_black(crop, num_cols, tol=50, black=0):
#    return (crop[:, :num_cols] < black + tol).any()


def first_rows_contains_black(crop, num_rows, tol=50, black=0):
    return (crop[:num_rows, :] < black + tol).any()


class Rectangle:

    def __init__(self, tl, br):
        assert isinstance(tl, tuple)
        assert len(tl) == 2
        assert isinstance(tl[0], int)
        assert isinstance(tl[1], int)
        assert isinstance(br, tuple)
        assert len(br) == 2
        assert isinstance(br[0], int)
        assert isinstance(br[1], int)

        # tl ve br birer pair
        # Öyle ki ilk değer x (yatay), ikinci değer y (dikey)
        # x sağa doğru artar, y aşağı doğru
        # Yani aslında satır sütun gibi ama tersten
        self.tl = tl
        self.br = br

    def width(self):
        width = self.br[0] - self.tl[0]
        assert width > 0
        return width

    def height(self):
        height = self.br[1] - self.tl[1]
        assert height > 0
        return height

    def move_right(self, amount, tl=True, br=True):
        assert isinstance(amount, int)
        if tl:
            self.tl = add_pairs(self.tl, (amount, 0))
        if br:
            self.br = add_pairs(self.br, (amount, 0))

    def move_left(self, amount, tl=True, br=True):
        assert isinstance(amount, int)
        self.move_right(-amount, tl=tl, br=br)

    def move_down(self, amount, tl=True, br=True):
        assert isinstance(amount, int)
        if tl:
            self.tl = add_pairs(self.tl, (0, amount))
        if br:
            self.br = add_pairs(self.br, (0, amount))

    def move_up(self, amount, tl=True, br=True):
        assert isinstance(amount, int)
        self.move_down(-amount, tl=tl, br=br)

    def expand_right(self, amount):
        assert isinstance(amount, int)
        self.move_right(amount, tl=False, br=True)

    def expand_left(self, amount):
        assert isinstance(amount, int)
        self.move_left(amount, tl=True, br=False)

    def expand_down(self, amount):
        assert isinstance(amount, int)
        self.move_down(amount, tl=False, br=True)

    def expand_up(self, amount):
        assert isinstance(amount, int)
        self.move_up(amount, tl=True, br=False)

    def expand_right_forever(self, img):
        w, h = img.shape[::-1]
        assert w > self.tl[0] >= 0
        assert w > self.br[0] >= 0
        self.br = (w - 1, self.br[1])

    def expand_left_forever(self):
        assert self.tl[0] >= 0
        assert self.br[0] >= 0
        self.tl = (0, self.tl[1])

    def expand_down_forever(self, img):
        w, h = img.shape[::-1]
        assert h > self.tl[1] >= 0
        assert h > self.br[1] >= 0
        self.br = (self.br[0], h - 1)

    def expand_up_forever(self):
        assert self.tl[1] >= 0
        assert self.br[1] >= 0
        self.tl = (self.tl[0], 0)

    # Şıklar alt alta ise, yüksekliklerini bulmak için:
    def expand_until_rectangle_below(self, rectangle_below):
        target_row = rectangle_below.tl[1] - 1
        amount = target_row - self.br[1]
        assert amount >= 0
        self.expand_down(amount)

    def expand_until_rectangle_next(self, rectangle_next):
        target_column = rectangle_next.tl[0] - 1
        amount = target_column - self.br[0]
        assert amount >= 0
        self.expand_right(amount)

    def shrink(self, img, padding=0):
        assert isinstance(padding, int)
        assert padding >= 0

        # Her yönden gereksiz kısımları at
        # Bundan önce expand_right_forever falan yapılabilir

        # En sağ sırf beyaz olduğu sürece küçült
        # Sonuna kadar büyüt:
        while self.br[0] > self.tl[0] + 1:
            # 1 piksel küçültüp bir bak
            new_rectangle = Rectangle(self.tl, self.br)
            new_rectangle.move_left(1, tl=False, br=True)
            if last_column_contains_non_white(crop_using_rectangle(img, new_rectangle)):
                break
            # Eğer tamamı beyazsa gerçekten 1 piksel küçült
            self.move_left(1, tl=False, br=True)
        self.move_right(padding, tl=False, br=True)

        # Sol için yap
        while self.br[0] > self.tl[0] + 1:
            new_rectangle = Rectangle(self.tl, self.br)
            new_rectangle.move_right(1, tl=True, br=False)
            if first_column_contains_non_white(crop_using_rectangle(img, new_rectangle)):
                break
            self.move_right(1, tl=True, br=False)
        self.move_left(padding, tl=True, br=False)

        # Aşağı için yap
        while self.br[1] > self.tl[1] + 1:
            # 1 piksel küçültüp bir bak
            new_rectangle = Rectangle(self.tl, self.br)
            new_rectangle.move_up(1, tl=False, br=True)
            if last_row_contains_non_white(crop_using_rectangle(img, new_rectangle)):
                break
            # Eğer tamamı beyazsa gerçekten 1 piksel küçült
            self.move_up(1, tl=False, br=True)
        self.move_down(padding, tl=False, br=True)

        # Yukarı için yap
        while self.br[1] > self.tl[1] + 1:
            new_rectangle = Rectangle(self.tl, self.br)
            new_rectangle.move_down(1, tl=True, br=False)
            if first_row_contains_non_white(crop_using_rectangle(img, new_rectangle)):
                break
            self.move_down(1, tl=True, br=False)
        self.move_up(padding, tl=True, br=False)

    def vertically_expand(self, img, padding=5):
        # En alttaki 5 sütun içinde siyah renk olduğu sürece aşağı doğru 1 piksel daha büyüt:
        while self.br[1] < img.shape[0] - 1 and last_rows_contains_black(crop_using_rectangle(img, self), padding):
            self.move_down(1, tl=False, br=True)

        # En üstteki 5 sütun içinde siyah renk olduğu sürece yukarı doğru 1 piksel daha büyüt:
        while self.tl[1] > 1 and first_rows_contains_black(crop_using_rectangle(img, self), padding):
            self.move_up(1, tl=True, br=False)

    def scale(self, scale):
        self.tl = (round(scale * self.tl[0]), round(scale * self.tl[1]))
        self.br = (round(scale * self.br[0]), round(scale * self.br[1]))


def crop_using_rectangle(img: np.ndarray, rectangle: Rectangle):
    return img[rectangle.tl[1]:rectangle.br[1], rectangle.tl[0]:rectangle.br[0]]


def match(img, template, method):
    #img = img.copy()
    method = eval(method)
    res = cv.matchTemplate(img, template, method)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

    if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
        top_left = min_loc
        score = -min_val
    else:
        top_left = max_loc
        score = max_val

    w, h = template.shape[::-1]
    bottom_right = (top_left[0] + w, top_left[1] + h)
    rect = Rectangle(top_left, bottom_right)
    return res, rect, score


def multiscale_match(img, template, method, min_scale=0.2, max_scale=5.0, num_scales=50):
    best_score = None
    best_rect = None
    best_scale = None

    for scale in np.geomspace(min_scale, max_scale, num_scales)[::-1]:  # np.linspace
        width = int(img.shape[1] * scale)
        height = int(img.shape[0] * scale)
        dim = (width, height)

        if width < template.shape[1] or height < template.shape[0]:
            break

        resized_img = cv.resize(img, dim)
        _, rect, score = match(resized_img, template, method)

        if best_score is None or score > best_score:
            best_score = score
            best_rect = rect
            best_scale = scale

    #print(best_scale)
    best_rect.scale(1 / best_scale)
    return best_rect, best_score, best_scale
