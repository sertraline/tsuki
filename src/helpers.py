import asyncio
import cv2
import math
import numpy as np
import os

from uuid import uuid4
from aiogram import types


def get_media_group(album):
    media_album = types.MediaGroup()
    for media in album:
        file_id, content_type, *caption = media
        media = {'media': file_id, 'type': content_type}
        media_album.attach(media)
    return media_album


async def get_photo_or_doc_or_reply(message):
    file_id = None

    if "photo" in message:
        file_id = message["photo"][-1]["file_id"]
    else:
        if "document" in message:
            file_id = message['document']['file_id']
        else:
            if "reply_to_message" in message:
                reply = message["reply_to_message"]
                if "photo" in reply:
                    file_id = reply["photo"][-1]["file_id"]
                else:
                    if "document" in reply:
                        file_id = reply["document"]["file_id"]
    return file_id


async def get_text_or_reply(message, cmd):
    suffix = 'pathselector_bot'
    text = message.text
    pos = text.find('/'+cmd)
    if pos != -1:
        text = text[pos+len(cmd)+1:]
    pos = text.find('@'+suffix)
    if pos != -1:
        text = text[pos+len(suffix)+1:]

    if not text:
        try:
            text = message["reply_to_message"]["text"]
        except:
            pass
    return text.strip()


async def get_doc_or_reply(message):
    file_id = None

    if "document" in message:
        file_id = message['document']['file_id']
    else:
        if "reply_to_message" in message:
            reply = message["reply_to_message"]
            if "document" in reply:
                file_id = reply["document"]["file_id"]
    return file_id


async def process_album(message, state, func):
    async with state.proxy() as data:
        if message.media_group_id not in data:
            asyncio.get_event_loop().call_later(0.5, asyncio.create_task,
                                                func(message, state))
        content_type = message.content_type
        file_id = await get_photo_or_doc_or_reply(message)

        if not file_id:
            return
        standard_values = {'album': []}
        media = (file_id, content_type)
        data._data.setdefault(message.media_group_id, standard_values)['album'].append(media)


async def check_if_not_album(message, state, kb):
    async with state.proxy() as data:
        if not message.document:
            if 'accepted' in data:
                return
            data['accepted'] = True
            await message.reply("Photo must be sent as document to avoid compression.")
            return
        try:
            album = data[message.media_group_id]['album']
            media_group = get_media_group(album)
            if media_group:
                return
        except KeyError:
            pass
    return True


async def download_by_id(message, dirname, image, bot):
    ext = ''
    if 'photo' in message:
        ext = 'jpg'
    elif 'document' in message:
        ext = message['document']['file_name'].split('.')[-1]
    elif 'reply_to_message' in message:
        if 'photo' in message['reply_to_message']:
            ext = 'jpg'
        elif 'document' in message['reply_to_message']:
            ext = message['reply_to_message']['document']['file_name'].split('.')[-1]

    name = os.path.join(dirname, str(uuid4()) + '.' + ext)
    if type(image) is not str:
        print('Downloading to %s' % name)
        await image.download(name)
    else:
        print("Downloading by id %s to %s" % (image, name))
        await bot.download_file_by_id(image, name)
    return image, name


async def get_photo(message, dirname, bot):
    image = await get_photo_or_doc_or_reply(message)
    if not image:
        return
    image, name = await download_by_id(message, dirname, image, bot)
    print('return', image, name)
    return image, name


async def get_document(message, dirname, bot):
    image = await get_doc_or_reply(message)
    if not image:
        return
    image, name = await download_by_id(message, dirname, image, bot)
    print('return', image, name)
    return image, name


def rotate_image(image, angle):
    image_size = (image.shape[1], image.shape[0])
    image_center = tuple(np.array(image_size) / 2)

    # Convert the OpenCV 3x2 rotation matrix to 3x3
    rot_mat = np.vstack(
        [cv2.getRotationMatrix2D(image_center, angle, 1.0), [0, 0, 1]]
    )

    rot_mat_notranslate = np.matrix(rot_mat[0:2, 0:2])

    # Shorthand for below calcs
    image_w2 = image_size[0] * 0.5
    image_h2 = image_size[1] * 0.5

    # Obtain the rotated coordinates of the image corners
    rotated_coords = [
        (np.array([
            -image_w2,  image_h2
        ]) * rot_mat_notranslate).A[0],
        (np.array([
            image_w2, image_h2
        ]) * rot_mat_notranslate).A[0],
        (np.array([
            -image_w2,-image_h2
        ]) * rot_mat_notranslate).A[0],
        (np.array([
            image_w2, -image_h2
        ]) * rot_mat_notranslate).A[0]
    ]

    # Find the size of the new image
    x_coords = [pt[0] for pt in rotated_coords]
    x_pos = [x for x in x_coords if x > 0]
    x_neg = [x for x in x_coords if x < 0]

    y_coords = [pt[1] for pt in rotated_coords]
    y_pos = [y for y in y_coords if y > 0]
    y_neg = [y for y in y_coords if y < 0]

    right_bound = max(x_pos)
    left_bound = min(x_neg)
    top_bound = max(y_pos)
    bot_bound = min(y_neg)

    new_w = int(abs(right_bound - left_bound))
    new_h = int(abs(top_bound - bot_bound))

    # We require a translation matrix to keep the image centred
    trans_mat = np.matrix([
        [1, 0, int(new_w * 0.5 - image_w2)],
        [0, 1, int(new_h * 0.5 - image_h2)],
        [0, 0, 1]
    ])
    affine_mat = (np.matrix(trans_mat) * np.matrix(rot_mat))[0:2, :]

    result = cv2.warpAffine(
        image,
        affine_mat,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR
    )

    return result


def largest_rotated_rect(w, h, angle):
    quadrant = int(math.floor(angle / (math.pi / 2))) & 3
    sign_alpha = angle if ((quadrant & 1) == 0) else math.pi - angle
    alpha = (sign_alpha % math.pi + math.pi) % math.pi

    bb_w = w * math.cos(alpha) + h * math.sin(alpha)
    bb_h = w * math.sin(alpha) + h * math.cos(alpha)

    gamma = math.atan2(bb_w, bb_w) if (w < h) else math.atan2(bb_w, bb_w)

    delta = math.pi - alpha - gamma

    length = h if (w < h) else w

    d = length * math.cos(alpha)
    a = d * math.sin(alpha) / math.sin(delta)

    y = a * math.cos(gamma)
    x = y * math.tan(gamma)

    return (
        bb_w - 2 * x,
        bb_h - 2 * y
    )


def crop_around_center(image, width, height):
    image_size = (image.shape[1], image.shape[0])
    image_center = (int(image_size[0] * 0.5), int(image_size[1] * 0.5))

    if width > image_size[0]:
        width = image_size[0]

    if height > image_size[1]:
        height = image_size[1]

    x1 = int(image_center[0] - width * 0.5)
    x2 = int(image_center[0] + width * 0.5)
    y1 = int(image_center[1] - height * 0.5)
    y2 = int(image_center[1] + height * 0.5)

    return image[y1:y2, x1:x2]


def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array(
        [((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]
    ).astype("uint8")
    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


def overlay_transparent(background, overlay, x, y):

    background_width = background.shape[1]
    background_height = background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype = overlay.dtype) * 255
            ],
            axis = 2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

    return background
