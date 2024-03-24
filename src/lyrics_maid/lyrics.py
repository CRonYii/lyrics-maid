import glob
import os
from pathlib import Path
from typing import List

import mutagen
import syncedlyrics

from .log import logger


# TODO multi-threading
def fetch_lyrics(args):
    directory: Path = args.directory
    skips: List[str] = args.skip
    if not args.directory.exists():
        logger.fatal("Aborted: Invalid directory '%s'" % (directory.absolute()))
        exit(-1)
    path = os.path.join(directory, "**", "*")
    files = glob.glob(path, recursive=True)
    for file in files:
        if skip_file(skips, file):
            continue
        song = mutagen.File(file, easy=True)
        if not song:
            continue
        fetch_lyric(file, song, args.force)


def skip_file(skips: List[str], file: str):
    if not Path(file).is_file():
        return True
    file = file.lower()
    for skip in skips:
        if skip in file:
            return True
    return False


def generate_song_serch_params(song: mutagen.File):
    if "title" in song and "artist" in song:
        yield "%s %s" % (song["title"][0], song["artist"][0])
    if "title" in song and "album" in song:
        yield "%s %s" % (song["title"][0], song["album"][0])
    if "title" in song:
        yield song["title"][0]


def save_lyric_file(path, lrc, force=False):
    ext = ".lrc" if syncedlyrics.is_lrc_valid(lrc) else ".txt"
    save_path = path + ext
    if not force:
        if Path(save_path).exists():
            return
    try:
        syncedlyrics.save_lrc_file(save_path, lrc)
        logger.info("Saved lyric for '%s'" % os.path.basename(save_path))
    except Exception as e:
        logger.error(
            "Failed to save lyric for '%s': %s" % (os.path.basename(save_path), e)
        )


def fetch_lyric(file, song: mutagen.File, force=False):
    filename, _ = os.path.splitext(file)
    if not force:
        # check if lyric already exists for this song
        if Path(filename + ".lrc").exists():
            return
    lrc = None
    for query in generate_song_serch_params(song):
        # TODO make each lyric source as a plugin
        logger.debug("Searching for lyrics for '%s'" % query)
        try:
            lrc = syncedlyrics.search(
                query,
                allow_plain_format=True,
                save_path=None,
                providers=["NetEase", "Lrclib", "Musixmatch"],
            )
        except Exception as e:
            logger.warn(
                "syncedlyrics encountered exception when search %s: %s" % (query, e)
            )
            continue
        if lrc:
            break
    if not lrc:
        return
    save_lyric_file(filename, lrc, force)
