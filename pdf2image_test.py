from pdf2image import convert_from_path
from img2pdf import convert
import cv2
import os
import numpy as np

OFFSET = 10

# Debug functions
def check_column(col, page):
    rcol = np.zeros((page.shape[0], 3))
    rcol[:, 2] = np.ones(page.shape[0])*255

    red_img = page.copy()
    red_img[:, col] = rcol

    cv2.imwrite('rcol_img.jpg', red_img)

def avg_color_column(page):
    avg_img = page.copy()

    for col in range(page.shape[1]):
        avg = page[:, col].mean()

        avg_col = np.ones((page.shape[0], 3))*avg
        avg_img[:, col] = avg_col

    return avg_img

def var_color_column(page):
    var_img = page.copy()

    var_vals = var_img[0, :, 0].copy()

    for col in range(page.shape[1]):
        var = page[:, col, 0].var()

        var_vals[col] = var

    for col in range(page.shape[1]):
        var_col = np.ones((page.shape[0], 3)) * var_vals[col]
        var_img[:, col] = var_col

    return var_img

def bwify(page, threshold = 150):
    bwimg = page.copy()

    for col in range(page.shape[1]):
        gcol = page[:, col].mean()
        b = 0

        if gcol > threshold:
            b = 255

        bw_col = np.ones((page.shape[0], 3))*b
        bwimg[:, col] = bw_col
    
    return bwimg

# Get limits of pages
def left_bound(page, ignore_first = 0):
    found = False
    index = -1
    wcount = 0

    while (not found) and index < page.shape[1] - 1:
        index += 1
        avg = page[:, index].mean()

        if avg > 240:
            if ignore_first == wcount:
                found = True

            wcount += 1
    
    return min(index, page.shape[1])

# Useless with left_bound and mirroring the image
def right_limit(page):
    found = False
    index = page.shape[1]

    while not found and index > 0:
        index -= 1
        avg = page[:, index].mean()

        if avg > 245:
            found = True
    
    return index - OFFSET

def get_bounds(page, ignore_first = 0):
    height, width = page.shape[:2]

    page_mirror = cv2.flip(page, 1)

    lbound = left_bound(page, ignore_first)
    rbound = width - left_bound(page_mirror, ignore_first)

    # Es necesario recortar parcialmente para no tener en cuenta los bordes que hay en los laterales
    # Afecta al tratamiento del escaneo horizontal
    cropped = page[:, lbound:rbound]

    page_rotated = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    page_rotated_mirrored = cv2.flip(page_rotated, 1)

    ubound = left_bound(page_rotated, ignore_first)
    dbound = height - left_bound(page_rotated_mirrored, 0)   # caso particular
    
    return (lbound, rbound, ubound, dbound)

# Muy lento (para una pagina de 1600x2300)
def clean_pages():
    pages = []
    count = 1
    # if not os.path.exists(f'{name}pages/split/'):
    #     os.mkdir(f'{name}pages/split/')

    # TODO: rango puesto a dedo
    for name_page in os.listdir('pages/split/'):
        side = name_page.split('_')[1].split('_')[0][0]
        n = 2*(int(name_page.split('e')[1].split('_')[0]) - 1) + (0 if side == 'l' else 1)

        page = cv2.imread(f'pages/split/{name_page}', cv2.IMREAD_GRAYSCALE)

        _, clean_page = cv2.threshold(page, 200, 255, cv2.THRESH_BINARY)

        cv2.imwrite(f'pages/clean/clean_page{n}.jpg', clean_page)
        
        pages.append(f'pages/clean/clean_page{n}.jpg')
        count += 1

    with open("clean.pdf", "wb") as f:
        f.write(convert(pages))


# Busca la division entre page.shape[1]/2 +- range
def get_division(page, width, threshold = 20):
    m = page.shape[1] // 2
    index = -1
    found = 0

    # max_avg = 0

    # stripe = page[:, m - width:m + width]

    # for col in range(stripe.shape[1]):
    #     avg = stripe[:, col].mean()
    #     bness = np.percentile(stripe[:, col], 2)
    #     # print(bness)

    #     if bness > 180 and avg > max_avg:
    #         index = col
    #         max_avg = avg
            

    while (not found) and index < width:
        index += 1

        avg_left = page[:, m - index].mean()
        avg_right = page[:, m + index].mean()

        if avg_left > threshold:
            found = 1
        elif avg_right > threshold:
            found = -1
        
    # return m - width + index
    return m + found * index

def divide_page(page, range = 50):
    div = get_division(page, range)

    return (page[:, :div], page[:, div:])

def split_pdf(name = ""):
    pages = []

    if not os.path.exists(f'{name}pages/split/'):
        os.mkdir(f'{name}pages/split/')

    # TODO: rango puesto a dedo
    for p in range(1, 104):
        page = cv2.imread(f'{name}pages/cropped/cropped_page{p}.jpg')
        avg_page = avg_color_column(page)
        bw_index = bwify(avg_page, 30)[0, :, 0] == 0    # muy bien con 30

        avg_index = avg_page[0, :, 0]
        avg_index[bw_index] = 255

        page_half = np.argmin(avg_index)

        # Si la primera prediccion se aleja mucho del centro, se prueba con algo mas sencillo
        if abs(page_half - (page.shape[1]//2)) > 50:
            page_half = get_division(page, 20, 0)
            print('^ here')

        print(f'{p} : {page_half}')

        page_left, page_right = (page[:, :page_half - OFFSET], page[:, page_half + OFFSET:])

        cv2.imwrite(f'{name}pages/split/split_page{p}_l.jpg', page_left)
        cv2.imwrite(f'{name}pages/split/split_page{p}_r.jpg', page_right)
        
        pages.append(f'{name}pages/split/split_page{p}_l.jpg')
        pages.append(f'{name}pages/split/split_page{p}_r.jpg')

    with open("split_pdf.pdf", "wb") as f:
        f.write(convert(pages))

def crop_page(page):
    lbound, rbound, ubound, dbound = get_bounds(page, OFFSET)

    cropped = page[ubound:dbound, lbound:rbound]
    return cropped

def crop_test():
    pages = []

    # TODO: rango puesto a dedo
    for p in range(1, 104):
        page = cv2.imread(f'pages/page{p}.jpg', cv2.IMREAD_GRAYSCALE)
        cropped = crop_page(page)
        cv2.imwrite(f'pages/cropped/cropped_page{p}.jpg', cropped)
        
        pages.append(f'pages/cropped/cropped_page{p}.jpg')

    with open("cropped_pdf.pdf", "wb") as f:
        f.write(convert(pages))

# Saves pdf into images
def transform_pages(pdf_path):
    images = convert_from_path(pdf_path)

    if not os.path.exists(f'{pdf_path}pages/'):
        os.mkdir(f'{pdf_path}pages/')

    for i in range(len(images)):
        print(f'Convirtiendo pagina {i}...')
        images[i].save(f'{pdf_path}pages/page{i}.jpg', 'JPEG')

def show(page):
    cv2.imshow("nueva imagen", page)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # img = cv2.imread('pages/cropped/cropped_page34.jpg')
    # avg_color_column(img)

    # var = cv2.imread('var_col_img.jpg')
    # avg = cv2.imread('avg_col_img.jpg')
    # cropped = crop_page(img)

    # transform_pages('cropped_compressed_deskewed.pdf')
    split_pdf()
    # clean_pages()

    # div_page = bwify(avg, 180)


    # var_color_column(img)

    # check_column(get_division(cropped, 50), cropped)

    # cv2.imwrite('clean_page.jpg', clean_page(img))

    # rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    # bwify(rotated)

    # cv2.imwrite('bw_img.jpg', cv2.rotate(cv2.imread('bw_img.jpg'), cv2.ROTATE_90_COUNTERCLOCKWISE))

    # cv2.imwrite('rotated_page.jpg', rotated)

    # crop_test()

# Procedimientos:
#   - (hecho) Cortar bordes laterales
#   - (hecho) Cortar bordes verticales (solo arriba)
#   - Dividir por la mitad
#   x Alinear
#   ~ Obtener bloque de texto (usar en parte bwify)
#   - Aclarar bordes
#   - Centrar texto añadiendo margenes
#   ...
#   Profit