import sys

from PIL import Image
import freetype

from animation.abstract import AbstractAnimation
import numpy as np


class TextAnimation(AbstractAnimation):
    def __init__(self,  width, height, frame_queue, repeat, text,
                 steps_per_second=15, pixels_per_step=1, text_size=13,
                 emoji_size=109,
                 text_font="resources/fonts/LiberationSans-Regular_2.1.2.ttf",
                 emoji_font="resources/fonts/joypixels-android_6.0.0.ttf"):
        super().__init__(width, height, frame_queue, repeat)

        self.name = "text"
        self.text = text
        self.text_size = text_size
        self.emoji_size = emoji_size
        self.steps_per_second = steps_per_second
        self.pixels_per_step = pixels_per_step

        self.text_face = freetype.Face(text_font)
        self.emoji_face = freetype.Face(emoji_font)

        self.text_face.set_char_size(self.text_size * 64)
        self.emoji_face.set_char_size(self.emoji_size * 64)
        np.set_printoptions(threshold=sys.maxsize, linewidth=300)

    def __del__(self):
        del self.text_face
        del self.emoji_face

    def render(self, text):
        xmin, xmax = 0, 0
        ymin, ymax = 0, 0
        previous = 0
        pen_x, pen_y = 0, 0
        # first pass
        for c in text:
            if self.text_face.get_char_index(c):
                self.text_face.load_char(c, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
                kerning = self.text_face.get_kerning(previous, c)
                previous = c
                bitmap = self.text_face.glyph.bitmap
                width = self.text_face.glyph.bitmap.width
                rows = self.text_face.glyph.bitmap.rows
                top = self.text_face.glyph.bitmap_top
                left = self.text_face.glyph.bitmap_left
                pen_x += (kerning.x >> 6)
                x0 = pen_x + left
                x1 = x0 + width
                y0 = pen_y - (rows - top)
                y1 = y0 + rows
                xmin, xmax = min(xmin, x0),  max(xmax, x1)
                ymin, ymax = min(ymin, y0), max(ymax, y1)
                pen_x += (self.text_face.glyph.advance.x >> 6)
                pen_y += (self.text_face.glyph.advance.y >> 6)
                # print(("char: {} width: {} rows: {} top: {} left: {} "
                #        "kernx: {} xmin: {} xmax: {} ymin: {} ymax: {} "
                #        "pen_x: {} pen_y {}").format(c, width, rows, top, left,
                #                                     (kerning.x >> 6), xmin, xmax, ymin, ymax,
                #                                     pen_x, pen_y))
            elif self.emoji_face.get_char_index(c):
                kerning = 0
                previous = 0
                width = self.text_size
                rows = self.text_size
                top = self.text_size - 3
                left = 0
                pen_x += kerning
                x0 = pen_x + left
                x1 = x0 + width
                y0 = pen_y - (rows - top)
                y1 = y0 + rows
                xmin, xmax = min(xmin, x0),  max(xmax, x1)
                ymin, ymax = min(ymin, y0), max(ymax, y1)
                pen_x += self.text_size

        L = np.zeros((ymax-ymin, xmax-xmin, 3), dtype=np.uint8)

        # second pass
        previous = 0
        pen_x, pen_y = 0, 0
        for c in text:
            if self.text_face.get_char_index(c):
                self.text_face.load_char(c,
                                         freetype.FT_LOAD_RENDER |
                                         freetype.FT_LOAD_TARGET_MONO)
                kerning = self.text_face.get_kerning(previous, c)
                previous = c
                bitmap = self.text_face.glyph.bitmap
                width = self.text_face.glyph.bitmap.width
                rows = self.text_face.glyph.bitmap.rows
                top = self.text_face.glyph.bitmap_top
                left = self.text_face.glyph.bitmap_left
                pen_x += (kerning.x >> 6)
                x = pen_x - xmin + left
                y = pen_y - ymin - (rows - top)
                Z = self.unpack_mono_bitmap(bitmap)
                # Z = np.array(bitmap.buffer, dtype=np.uint8).reshape(rows,
                #                                                     width)
                Z = np.repeat(Z, 3, axis=1).reshape(rows, width, 3)
                L[y:y+rows, x:x+width] |= Z[::-1, ::1]

                pen_x += (self.text_face.glyph.advance.x >> 6)
                pen_y += (self.text_face.glyph.advance.y >> 6)
            elif self.emoji_face.get_char_index(c):
                kerning = 0
                previous = 0
                width = self.text_size
                rows = self.text_size
                top = self.text_size - 3
                left = 0
                pen_x += kerning
                x = pen_x - xmin + left
                y = pen_y - ymin - (rows - top)
                Z = self.get_color_char(c)
                L[y:y+rows, x:x+width] |= Z[::-1, ::1]
                pen_x += self.text_size
        return L[::-1, ::1]

    @staticmethod
    def unpack_mono_bitmap(bitmap):
        data = bytearray(bitmap.rows * bitmap.width)

        for y in range(bitmap.rows):
            for byte_index in range(bitmap.pitch):
                byte_value = bitmap.buffer[y * bitmap.pitch + byte_index]
                num_bits_done = byte_index * 8
                rowstart = y * bitmap.width + byte_index * 8
                for bit_index in range(min(8, bitmap.width - num_bits_done)):
                    bit = byte_value & (1 << (7 - bit_index))
                    data[rowstart + bit_index] = 255 if bit else 0
        return np.array(data).reshape(bitmap.rows, bitmap.width)

    def get_color_char(self, char):
        self.emoji_face.load_char(char, freetype.FT_LOAD_COLOR)
        bitmap = self.emoji_face.glyph.bitmap
        bitmap = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows,
                                                                  bitmap.width,
                                                                  4))
        rgb = self.convert_bgra_to_rgb(bitmap)
        im = Image.fromarray(rgb)
        # image offset
        im = im.crop((0, 4, im.width, im.height))
        im = im.resize((self.text_size, self.text_size))
        return np.array(im)

    def convert_bgra_to_rgb(self, buf):
        blue = buf[:, :, 0]
        green = buf[:, :, 1]
        red = buf[:, :, 2]
        return np.dstack((red, green, blue))

    def animate(self):
        if not self._stop_event.is_set():
            if self.steps_per_second <= 0 or self.pixels_per_step < 1:
                return
            buf = self.render(self.text)
            height, _width, _nbytes = buf.shape
            h_pad_0 = self.height
            h_pad_1 = self.width + self.pixels_per_step
            v_pad_0 = 0
            v_pad_1 = 0
            if height < self.height:
                v_pad_0 = int((self.height - height)/2)
                v_pad_1 = self.height - height - v_pad_0

            buf = np.pad(buf, ((v_pad_0, v_pad_1), (h_pad_0, h_pad_1), (0, 0)),
                         'constant', constant_values=0)
            wait = 1.0 / self.steps_per_second

            for i in range(0, buf.shape[1] - self.width, self.pixels_per_step):
                if self._stop_event.is_set():
                    break
                cut = buf[0:self.height, i:i+self.width, :]
                self.frame_queue.put(cut.copy())
                self._stop_event.wait(timeout=wait)

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat,
                "text": self.text, "steps_per_second": self.steps_per_second,
                "pixels_per_step": self.pixels_per_step,
                "text_size": self.text_size, "emoji_size": self.emoji_size,
                "text_font": self.text_font, "emoji_font": self.emoji_font}
