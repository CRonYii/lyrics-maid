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
    if not directory.exists():
        logger.fatal("Aborted: Invalid directory '%s'" % (directory.absolute()))
        exit(-1)
    # Initialize fetcher and load providers
    lyrics_fetcher = LyricsFetcher(skips=args.skip, overwrite=args.force)
    # TODO: load from config
    lyrics_fetcher.providers.append(
        SyncedLyricsProvider(),
    )

    lyrics_fetcher.fetch_directory(directory)


class LyricsFetcher:

    def generate_song_serch_params(song: mutagen.File):
        if "title" in song and "artist" in song:
            yield "%s %s" % (song["title"][0], song["artist"][0])
        if "title" in song and "album" in song:
            yield "%s %s" % (song["title"][0], song["album"][0])
        # TODO: this should be asked to be saved or not
        # if "title" in song:
        #     yield song["title"][0]

    def __init__(self, skips: List[str], overwrite=False):
        self.providers: List[LyricsProvider] = []
        self.skips = skips
        self.overwrite = overwrite

    def fetch_directory(self, directory):
        directory = os.path.join(directory, "**", "*")
        files = glob.glob(directory, recursive=True)
        for file in files:
            if self.skip_file(file):
                continue
            song = mutagen.File(file, easy=True)
            if not song:
                continue
            self.fetch_song(file, song)

    def fetch_song(self, file, song: mutagen.File):
        filename, _ = os.path.splitext(file)
        lrc = None
        for query in LyricsFetcher.generate_song_serch_params(song):
            for provider in self.providers:
                try:
                    lrc = provider.serach(query)
                    if lrc:
                        break
                except Exception as e:
                    logger.warn(
                        "[%s] encountered exception when search %s: %s"
                        % (provider, query, e)
                    )
                    continue
            if lrc:
                break
        if not lrc:
            return
        self.save_lyric_file(filename, lrc)

    def skip_file(self, file: str):
        if not Path(file).is_file():
            return True
        file = file.lower()
        for skip in self.skips:
            if skip in file:
                return True
        if not self.overwrite:
            filename, _ = os.path.splitext(file)
            # check if lyric already exists for this song
            if Path(filename + ".lrc").exists():
                return True
        return False

    def save_lyric_file(self, path, lrc):
        [ext, lrc] = lrc
        save_path = path + ext
        if not self.overwrite:
            if Path(save_path).exists():
                return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(lrc)
            logger.info("Saved lyric for '%s'" % os.path.basename(save_path))
        except Exception as e:
            logger.error(
                "Failed to save lyric for '%s': %s" % (os.path.basename(save_path), e)
            )


class LyricsProvider:

    LRC = ".lrc"
    TXT = ".txt"

    def serach(self, query: str):
        raise NotImplementedError()

    def __repr__(self) -> str:
        return "unknown provider"


class SyncedLyricsProvider(LyricsProvider):

    def __init__(
        self,
        allow_plain_format=True,
        providers=["NetEase", "Lrclib", "Musixmatch"],
    ):
        self.allow_plain_format = allow_plain_format
        self.providers = providers

    def serach(self, query: str):
        lrc = None
        for provider in self.providers:
            logger.debug(
                "[syncedlyrics]: Searching for lyrics for '%s' on '%s'"
                % (query, provider)
            )
            try:
                lrc = syncedlyrics.search(
                    query,
                    allow_plain_format=self.allow_plain_format,
                    save_path=None,
                    providers=[provider],
                )
                if lrc:
                    break
            except Exception as e:
                logger.warn(
                    "[syncedlyrics] encountered exception when search '%s' on '%s': %s"
                    % (query, provider, e)
                )
                continue
        if not lrc:
            return None
        ext = (
            LyricsProvider.LRC if syncedlyrics.is_lrc_valid(lrc) else LyricsProvider.TXT
        )
        return [ext, lrc]

    def __repr__(self) -> str:
        return "syncedlyrics"
