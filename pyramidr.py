#!/usr/bin/python
#! -*- coding: utf-8 -*-

"""
Pyramidr - it packs image pyramid in the smallest possible rectangle.
Version: 1.00
Author: Igor Ryabtsov aka Tinnulion
"""

import os
import sys
from PIL import Image

class Profile:
    __slots__ = ['x0', 'x1', 'h']
    def __init__(self, _x0, _x1, _h):
        self.x0, self.x1, self.h = _x0, _x1, _h

class Rect():
    __slots__ = ['x', 'y', 'w', 'h']
    def __init__(self, _x, _y, _w, _h):
        self.x, self.y, self.w, self.h = _x, _y, _w, _h

def __align_up(a, b):
    return int((a + b - 1) / b) * b

def __generate_rects(im_size, alpha, stop_dim):
    rects = []
    ratio = 1.0
    while True:
        w = int(im_size[0] * ratio + 0.5)
        h = int(im_size[1] * ratio + 0.5)
        if (w < stop_dim) or (h < stop_dim):
            break
        rects.append(Rect(0, 0, w, h))
        ratio *= alpha
    return rects

def __eval_rect_sum_widths(rects):
    rect_sum_widths = [rects[0].w + padding]
    for i in range(1, len(rects)):
        rect_sum_widths.append(rect_sum_widths[i - 1] + rects[i].w + padding)
    return rect_sum_widths

def __build_profile(rects, padding, head_count, tail_count, strip_w):
    head_profile = []
    x = 0
    for i in range(head_count):
        pw = rects[i].w + padding
        ph = rects[i].h + padding
        head_profile.append(Profile(x, x + pw - 1, ph))
        x += rects[i].w + padding
    if x < strip_w - 1:
        head_profile.append(Profile(x, strip_w - 1, 0))
    tail_profile = []
    x = strip_w - 1
    for i in range(head_count, head_count + tail_count):
        pw = rects[i].w
        ph = rects[i].h
        tail_profile.append(Profile(x - pw + 1, x, ph))
        x -= rects[i].w + padding
    if x > 0:
        tail_profile.append(Profile(0, x, 0))
    tail_profile.reverse()
    return head_profile, tail_profile

def __estimate_strip_height(head_profile, tail_profile):
    max_h = 0
    ceil_pos = 0
    floor_pos = 0
    while (ceil_pos < len(head_profile)) and (floor_pos < len(tail_profile)):
        ceil_item = head_profile[ceil_pos]
        floor_item = tail_profile[floor_pos]
        max_h = max(max_h, ceil_item.h + floor_item.h)
        if ceil_item.x1 <= floor_item.x1:
            ceil_pos += 1
        if ceil_item.x1 >= floor_item.x1:
            floor_pos += 1
    return max_h

def __place_level_rects(rects, padding, head_count, tail_count, strip_w, strip_h):
    x = 0
    for i in range(head_count):
        rects[i].x = x
        rects[i].y = 0
        x += rects[i].w + padding
    x = strip_w - 1
    for i in range(head_count, head_count + tail_count):
        rects[i].x = x - rects[i].w + 1
        rects[i].y = strip_h - rects[i].h
        x -= rects[i].w + padding

def __pack_strip(rects, padding, head_count, tail_count, strip_w):
    head_profile, tail_profile = __build_profile(rects, padding, head_count, tail_count, strip_w)
    strip_h = __estimate_strip_height(head_profile, tail_profile)
    __place_level_rects(rects, padding, head_count, tail_count, strip_w, strip_h)
    return strip_h

def __pack(imsize, alpha, stop_dim, padding, alignment):
    rects = __generate_rects(imsize, alpha, stop_dim)
    rect_sum_widths = __eval_rect_sum_widths(rects)
    for head_count in range(1, len(rects)):
        tail_count = len(rects) - head_count
        head_size = rect_sum_widths[head_count - 1] - padding
        tail_size = rect_sum_widths[-1] - head_size - padding
        if head_size >= tail_size:
            break
    strip_w = __align_up(head_size, alignment)
    strip_h = __pack_strip(rects, padding, head_count, tail_count, strip_w)
    strip_h = __align_up(strip_h, alignment)
    return (strip_w, strip_h), rects

def __render(image, canvas, rects, border):
    w, h = canvas[0] + 2 * border, canvas[1] + 2 * border
    mosaic = Image.new('RGB', (w, h), 'black')
    for rect in rects:
        new_item = image.resize((rect.w, rect.h), Image.ANTIALIAS)
        mosaic.paste(new_item, (border + rect.x, border + rect.y))
    return mosaic

def __calculate_utilization_ratio(canvas, rects):
    canvas_area = canvas[0] * canvas[1]
    sum_rect_area = 0
    for rect in rects:
        sum_rect_area += rect.w * rect.h
    return float(sum_rect_area) / canvas_area

def pack(image, alpha, stop_dim, padding=0, alignment=1, border=0):
    """
    Pack pyramid trying to minimize necessary canvas.
    image     <- PIL.Image, source image which will bew used to build pyramid.
    alpha     <- float in [0.0, 1.0), pyramid downsampling step.
    stop_dim  <- int, minimal dimension (width and height) of image in pyramid.
    padding   <- int, number of pixels, placed between two pyramid items.
    alignment <- int, canvas dimensions with be divisible by that number.
    returns:
    mosaic    <- PIL.Image, new image with optimally placed pyramid items.
    r         <- float in [0.0, 1.0], utilization of canvas space.
    """
    canvas, rects = __pack(image.size, alpha, stop_dim, padding, alignment)
    mosaic = __render(image, canvas, rects, border)
    r = __calculate_utilization_ratio(canvas, rects)
    return mosaic, r

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog='Pyramidr.py', description=__doc__, add_help=False)
    parser.add_argument('-i', default='', type=str, help='Input image path', dest='input')
    parser.add_argument('-o', default='', type=str, help='Output image path', dest='output')
    parser.add_argument('-a', default=1, type=float, help='Pyramid downsample factor, float between 0 and 1', dest='alpha')
    parser.add_argument('-s', default=1, type=int, help='Smallest possible pyramid item', dest='stop_dim')
    parser.add_argument('-p', default=0, type=int, help='Padding between pyramid items', dest='padding')
    parser.add_argument('-l', default=1, type=int, help='Output image size alignment (just in case)', dest='align')
    parser.add_argument('-b', default=0, type=int, help='Adds outer border', dest='border')
    parser.add_argument('-h', action='store_true', help='Shows this help', dest='help')
    options = parser.parse_args()

    # Check if help called.
    if options.help or options.input == '':
        parser.print_help()
        sys.exit(0)

    # Check attributes.
    if not os.path.exists(options.input):
        print('Input file', options.input, 'does not exist!')
        sys.exit(1)
    output_image = os.path.abspath(options.output)
    output_folder = os.path.dirname(output_image)
    if not os.path.exists(output_folder):
        print('Output folder', options.output, 'does not exist!')
        sys.exit(1)
    if (options.alpha <= 0) or (options.alpha >= 1):
        print('Parameter alpha =', options.alpha, 'is out of range (should be in [0, 1])!')
        sys.exit(1)
    if options.stop_dim <= 0:
        print('Parameter stopdim =', options.stop, 'is out of range (should be strictly positive)!')
        sys.exit(1)
    if options.align < 0:
        print('Parameter align =', options.align, 'is out of range (should be strictly positive)!')
        sys.exit(1)
    if options.border < 0:
        print('Parameter border =', options.align, 'is out of range (should be nonnegative)!')
        sys.exit(1)

    # Do necessary work.
    try:
        input_im = Image.open(options.input)
        alpha = options.alpha
        stop_dim = options.stop_dim
        padding = options.padding
        align = options.align
        border = options.border
        mosaic, r = pack(input_im, alpha, stop_dim, padding, align, border)
        print('Mosaic image generated, size:', mosaic.size)
        print('Utilization ratio:', r)
        mosaic.save(output_image)
        print('Mosaic saved to', output_image)
    except Exception as error:
        print('Error in pyramidr.py:', error)
        sys.exit(1)
