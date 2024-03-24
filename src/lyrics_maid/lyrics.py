import os
import time
from pathlib import Path
from typing import List

import mutagen
import syncedlyrics

from .log import logger
from .store import JSONStore


# TODO multi-threading
def fetch_lyrics(args):
    directory: Path = args.directory
    if not directory.exists():
        logger.fatal("Aborted: Invalid directory '%s'" % (directory.absolute()))
        exit(-1)
    # Initialize fetcher and load providers
    lyrics_fetcher = LyricsFetcher(
        skips=args.skip, overwrite=args.force, incremental=args.incremental
    )
    # TODO: load from config
    lyrics_fetcher.providers.append(
        SyncedLyricsProvider(
            providers=[
                SyncedLyricsProvider.NetEase(),
                SyncedLyricsProvider.LrcLib(),
                SyncedLyricsProvider.Musixmatch(),
            ]
        ),
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

    def __init__(self, skips: List[str], overwrite=False, incremental=False):
        self.providers: List[LyricsProvider] = []
        self.skips = skips
        self.overwrite = overwrite
        self.history_store = self.history_store = (
            JSONStore("history.json", table_version=1) if incremental else None
        )
        self.skipped_count = 0

    def fetch_directory(self, directory):
        self.__fetch_directory(directory)
        if self.skipped_count > 0:
            logger.info("[LyricsFetcher] skipped %d directories" % (self.skipped_count))

    def __fetch_directory(self, directory):
        directory = os.path.abspath(directory)
        # Skips previously searched directory
        if self.history_store:
            if self.history_store.get(directory):
                logger.debug("[LyricsFetcher] skipped '%s'" % (directory))
                self.skipped_count += 1
                return
        # Searches for songs under this directory
        for file in os.scandir(directory):
            if file.is_dir():
                self.__fetch_directory(file)
            elif file.is_file():
                if self.skip_file(file):
                    continue
                song = self.get_song_file(file)
                if not song:
                    continue
                self.fetch_song(file, song)
        # Now the search has completed for this entire directory, saves search historty
        if self.history_store:
            logger.debug("[LyricsFetcher] marked '%s' as searched" % (directory))
            self.history_store.set(directory, True)

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
                        "[LyricsFetcher] [%s] encountered exception when search %s: %s"
                        % (provider, query, e)
                    )
                    continue
            if lrc:
                break
        if not lrc:
            return
        self.save_lyric_file(filename, lrc)

    def get_song_file(self, file: str):
        song = mutagen.File(file, easy=True)
        if not song:
            return None
        for skip in self.skips:
            if "title" in song and skip in song["title"][0].lower():
                return None
            if "album" in song and skip in song["album"][0].lower():
                return None
        return song

    def skip_file(self, file: str):
        file = os.path.basename(file).lower()
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
            logger.info(
                "[LyricsFetcher] Saved lyric for '%s'" % os.path.basename(save_path)
            )
        except Exception as e:
            logger.error(
                "[LyricsFetcher] Failed to save lyric for '%s': %s"
                % (os.path.basename(save_path), e)
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
        providers=[],
    ):
        self.allow_plain_format = allow_plain_format
        self.providers: List[SyncedLyricsProvider.SyncedLyricsSubProvider] = providers

    class SyncedLyricsSubProvider:
        def search(self, query: str):
            raise NotImplementedError()

        def retry(self) -> bool:
            raise NotImplementedError()

        def __repr__(self) -> str:
            return "unknown provider"

    class NetEase:

        def __init__(self):
            from syncedlyrics import NetEase

            self.provider = NetEase()

        def search(self, query):
            lrc = self.provider.get_lrc(query)
            return lrc

        def retry(self):
            time.sleep(10)
            return True

        def __repr__(self) -> str:
            return "NetEase"

    class LrcLib:

        def __init__(self):
            from syncedlyrics import Lrclib

            self.provider = Lrclib()

        def search(self, query):
            lrc = self.provider.get_lrc(query)
            return lrc

        def retry(self):
            time.sleep(10)
            return True

        def __repr__(self) -> str:
            return "Lrclib"

    class Musixmatch:

        def __init__(self):
            from syncedlyrics import Musixmatch

            self.provider = Musixmatch()

        def search(self, query):
            lrc = self.provider.get_lrc(query)
            return lrc

        def retry(self):
            token_path = os.path.join(".syncedlyrics", "musixmatch_token.json")
            if os.path.exists(token_path):
                # Maybe the token needs to be renewed, removed the cached token
                try:
                    self.provider.token = None
                    os.remove(token_path)
                    time.sleep(10)
                    return True
                except:
                    pass
            return False

        def __repr__(self) -> str:
            return "Musixmatch"

    def serach(self, query: str):
        lrc = None
        i = 0
        can_retry = True
        # search through all providers
        while i < len(self.providers):
            provider = self.providers[i]
            i += 1
            logger.debug(
                "[syncedlyrics] [%s]: Searching for lyrics for '%s'" % (provider, query)
            )
            try:
                _l = provider.search(query)
                # search succeeded, reset retry
                can_retry = True
                # validate response
                if _l is None:
                    continue
                if syncedlyrics.is_lrc_valid(_l, self.allow_plain_format):
                    lrc = _l
                    break
            except Exception as e:
                logger.warn(
                    "[syncedlyrics] [%s] encountered exception when search '%s': %s"
                    % (provider, query, e)
                )
                if can_retry and provider.retry():
                    # go back to the current provider and try again
                    # retry and only retry once for each time
                    i -= 1
                    can_retry = False
                continue

        # Prepare the result
        if not lrc:
            return None
        ext = (
            LyricsProvider.LRC if syncedlyrics.is_lrc_valid(lrc) else LyricsProvider.TXT
        )
        return [ext, lrc]

    def __repr__(self) -> str:
        return "syncedlyrics"
