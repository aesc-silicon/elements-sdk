"""Script to generate a boundground.h file with arrays of PIXEL(x, y) for red, green, blue
and grey colors from an image. These arrays can be used to draw images/fonts in the
framebuffer."""
#!/usr/bin/env python3

import sys
import os
from PIL import Image

def write_color(file_, color, data):
    """Writes the array of pixels for one color to the files."""
    if not data:
        return
    file_.write("\n")
    file_.write("#define\t{}_PIXELS\t{}\n\n".format(color.upper(), len(data)))
    file_.write("unsigned short {}_pixel[{}_PIXELS] = {{\n".format(color, color.upper()))
    for index in range(0, len(data) - 1):
        file_.write("\tPIXEL({}, {}),\n".format(*data[index]))
    file_.write("\tPIXEL({}, {})\n".format(*data[len(data) - 1]))
    file_.write("};\n\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: {} [image name]".format(sys.argv[0]))
        sys.exit(-1)

    im = Image.open(sys.argv[1])
    pix = im.load()

    red = []
    green = []
    blue = []
    grey = []

    filename = os.path.splitext(sys.argv[1])[0]
    f = open("{}.h".format(filename), "w+")
    f.write("#ifndef BACKGROUND_H\n")
    f.write("#define BACKGROUND_H\n")

    for y in range(0, im.size[1]):
        for x in range(0, im.size[0]):
            r, g, b, a = pix[x, y]
            if r == 255 and g == 0 and b == 0:
                red.append((x, y))
            if r == 0 and g == 255 and b == 0:
                green.append((x, y))
            if r == 0 and g == 0 and b == 255:
                blue.append((x, y))
            if r == 128 and g == 128 and b == 128:
                grey.append((x, y))

    write_color(f, "red", red)
    write_color(f, "green", green)
    write_color(f, "blue", blue)
    write_color(f, "grey", grey)

    f.write("#endif /* BACKGROUND_H */\n")
    f.close()
